import json
import random

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
from inventory.models import InventoryEntry, InventoryItem, Kind, PotionBatch, ProcessedReagent, ReagentSample, State
from knowledge.models import (
    CharacterReagentBiome, CharacterReagentEffect, CharacterReagentKnowledge,
    CharacterReagentMix, HowLearned, KnowledgeUnlockEvent, MixResult, WhatLearned,
)

from items.models import Item
from reagents.models import Biome, PotionEffect, PotionEffectLevel, Reagent

from .forms import (
    CampaignCreateForm,
    CampaignJoinForm,
    CampaignManageForm,
    CampaignSearchForm,
    ExpeditionFilterForm,
    ExpeditionForm,
    GMExpeditionForm,
    LabTimeForm,
    ManageSBForm,
    TransferOwnershipForm,
    _name_taken_for_owner,
)
from .models import ApprovalStatus, Campaign, CampaignBan, CampaignMembership, Expedition, GameRole, Participation, PotionOutcome, PotionUseEvent
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

        elif action == 'refine_crude':
            try:
                _scroll = int(request.POST.get('scroll_y', 0))
            except (ValueError, TypeError):
                _scroll = 0
            lab_redirect = f"{request.path}?tab=laboratory" + (f"&scroll={_scroll}" if _scroll else "")
            entry_id = request.POST.get('entry_id')
            try:
                qty = max(1, int(request.POST.get('qty', 1)))
            except (ValueError, TypeError):
                qty = 1

            entry = get_object_or_404(
                InventoryEntry, id=entry_id, character=character, kind=Kind.RAW_REAGENT,
            )
            sample = entry.sample
            qty = min(qty, min(10, entry.quantity))

            if not character.lab_time_unlimited and character.lab_minutes < 5:
                messages.error(request, "Not enough lab time. You need at least 5 minutes.")
                return redirect(lab_redirect)

            roll, total = _alchemy_check(character)
            dc = 14
            success = total >= dc
            true_reagent = sample.true_reagent
            source_biome = sample.found_biome

            with transaction.atomic():
                if entry.quantity <= qty:
                    entry.delete()
                else:
                    entry.quantity -= qty
                    entry.save(update_fields=['quantity'])

                if success:
                    new_entry = InventoryEntry.objects.create(
                        character=character, kind=Kind.CRUDE_REAGENT, quantity=qty,
                    )
                    ProcessedReagent.objects.create(
                        inventory_entry=new_entry, reagent=true_reagent,
                        state=State.CRUDE, source_biome=source_biome,
                        observed_category=sample.observed_category,
                        observed_description=sample.observed_description,
                    )

                if not character.lab_time_unlimited:
                    character.lab_minutes = max(0, character.lab_minutes - 5)
                    character.save(update_fields=['lab_minutes'])

            roll_info = f"(Roll {roll} + modifiers = {total} vs DC {dc})"
            if success:
                messages.success(request, f"Refining succeeded! {roll_info} — {qty} unit(s) converted to crude.")
            else:
                messages.warning(request, f"Refining failed. {roll_info} — The batch was ruined.")
            return redirect(lab_redirect)

        elif action == 'refine_advanced':
            try:
                _scroll = int(request.POST.get('scroll_y', 0))
            except (ValueError, TypeError):
                _scroll = 0
            lab_redirect = f"{request.path}?tab=laboratory" + (f"&scroll={_scroll}" if _scroll else "")
            entry_id = request.POST.get('entry_id')

            entry = get_object_or_404(
                InventoryEntry, id=entry_id, character=character, kind=Kind.CRUDE_REAGENT,
            )
            pr = entry.processed_reagent

            if pr.reagent_id is None:
                messages.error(request, "Mundane or unidentified substances cannot be advanced-refined.")
                return redirect(lab_redirect)

            knows = CharacterReagentKnowledge.objects.filter(
                character=character, reagent=pr.reagent,
            ).filter(Q(knows_upv=True) | Q(knows_name=True)).exists()
            if not knows:
                messages.error(request, "You haven't confirmed this substance is alchemical yet. Test it with Storgstrum's Brew first.")
                return redirect(lab_redirect)

            if not character.lab_time_unlimited and character.lab_minutes < 10:
                messages.error(request, "Not enough lab time. You need at least 10 minutes.")
                return redirect(lab_redirect)

            reagent = pr.reagent
            dc = reagent.refine_dc
            roll, total = _alchemy_check(character)
            success = total >= dc

            with transaction.atomic():
                if entry.quantity <= 1:
                    entry.delete()
                else:
                    entry.quantity -= 1
                    entry.save(update_fields=['quantity'])

                if success:
                    new_entry = InventoryEntry.objects.create(
                        character=character, kind=Kind.REFINED_REAGENT, quantity=1,
                    )
                    ProcessedReagent.objects.create(
                        inventory_entry=new_entry, reagent=reagent, state=State.REFINED,
                    )

                if not character.lab_time_unlimited:
                    character.lab_minutes = max(0, character.lab_minutes - 10)
                    character.save(update_fields=['lab_minutes'])

            roll_info = f"(Roll {roll} + modifiers = {total})"
            if success:
                messages.success(request, f"Advanced refining succeeded! {roll_info} — 1 unit refined.")
            else:
                messages.warning(request, f"Advanced refining failed. {roll_info} — 1 crude unit was ruined.")
            return redirect(lab_redirect)

        elif action == 'test_potency':
            try:
                _scroll = int(request.POST.get('scroll_y', 0))
            except (ValueError, TypeError):
                _scroll = 0
            lab_redirect = f"{request.path}?tab=laboratory" + (f"&scroll={_scroll}" if _scroll else "")
            entry_id = request.POST.get('entry_id')

            entry = get_object_or_404(
                InventoryEntry,
                id=entry_id, character=character,
                kind__in=[Kind.CRUDE_REAGENT, Kind.REFINED_REAGENT],
            )
            pr = entry.processed_reagent

            if not character.lab_time_unlimited and character.lab_minutes < 5:
                messages.error(request, "Not enough lab time. You need at least 5 minutes.")
                return redirect(lab_redirect)

            sb_entry = InventoryEntry.objects.filter(
                character=character, kind=Kind.STORGSTRUM,
            ).first()
            if not sb_entry:
                messages.error(request, "You have no Storgstrum's Brew.")
                return redirect(lab_redirect)

            reagent = pr.reagent
            state = pr.state
            source_biome = pr.source_biome  # save before potential delete

            with transaction.atomic():
                if sb_entry.quantity <= 1:
                    sb_entry.delete()
                else:
                    sb_entry.quantity -= 1
                    sb_entry.save(update_fields=['quantity'])

                if entry.quantity <= 1:
                    entry.delete()
                    pr_still_exists = False
                else:
                    entry.quantity -= 1
                    entry.save(update_fields=['quantity'])
                    pr_still_exists = True

                if not character.lab_time_unlimited:
                    character.lab_minutes = max(0, character.lab_minutes - 5)
                    character.save(update_fields=['lab_minutes'])

                if reagent is None:
                    if pr_still_exists:
                        pr.is_confirmed_mundane = True
                        pr.save(update_fields=['is_confirmed_mundane'])
                    messages.info(request, "No reaction. This substance is entirely mundane.")
                else:
                    how = HowLearned.UNREFINED_TEST if state == State.CRUDE else HowLearned.REFINED_TEST
                    crk, _ = CharacterReagentKnowledge.objects.get_or_create(
                        character=character, reagent=reagent,
                    )
                    name_was_known = crk.knows_name
                    changed = set()
                    unlocks = []

                    if not crk.knows_name:
                        crk.knows_name = True; changed.add('knows_name')
                        unlocks.append(WhatLearned.LEARNED_NAME)
                    if not crk.knows_description:
                        crk.knows_description = True; changed.add('knows_description')
                        unlocks.append(WhatLearned.LEARNED_DESCRIPTION)
                    if not crk.knows_category:
                        crk.knows_category = True; changed.add('knows_category')
                        unlocks.append(WhatLearned.LEARNED_CATEGORY)
                    if not crk.knows_rarity:
                        crk.knows_rarity = True; changed.add('knows_rarity')
                        unlocks.append(WhatLearned.LEARNED_RARITY)
                    if state == State.CRUDE and not crk.knows_upv:
                        crk.knows_upv = True; changed.add('knows_upv')
                        unlocks.append(WhatLearned.LEARNED_UPV)
                    if state == State.REFINED and not crk.knows_rpv:
                        crk.knows_rpv = True; changed.add('knows_rpv')
                        unlocks.append(WhatLearned.LEARNED_RPV)

                    if changed:
                        crk.save(update_fields=list(changed) + ['updated_at'])
                        for what in unlocks:
                            KnowledgeUnlockEvent.objects.create(
                                character=character, reagent=reagent,
                                how_learned=how, what_learned=what,
                            )

                    if source_biome:
                        _, biome_new = CharacterReagentBiome.objects.get_or_create(
                            character=character, reagent=reagent, biome=source_biome,
                        )
                        if biome_new:
                            KnowledgeUnlockEvent.objects.create(
                                character=character, reagent=reagent, biome=source_biome,
                                how_learned=how, what_learned=WhatLearned.LEARNED_BIOME,
                            )

                    if changed:
                        if state == State.CRUDE:
                            if not name_was_known:
                                msg = (f"Reaction found! {reagent.name} identified and logged! "
                                       f"You noted a UPV of {reagent.upv}.")
                            else:
                                msg = (f"You discovered that crude {reagent.name} "
                                       f"has a potency level of {reagent.upv}!")
                        else:
                            if not name_was_known:
                                msg = (f"Reaction found! {reagent.name} identified and logged! "
                                       f"You note that this reagent has already been refined "
                                       f"and has an RPV of {reagent.rpv}.")
                            else:
                                msg = (f"You discovered that refined {reagent.name} "
                                       f"has a potency level of {reagent.rpv}!")
                        messages.success(request, msg)
                    else:
                        messages.info(request, "Test complete. No new information gained.")

            return redirect(lab_redirect)

        elif action == 'use_potion':
            inv_redirect = f"{request.path}?tab=inventory"
            entry_id = request.POST.get('entry_id')

            entry = get_object_or_404(
                InventoryEntry, id=entry_id, character=character, kind=Kind.POTION,
            )
            batch = entry.potion_batch
            ra_id = batch.reagent_a_id
            rb_id = batch.reagent_b_id
            is_mystery = ra_id is None
            actual_effects = list(batch.effects.select_related().order_by('name'))
            is_success = len(actual_effects) > 0
            actual_potency = batch.potency

            if is_mystery:
                r_lo = r_hi = None
                crm = None
                already_confirmed = True   # no mix record to update
                already_dud_known = False
            else:
                r_lo = min(ra_id, rb_id)
                r_hi = max(ra_id, rb_id)
                crm = CharacterReagentMix.objects.filter(
                    character=character, reagent_a_id=r_lo, reagent_b_id=r_hi,
                ).first()
                already_confirmed = crm and crm.is_confirmed
                already_dud_known = batch.is_dud_known

            # Build dialog payload
            if is_success and actual_potency:
                lines = []
                for eff in actual_effects:
                    try:
                        el = PotionEffectLevel.objects.get(potion_effect=eff, level=actual_potency)
                        lines.append(f"{eff.name}: {el.rules_text}")
                    except PotionEffectLevel.DoesNotExist:
                        lines.append(f"{eff.name} (no rules text for level {actual_potency})")
                dialog = json.dumps({'outcome': 'success', 'lines': lines})
            else:
                dialog = json.dumps({'outcome': 'dud', 'lines': []})

            with transaction.atomic():
                # Consume 1 unit
                if entry.quantity <= 1:
                    entry.delete()
                else:
                    entry.quantity -= 1
                    entry.save(update_fields=['quantity'])

                # Log the use event
                use_event = PotionUseEvent.objects.create(
                    character=character,
                    reagent_a=batch.reagent_a,
                    reagent_b=batch.reagent_b,
                    potency=actual_potency,
                    outcome=PotionOutcome.SUCCESS if is_success else PotionOutcome.DUD,
                )
                if is_success:
                    use_event.effects.set([e.id for e in actual_effects])

                how = HowLearned.USED_POTION

                # Knowledge unlock only applies to normal (non-mystery) potions
                if not is_mystery:
                    if is_success and not already_confirmed:
                        # Unlock effects on both reagents
                        for eff in actual_effects:
                            for reagent in [batch.reagent_a, batch.reagent_b]:
                                _, eff_new = CharacterReagentEffect.objects.get_or_create(
                                    character=character, reagent=reagent, effect=eff,
                                )
                                if eff_new:
                                    KnowledgeUnlockEvent.objects.create(
                                        character=character, reagent=reagent, effect=eff,
                                        how_learned=how, what_learned=WhatLearned.LEARNED_EFFECT,
                                    )
                        # Ensure name is known for both reagents
                        for reagent in [batch.reagent_a, batch.reagent_b]:
                            crk, _ = CharacterReagentKnowledge.objects.get_or_create(
                                character=character, reagent=reagent,
                            )
                            if not crk.knows_name:
                                crk.knows_name = True
                                crk.save(update_fields=['knows_name', 'updated_at'])
                                KnowledgeUnlockEvent.objects.create(
                                    character=character, reagent=reagent,
                                    how_learned=how, what_learned=WhatLearned.LEARNED_NAME,
                                )
                        # Mark mix as confirmed
                        if crm:
                            crm.is_confirmed = True
                            crm.save(update_fields=['is_confirmed'])
                        else:
                            CharacterReagentMix.objects.create(
                                character=character,
                                reagent_a_id=r_lo,
                                reagent_b_id=r_hi,
                                mix_result=MixResult.SUCCESS,
                                discovered_effect=actual_effects[0] if actual_effects else None,
                                is_confirmed=True,
                            )

                    elif not is_success and not already_dud_known:
                        # Mark remaining batches of this combo as dud-known
                        from django.db.models import Q as _Q
                        PotionBatch.objects.filter(
                            inventory_entry__character=character,
                        ).filter(
                            _Q(reagent_a_id=ra_id, reagent_b_id=rb_id) |
                            _Q(reagent_a_id=rb_id, reagent_b_id=ra_id)
                        ).update(is_dud_known=True)
                        # Mark mix as confirmed dud
                        if crm:
                            if not crm.is_confirmed:
                                crm.is_confirmed = True
                                crm.save(update_fields=['is_confirmed'])
                        else:
                            CharacterReagentMix.objects.create(
                                character=character,
                                reagent_a_id=r_lo,
                                reagent_b_id=r_hi,
                                mix_result=MixResult.DUD,
                                discovered_effect=None,
                                is_confirmed=True,
                            )

            request.session['potion_dialog'] = dialog
            return redirect(inv_redirect)

        elif action == 'mix_potion':
            try:
                _scroll = int(request.POST.get('scroll_y', 0))
            except (ValueError, TypeError):
                _scroll = 0
            lab_redirect = f"{request.path}?tab=laboratory" + (f"&scroll={_scroll}" if _scroll else "")

            base_entry_id = request.POST.get('base_entry_id')
            catalyst_entry_id = request.POST.get('catalyst_entry_id')
            try:
                qty = max(1, int(request.POST.get('qty', 1)))
            except (ValueError, TypeError):
                qty = 1

            base_entry = get_object_or_404(
                InventoryEntry, id=base_entry_id, character=character,
                kind__in=[Kind.CRUDE_REAGENT, Kind.REFINED_REAGENT],
            )
            catalyst_entry = get_object_or_404(
                InventoryEntry, id=catalyst_entry_id, character=character,
                kind__in=[Kind.CRUDE_REAGENT, Kind.REFINED_REAGENT],
            )

            base_pr = base_entry.processed_reagent
            catalyst_pr = catalyst_entry.processed_reagent
            base_reagent = base_pr.reagent
            catalyst_reagent = catalyst_pr.reagent

            if base_reagent is None or not CharacterReagentKnowledge.objects.filter(
                character=character, reagent=base_reagent, knows_name=True,
            ).exists():
                messages.error(request, "Base reagent must be identified before mixing.")
                return redirect(lab_redirect)
            if catalyst_reagent is None or not CharacterReagentKnowledge.objects.filter(
                character=character, reagent=catalyst_reagent, knows_name=True,
            ).exists():
                messages.error(request, "Catalyst reagent must be identified before mixing.")
                return redirect(lab_redirect)
            if base_reagent.id == catalyst_reagent.id:
                messages.error(request, "Cannot mix a reagent with itself.")
                return redirect(lab_redirect)

            r_lo = min(base_reagent.id, catalyst_reagent.id)
            r_hi = max(base_reagent.id, catalyst_reagent.id)

            if CharacterReagentMix.objects.filter(
                character=character, reagent_a_id=r_lo, reagent_b_id=r_hi,
                mix_result=MixResult.DUD,
            ).exists():
                messages.error(request, "This combination is already known to produce a dud.")
                return redirect(lab_redirect)

            if not character.lab_time_unlimited and character.lab_minutes < 5:
                messages.error(request, "Not enough lab time. You need at least 5 minutes.")
                return redirect(lab_redirect)

            qty = min(qty, min(10, base_entry.quantity, catalyst_entry.quantity))

            base_effect_ids = set(base_reagent.potion_effects.values_list('id', flat=True))
            catalyst_effect_ids = set(catalyst_reagent.potion_effects.values_list('id', flat=True))
            shared_effect_ids = base_effect_ids & catalyst_effect_ids

            char_base_eff_ids = set(
                CharacterReagentEffect.objects.filter(
                    character=character, reagent=base_reagent,
                ).values_list('effect_id', flat=True)
            )
            char_cat_eff_ids = set(
                CharacterReagentEffect.objects.filter(
                    character=character, reagent=catalyst_reagent,
                ).values_list('effect_id', flat=True)
            )
            char_known_shared_ids = char_base_eff_ids & char_cat_eff_ids

            base_pv = base_reagent.upv if base_pr.state == State.CRUDE else base_reagent.rpv
            catalyst_pv = catalyst_reagent.upv if catalyst_pr.state == State.CRUDE else catalyst_reagent.rpv
            potion_potency = (base_pv + catalyst_pv) // 2

            if char_known_shared_ids:
                effect_names = list(
                    PotionEffect.objects.filter(id__in=char_known_shared_ids)
                    .order_by('name').values_list('name', flat=True)
                )
                if len(effect_names) == 1:
                    effect_str = effect_names[0]
                elif len(effect_names) == 2:
                    effect_str = f"{effect_names[0]} and {effect_names[1]}"
                else:
                    effect_str = ", ".join(effect_names[:-1]) + f", and {effect_names[-1]}"
                msg = (
                    f"You mixed a potion of {effect_str}!" if qty == 1
                    else f"You mixed {qty} potions of {effect_str}!"
                )
            else:
                msg = (
                    "You have created an untested alchemical solution." if qty == 1
                    else f"You have created {qty} untested alchemical solutions."
                )

            primary_effect = (
                PotionEffect.objects.filter(id__in=shared_effect_ids).order_by('name').first()
                if shared_effect_ids else None
            )

            with transaction.atomic():
                if base_entry.quantity <= qty:
                    base_entry.delete()
                else:
                    base_entry.quantity -= qty
                    base_entry.save(update_fields=['quantity'])

                if catalyst_entry.quantity <= qty:
                    catalyst_entry.delete()
                else:
                    catalyst_entry.quantity -= qty
                    catalyst_entry.save(update_fields=['quantity'])

                potion_entry = InventoryEntry.objects.create(
                    character=character, kind=Kind.POTION, quantity=qty,
                )
                potion_batch = PotionBatch.objects.create(
                    inventory_entry=potion_entry,
                    reagent_a=base_reagent,
                    reagent_b=catalyst_reagent,
                    state_a=base_pr.state,
                    state_b=catalyst_pr.state,
                    potency=potion_potency if shared_effect_ids else None,
                )
                if shared_effect_ids:
                    potion_batch.effects.set(shared_effect_ids)

                if not character.lab_time_unlimited:
                    character.lab_minutes = max(0, character.lab_minutes - 5)
                    character.save(update_fields=['lab_minutes'])

                if not CharacterReagentMix.objects.filter(
                    character=character, reagent_a_id=r_lo, reagent_b_id=r_hi,
                ).exists():
                    CharacterReagentMix.objects.create(
                        character=character,
                        reagent_a_id=r_lo,
                        reagent_b_id=r_hi,
                        mix_result=MixResult.SUCCESS if shared_effect_ids else MixResult.DUD,
                        discovered_effect=primary_effect,
                    )

            messages.success(request, msg)
            return redirect(lab_redirect)

    active_tab = request.GET.get('tab', 'expeditions')

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

    # ── Lab context ───────────────────────────────────────────────────────────
    sb_entry = InventoryEntry.objects.filter(character=character, kind=Kind.STORGSTRUM).first()
    sb_qty = sb_entry.quantity if sb_entry else 0

    knows_name_ids = set(
        CharacterReagentKnowledge.objects
        .filter(character=character, knows_name=True)
        .values_list('reagent_id', flat=True)
    )
    knows_upv_ids = set(
        CharacterReagentKnowledge.objects
        .filter(character=character, knows_upv=True)
        .values_list('reagent_id', flat=True)
    )
    knows_rpv_ids = set(
        CharacterReagentKnowledge.objects
        .filter(character=character, knows_rpv=True)
        .values_list('reagent_id', flat=True)
    )
    alchemical_known_ids = knows_name_ids | knows_upv_ids

    # ── Raw samples: collapse identified reagents into one row each ───────────
    _raw_qs = (
        ReagentSample.objects
        .filter(inventory_entry__character=character)
        .select_related('inventory_entry', 'true_reagent', 'true_reagent__category')
        .order_by('observed_category', 'inventory_entry__created_at')
    )
    raw_display = []
    _raw_id_map = {}  # reagent_id -> row dict
    for _s in _raw_qs:
        _is_id = (not _s.is_mundane and _s.true_reagent_id
                  and _s.true_reagent_id in knows_name_ids)
        if _is_id:
            _rid = _s.true_reagent_id
            if _rid not in _raw_id_map:
                _raw_id_map[_rid] = {
                    'display_name': _s.true_reagent.name,
                    'type_display': _s.true_reagent.category.name,
                    'description':  _s.true_reagent.description or '',
                    'total_qty':    0,
                    'entry_id':     _s.inventory_entry_id,
                    'batch_max':    min(10, _s.inventory_entry.quantity),
                    'is_identified': True,
                    '_sort': (_s.true_reagent.category.name, _s.inventory_entry.created_at),
                }
            _raw_id_map[_rid]['total_qty'] += _s.inventory_entry.quantity
        else:
            _cat = _s.observed_category or 'Unknown'
            raw_display.append({
                'display_name': 'Unidentified',
                'type_display': _cat,
                'description':  _s.observed_description or '',
                'total_qty':    _s.inventory_entry.quantity,
                'entry_id':     _s.inventory_entry_id,
                'batch_max':    min(10, _s.inventory_entry.quantity),
                'is_identified': False,
                '_sort': (_cat, _s.inventory_entry.created_at),
            })
    raw_display.extend(_raw_id_map.values())
    raw_display.sort(key=lambda x: x['_sort'])

    # ── Advanced refinement: collapse by reagent ──────────────────────────────
    _crude_qs = (
        ProcessedReagent.objects
        .filter(inventory_entry__character=character, state=State.CRUDE,
                reagent_id__in=alchemical_known_ids)
        .select_related('inventory_entry', 'reagent', 'reagent__category')
        .order_by('reagent__category__name', 'inventory_entry__created_at')
    )
    _crude_map = {}
    for _pr in _crude_qs:
        _rid = _pr.reagent_id
        if _rid not in _crude_map:
            _crude_map[_rid] = {
                'name':         _pr.reagent.name,
                'type_display': _pr.reagent.category.name,
                'description':  _pr.reagent.description or '',
                'total_qty':    0,
                'entry_id':     _pr.inventory_entry_id,
                '_sort': (_pr.reagent.category.name, _pr.inventory_entry.created_at),
            }
        _crude_map[_rid]['total_qty'] += _pr.inventory_entry.quantity
    crude_display = sorted(_crude_map.values(), key=lambda x: x['_sort'])

    # ── Potency testing: collapse named (reagent+state) pairs ─────────────────
    _test_qs = (
        ProcessedReagent.objects
        .filter(inventory_entry__character=character)
        .filter(
            Q(state=State.CRUDE, reagent__isnull=False) & ~Q(reagent_id__in=knows_upv_ids)
            | Q(state=State.CRUDE, reagent__isnull=True, is_confirmed_mundane=False)
            | Q(state=State.REFINED, reagent__isnull=False) & ~Q(reagent_id__in=knows_rpv_ids)
        )
        .select_related('inventory_entry', 'reagent', 'reagent__category')
        .order_by('inventory_entry__created_at')
    )
    testable_display = []
    _test_named = {}  # (reagent_id, state) -> row dict
    for _pr in _test_qs:
        _is_id = bool(_pr.reagent_id and _pr.reagent_id in alchemical_known_ids)
        if _is_id:
            _key = (_pr.reagent_id, _pr.state)
            if _key not in _test_named:
                _test_named[_key] = {
                    'display_name': _pr.reagent.name,
                    'type_display': _pr.reagent.category.name,
                    'state_display': _pr.get_state_display(),
                    'description':  _pr.reagent.description or '',
                    'total_qty':    0,
                    'entry_id':     _pr.inventory_entry_id,
                    'is_identified': True,
                    '_sort': (_pr.reagent.category.name, _pr.inventory_entry.created_at),
                }
            _test_named[_key]['total_qty'] += _pr.inventory_entry.quantity
        else:
            if _pr.reagent_id:
                _cat = _pr.reagent.category.name
            else:
                _cat = _pr.observed_category or 'Unknown'
            _desc = _pr.observed_description or ''
            testable_display.append({
                'display_name': 'Unidentified',
                'type_display': _cat,
                'state_display': _pr.get_state_display(),
                'description':  _desc,
                'total_qty':    _pr.inventory_entry.quantity,
                'entry_id':     _pr.inventory_entry_id,
                'is_identified': False,
                '_sort': (_cat, _pr.inventory_entry.created_at),
            })
    testable_display.extend(_test_named.values())
    testable_display.sort(key=lambda x: x['_sort'])

    # ── Potion Mixing ─────────────────────────────────────────────────────────
    _mixable_qs = (
        ProcessedReagent.objects
        .filter(inventory_entry__character=character, reagent_id__in=knows_name_ids)
        .select_related('inventory_entry', 'reagent')
        .order_by('reagent__name', 'state')
    )
    _mix_map = {}  # (reagent_id, state) -> row dict
    for _pr in _mixable_qs:
        _key = (_pr.reagent_id, _pr.state)
        if _key not in _mix_map:
            _knows_pv = (
                _pr.reagent_id in knows_upv_ids if _pr.state == State.CRUDE
                else _pr.reagent_id in knows_rpv_ids
            )
            _pv = (
                (_pr.reagent.upv if _pr.state == State.CRUDE else _pr.reagent.rpv)
                if _knows_pv else None
            )
            _mix_map[_key] = {
                'entry_id':       _pr.inventory_entry_id,
                'reagent_id':     _pr.reagent_id,
                'name':           _pr.reagent.name,
                'state':          _pr.state,
                'state_display':  _pr.get_state_display(),
                'potency':        _pv,
                'potency_display': str(_pv) if _pv is not None else '?',
                'total_qty':      0,
            }
        _mix_map[_key]['total_qty'] += _pr.inventory_entry.quantity
    mixing_items = sorted(_mix_map.values(), key=lambda x: (x['name'], x['state']))

    _dud_pairs = list(
        CharacterReagentMix.objects
        .filter(character=character, mix_result=MixResult.DUD)
        .values_list('reagent_a_id', 'reagent_b_id')
    )

    _char_effects_map = {}
    for _rid, _ename in (
        CharacterReagentEffect.objects
        .filter(character=character)
        .values_list('reagent_id', 'effect__name')
    ):
        _char_effects_map.setdefault(str(_rid), []).append(_ename)

    mixing_data_json = json.dumps({
        'items':       mixing_items,
        'dud_pairs':   _dud_pairs,
        'char_effects': _char_effects_map,
    })

    # ── Inventory context ─────────────────────────────────────────────────────
    # Potions
    _potion_batches = (
        PotionBatch.objects
        .filter(inventory_entry__character=character)
        .select_related('inventory_entry', 'reagent_a', 'reagent_b')
        .prefetch_related('effects')
        .order_by('-inventory_entry__created_at')
    )
    _crm_lookup = {
        (crm.reagent_a_id, crm.reagent_b_id): crm
        for crm in CharacterReagentMix.objects.filter(character=character)
    }
    _crk_lookup = {
        crk.reagent_id: crk
        for crk in CharacterReagentKnowledge.objects.filter(character=character)
    }
    _char_eff_by_reagent = {}  # reagent_id -> set of effect_ids
    for _cre in CharacterReagentEffect.objects.filter(character=character):
        _char_eff_by_reagent.setdefault(_cre.reagent_id, set()).add(_cre.effect_id)

    potion_display = []
    for _batch in _potion_batches:
        _ra_id = _batch.reagent_a_id
        _rb_id = _batch.reagent_b_id

        # Mystery potions (GM-given, no known recipe) — treat as confirmed Case 3
        if _ra_id is None:
            _actual_effects = sorted(_batch.effects.all(), key=lambda e: e.name)
            _eff_names = [e.name for e in _actual_effects]
            if _eff_names:
                if len(_eff_names) == 1:
                    _mys_name = f"Potion of {_eff_names[0]}"
                elif len(_eff_names) == 2:
                    _mys_name = f"Potion of {_eff_names[0]} and {_eff_names[1]}"
                else:
                    _mys_name = "Potion of " + ", ".join(_eff_names[:-1]) + f", and {_eff_names[-1]}"
            else:
                _mys_name = "Mystery Potion"
            _mys_level = str(_batch.potency) if _batch.potency else "?"
            _n_eff = len(_actual_effects)
            _mys_value = (f"{(_batch.potency ** 3) * 10 * _n_eff:,} gp"
                          if _batch.potency and _n_eff else "?")
            potion_display.append({
                'entry_id':      _batch.inventory_entry_id,
                'display_name':  _mys_name,
                'level_display': _mys_level,
                'value_display': _mys_value,
                'quantity':      _batch.inventory_entry.quantity,
                'case':          3,
            })
            continue

        _r_lo = min(_ra_id, _rb_id)
        _r_hi = max(_ra_id, _rb_id)
        _crm = _crm_lookup.get((_r_lo, _r_hi))
        _actual_effects = sorted(_batch.effects.all(), key=lambda e: e.name)

        _known_a = _char_eff_by_reagent.get(_ra_id, set())
        _known_b = _char_eff_by_reagent.get(_rb_id, set())
        _known_shared_ids = _known_a & _known_b
        _known_shared_names = sorted(
            PotionEffect.objects.filter(id__in=_known_shared_ids).values_list('name', flat=True)
        ) if _known_shared_ids else []

        # Determine case
        if _batch.is_dud_known:
            _case = 4
        elif _crm and _crm.is_confirmed:
            _case = 3
        elif _known_shared_ids:
            _case = 2
        else:
            _case = 1

        # Name
        def _fmt_effects(names, question_mark=False):
            q = '?' if question_mark else ''
            if len(names) == 1:
                return f"Potion of {names[0]}{q}"
            elif len(names) == 2:
                return f"Potion of {names[0]} and {names[1]}{q}"
            else:
                return "Potion of " + ", ".join(names[:-1]) + f", and {names[-1]}{q}"

        if _case == 4:
            _name = "Failed Experiment"
        elif _case == 3:
            _effect_names = [e.name for e in _actual_effects]
            _name = _fmt_effects(_effect_names) if _effect_names else "Failed Experiment"
        elif _case == 2:
            _name = _fmt_effects(_known_shared_names, question_mark=True)
        else:
            _name = f"Untested Mixture — {_batch.reagent_a.name} + {_batch.reagent_b.name}"

        # Level and value
        _crk_a = _crk_lookup.get(_ra_id)
        _crk_b = _crk_lookup.get(_rb_id)
        _a_pv = None
        if _batch.state_a == State.CRUDE and _crk_a and _crk_a.knows_upv:
            _a_pv = _batch.reagent_a.upv
        elif _batch.state_a == State.REFINED and _crk_a and _crk_a.knows_rpv:
            _a_pv = _batch.reagent_a.rpv
        _b_pv = None
        if _batch.state_b == State.CRUDE and _crk_b and _crk_b.knows_upv:
            _b_pv = _batch.reagent_b.upv
        elif _batch.state_b == State.REFINED and _crk_b and _crk_b.knows_rpv:
            _b_pv = _batch.reagent_b.rpv
        _calc_level = ((_a_pv + _b_pv) // 2) if (_a_pv is not None and _b_pv is not None) else None

        if _case == 4:
            _level_str = "Mundane"
            _value_str = "0 gp"
        elif _case == 3:
            _level_str = str(_batch.potency) if _batch.potency else "?"
            _n_eff = len(_actual_effects)
            if _batch.potency and _n_eff:
                _value_str = f"{(_batch.potency ** 3) * 10 * _n_eff:,} gp"
            else:
                _value_str = "?"
        elif _case == 2:
            if _calc_level is not None:
                _level_str = str(_calc_level)
                _n_known = len(_known_shared_ids)
                _value_str = f"{(_calc_level ** 3) * 10 * _n_known:,} gp?"
            else:
                _level_str = "?"
                _value_str = "?"
        else:  # case 1
            _level_str = f"{_calc_level}?" if _calc_level is not None else "?"
            _value_str = "?"

        potion_display.append({
            'entry_id':     _batch.inventory_entry_id,
            'display_name': _name,
            'level_display': _level_str,
            'value_display': _value_str,
            'quantity':     _batch.inventory_entry.quantity,
            'case':         _case,
        })

    # Reagents inventory
    _inv_raw_qs = (
        ReagentSample.objects
        .filter(inventory_entry__character=character)
        .select_related('inventory_entry', 'true_reagent', 'true_reagent__category')
        .order_by('observed_category', 'inventory_entry__created_at')
    )
    inv_reagent_display = []
    for _s in _inv_raw_qs:
        _known = (not _s.is_mundane and _s.true_reagent_id and
                  _s.true_reagent_id in knows_name_ids)
        inv_reagent_display.append({
            'name':     _s.true_reagent.name if _known else 'Unidentified',
            'category': (_s.true_reagent.category.name if _known
                         else (_s.observed_category or 'Unknown')),
            'state':    'Raw',
            'potency':  '—',
            'quantity': _s.inventory_entry.quantity,
            'identified': _known,
        })
    _inv_proc_qs = (
        ProcessedReagent.objects
        .filter(inventory_entry__character=character)
        .select_related('inventory_entry', 'reagent', 'reagent__category')
        .order_by('reagent__name', 'state', 'inventory_entry__created_at')
    )
    _inv_proc_map = {}  # (reagent_id or None, state, is_mundane) -> row
    for _pr in _inv_proc_qs:
        _pr_known = bool(_pr.reagent_id and _pr.reagent_id in knows_name_ids)
        if _pr.is_confirmed_mundane:
            _key = (None, _pr.state, True)
        elif _pr_known:
            _key = (_pr.reagent_id, _pr.state, False)
        else:
            _key = (None, _pr.state, False)

        if _pr_known:
            _crk = _crk_lookup.get(_pr.reagent_id)
            if _pr.state == State.CRUDE:
                _pv = str(_pr.reagent.upv) if (_crk and _crk.knows_upv) else '?'
            else:
                _pv = str(_pr.reagent.rpv) if (_crk and _crk.knows_rpv) else '?'
            _row = _inv_proc_map.get(_key) or {
                'name':     _pr.reagent.name,
                'category': _pr.reagent.category.name,
                'state':    _pr.get_state_display(),
                'potency':  _pv,
                'quantity': 0,
                'identified': True,
            }
            _row['quantity'] += _pr.inventory_entry.quantity
            _inv_proc_map[_key] = _row
        elif _pr.is_confirmed_mundane:
            _row = _inv_proc_map.get(_key) or {
                'name':     'Mundane Substance',
                'category': _pr.observed_category or 'Unknown',
                'state':    _pr.get_state_display(),
                'potency':  '—',
                'quantity': 0,
                'identified': False,
            }
            _row['quantity'] += _pr.inventory_entry.quantity
            _inv_proc_map[_key] = _row
        else:
            inv_reagent_display.append({
                'name':     'Unidentified',
                'category': _pr.observed_category or 'Unknown',
                'state':    _pr.get_state_display(),
                'potency':  '?',
                'quantity': _pr.inventory_entry.quantity,
                'identified': False,
            })
    inv_reagent_display.extend(_inv_proc_map.values())

    # Equipment inventory (items + Storgstrum's Brew)
    inv_equipment_display = []
    for _ie in (
        InventoryItem.objects
        .filter(inventory_entry__character=character)
        .select_related('inventory_entry', 'item')
        .order_by('item__name')
    ):
        inv_equipment_display.append({
            'name':        _ie.item.name,
            'item_type':   _ie.item.get_item_type_display(),
            'description': _ie.item.description,
            'quantity':    _ie.inventory_entry.quantity,
        })
    if sb_qty > 0:
        inv_equipment_display.insert(0, {
            'name':        "Storgstrum's Brew",
            'item_type':   'Consumable',
            'description': 'A reagent-testing solution used in the laboratory.',
            'quantity':    sb_qty,
        })

    potion_dialog = request.session.pop('potion_dialog', None)

    lab_time_display = '∞' if character.lab_time_unlimited else (
        _fmt_lab_time(character.lab_minutes) if character.lab_minutes else '0m'
    )

    return render(request, 'campaigns/campaign_play.html', {
        'campaign':          campaign,
        'character':         character,
        'membership':        membership,
        'form':              form,
        'expeditions':       expeditions,
        'ApprovalStatus':    ApprovalStatus,
        'active_tab':        active_tab,
        'sb_qty':            sb_qty,
        'raw_display':       raw_display,
        'crude_display':     crude_display,
        'testable_display':  testable_display,
        'lab_time_display':  lab_time_display,
        'mixing_items':      mixing_items,
        'mixing_data_json':  mixing_data_json,
        'potion_display':       potion_display,
        'inv_reagent_display':  inv_reagent_display,
        'inv_equipment_display': inv_equipment_display,
        'potion_dialog':        potion_dialog,
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


def _alchemy_check(character):
    """Roll a d20 + Intelligence modifier + alchemy_bonus. Returns (raw_roll, total)."""
    roll = random.randint(1, 20)
    int_mod = (character.intelligence - 10) // 2
    return roll, roll + int_mod + character.alchemy_bonus


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

    # ── Manage SB form (default empty; replaced on failed submission) ───────
    manage_sb_form = ManageSBForm(campaign=campaign)

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

        elif action == 'manage_sb':
            manage_sb_form = ManageSBForm(request.POST, campaign=campaign)
            if manage_sb_form.is_valid():
                char    = manage_sb_form.cleaned_data['character']
                op      = manage_sb_form.cleaned_data['operation']
                qty     = manage_sb_form.cleaned_data['quantity']
                sb_entry = InventoryEntry.objects.filter(
                    character=char, kind=Kind.STORGSTRUM,
                ).first()
                current = sb_entry.quantity if sb_entry else 0

                if op == ManageSBForm.OP_ADD:
                    new_qty = min(9999, current + qty)
                elif op == ManageSBForm.OP_REMOVE:
                    new_qty = max(0, current - qty)
                else:  # SET
                    new_qty = qty

                if new_qty == 0:
                    if sb_entry:
                        sb_entry.delete()
                elif sb_entry:
                    sb_entry.quantity = new_qty
                    sb_entry.save(update_fields=['quantity'])
                else:
                    InventoryEntry.objects.create(
                        character=char, kind=Kind.STORGSTRUM, quantity=new_qty,
                    )
                messages.success(
                    request,
                    f"{char.name}'s Storgstrum's Brew: {current} → {new_qty}.",
                )
                return redirect(f"{request.path}?tab=manage_items")

        elif action == 'gm_adjust_qty':
            entry_id = request.POST.get('entry_id')
            char_id  = request.POST.get('char_id', '')
            try:
                new_qty = int(request.POST.get('qty', 0))
            except (ValueError, TypeError):
                new_qty = 0
            entry = get_object_or_404(InventoryEntry, id=entry_id, character__campaign=campaign)
            if new_qty <= 0:
                entry.delete()
                messages.success(request, 'Item removed.')
            else:
                entry.quantity = min(new_qty, 999)
                entry.save(update_fields=['quantity'])
                messages.success(request, 'Quantity updated.')
            return redirect(f"{request.path}?tab=inventory&gm_char={char_id}")

        elif action == 'gm_remove_item':
            entry_id = request.POST.get('entry_id')
            char_id  = request.POST.get('char_id', '')
            entry = get_object_or_404(InventoryEntry, id=entry_id, character__campaign=campaign)
            entry.delete()
            messages.success(request, 'Item removed.')
            return redirect(f"{request.path}?tab=inventory&gm_char={char_id}")

        elif action == 'gm_give_raw_reagent':
            char_ids = request.POST.getlist('char_ids') or (
                [request.POST.get('char_id')] if request.POST.get('char_id') else []
            )
            char_id = request.POST.get('char_id', '')
            try:
                qty = max(1, min(999, int(request.POST.get('qty', 1))))
            except (ValueError, TypeError):
                qty = 1
            reagent_id  = request.POST.get('reagent_id') or None
            biome_id    = request.POST.get('biome_id') or None
            is_mundane  = reagent_id is None
            observed_description = request.POST.get('observed_description', '').strip() or None
            observed_category    = request.POST.get('observed_category', '').strip() or None
            true_reagent = get_object_or_404(Reagent, id=reagent_id) if reagent_id else None
            biome        = get_object_or_404(Biome, id=biome_id) if biome_id else None
            targets = list(Character.objects.filter(id__in=char_ids, campaign=campaign))
            if not targets:
                messages.error(request, 'No valid characters selected.')
            else:
                with transaction.atomic():
                    for char in targets:
                        _entry = InventoryEntry.objects.create(
                            character=char, kind=Kind.RAW_REAGENT, quantity=qty,
                        )
                        ReagentSample.objects.create(
                            inventory_entry=_entry,
                            true_reagent=true_reagent,
                            is_mundane=is_mundane,
                            found_biome=biome,
                            observed_description=observed_description,
                            observed_category=observed_category,
                        )
                names = ', '.join(c.name for c in targets)
                messages.success(request, f'Raw reagent given to: {names}.')
            return redirect(
                f"{request.path}?tab=inventory&gm_char={char_id}" if char_id
                else f"{request.path}?tab=inventory"
            )

        elif action == 'gm_give_processed_reagent':
            char_ids = request.POST.getlist('char_ids') or (
                [request.POST.get('char_id')] if request.POST.get('char_id') else []
            )
            char_id   = request.POST.get('char_id', '')
            reagent_id = request.POST.get('reagent_id')
            state = request.POST.get('state', State.CRUDE)
            if state not in (State.CRUDE, State.REFINED):
                state = State.CRUDE
            kind = Kind.CRUDE_REAGENT if state == State.CRUDE else Kind.REFINED_REAGENT
            try:
                qty = max(1, min(999, int(request.POST.get('qty', 1))))
            except (ValueError, TypeError):
                qty = 1
            reagent = get_object_or_404(Reagent, id=reagent_id) if reagent_id else None
            if not reagent:
                messages.error(request, 'A reagent must be selected.')
            else:
                targets = list(Character.objects.filter(id__in=char_ids, campaign=campaign))
                if not targets:
                    messages.error(request, 'No valid characters selected.')
                else:
                    with transaction.atomic():
                        for char in targets:
                            _entry = InventoryEntry.objects.create(
                                character=char, kind=kind, quantity=qty,
                            )
                            ProcessedReagent.objects.create(
                                inventory_entry=_entry, reagent=reagent, state=state,
                            )
                    names = ', '.join(c.name for c in targets)
                    messages.success(request, f'{reagent.name} ({state}) given to: {names}.')
            return redirect(
                f"{request.path}?tab=inventory&gm_char={char_id}" if char_id
                else f"{request.path}?tab=inventory"
            )

        elif action == 'gm_give_normal_potion':
            char_ids = request.POST.getlist('char_ids') or (
                [request.POST.get('char_id')] if request.POST.get('char_id') else []
            )
            char_id    = request.POST.get('char_id', '')
            reagent_a_id = request.POST.get('reagent_a_id')
            reagent_b_id = request.POST.get('reagent_b_id')
            state_a = request.POST.get('state_a', State.CRUDE)
            state_b = request.POST.get('state_b', State.CRUDE)
            if state_a not in (State.CRUDE, State.REFINED): state_a = State.CRUDE
            if state_b not in (State.CRUDE, State.REFINED): state_b = State.CRUDE
            try:
                qty = max(1, min(999, int(request.POST.get('qty', 1))))
            except (ValueError, TypeError):
                qty = 1
            if not reagent_a_id or not reagent_b_id or reagent_a_id == reagent_b_id:
                messages.error(request, 'Two different reagents must be selected.')
            else:
                reagent_a = get_object_or_404(Reagent, id=reagent_a_id)
                reagent_b = get_object_or_404(Reagent, id=reagent_b_id)
                base_eff_ids = set(reagent_a.potion_effects.values_list('id', flat=True))
                cat_eff_ids  = set(reagent_b.potion_effects.values_list('id', flat=True))
                shared_eff_ids = base_eff_ids & cat_eff_ids
                pv_a = reagent_a.upv if state_a == State.CRUDE else reagent_a.rpv
                pv_b = reagent_b.upv if state_b == State.CRUDE else reagent_b.rpv
                potency = (pv_a + pv_b) // 2 if shared_eff_ids else None
                targets = list(Character.objects.filter(id__in=char_ids, campaign=campaign))
                if not targets:
                    messages.error(request, 'No valid characters selected.')
                else:
                    with transaction.atomic():
                        for char in targets:
                            _entry = InventoryEntry.objects.create(
                                character=char, kind=Kind.POTION, quantity=qty,
                            )
                            _batch = PotionBatch.objects.create(
                                inventory_entry=_entry,
                                reagent_a=reagent_a, reagent_b=reagent_b,
                                state_a=state_a, state_b=state_b,
                                potency=potency,
                            )
                            if shared_eff_ids:
                                _batch.effects.set(shared_eff_ids)
                    names = ', '.join(c.name for c in targets)
                    messages.success(request, f'Potion given to: {names}.')
            return redirect(
                f"{request.path}?tab=inventory&gm_char={char_id}" if char_id
                else f"{request.path}?tab=inventory"
            )

        elif action == 'gm_give_mystery_potion':
            char_ids = request.POST.getlist('char_ids') or (
                [request.POST.get('char_id')] if request.POST.get('char_id') else []
            )
            char_id    = request.POST.get('char_id', '')
            effect_ids = request.POST.getlist('effect_ids')
            try:
                potency = max(1, min(10, int(request.POST.get('potency', 1))))
            except (ValueError, TypeError):
                potency = 1
            try:
                qty = max(1, min(999, int(request.POST.get('qty', 1))))
            except (ValueError, TypeError):
                qty = 1
            if not effect_ids:
                messages.error(request, 'At least one effect must be selected.')
            else:
                valid_effects = list(PotionEffect.objects.filter(id__in=effect_ids))
                targets = list(Character.objects.filter(id__in=char_ids, campaign=campaign))
                if not targets:
                    messages.error(request, 'No valid characters selected.')
                else:
                    with transaction.atomic():
                        for char in targets:
                            _entry = InventoryEntry.objects.create(
                                character=char, kind=Kind.POTION, quantity=qty,
                            )
                            _batch = PotionBatch.objects.create(
                                inventory_entry=_entry,
                                reagent_a=None, reagent_b=None,
                                state_a=State.CRUDE, state_b=State.CRUDE,
                                potency=potency,
                            )
                            _batch.effects.set([e.id for e in valid_effects])
                    names = ', '.join(c.name for c in targets)
                    messages.success(request, f'Mystery potion given to: {names}.')
            return redirect(
                f"{request.path}?tab=inventory&gm_char={char_id}" if char_id
                else f"{request.path}?tab=inventory"
            )

        elif action == 'gm_give_equipment':
            char_ids = request.POST.getlist('char_ids') or (
                [request.POST.get('char_id')] if request.POST.get('char_id') else []
            )
            char_id = request.POST.get('char_id', '')
            item_id = request.POST.get('item_id')
            try:
                qty = max(1, min(999, int(request.POST.get('qty', 1))))
            except (ValueError, TypeError):
                qty = 1
            item = get_object_or_404(Item, id=item_id) if item_id else None
            if not item:
                messages.error(request, 'An item must be selected.')
            else:
                targets = list(Character.objects.filter(id__in=char_ids, campaign=campaign))
                if not targets:
                    messages.error(request, 'No valid characters selected.')
                else:
                    with transaction.atomic():
                        for char in targets:
                            _entry = InventoryEntry.objects.create(
                                character=char, kind=Kind.ITEM, quantity=qty,
                            )
                            InventoryItem.objects.create(inventory_entry=_entry, item=item)
                    names = ', '.join(c.name for c in targets)
                    messages.success(request, f'{item.name} given to: {names}.')
            return redirect(
                f"{request.path}?tab=inventory&gm_char={char_id}" if char_id
                else f"{request.path}?tab=inventory"
            )

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

    # SB amounts per character for the Manage Items overview table
    _sb_map = {
        e['character_id']: e['quantity']
        for e in InventoryEntry.objects.filter(
            character__campaign=campaign, kind=Kind.STORGSTRUM,
        ).values('character_id', 'quantity')
    }
    sb_overview = [
        {'char': c, 'qty': _sb_map.get(c.pk, 0)}
        for c in manage_sb_form.fields['character'].queryset
    ]

    # ── GM Inventory tab context ──────────────────────────────────────────────
    gm_characters = list(Character.objects.filter(campaign=campaign).order_by('name'))
    gm_char_id_param = request.GET.get('gm_char', '')
    gm_selected_char = None
    gm_char_inv = None

    if gm_char_id_param:
        try:
            gm_selected_char = Character.objects.get(pk=int(gm_char_id_param), campaign=campaign)
        except (Character.DoesNotExist, ValueError):
            gm_selected_char = None

    if gm_selected_char:
        _gc = gm_selected_char
        _gm_potions = []
        for _b in (
            PotionBatch.objects
            .filter(inventory_entry__character=_gc)
            .select_related('inventory_entry', 'reagent_a', 'reagent_b')
            .prefetch_related('effects')
            .order_by('-inventory_entry__created_at')
        ):
            _effs = sorted(_b.effects.all(), key=lambda e: e.name)
            _eff_str = ', '.join(e.name for e in _effs) if _effs else '—'
            if _b.reagent_a_id is None:
                _recipe = 'Mystery'
            else:
                _recipe = (
                    f'{_b.reagent_a.name} ({_b.get_state_a_display()})'
                    f' + {_b.reagent_b.name} ({_b.get_state_b_display()})'
                )
            _gm_potions.append({
                'entry_id':  _b.inventory_entry_id,
                'recipe':    _recipe,
                'effects':   _eff_str,
                'potency':   str(_b.potency) if _b.potency else '?',
                'quantity':  _b.inventory_entry.quantity,
            })

        _gm_raw = []
        for _s in (
            ReagentSample.objects
            .filter(inventory_entry__character=_gc)
            .select_related('inventory_entry', 'true_reagent', 'found_biome')
            .order_by('inventory_entry__created_at')
        ):
            _gm_raw.append({
                'entry_id':     _s.inventory_entry_id,
                'reagent_name': _s.true_reagent.name if _s.true_reagent else '(Mundane)',
                'biome':        _s.found_biome.get_name_display() if _s.found_biome else '—',
                'is_mundane':   _s.is_mundane,
                'quantity':     _s.inventory_entry.quantity,
            })

        _gm_processed = []
        for _pr in (
            ProcessedReagent.objects
            .filter(inventory_entry__character=_gc)
            .select_related('inventory_entry', 'reagent')
            .order_by('reagent__name', 'state', 'inventory_entry__created_at')
        ):
            _gm_processed.append({
                'entry_id':     _pr.inventory_entry_id,
                'reagent_name': _pr.reagent.name if _pr.reagent else '(Unknown)',
                'state':        _pr.get_state_display(),
                'quantity':     _pr.inventory_entry.quantity,
            })

        _gm_equipment = []
        _gm_sb = InventoryEntry.objects.filter(character=_gc, kind=Kind.STORGSTRUM).first()
        if _gm_sb:
            _gm_equipment.append({
                'entry_id':  _gm_sb.id,
                'name':      "Storgstrum's Brew",
                'item_type': 'Consumable',
                'quantity':  _gm_sb.quantity,
            })
        for _ie in (
            InventoryItem.objects
            .filter(inventory_entry__character=_gc)
            .select_related('inventory_entry', 'item')
            .order_by('item__name')
        ):
            _gm_equipment.append({
                'entry_id':  _ie.inventory_entry_id,
                'name':      _ie.item.name,
                'item_type': _ie.item.get_item_type_display(),
                'quantity':  _ie.inventory_entry.quantity,
            })

        gm_char_inv = {
            'potions':   _gm_potions,
            'raw':       _gm_raw,
            'processed': _gm_processed,
            'equipment': _gm_equipment,
        }

    all_reagents       = list(Reagent.objects.order_by('name').values('id', 'name'))
    all_biomes         = list(Biome.objects.order_by('name').values('id', 'name'))
    all_items          = list(Item.objects.order_by('name').values('id', 'name', 'item_type'))
    all_potion_effects = list(PotionEffect.objects.order_by('name').values('id', 'name'))

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
        'manage_sb_form':        manage_sb_form,
        'sb_overview':           sb_overview,
        'active_tab':            request.GET.get('tab', 'expeditions'),
        'gm_characters':         gm_characters,
        'gm_selected_char':      gm_selected_char,
        'gm_char_inv':           gm_char_inv,
        'all_reagents':          all_reagents,
        'all_biomes':            all_biomes,
        'all_items':             all_items,
        'all_potion_effects':    all_potion_effects,
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
