from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db import models


class Kind(models.TextChoices):
    ITEM = ("item", "Item")
    RAW_REAGENT = ("raw_reagent", "Raw Reagent")
    CRUDE_REAGENT = ("crude_reagent", "Crude Reagent")
    REFINED_REAGENT = ("refined_reagent", "Refined Reagent")
    POTION = ("potion", "Potion")
    STORGSTRUM = ("storgstrum", "Storgstrum's Brew")

class State(models.TextChoices):
    CRUDE = ("crude", "Crude")
    REFINED = ("refined", "Refined")

class InventoryEntry(models.Model):
    character = models.ForeignKey("characters.Character", on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_entries")
    kind = models.CharField(max_length=20, choices=Kind.choices, db_index=True)
    quantity = models.PositiveSmallIntegerField(validators=[MaxValueValidator(999), MinValueValidator(1)], default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        owner = self.character.name if self.character else "No Owner"
        return f"{owner} - {self.get_kind_display()} x{self.quantity}"

class ReagentSample(models.Model):
    true_reagent = models.ForeignKey("reagents.Reagent", on_delete=models.PROTECT, null=True, blank=True, related_name="samples")
    inventory_entry = models.OneToOneField(InventoryEntry, on_delete=models.CASCADE, related_name="sample")
    observed_description = models.TextField(null=True, blank=True)
    found_biome = models.ForeignKey("reagents.Biome", on_delete=models.SET_NULL, null=True, blank=True, related_name="found_samples") # Can be blank in cases where it was simply given to the character.
    source_expedition = models.ForeignKey("campaigns.Expedition", on_delete=models.SET_NULL, null=True, blank=True, related_name="found_samples") # Null if obtained outside of an expedition (e.g., given by the DM).
    is_mundane = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.observed_description:
            preview = self.observed_description[:20]
            suffix = "..." if len(self.observed_description) > 20 else ""
            return f"{preview}{suffix} x{self.inventory_entry.quantity}"
        return f"Unidentified sample x{self.inventory_entry.quantity}"

    def clean(self):
        super().clean()
        if self.inventory_entry and self.inventory_entry.kind != Kind.RAW_REAGENT:
            raise ValidationError("ReagentSample can only be attached to a RAW_REAGENT inventory entry.")
        if self.is_mundane and self.true_reagent is not None:
            raise ValidationError({"true_reagent": "Mundane samples should not have a true reagent."})
        if not self.is_mundane and self.true_reagent is None:
            raise ValidationError({"true_reagent": "Non-mundane samples must have a true reagent."})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class ProcessedReagent(models.Model):
    inventory_entry = models.OneToOneField(InventoryEntry, on_delete=models.CASCADE, related_name="processed_reagent")
    reagent = models.ForeignKey("reagents.Reagent", on_delete=models.PROTECT, related_name="processed_reagents")
    state = models.CharField(max_length=10, choices=State.choices, default=State.CRUDE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.reagent} ({self.get_state_display()}) x{self.inventory_entry.quantity}"

    def clean(self):
        super().clean()

        if self.inventory_entry:
            if self.state == State.CRUDE and self.inventory_entry.kind != Kind.CRUDE_REAGENT:
                raise ValidationError("CRUDE processed reagents must use a CRUDE_REAGENT inventory entry.")
            if self.state == State.REFINED and self.inventory_entry.kind != Kind.REFINED_REAGENT:
                raise ValidationError("REFINED processed reagents must use a REFINED_REAGENT inventory entry.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class PotionBatch(models.Model):
    discovered_effect = models.ForeignKey("reagents.PotionEffect", on_delete=models.PROTECT, null=True, blank=True)
    inventory_entry = models.OneToOneField(InventoryEntry, on_delete=models.CASCADE, related_name="potion_batch")
    reagent_a = models.ForeignKey("reagents.Reagent", on_delete=models.PROTECT, related_name="uses_in_first_slot")
    reagent_b = models.ForeignKey("reagents.Reagent", on_delete=models.PROTECT, related_name="uses_in_second_slot")
    is_dud_known = models.BooleanField(default=False)
    potency = models.PositiveSmallIntegerField(validators=[MaxValueValidator(10), MinValueValidator(1)], null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        effect = str(self.discovered_effect) if self.discovered_effect else "Unknown Effect"
        return f"Potion: {effect} (level {self.potency or '?'})"

    def clean(self):
        super().clean()

        if self.inventory_entry and self.inventory_entry.kind != Kind.POTION:
            raise ValidationError("PotionBatch can only be attached to a POTION inventory entry.")
        if self.reagent_a_id == self.reagent_b_id:
            raise ValidationError("A potion batch must use two different reagents.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~models.Q(reagent_a=models.F("reagent_b")),
                name="potion_batch_distinct_reagents"
            )
        ]

class InventoryItem(models.Model):
    inventory_entry = models.OneToOneField(InventoryEntry, on_delete=models.CASCADE, related_name="item_entry")
    item = models.ForeignKey("items.Item", on_delete=models.PROTECT, related_name="inventory_items")

    def __str__(self):
        owner = self.inventory_entry.character.name if self.inventory_entry.character else "No Owner"
        return f"{self.item} (owned by {owner})"

    def clean(self):
        super().clean()
        if self.inventory_entry and self.inventory_entry.kind != Kind.ITEM:
            raise ValidationError("InventoryItem can only be attached to an ITEM inventory entry.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)