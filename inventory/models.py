from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Kind(models.TextChoices):
    ITEM = ("item", "Item")
    RAW_REAGENT = ("raw_reagent", "Raw Reagent")
    CRUDE_REAGENT = ("crude_reagent", "Crude Reagent")
    REFINED_REAGENT = ("refined_reagent", "Refined Reagent")
    POTION = ("potion", "Potion")

class State(models.TextChoices):
    RAW = ("raw", "Raw")
    CRUDE = ("crude", "Crude")
    REFINED = ("refined", "Refined")

class InventoryEntry(models.Model):
    character = models.ForeignKey("characters.Character", on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_entries")
    kind = models.CharField(choices=Kind.choices, db_index=True)
    quantity = models.PositiveSmallIntegerField(validators=[MaxValueValidator(999), MinValueValidator(1)], default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.character.name}-{self.kind_???}"

class ReagentSample(models.Model):
    true_reagent = models.ForeignKey("reagents.Reagent", on_delete=models.CASCADE, null=True, blank=True, related_name="samples")
    inventory_entry = models.ForeignKey(InventoryEntry, on_delete=models.CASCADE, related_name="samples")
    observed_description = models.CharField(max_length=500, null=True, blank=True)
    found_biome = models.CharField(max_length=20, null=True, blank=True) # Can be blank in cases where it was simply given to the character.
    is_mundane = models.BooleanField(default=True)

class ProcessedReagent(models.Model):


class PotionBatch(models.Model):
