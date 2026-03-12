from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Item(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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