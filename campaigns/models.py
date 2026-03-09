from django.db import models
from django.utils.text import slugify
from django.conf import settings
from accounts.models import Subscription

GAME_ROLES = [
    ("gm", "GM"),
    ("player", "Player")
]
# Create your models here.
class Campaign(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_campaigns")
    billing_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="billing_campaigns")
    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT, related_name="campaigns")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class CampaignMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="campaign_memberships")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="campaign_memberships")
    role = models.CharField(max_length=20, choices=GAME_ROLES, default="player", db_index=True)
    is_owner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "campaign"], name="unique_campaign_membership")
        ]
