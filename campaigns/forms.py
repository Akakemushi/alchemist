from django import forms

from .models import Campaign, CampaignMembership, GameRole


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
