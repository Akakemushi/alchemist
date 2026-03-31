from django import forms

from characters.models import Character
from knowledge.models import CharacterReagentKnowledge
from reagents.models import Biome, Reagent

from .models import ApprovalStatus, Campaign, CampaignMembership, Expedition, GameRole


def _name_taken_for_owner(name, owner, exclude_pk=None):
    qs = Campaign.objects.filter(billing_owner=owner, name=name)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


# ── Shared widget helper ───────────────────────────────────────────────────────

def _add_class(fields):
    for field in fields.values():
        field.widget.attrs['class'] = 'form-control'


# ── Custom field for membership choices ───────────────────────────────────────

class MembershipChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.user.username}  ({obj.get_role_display()})"


# ── Forms ──────────────────────────────────────────────────────────────────────

class CampaignCreateForm(forms.Form):
    name = forms.CharField(max_length=100, label="Campaign Name")
    role = forms.ChoiceField(choices=GameRole.choices, label="Your Role")
    password = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False),
        label="Password (optional)",
        help_text="Leave blank for an open campaign anyone can join.",
    )
    confirm_password = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False),
        label="Confirm Password",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        _add_class(self.fields)

    def clean_name(self):
        name = self.cleaned_data['name']
        if self.user and _name_taken_for_owner(name, self.user):
            raise forms.ValidationError("You already own a campaign with this name.")
        return name

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


class CampaignSearchForm(forms.Form):
    q = forms.CharField(required=False, label="", widget=forms.TextInput(attrs={'placeholder': 'Search by campaign name…'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_class(self.fields)


class CampaignJoinForm(forms.Form):
    password = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False),
        label="Campaign Password",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_class(self.fields)


class CampaignManageForm(forms.ModelForm):
    new_password = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False),
        label="New Password",
        help_text="Fill in to set or change the password. Leave blank to keep the current one.",
    )
    confirm_password = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False),
        label="Confirm New Password",
    )
    clear_password = forms.BooleanField(
        required=False,
        label="Remove password protection",
    )

    class Meta:
        model = Campaign
        fields = ['name']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        _add_class(self.fields)

    def clean_name(self):
        name = self.cleaned_data['name']
        if self.user and _name_taken_for_owner(name, self.user, exclude_pk=self.instance.pk):
            raise forms.ValidationError("You already own a campaign with this name.")
        return name

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('new_password')
        cpw = cleaned.get('confirm_password')
        if pw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        if pw and cleaned.get('clear_password'):
            raise forms.ValidationError("You cannot set a new password and clear the password at the same time.")
        return cleaned


class ParticipantField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name}  ({obj.owner.username})"


class ExpeditionForm(forms.ModelForm):
    participants = ParticipantField(
        queryset=Character.objects.none(),
        required=False,
        label="Party Members",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Expedition
        fields = ['biome', 'target_reagent', 'search_mode', 'search_speed', 'search_at_night', 'hours']

    def __init__(self, *args, campaign, leader, **kwargs):
        super().__init__(*args, **kwargs)
        self._leader = leader

        self.fields['biome'].queryset = Biome.objects.all()
        self.fields['biome'].label_from_instance = lambda obj: obj.get_name_display()
        self.fields['biome'].empty_label = None

        known_ids = (
            CharacterReagentKnowledge.objects
            .filter(character=leader, knows_name=True)
            .values_list('reagent_id', flat=True)
        )
        self.fields['target_reagent'].queryset = Reagent.objects.filter(id__in=known_ids)
        self.fields['target_reagent'].required = False
        self.fields['target_reagent'].empty_label = 'No specific target'

        self.fields['participants'].queryset = (
            Character.objects
            .filter(campaign=campaign)
            .exclude(pk=leader.pk)
            .select_related('owner')
        )

        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxSelectMultiple, forms.CheckboxInput)):
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned = super().clean()
        target_reagent = cleaned.get('target_reagent')
        if target_reagent and self._leader:
            knows = CharacterReagentKnowledge.objects.filter(
                character=self._leader, reagent=target_reagent, knows_name=True,
            ).exists()
            if not knows:
                raise forms.ValidationError(
                    {'target_reagent': 'The expedition leader does not know the name of that reagent.'}
                )
        return cleaned


class GMExpeditionForm(forms.ModelForm):
    participants = ParticipantField(
        queryset=Character.objects.none(),
        required=False,
        label="Party Members",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Expedition
        fields = ['leader', 'biome', 'target_reagent', 'search_mode', 'search_speed', 'search_at_night', 'hours']

    def __init__(self, *args, campaign, **kwargs):
        super().__init__(*args, **kwargs)

        all_chars = (
            Character.objects
            .filter(campaign=campaign)
            .select_related('owner')
            .order_by('name')
        )
        self.fields['leader'].queryset = all_chars
        self.fields['leader'].label_from_instance = lambda obj: f"{obj.name}  ({obj.owner.username})"
        self.fields['leader'].empty_label = 'Select leader…'

        self.fields['biome'].queryset = Biome.objects.all()
        self.fields['biome'].label_from_instance = lambda obj: obj.get_name_display()
        self.fields['biome'].empty_label = None

        self.fields['target_reagent'].queryset = (
            Reagent.objects.select_related('category').order_by('name')
        )
        self.fields['target_reagent'].required = False
        self.fields['target_reagent'].empty_label = 'No specific target'

        self.fields['participants'].queryset = all_chars

        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxSelectMultiple, forms.CheckboxInput)):
                field.widget.attrs['class'] = 'form-control'


class ExpeditionFilterForm(forms.Form):
    _SORT_CHOICES = [
        ('pending_first', 'Pending first'),
        ('-created_at',   'Newest first'),
        ('created_at',    'Oldest first'),
        ('leader__name',  'Leader A–Z'),
        ('biome__name',   'Biome'),
        ('-executed_at',  'Execution time'),
    ]
    status    = forms.ChoiceField(
        choices=[('', 'All statuses')] + ApprovalStatus.choices,
        required=False, label='Status',
    )
    leader    = forms.ModelChoiceField(queryset=None, required=False, empty_label='Any leader')
    character = forms.ModelChoiceField(
        queryset=None, required=False, empty_label='Any character', label='Includes character',
    )
    biome     = forms.ModelChoiceField(queryset=Biome.objects.all(), required=False, empty_label='Any biome')
    night     = forms.ChoiceField(
        choices=[('', 'Day or night'), ('day', 'Day only'), ('night', 'Night only')],
        required=False, label='Time of day',
    )
    sort      = forms.ChoiceField(choices=_SORT_CHOICES, required=False, label='Sort by')

    def __init__(self, *args, campaign, **kwargs):
        super().__init__(*args, **kwargs)
        char_qs = (
            Character.objects
            .filter(campaign=campaign)
            .select_related('owner')
            .order_by('name')
        )
        lbl = lambda obj: f"{obj.name}  ({obj.owner.username})"
        self.fields['leader'].queryset = char_qs
        self.fields['leader'].label_from_instance = lbl
        self.fields['character'].queryset = char_qs
        self.fields['character'].label_from_instance = lbl
        self.fields['biome'].label_from_instance = lambda obj: obj.get_name_display()
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class TransferOwnershipForm(forms.Form):
    new_owner = MembershipChoiceField(queryset=None, label="Transfer to")

    def __init__(self, campaign, current_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_owner'].queryset = (
            CampaignMembership.objects
            .filter(campaign=campaign)
            .exclude(user=current_user)
            .select_related('user')
        )
        _add_class(self.fields)
