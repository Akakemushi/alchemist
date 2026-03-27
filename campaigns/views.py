from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    CampaignCreateForm,
    CampaignJoinForm,
    CampaignManageForm,
    CampaignSearchForm,
    TransferOwnershipForm,
    _name_taken_for_owner,
)
from .models import Campaign, CampaignMembership, GameRole


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
    membership = get_object_or_404(
        CampaignMembership, campaign=campaign, user=request.user, is_owner=True
    )

    manage_form = CampaignManageForm(instance=campaign, user=request.user)
    other_members = CampaignMembership.objects.filter(
        campaign=campaign
    ).exclude(user=request.user).select_related('user')
    transfer_form = TransferOwnershipForm(campaign=campaign, current_user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

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

        elif action == 'delete':
            name = campaign.name
            campaign.delete()
            messages.success(request, f'Campaign "{name}" has been deleted.')
            return redirect('campaign_list')

    return render(request, 'campaigns/campaign_manage.html', {
        'campaign': campaign,
        'manage_form': manage_form,
        'transfer_form': transfer_form,
        'other_members': other_members,
        'has_password': bool(campaign.password),
    })
