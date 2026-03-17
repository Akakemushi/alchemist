from django.core.exceptions import ValidationError
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


class EquipSlot(models.TextChoices):
    HEAD   = ("head",   "Head")
    NECK   = ("neck",   "Neck")
    ARMOR  = ("armor",  "Armor")
    ARM    = ("arm",    "Arm")
    HAND   = ("hand",   "Hand")
    HAND_1 = ("hand_1", "Main Hand")   # weapon or implement
    HAND_2 = ("hand_2", "Off Hand")    # weapon or implement (one-handed only)
    WAIST  = ("waist",  "Waist")
    FEET   = ("feet",   "Feet")
    RING_1 = ("ring_1", "Ring (1)")
    RING_2 = ("ring_2", "Ring (2)")


# Maps each slot to the set of item_type values allowed in it.
_SLOT_ALLOWED_TYPES = {
    EquipSlot.HEAD:   {"head"},
    EquipSlot.NECK:   {"neck"},
    EquipSlot.ARMOR:  {"armor"},
    EquipSlot.ARM:    {"arm"},
    EquipSlot.HAND:   {"hand"},
    EquipSlot.HAND_1: {"weapon", "implement"},
    EquipSlot.HAND_2: {"weapon", "implement"},
    EquipSlot.WAIST:  {"waist"},
    EquipSlot.FEET:   {"feet"},
    EquipSlot.RING_1: {"ring"},
    EquipSlot.RING_2: {"ring"},
}

# HAND_1 and HAND_2 share the two physical hands.
_SLOT_PAIRS = {
    EquipSlot.HAND_1: EquipSlot.HAND_2,
    EquipSlot.HAND_2: EquipSlot.HAND_1,
}


class EquippedItem(models.Model):
    character      = models.ForeignKey(Character, on_delete=models.CASCADE, related_name="equipped_items")
    inventory_item = models.OneToOneField("inventory.InventoryItem", on_delete=models.CASCADE, related_name="equipped_as")
    slot           = models.CharField(max_length=15, choices=EquipSlot.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["character", "slot"], name="unique_item_per_slot"),
        ]

    def __str__(self):
        return f"{self.character} — {self.get_slot_display()}: {self.inventory_item.item}"

    def clean(self):
        super().clean()
        if self.inventory_item_id and self.character_id:
            # Verify the inventory item belongs to this character.
            entry_character = self.inventory_item.inventory_entry.character
            if entry_character is None or entry_character.pk != self.character_id:
                raise ValidationError("You can only equip items from your own inventory.")
        if self.slot and self.inventory_item_id:
            item = self.inventory_item.item
            # Verify the item type is allowed in this slot.
            allowed = _SLOT_ALLOWED_TYPES.get(self.slot, set())
            if item.item_type not in allowed:
                allowed_display = " or ".join(sorted(allowed))
                raise ValidationError({
                    "inventory_item": (
                        f"The {self.get_slot_display()} slot accepts {allowed_display}, "
                        f"but '{item}' is type '{item.item_type}'."
                    )
                })
            # Two-handed validation for hand slots.
            paired_slot = _SLOT_PAIRS.get(self.slot)
            if paired_slot and self.character_id:
                if item.is_two_handed and self.slot == EquipSlot.HAND_2:
                    raise ValidationError({
                        "inventory_item": "Two-handed items must be equipped in the main hand slot."
                    })
                paired_qs = EquippedItem.objects.filter(
                    character_id=self.character_id, slot=paired_slot,
                ).select_related("inventory_item__item")
                if self.pk:
                    paired_qs = paired_qs.exclude(pk=self.pk)
                paired = paired_qs.first()
                if paired:
                    paired_item = paired.inventory_item.item
                    if item.is_two_handed:
                        raise ValidationError({
                            "inventory_item": (
                                f"Cannot equip a two-handed item while '{paired_item}' "
                                f"occupies the off-hand slot. Unequip it first."
                            )
                        })
                    if paired_item.is_two_handed:
                        raise ValidationError({
                            "slot": (
                                f"Cannot use the off-hand slot while '{paired_item}' "
                                f"(two-handed) is equipped in the main hand slot."
                            )
                        })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)