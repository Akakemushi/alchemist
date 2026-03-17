from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

class ItemType(models.TextChoices):
    ARM = ("arm", "Arm Slot Item")
    ARMOR = ("armor", "Armor")
    BOOK = ("book", "Book")
    FEET = ("feet", "Feet Slot Item")
    HAND = ("hand", "Hand Slot Item")
    HEAD = ("head", "Head Slot Item")
    IMPLEMENT = ("implement", "Implement")
    NECK = ("neck", "Neck Slot Item")
    RING = ("ring", "Ring Slot Item")
    TRAP = ("trap", "Trap")
    WAIST = ("waist", "Waist Slot Item")
    WEAPON = ("weapon", "Weapon")
    WONDROUS = ("wondrous", "Wondrous Item")

class RollType(models.TextChoices):
    ALCHEMY = ("alchemy", "Alchemy")
    ARCANA = ("arcana", "Arcana")
    DUNGEONEERING = ("dungeoneering", "Dungeoneering")
    HISTORY = ("history", "History")
    INSIGHT = ("insight", "Insight")
    NATURE = ("nature", "Nature")
    PERCEPTION = ("perception", "Perception")
    TRAPPING = ("trapping", "Trapping")
    # add more as needed

class StackingRule(models.TextChoices):
    ITEM_BONUS = ("item_bonus", "Item Bonus")
    ENHANCEMENT_BONUS = ("enhancement_bonus", "Enhancement Bonus")
    PROFICIENCY_BONUS = ("proficiency_bonus", "Proficiency Bonus")
    TRAINING_BONUS = ("training_bonus", "Training Bonus")
    UNTYPED_BONUS = ("untyped_bonus", "Bonus")

class ModifierType(models.TextChoices):
    FLAT = ("flat", "Flat Modifier")
    MULTIPLIER = ("multiplier", "Roll Multiplier")
    DICE = ("dice", "Bonus Dice Roll")


class Item(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    item_type = models.CharField(choices=ItemType.choices, max_length=20, default=ItemType.WONDROUS)
    is_two_handed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.is_two_handed and self.item_type not in (ItemType.WEAPON, ItemType.IMPLEMENT):
            raise ValidationError({"is_two_handed": "Only weapons and implements can be two-handed."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)

class ItemModifier(models.Model):
    applies_to_party = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="modifiers")
    bonus_value = models.SmallIntegerField()  # allow negatives if you ever want
    roll_type = models.CharField(max_length=20, choices=RollType.choices)
    stacking_rule = models.CharField(max_length=20, choices=StackingRule.choices, default=StackingRule.ITEM_BONUS)
    modifier_type = models.CharField(max_length=20, choices=ModifierType.choices, default=ModifierType.FLAT)
    required_biome = models.ForeignKey("reagents.Biome", on_delete=models.PROTECT, null=True, blank=True, related_name="restricted_modifiers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # At most one unrestricted modifier per roll type per item (required_biome is null).
            models.UniqueConstraint(
                fields=["item", "roll_type"],
                condition=models.Q(required_biome__isnull=True),
                name="unique_global_modifier_per_roll_type",
            ),
            # At most one biome-specific modifier per (item, roll_type, biome).
            models.UniqueConstraint(
                fields=["item", "roll_type", "required_biome"],
                condition=models.Q(required_biome__isnull=False),
                name="unique_biome_modifier_per_roll_type",
            ),
        ]