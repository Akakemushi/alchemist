from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from campaigns.models import CampaignMembership, GameRole
from inventory.models import (
    InventoryEntry, ReagentSample, ProcessedReagent,
    PotionBatch, InventoryItem, Kind,
)
from knowledge.models import (
    CharacterReagentKnowledge, CharacterReagentEffect,
    CharacterReagentBiome, CharacterReagentMix,
)

from .forms import (
    CharacterCreateForm, CharacterEditForm, CharacterCopyForm,
    CharacterMoveInForm, CharacterTransferForm,
)
from .models import Character

User = get_user_model()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _available_slug(name, owner, campaign, exclude_pk=None):
    """Return a slug unique in the target scope, appending -2, -3, … if needed."""
    base = slugify(name)
    slug = base
    n = 1
    xpk = exclude_pk or 0
    if campaign is not None:
        while Character.objects.filter(campaign=campaign, slug=slug).exclude(pk=xpk).exists():
            slug = f'{base}-{n}'
            n += 1
    else:
        while Character.objects.filter(owner=owner, slug=slug, campaign__isnull=True).exclude(pk=xpk).exists():
            slug = f'{base}-{n}'
            n += 1
    return slug


def _name_conflict(name, campaign, owner, exclude_pk=None):
    """Return an error string if name conflicts in target scope, else None."""
    xpk = exclude_pk or 0
    if campaign is not None:
        if Character.objects.filter(name=name, campaign=campaign).exclude(pk=xpk).exists():
            return f'A character named "{name}" already exists in that campaign.'
    else:
        slug = slugify(name)
        if Character.objects.filter(owner=owner, slug=slug, campaign__isnull=True).exclude(pk=xpk).exists():
            return f'You already have a no campaign character with that name.'
    return None


def _can_edit(user, character):
    """True if user may edit this character's stats/name/image."""
    if user == character.owner:
        return not character.is_locked or character.campaign is None
    if character.campaign:
        return CampaignMembership.objects.filter(
            user=user, campaign=character.campaign,
        ).filter(Q(role=GameRole.GM) | Q(is_owner=True)).exists()
    return False


def _deep_copy_character(original, new_owner, new_campaign, new_name):
    """
    Deep-copy original to new_owner/new_campaign.
    Copies stats, inventory (minus equipped state and source_expedition),
    and current knowledge state (not the event log).
    """
    slug = _available_slug(new_name, new_owner, new_campaign)

    new_char = Character(
        name=new_name,
        slug=slug,
        campaign=new_campaign,
        home_campaign=new_campaign,  # chains immediately if placed in a campaign, else None
        owner=new_owner,
        level=original.level,
        strength=original.strength,
        constitution=original.constitution,
        dexterity=original.dexterity,
        intelligence=original.intelligence,
        wisdom=original.wisdom,
        charisma=original.charisma,
        alchemy_bonus=original.alchemy_bonus,
        arcana_bonus=original.arcana_bonus,
        dungeoneering_bonus=original.dungeoneering_bonus,
        history_bonus=original.history_bonus,
        insight_bonus=original.insight_bonus,
        nature_bonus=original.nature_bonus,
        perception_bonus=original.perception_bonus,
        has_darkvision=original.has_darkvision,
        has_lowlightvision=original.has_lowlightvision,
        has_tremorsense=original.has_tremorsense,
        image=original.image,
        is_locked=False,
    )
    new_char.save()

    # ── Inventory ──────────────────────────────────────────────
    for entry in original.inventory_entries.select_related(
        'sample', 'processed_reagent', 'potion_batch', 'item_entry'
    ):
        new_entry = InventoryEntry.objects.create(
            character=new_char,
            kind=entry.kind,
            quantity=entry.quantity,
        )
        if entry.kind == Kind.RAW_REAGENT and hasattr(entry, 'sample'):
            s = entry.sample
            ReagentSample.objects.create(
                inventory_entry=new_entry,
                true_reagent=s.true_reagent,
                observed_description=s.observed_description,
                found_biome=s.found_biome,
                source_expedition=None,   # nulled — copy wasn't on that expedition
                is_mundane=s.is_mundane,
            )
        elif entry.kind in (Kind.CRUDE_REAGENT, Kind.REFINED_REAGENT) and hasattr(entry, 'processed_reagent'):
            pr = entry.processed_reagent
            ProcessedReagent.objects.create(
                inventory_entry=new_entry,
                reagent=pr.reagent,
                state=pr.state,
            )
        elif entry.kind == Kind.POTION and hasattr(entry, 'potion_batch'):
            pb = entry.potion_batch
            PotionBatch.objects.create(
                inventory_entry=new_entry,
                discovered_effect=pb.discovered_effect,
                reagent_a=pb.reagent_a,
                reagent_b=pb.reagent_b,
                is_dud_known=pb.is_dud_known,
                potency=pb.potency,
            )
        elif entry.kind == Kind.ITEM and hasattr(entry, 'item_entry'):
            InventoryItem.objects.create(
                inventory_entry=new_entry,
                item=entry.item_entry.item,
            )
        # Kind.STORGSTRUM has no sub-model — InventoryEntry alone is sufficient.

    # ── Knowledge state (not event log) ────────────────────────
    for k in original.reagent_knowledge.all():
        CharacterReagentKnowledge.objects.create(
            character=new_char, reagent=k.reagent,
            knows_name=k.knows_name, knows_description=k.knows_description,
            knows_upv=k.knows_upv, knows_rpv=k.knows_rpv,
            knows_category=k.knows_category, knows_rarity=k.knows_rarity,
        )
    for e in original.reagent_effect_knowledge.all():
        CharacterReagentEffect.objects.create(
            character=new_char, reagent=e.reagent, effect=e.effect,
        )
    for b in original.reagent_biome_knowledge.all():
        CharacterReagentBiome.objects.create(
            character=new_char, reagent=b.reagent, biome=b.biome,
        )
    for m in original.reagent_mixes.all():
        CharacterReagentMix.objects.create(
            character=new_char, reagent_a=m.reagent_a, reagent_b=m.reagent_b,
            mix_result=m.mix_result, discovered_effect=m.discovered_effect,
        )

    return new_char


# ── Views ──────────────────────────────────────────────────────────────────────

@login_required
def character_list(request):
    characters = (
        Character.objects
        .filter(owner=request.user)
        .select_related('campaign')
        .order_by('campaign__name', 'name')
    )
    return render(request, 'characters/character_list.html', {'characters': characters})


@login_required
def character_create(request):
    if request.method == 'POST':
        form = CharacterCreateForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            campaign = form.cleaned_data.get('campaign')
            name = form.cleaned_data['name']
            error = _name_conflict(name, campaign, request.user)
            if error:
                form.add_error('name', error)
            else:
                character = form.save(commit=False)
                character.owner = request.user
                character.campaign = campaign
                character.home_campaign = campaign  # chains on first join; None if campaign-less
                character.slug = _available_slug(name, request.user, campaign)
                character.is_locked = False
                character.save()
                messages.success(request, f'Character "{character.name}" created.')
                return redirect('character_list')
    else:
        form = CharacterCreateForm(user=request.user)
    return render(request, 'characters/character_create.html', {'form': form})


@login_required
def character_edit(request, pk):
    character = get_object_or_404(Character, pk=pk)
    if not _can_edit(request.user, character):
        if character.owner != request.user:
            raise Http404
        # Owner but locked — redirect to list with message
        messages.error(request, f'"{character.name}" is locked. Ask your GM to unlock it before editing.')
        return redirect('character_list')

    if request.method == 'POST':
        form = CharacterEditForm(request.POST, request.FILES, instance=character, user=request.user)
        if form.is_valid():
            name = form.cleaned_data['name']
            error = _name_conflict(name, character.campaign, character.owner, exclude_pk=character.pk)
            if error:
                form.add_error('name', error)
            else:
                char = form.save(commit=False)
                if name != character.name:
                    char.slug = _available_slug(name, character.owner, character.campaign, exclude_pk=character.pk)
                char.save()
                messages.success(request, f'"{char.name}" updated.')
                return redirect('character_list')
    else:
        form = CharacterEditForm(instance=character, user=request.user)

    return render(request, 'characters/character_edit.html', {
        'form': form,
        'character': character,
    })


@login_required
def character_copy(request, pk):
    character = get_object_or_404(Character, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = CharacterCopyForm(request.POST, user=request.user)
        if form.is_valid():
            new_name = form.cleaned_data['name']
            target_campaign = form.cleaned_data.get('campaign')
            error = _name_conflict(new_name, target_campaign, request.user)
            if error:
                form.add_error('name', error)
            else:
                with transaction.atomic():
                    new_char = _deep_copy_character(character, request.user, target_campaign, new_name)
                scope = target_campaign.name if target_campaign else 'no campaign'
                messages.success(request, f'"{new_char.name}" created as a copy in {scope}.')
                return redirect('character_list')
    else:
        form = CharacterCopyForm(initial={'name': character.name}, user=request.user)

    return render(request, 'characters/character_copy.html', {
        'form': form,
        'character': character,
    })


@login_required
def character_move(request, pk):
    character = get_object_or_404(Character, pk=pk, owner=request.user)

    if character.campaign is not None:
        # Moving OUT to no campaign
        if request.method == 'POST':
            from campaigns.signals import _resolve_slug_for_no_campaign
            _resolve_slug_for_no_campaign(character)
            character.campaign = None
            character.is_locked = False
            character.save(update_fields=['campaign', 'slug', 'is_locked'])
            messages.success(request, f'"{character.name}" moved to no campaign. History preserved.')
            return redirect('character_list')
        return render(request, 'characters/character_move.html', {
            'character': character,
            'direction': 'out',
        })
    elif character.home_campaign_id is not None:
        # Moving IN — chained character: can only rejoin its one campaign
        target = character.home_campaign
        move_error = None
        if request.method == 'POST':
            error = _name_conflict(character.name, target, request.user)
            if error:
                move_error = error + ' Rename the character first, or make a copy instead.'
            else:
                character.campaign = target
                character.slug = _available_slug(character.name, request.user, target, exclude_pk=character.pk)
                character.save(update_fields=['campaign', 'slug'])
                messages.success(request, f'"{character.name}" rejoined {target.name}.')
                return redirect('character_list')
        return render(request, 'characters/character_move.html', {
            'character': character,
            'direction': 'in',
            'is_chained': True,
            'move_error': move_error,
        })
    else:
        # Moving IN — unchained character: show campaign picker
        form = CharacterMoveInForm(request.POST or None, user=request.user)
        if request.method == 'POST' and form.is_valid():
            target = form.cleaned_data['campaign']
            error = _name_conflict(character.name, target, request.user)
            if error:
                form.add_error('campaign', error + ' Rename the character first, or make a copy instead.')
            else:
                with transaction.atomic():
                    character.knowledge_events.all().delete()  # purge logs from any prior campaign
                    character.campaign = target
                    character.home_campaign = target  # chains here for the first time
                    character.slug = _available_slug(character.name, request.user, target, exclude_pk=character.pk)
                    character.save(update_fields=['campaign', 'home_campaign', 'slug'])
                messages.success(request, f'"{character.name}" moved into {target.name}.')
                return redirect('character_list')
        return render(request, 'characters/character_move.html', {
            'character': character,
            'form': form,
            'direction': 'in',
            'is_chained': False,
        })


@login_required
def character_delete(request, pk):
    character = get_object_or_404(Character, pk=pk, owner=request.user)
    if request.method == 'POST':
        name = character.name
        character.delete()
        messages.success(request, f'"{name}" has been deleted.')
        return redirect('character_list')
    return render(request, 'characters/character_delete.html', {'character': character})


@login_required
def character_transfer(request, pk):
    character = get_object_or_404(Character, pk=pk, owner=request.user)
    found_user = None
    confirm_error = None

    if request.method == 'POST':
        action = request.POST.get('action', 'find')

        if action == 'find':
            form = CharacterTransferForm(request.POST)
            if form.is_valid():
                found_user = form.get_target_user()
                if found_user == request.user:
                    form.add_error('username', 'You already own this character.')
                    found_user = None
        elif action == 'confirm':
            target_id = request.POST.get('target_user_id')
            target_user = get_object_or_404(User, pk=target_id)
            error = _name_conflict(character.name, character.campaign, target_user, exclude_pk=character.pk)
            if error:
                found_user = target_user  # keep confirmation UI visible so the error is shown
                confirm_error = error + ' The recipient must resolve this conflict before you can transfer.'
            else:
                character.owner = target_user
                character.home_campaign = None  # reset chain — receiver should not be locked to sender's campaign
                character.slug = _available_slug(character.name, target_user, character.campaign)
                character.save(update_fields=['owner', 'home_campaign', 'slug'])
                messages.success(request, f'"{character.name}" transferred to {target_user.username}.')
                return redirect('character_list')
            form = CharacterTransferForm()
        else:
            form = CharacterTransferForm()
    else:
        form = CharacterTransferForm()

    return render(request, 'characters/character_transfer.html', {
        'form': form,
        'character': character,
        'found_user': found_user,
        'confirm_error': confirm_error,
    })
