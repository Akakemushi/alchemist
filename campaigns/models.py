from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.conf import settings

class GameRole(models.TextChoices):
    GM     = "gm",     "GM"
    PLAYER = "player", "Player"

class SearchMode(models.TextChoices):
    TOGETHER = ("together", "Together")
    SPLITUP  = ("splitup",  "Split Up")

class SearchSpeed(models.TextChoices):
    NORMAL = ("normal", "Normal Speed")
    RUSH   = ("rush", "Rush Job")

class ApprovalStatus(models.TextChoices):
    PENDING  = ("pending",  "Pending")
    APPROVED = ("approved", "Approved")
    DENIED   = ("denied",   "Denied")

# Create your models here.
class Campaign(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="created_campaigns", null=True)
    billing_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="billing_campaigns")
    subscription = models.ForeignKey("accounts.Subscription", on_delete=models.PROTECT, related_name="campaigns", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            n = 1
            while Campaign.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]

class CampaignMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="campaign_memberships")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="campaign_memberships")
    role = models.CharField(max_length=20, choices=GameRole.choices, default=GameRole.PLAYER, db_index=True)
    is_owner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} in {self.campaign} ({self.role})"

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "campaign"], name="unique_campaign_membership")]
        ordering = ["-created_at"]


class Expedition(models.Model):
    campaign        = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="expeditions")
    leader          = models.ForeignKey("characters.Character", on_delete=models.PROTECT, related_name="led_expeditions")
    biome           = models.ForeignKey("reagents.Biome", on_delete=models.PROTECT, related_name="expeditions")
    target_reagent  = models.ForeignKey("reagents.Reagent", on_delete=models.PROTECT, null=True, blank=True, related_name="targeted_expeditions")
    search_mode     = models.CharField(max_length=10, choices=SearchMode.choices, default=SearchMode.TOGETHER)
    search_speed    = models.CharField(max_length=10, choices=SearchSpeed.choices, default=SearchSpeed.NORMAL)
    search_at_night = models.BooleanField(default=False)
    hours           = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    approval_status = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    approved_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_expeditions")
    approved_at     = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.campaign} — {self.biome} expedition"

    def clean(self):
        super().clean()
        # Leader's character must belong to this campaign.
        if self.leader_id and self.campaign_id:
            if self.leader.campaign_id != self.campaign_id:
                raise ValidationError({"leader": "The expedition leader must be a character in this campaign."})
        # If a target reagent is set, the leader must know its name.
        if self.target_reagent_id and self.leader_id:
            from knowledge.models import CharacterReagentKnowledge
            knows = CharacterReagentKnowledge.objects.filter(
                character_id=self.leader_id,
                reagent_id=self.target_reagent_id,
                knows_name=True,
            ).exists()
            if not knows:
                raise ValidationError({"target_reagent": "The expedition leader must know the name of the target reagent."})
        # approved_by and approved_at must be set together.
        if bool(self.approved_by_id) != bool(self.approved_at):
            raise ValidationError("approved_by and approved_at must both be set or both be empty.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class Participation(models.Model):
    character  = models.ForeignKey("characters.Character", on_delete=models.CASCADE, related_name="participations")
    expedition = models.ForeignKey(Expedition, on_delete=models.CASCADE, related_name="participants")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.character} in {self.expedition}"

    def clean(self):
        super().clean()
        if self.character_id and self.expedition_id:
            if self.character.campaign_id != self.expedition.campaign_id:
                raise ValidationError({"character": "Participants must be characters in the expedition's campaign."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["character", "expedition"], name="unique_character_per_expedition"),
        ]
