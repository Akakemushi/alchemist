from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Item(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class CharacterItem(models.Model):
    character = models.ForeignKey("character.Character", on_delete=models.CASCADE, related_name="inventory")
    item = models.ForeignKey("item.Item", on_delete=models.PROTECT, related_name="owned_by")
    quantity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    is_equipped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["character", "item"], name="uniq_character_item")
        ]

class RollType(models.TextChoices):
    FORAGE = "forage", "Forage"
    REFINE = "refine", "Refine"
    TRAP = "trap", "Trap Animals"
    ALCHEMY = "alchemy", "Alchemy Check"
    # add more as needed

class ItemModifier(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="modifiers")
    roll_type = models.CharField(max_length=20, choices=RollType.choices)
    bonus = models.SmallIntegerField()  # allow negatives if you ever want
    applies_to_party = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)