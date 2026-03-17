from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.text import slugify
from django.conf import settings

# class Party(models.Model):
#     name = models.CharField(max_length=100)
#     slug = models.SlugField(max_length=100, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)

class Character(models.Model):
    name = models.CharField(max_length=50, db_index=True)
    slug = models.SlugField(max_length=50, blank=True)
    campaign = models.ForeignKey("campaigns.Campaign", null=True, blank=True, on_delete=models.SET_NULL, related_name="characters")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="characters")
    # party = models.ForeignKey(Party, on_delete=models.SET_NULL, null=True, blank=True, related_name="characters")
    level = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)], default=1)
    strength = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)], default=10)
    constitution = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)], default=10)
    dexterity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)], default=10)
    intelligence = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)], default=10)
    wisdom = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)], default=10)
    charisma = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)], default=10)
    alchemy_bonus = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(50)], default=0)
    arcana_bonus = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(50)], default=0)
    dungeoneering_bonus = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(50)], default=0)
    history_bonus = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(50)], default=0)
    insight_bonus = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(50)], default=0)
    nature_bonus = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(50)], default=0)
    perception_bonus = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(50)], default=0)
    #items = models.ManyToManyField("item.Item", through="item.CharacterItem", related_name="characters", blank=True) this was commented out in favor of the new inventory system.
    has_darkvision = models.BooleanField(default=False)
    has_lowlightvision = models.BooleanField(default=False)
    has_tremorsense = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "campaign"],
                condition=models.Q(campaign__isnull=False),
                name="unique_character_name_per_campaign",
            ),
            models.UniqueConstraint(
                fields=["campaign", "slug"],
                condition=models.Q(campaign__isnull=False),
                name="unique_slug_per_campaign",
            ),
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(campaign__isnull=True),
                name="unique_slug_no_campaign",
            ),
        ]

# The below has been commented out in favor of the new inventory system.
# class CharacterItem(models.Model):
#     character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="inventory")
#     item = models.ForeignKey("item.Item", on_delete=models.PROTECT, related_name="owned_by")
#     quantity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
#     is_equipped = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         constraints = [
#             models.UniqueConstraint(fields=["character", "item"], name="uniq_character_item")
#         ]