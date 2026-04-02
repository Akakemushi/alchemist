import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Case, Count, IntegerField, OuterRef, Q, Subquery, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from characters.models import Character
from knowledge.models import CharacterReagentKnowledge

from .forms import (
    CampaignCreateForm,
    CampaignJoinForm,
    CampaignManageForm,
    CampaignSearchForm,
    ExpeditionFilterForm,
    ExpeditionForm,
    GMExpeditionForm,
    LabTimeForm,
    TransferOwnershipForm,
    _name_taken_for_owner,
)
from .models import ApprovalStatus, Campaign, CampaignBan, CampaignMembership, Expedition, GameRole, Participation
from .signals import _resolve_slug_for_no_campaign


@login_required
def campaign_list(request):
    memberships = (
        CampaignMembership.objects
        .filter(user=request.user)
        .select_related('campaign', 'campaign__created_by')
        .order_by('-campaign__created_at')
    )
    return render(request, 'campaigns/campaign_list.html', {'memberships': memberships})


@login_required
def campaign_create(request):
    if request.method == 'POST':
        form = CampaignCreateForm(request.POST, user=request.user)
        if form.is_valid():
            raw_password = form.cleaned_data.get('password') or None
            campaign = Campaign(
                name=form.cleaned_data['name'],
                created_by=request.user,
                billing_owner=request.user,
                password=make_password(raw_password) if raw_password else None,
            )
            campaign.save()
            CampaignMembership.objects.create(
                user=request.user,
                campaign=campaign,
                role=form.cleaned_data['role'],
                is_owner=True,
            )
            messages.success(request, f'Campaign "{campaign.name}" created.')
            return redirect('campaign_list')
    else:
        form = CampaignCreateForm(user=request.user)
    return render(request, 'campaigns/campaign_create.html', {'form': form})


@login_required
def campaign_search(request):
    form = CampaignSearchForm(request.GET or None)
    results = []
    searched = False

    if form.is_valid():
        q = form.cleaned_data.get('q', '').strip()
        if q:
            searched = True
            already_member_ids = CampaignMembership.objects.filter(
                user=request.user
            ).values_list('campaign_id', flat=True)
            results = Campaign.objects.filter(
                name__icontains=q
            ).exclude(id__in=already_member_ids).select_related('created_by')

    return render(request, 'campaigns/campaign_search.html', {
        'form': form,
        'results': results,
        'searched': searched,
    })


@login_required
def campaign_join(request, slug):
    campaign = get_object_or_404(Campaign, slug=slug)

    if CampaignMembership.objects.filter(user=request.user, campaign=campaign).exists():
        messages.info(request, f'You are already a member of "{campaign.name}".')
        return redirect('campaign_list')

    if CampaignBan.objects.filter(campaign=campaign, user=request.user).exists():
        messages.error(request, f'You have been banned from "{campaign.name}".')
        return redirect('campaign_list')

    if request.method == 'POST':
        form = CampaignJoinForm(request.POST)
        if form.is_valid():
            if campaign.password:
                submitted = form.cleaned_data.get('password', '')
                if not check_password(submitted, campaign.password):
                    form.add_error('password', 'Incorrect password.')
                else:
                    _join(request, campaign)
                    return redirect('campaign_list')
            else:
                _join(request, campaign)
                return redirect('campaign_list')
    else:
        form = CampaignJoinForm()

    return render(request, 'campaigns/campaign_join.html', {
        'campaign': campaign,
        'form': form,
        'has_password': bool(campaign.password),
    })


def _join(request, campaign):
    CampaignMembership.objects.create(
        user=request.user,
        campaign=campaign,
        role=GameRole.PLAYER,
        is_owner=False,
    )
    messages.success(request, f'You have joined "{campaign.name}" as a Player.')


@login_required
def campaign_manage(request, slug):
    campaign = get_object_or_404(Campaign, slug=slug)
    membership = get_object_or_404(CampaignMembership, campaign=campaign, user=request.user)
    if not membership.is_owner and membership.role != GameRole.GM:
        from django.http import Http404
        raise Http404

    manage_form = CampaignManageForm(instance=campaign, user=request.user)
    other_members = CampaignMembership.objects.filter(
        campaign=campaign
    ).exclude(user=request.user).select_related('user')
    transfer_form = TransferOwnershipForm(campaign=campaign, current_user=request.user)
    campaign_characters = Character.objects.filter(campaign=campaign).select_related('owner')
    banned_users = CampaignBan.objects.filter(campaign=campaign).select_related('user').order_by('banned_at')

    if request.method == 'POST':
        action = request.POST.get('action')

        _owner_only = {'update', 'transfer', 'toggle_role', 'kick_member', 'delete', 'ban', 'unban'}
        if action in _owner_only and not membership.is_owner:
            messages.error(request, 'Only the campaign owner can perform that action.')
            return redirect('campaign_manage', slug=campaign.slug)

        if action == 'update':
            manage_form = CampaignManageForm(request.POST, instance=campaign, user=request.user)
            if manage_form.is_valid():
                campaign = manage_form.save(commit=False)
                if manage_form.cleaned_data.get('clear_password'):
                    campaign.password = None
                elif manage_form.cleaned_data.get('new_password'):
                    campaign.password = make_password(manage_form.cleaned_data['new_password'])
                campaign.save()
                messages.success(request, 'Campaign updated.')
                return redirect('campaign_manage', slug=campaign.slug)

        elif action == 'transfer':
            transfer_form = TransferOwnershipForm(
                campaign=campaign, current_user=request.user, data=request.POST
            )
            if transfer_form.is_valid():
                new_membership = transfer_form.cleaned_data['new_owner']
                new_owner = new_membership.user
                if _name_taken_for_owner(campaign.name, new_owner):
                    transfer_form.add_error(
                        'new_owner',
                        f'{new_owner.username} already owns a campaign named "{campaign.name}". '
                        'They must rename or delete it before taking ownership of this one.',
                    )
                else:
                    membership.is_owner = False
                    membership.save()
                    new_membership.is_owner = True
                    new_membership.save()
                    campaign.billing_owner = new_owner
                    campaign.save()
                    messages.success(
                        request,
                        f'Ownership of "{campaign.name}" transferred to {new_owner.username}.',
                    )
                    return redirect('campaign_list')

        elif action == 'toggle_role':
            mid = request.POST.get('membership_id')
            target = get_object_or_404(CampaignMembership, id=mid, campaign=campaign)
            if target.user != request.user:
                target.role = GameRole.PLAYER if target.role == GameRole.GM else GameRole.GM
                target.save()
                messages.success(request, f'{target.user.username} is now a {target.get_role_display()}.')
            return redirect('campaign_manage', slug=campaign.slug)

        elif action == 'kick_member':
            mid = request.POST.get('membership_id')
            target = get_object_or_404(CampaignMembership, id=mid, campaign=campaign)
            if not target.is_owner:
                username = target.user.username
                target.delete()
                messages.success(request, f'{username} has been removed from the campaign.')
            return redirect('campaign_manage', slug=campaign.slug)

        elif action == 'ban':
            mid = request.POST.get('membership_id')
            target = get_object_or_404(CampaignMembership, id=mid, campaign=campaign)
            if not target.is_owner:
                user_to_ban = target.user
                CampaignBan.objects.get_or_create(campaign=campaign, user=user_to_ban)
                target.delete()
                messages.success(request, f'{user_to_ban.username} has been banned from the campaign.')
            return redirect('campaign_manage', slug=campaign.slug)

        elif action == 'unban':
            ban_id = request.POST.get('ban_id')
            ban = get_object_or_404(CampaignBan, id=ban_id, campaign=campaign)
            username = ban.user.username
            ban.delete()
            messages.success(request, f'{username} has been unbanned.')
            return redirect('campaign_manage', slug=campaign.slug)

        elif action == 'kick_character':
            char_id = request.POST.get('character_id')
            character = get_object_or_404(Character, id=char_id, campaign=campaign)
            _resolve_slug_for_no_campaign(character)
            character.campaign = None
            character.is_locked = False
            character.save(update_fields=['slug', 'campaign', 'is_locked'])
            messages.success(request, f'"{character.name}" has been removed from the campaign.')
            return redirect('campaign_manage', slug=campaign.slug)

        elif action == 'delete':
            name = campaign.name
            campaign.delete()
            messages.success(request, f'Campaign "{name}" has been deleted.')
            return redirect('campaign_list')

        elif action == 'lock_character':
            char_id = request.POST.get('character_id')
            character = get_object_or_404(Character, id=char_id, campaign=campaign)
            character.is_locked = True
            character.save(update_fields=['is_locked'])
            messages.success(request, f'"{character.name}" has been locked.')
            return redirect('campaign_manage', slug=campaign.slug)

        elif action == 'unlock_character':
            char_id = request.POST.get('character_id')
            character = get_object_or_404(Character, id=char_id, campaign=campaign)
            character.is_locked = False
            character.save(update_fields=['is_locked'])
            messages.success(request, f'"{character.name}" has been unlocked.')
            return redirect('campaign_manage', slug=campaign.slug)

        elif action == 'lock_all':
            Character.objects.filter(campaign=campaign).update(is_locked=True)
            messages.success(request, 'All characters locked.')
            return redirect('campaign_manage', slug=campaign.slug)

        elif action == 'unlock_all':
            Character.objects.filter(campaign=campaign).update(is_locked=False)
            messages.success(request, 'All characters unlocked.')
            return redirect('campaign_manage', slug=campaign.slug)

    return render(request, 'campaigns/campaign_manage.html', {
        'campaign': campaign,
        'manage_form': manage_form,
        'transfer_form': transfer_form,
        'other_members': other_members,
        'banned_users': banned_users,
        'campaign_characters': campaign_characters,
        'has_password': bool(campaign.password),
        'is_owner': membership.is_owner,
    })


@login_required
def campaign_enter(request, slug):
    campaign = get_object_or_404(Campaign, slug=slug)
    membership = get_object_or_404(CampaignMembership, campaign=campaign, user=request.user)
    can_be_gm = membership.is_owner or membership.role == GameRole.GM
    characters = Character.objects.filter(campaign=campaign, owner=request.user)

    if can_be_gm:
        # Always show selection screen so the GM can choose their hat
        return render(request, 'campaigns/campaign_enter.html', {
            'campaign': campaign,
            'characters': characters,
            'can_be_gm': True,
        })

    # Player path
    if not characters.exists():
        messages.error(
            request,
            f'You have no characters in "{campaign.name}". '
            'Add a character to this campaign first.',
        )
        return redirect('campaign_list')
    if characters.count() == 1:
        return redirect('campaign_play', slug=campaign.slug, character_id=characters.first().id)
    return render(request, 'campaigns/campaign_enter.html', {
        'campaign': campaign,
        'characters': characters,
        'can_be_gm': False,
    })


@login_required
def campaign_play(request, slug, character_id):
    campaign = get_object_or_404(Campaign, slug=slug)
    membership = get_object_or_404(CampaignMembership, campaign=campaign, user=request.user)
    character = get_object_or_404(Character, id=character_id, campaign=campaign, owner=request.user)

    form = ExpeditionForm(campaign=campaign, leader=character)

    # Pre-fill form when ?repeat=<id> is present
    repeat_id = request.GET.get('repeat')
    if repeat_id and request.method == 'GET':
        try:
            repeat_exp = (
                Expedition.objects
                .prefetch_related('participants')
                .get(id=repeat_id, campaign=campaign)
            )
            involved = (
                repeat_exp.leader_id == character.pk or
                repeat_exp.participants.filter(character=character).exists()
            )
            if involved:
                form = ExpeditionForm(campaign=campaign, leader=character, initial={
                    'biome': repeat_exp.biome_id,
                    'target_reagent': repeat_exp.target_reagent_id,
                    'search_mode': repeat_exp.search_mode,
                    'search_speed': repeat_exp.search_speed,
                    'search_at_night': repeat_exp.search_at_night,
                    'hours': repeat_exp.hours,
                    'participants': list(
                        repeat_exp.participants.values_list('character_id', flat=True)
                    ),
                })
        except Expedition.DoesNotExist:
            pass

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'new_expedition':
            form = ExpeditionForm(request.POST, campaign=campaign, leader=character)
            if form.is_valid():
                try:
                    expedition = form.save(commit=False)
                    expedition.campaign = campaign
                    expedition.leader = character
                    expedition.approval_status = ApprovalStatus.PENDING
                    with transaction.atomic():
                        expedition.save()
                        for participant_char in form.cleaned_data.get('participants', []):
                            Participation.objects.create(
                                expedition=expedition, character=participant_char
                            )
                    messages.success(request, 'Expedition plan submitted to the GM for approval.')
                    return redirect('campaign_play', slug=campaign.slug, character_id=character.id)
                except ValidationError as e:
                    form.add_error(None, e)

        elif action == 'cancel_expedition':
            exp_id = request.POST.get('expedition_id')
            expedition = get_object_or_404(Expedition, id=exp_id, campaign=campaign)
            if expedition.leader == character:
                expedition.delete()
                messages.success(request, 'Expedition cancelled.')
            return redirect('campaign_play', slug=campaign.slug, character_id=character.id)

        elif action == 'go':
            exp_id = request.POST.get('expedition_id')
            expedition = get_object_or_404(
                Expedition.objects.select_related(
                    'biome', 'target_reagent', 'leader'
                ).prefetch_related('participants__character'),
                id=exp_id, campaign=campaign,
            )
            if (expedition.leader == character and
                    expedition.approval_status == ApprovalStatus.APPROVED):
                expedition.approval_status = ApprovalStatus.EXECUTED
                expedition.executed_at = timezone.now()
                expedition.save()
                from .expedition_engine import run_expedition
                found_counts = run_expedition(expedition)
                total_found = sum(c for _, c in found_counts.values())
                messages.success(
                    request,
                    f'Expedition complete! {total_found} item(s) added to inventory.'
                )
                return redirect(
                    'expedition_detail',
                    slug=campaign.slug,
                    character_id=character.id,
                    expedition_id=expedition.id,
                )
            return redirect('campaign_play', slug=campaign.slug, character_id=character.id)

    _participant_count_sq = (
        Participation.objects
        .filter(expedition=OuterRef('pk'))
        .values('expedition')
        .annotate(cnt=Count('pk'))
        .values('cnt')
    )
    expeditions = (
        Expedition.objects
        .filter(Q(leader=character) | Q(participants__character=character))
        .distinct()
        .select_related('biome', 'target_reagent')
        .annotate(participant_count=Subquery(_participant_count_sq))
        .order_by('-created_at')
    )

    return render(request, 'campaigns/campaign_play.html', {
        'campaign': campaign,
        'character': character,
        'membership': membership,
        'form': form,
        'expeditions': expeditions,
        'ApprovalStatus': ApprovalStatus,
    })


@login_required
def expedition_detail(request, slug, character_id, expedition_id):
    campaign = get_object_or_404(Campaign, slug=slug)
    membership = get_object_or_404(CampaignMembership, campaign=campaign, user=request.user)
    character = get_object_or_404(Character, id=character_id, campaign=campaign, owner=request.user)
    expedition = get_object_or_404(
        Expedition.objects.select_related('biome', 'target_reagent', 'leader'),
        id=expedition_id, campaign=campaign,
    )

    is_leader = expedition.leader_id == character.pk
    is_participant = expedition.participants.filter(character=character).exists()
    if not (is_leader or is_participant):
        raise Http404

    participants = expedition.participants.select_related('character', 'character__owner')

    # Results: what this character found on the expedition.
    # For split-up expeditions the player only sees their own finds; for
    # together expeditions they see everything found by the whole party.
    from campaigns.models import SearchMode
    from inventory.models import ReagentSample
    from knowledge.models import CharacterReagentKnowledge
    if expedition.search_mode == SearchMode.SPLITUP:
        found_samples = (
            ReagentSample.objects
            .filter(source_expedition=expedition, inventory_entry__character=character)
            .select_related('true_reagent', 'inventory_entry')
        )
    else:
        found_samples = (
            ReagentSample.objects
            .filter(source_expedition=expedition)
            .select_related('true_reagent', 'inventory_entry__character')
            .order_by('inventory_entry__character__name')
        )

    known_reagent_ids = set(
        CharacterReagentKnowledge.objects
        .filter(character=character, knows_name=True)
        .values_list('reagent_id', flat=True)
    )

    return render(request, 'campaigns/expedition_detail.html', {
        'campaign': campaign,
        'character': character,
        'membership': membership,
        'expedition': expedition,
        'is_leader': is_leader,
        'participants': participants,
        'found_samples': found_samples,
        'known_reagent_ids': known_reagent_ids,
        'SearchMode': SearchMode,
    })


# ── GM views ────────────────────────────────────────────────────────────────


def _fmt_lab_time(minutes):
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    return f"{h}h" if h else f"{m}m"


def _gm_required(request, campaign):
    """Returns membership if user is a GM/owner, raises Http404 otherwise."""
    membership = get_object_or_404(CampaignMembership, campaign=campaign, user=request.user)
    if not (membership.is_owner or membership.role == GameRole.GM):
        raise Http404
    return membership


@login_required
def campaign_gm(request, slug):
    campaign = get_object_or_404(Campaign, slug=slug)
    membership = _gm_required(request, campaign)

    # ── Lab time form (default empty; replaced on failed submission) ────────
    lab_time_form = LabTimeForm(campaign=campaign)

    # ── Expedition creation form ────────────────────────────────
    form = GMExpeditionForm(campaign=campaign)

    repeat_id = request.GET.get('repeat')
    if repeat_id and request.method == 'GET':
        try:
            repeat_exp = (
                Expedition.objects
                .prefetch_related('participants')
                .get(id=repeat_id, campaign=campaign)
            )
            form = GMExpeditionForm(campaign=campaign, initial={
                'leader':          repeat_exp.leader_id,
                'biome':           repeat_exp.biome_id,
                'target_reagent':  repeat_exp.target_reagent_id,
                'search_mode':     repeat_exp.search_mode,
                'search_speed':    repeat_exp.search_speed,
                'search_at_night': repeat_exp.search_at_night,
                'hours':           repeat_exp.hours,
                'participants':    list(
                    repeat_exp.participants.values_list('character_id', flat=True)
                ),
            })
        except Expedition.DoesNotExist:
            pass

    # ── POST actions ────────────────────────────────────────────
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'new_expedition':
            form = GMExpeditionForm(request.POST, campaign=campaign)
            if form.is_valid():
                try:
                    expedition = form.save(commit=False)
                    expedition.campaign = campaign
                    expedition.approval_status = ApprovalStatus.PENDING
                    leader_char = expedition.leader
                    target_reagent = form.cleaned_data.get('target_reagent')
                    with transaction.atomic():
                        # Grant leader knowledge of the target reagent if missing
                        if target_reagent:
                            crk, created = CharacterReagentKnowledge.objects.get_or_create(
                                character=leader_char,
                                reagent=target_reagent,
                                defaults={'knows_name': True},
                            )
                            if not created and not crk.knows_name:
                                crk.knows_name = True
                                crk.save(update_fields=['knows_name'])
                        expedition.save()
                        for participant_char in form.cleaned_data.get('participants', []):
                            if participant_char.pk != leader_char.pk:
                                Participation.objects.create(
                                    expedition=expedition, character=participant_char
                                )
                    messages.success(request, 'Expedition created.')
                    return redirect('campaign_gm', slug=campaign.slug)
                except ValidationError as e:
                    form.add_error(None, e)

        elif action == 'approve':
            exp_id = request.POST.get('expedition_id')
            expedition = get_object_or_404(Expedition, id=exp_id, campaign=campaign)
            if expedition.approval_status == ApprovalStatus.PENDING:
                expedition.approval_status = ApprovalStatus.APPROVED
                expedition.approved_by = request.user
                expedition.approved_at = timezone.now()
                expedition.save()
                messages.success(request, 'Expedition approved.')
            return redirect('campaign_gm', slug=campaign.slug)

        elif action == 'deny':
            exp_id = request.POST.get('expedition_id')
            expedition = get_object_or_404(Expedition, id=exp_id, campaign=campaign)
            if expedition.approval_status == ApprovalStatus.PENDING:
                expedition.approval_status = ApprovalStatus.DENIED
                expedition.save()
                messages.success(request, 'Expedition denied.')
            return redirect('campaign_gm', slug=campaign.slug)

        elif action == 'gm_go':
            exp_id = request.POST.get('expedition_id')
            expedition = get_object_or_404(
                Expedition.objects.select_related(
                    'biome', 'target_reagent', 'leader'
                ).prefetch_related('participants__character'),
                id=exp_id, campaign=campaign,
            )
            if expedition.approval_status in (ApprovalStatus.PENDING, ApprovalStatus.APPROVED):
                if expedition.approval_status == ApprovalStatus.PENDING:
                    expedition.approved_by = request.user
                    expedition.approved_at = timezone.now()
                expedition.approval_status = ApprovalStatus.EXECUTED
                expedition.executed_at = timezone.now()
                expedition.save()
                from .expedition_engine import run_expedition
                found_counts = run_expedition(expedition)
                total_found = sum(c for _, c in found_counts.values())
                messages.success(
                    request,
                    f'Expedition complete! {total_found} item(s) found across all characters.'
                )
                return redirect('gm_expedition_detail', slug=campaign.slug, expedition_id=expedition.id)
            return redirect('campaign_gm', slug=campaign.slug)

        elif action == 'delete_expedition':
            exp_id = request.POST.get('expedition_id')
            expedition = get_object_or_404(Expedition, id=exp_id, campaign=campaign)
            expedition.delete()
            messages.success(request, 'Expedition deleted.')
            return redirect('campaign_gm', slug=campaign.slug)

        elif action == 'lab_time':
            lab_time_form = LabTimeForm(request.POST, campaign=campaign)
            if lab_time_form.is_valid():
                char = lab_time_form.cleaned_data['character']
                mode = lab_time_form.cleaned_data['mode']
                op   = lab_time_form.cleaned_data['operation']
                if mode == LabTimeForm.MODE_UNLIMITED:
                    char.lab_time_unlimited = not char.lab_time_unlimited
                    msg = (f'{char.name} now has unlimited lab time.'
                           if char.lab_time_unlimited
                           else f'Lab time limits restored for {char.name}.')
                    char.save(update_fields=['lab_time_unlimited'])
                    messages.success(request, msg)
                else:
                    total = lab_time_form.compute_minutes()
                    if op == LabTimeForm.OP_ADD:
                        char.lab_minutes += total
                        messages.success(request, f'Added {_fmt_lab_time(total)} to {char.name}\'s lab time.')
                    elif op == LabTimeForm.OP_SET:
                        char.lab_minutes = total
                        messages.success(request, f'Set {char.name}\'s lab time to {_fmt_lab_time(total)}.')
                    elif op == LabTimeForm.OP_SUBTRACT:
                        before = char.lab_minutes
                        char.lab_minutes = max(0, char.lab_minutes - total)
                        messages.success(request, f'Subtracted {_fmt_lab_time(before - char.lab_minutes)} from {char.name}\'s lab time.')
                    char.save(update_fields=['lab_minutes'])
                return redirect(f"{request.path}?tab=lab_time")

        elif action == 'lab_time_zero':
            char_id = request.POST.get('character')
            char = get_object_or_404(Character, id=char_id, campaign=campaign)
            char.lab_minutes = 0
            char.save(update_fields=['lab_minutes'])
            messages.success(request, f'{char.name}\'s lab time has been set to 0.')
            return redirect(f"{request.path}?tab=lab_time")

    # ── Filter / sort ────────────────────────────────────────────
    filter_form = ExpeditionFilterForm(request.GET or None, campaign=campaign)

    expeditions = (
        Expedition.objects
        .filter(campaign=campaign)
        .select_related('biome', 'target_reagent', 'leader', 'leader__owner', 'approved_by')
        .annotate(participant_count=Count('participants', distinct=True))
    )

    sort_key = 'pending_first'
    if filter_form.is_valid():
        cd = filter_form.cleaned_data
        if cd.get('status'):
            expeditions = expeditions.filter(approval_status=cd['status'])
        if cd.get('leader'):
            expeditions = expeditions.filter(leader=cd['leader'])
        if cd.get('character'):
            expeditions = expeditions.filter(
                Q(leader=cd['character']) | Q(participants__character=cd['character'])
            ).distinct()
        if cd.get('biome'):
            expeditions = expeditions.filter(biome=cd['biome'])
        if cd.get('night') == 'day':
            expeditions = expeditions.filter(search_at_night=False)
        elif cd.get('night') == 'night':
            expeditions = expeditions.filter(search_at_night=True)
        sort_key = cd.get('sort') or 'pending_first'

    if sort_key == 'pending_first':
        expeditions = expeditions.annotate(
            _status_order=Case(
                When(approval_status=ApprovalStatus.PENDING,  then=0),
                When(approval_status=ApprovalStatus.APPROVED, then=1),
                When(approval_status=ApprovalStatus.DENIED,   then=2),
                When(approval_status=ApprovalStatus.EXECUTED, then=3),
                default=4, output_field=IntegerField(),
            )
        ).order_by('_status_order', '-created_at')
    elif sort_key == '-executed_at':
        from django.db.models import F
        expeditions = expeditions.order_by(F('executed_at').desc(nulls_last=True))
    else:
        expeditions = expeditions.order_by(sort_key, '-created_at')

    # ── Pagination ───────────────────────────────────────────────
    paginator = Paginator(expeditions, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Strip 'page' from query string for pagination links
    qs = request.GET.copy()
    qs.pop('page', None)
    query_string = qs.urlencode()

    # Leader→known-reagent map for JS filter toggle
    raw_knowledge = (
        CharacterReagentKnowledge.objects
        .filter(character__campaign=campaign, knows_name=True)
        .values_list('character_id', 'reagent_id')
    )
    leader_knowledge: dict[int, list[int]] = {}
    for char_id, reagent_id in raw_knowledge:
        leader_knowledge.setdefault(char_id, []).append(reagent_id)

    # Character lab-time status for JS (used by the Lab Time tab)
    lab_chars = (
        Character.objects
        .filter(campaign=campaign)
        .values('id', 'lab_minutes', 'lab_time_unlimited')
    )
    lab_chars_json = json.dumps({
        c['id']: {'minutes': c['lab_minutes'], 'unlimited': c['lab_time_unlimited']}
        for c in lab_chars
    })

    return render(request, 'campaigns/campaign_gm.html', {
        'campaign':              campaign,
        'membership':            membership,
        'form':                  form,
        'filter_form':           filter_form,
        'page_obj':              page_obj,
        'query_string':          query_string,
        'ApprovalStatus':        ApprovalStatus,
        'leader_knowledge_json': json.dumps(leader_knowledge),
        'lab_time_form':         lab_time_form,
        'lab_chars_json':        lab_chars_json,
        'active_tab':            request.GET.get('tab', 'expeditions'),
    })


@login_required
def gm_expedition_detail(request, slug, expedition_id):
    campaign = get_object_or_404(Campaign, slug=slug)
    membership = _gm_required(request, campaign)
    expedition = get_object_or_404(
        Expedition.objects.select_related(
            'biome', 'target_reagent', 'leader', 'leader__owner', 'approved_by'
        ),
        id=expedition_id, campaign=campaign,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve' and expedition.approval_status == ApprovalStatus.PENDING:
            expedition.approval_status = ApprovalStatus.APPROVED
            expedition.approved_by = request.user
            expedition.approved_at = timezone.now()
            expedition.save()
            messages.success(request, 'Expedition approved.')
            return redirect('campaign_gm', slug=campaign.slug)
        elif action == 'deny' and expedition.approval_status == ApprovalStatus.PENDING:
            expedition.approval_status = ApprovalStatus.DENIED
            expedition.save()
            messages.success(request, 'Expedition denied.')
            return redirect('campaign_gm', slug=campaign.slug)

    participants = expedition.participants.select_related('character', 'character__owner')

    # GM sees everything found by all characters, grouped by finder.
    from inventory.models import ReagentSample
    found_samples = (
        ReagentSample.objects
        .filter(source_expedition=expedition)
        .select_related('true_reagent', 'true_reagent__category', 'inventory_entry__character')
        .order_by('inventory_entry__character__name')
    )

    return render(request, 'campaigns/gm_expedition_detail.html', {
        'campaign':       campaign,
        'membership':     membership,
        'expedition':     expedition,
        'participants':   participants,
        'found_samples':  found_samples,
        'ApprovalStatus': ApprovalStatus,
    })
