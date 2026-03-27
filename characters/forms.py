from django import forms
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from campaigns.models import Campaign, CampaignMembership

from .models import Character

User = get_user_model()


def _add_class(fields):
    for field in fields.values():
        field.widget.attrs.setdefault('class', 'form-control')


def _campaign_qs(user):
    ids = CampaignMembership.objects.filter(user=user).values_list('campaign_id', flat=True)
    return Campaign.objects.filter(id__in=ids).select_related('created_by').order_by('name')


def _campaign_label(obj):
    creator = obj.created_by.username if obj.created_by else '?'
    return f"{obj.name} ({creator})"


_STAT_WIDGETS = {
    'level':               forms.NumberInput(attrs={'min': 1,  'max': 50}),
    'strength':            forms.NumberInput(attrs={'min': 1,  'max': 50}),
    'constitution':        forms.NumberInput(attrs={'min': 1,  'max': 50}),
    'dexterity':           forms.NumberInput(attrs={'min': 1,  'max': 50}),
    'intelligence':        forms.NumberInput(attrs={'min': 1,  'max': 50}),
    'wisdom':              forms.NumberInput(attrs={'min': 1,  'max': 50}),
    'charisma':            forms.NumberInput(attrs={'min': 1,  'max': 50}),
    'alchemy_bonus':        forms.NumberInput(attrs={'min': 0,  'max': 50}),
    'arcana_bonus':         forms.NumberInput(attrs={'min': 0,  'max': 50}),
    'dungeoneering_bonus':  forms.NumberInput(attrs={'min': 0,  'max': 50}),
    'history_bonus':        forms.NumberInput(attrs={'min': 0,  'max': 50}),
    'insight_bonus':        forms.NumberInput(attrs={'min': 0,  'max': 50}),
    'nature_bonus':         forms.NumberInput(attrs={'min': 0,  'max': 50}),
    'perception_bonus':     forms.NumberInput(attrs={'min': 0,  'max': 50}),
}

_STAT_FIELDS = [
    'name', 'level',
    'strength', 'constitution', 'dexterity', 'intelligence', 'wisdom', 'charisma',
    'alchemy_bonus', 'arcana_bonus', 'dungeoneering_bonus', 'history_bonus',
    'insight_bonus', 'nature_bonus', 'perception_bonus',
    'has_darkvision', 'has_lowlightvision', 'has_tremorsense',
    'image',
]


class CharacterEditForm(forms.ModelForm):
    class Meta:
        model = Character
        fields = _STAT_FIELDS
        widgets = _STAT_WIDGETS

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        _add_class(self.fields)
        for fname in ('has_darkvision', 'has_lowlightvision', 'has_tremorsense'):
            self.fields[fname].widget.attrs['class'] = 'form-check-input'


class CharacterCreateForm(CharacterEditForm):
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.none(),
        required=False,
        empty_label='No Campaign',
        label='Campaign',
    )
    field_order = ['name', 'campaign'] + _STAT_FIELDS[1:]  # name first, then campaign, then rest

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        if user:
            self.fields['campaign'].queryset = _campaign_qs(user)
        self.fields['campaign'].label_from_instance = _campaign_label
        self.fields['campaign'].widget.attrs['class'] = 'form-control'


class CharacterCopyForm(forms.Form):
    name = forms.CharField(max_length=50, label='Name for Copy')
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.none(),
        required=False,
        empty_label='No Campaign',
        label='Target Campaign',
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['campaign'].queryset = _campaign_qs(user)
        self.fields['campaign'].label_from_instance = _campaign_label
        _add_class(self.fields)


class CharacterMoveInForm(forms.Form):
    """Used when moving a no campaign character into a campaign."""
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.none(),
        required=True,
        label='Target Campaign',
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['campaign'].queryset = _campaign_qs(user)
        self.fields['campaign'].label_from_instance = _campaign_label
        _add_class(self.fields)


class CharacterTransferForm(forms.Form):
    username = forms.CharField(max_length=150, label='Transfer to Username')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_class(self.fields)

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            self._target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError(f'No user found with username "{username}".')
        return username

    def get_target_user(self):
        return getattr(self, '_target_user', None)
