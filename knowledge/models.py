from django.core.exceptions import ValidationError
from django.db import models


class HowLearned(models.TextChoices):
    UNREFINED_TEST  = "unrefined_test",  "Unrefined Test"
    REFINED_TEST    = "refined_test",    "Refined Test"
    USED_POTION     = "used_potion",     "Used Potion"
    EDUCATION       = "education",       "Education"
    FIELD_DISCOVERY = "field_discovery", "Field Discovery"
    FROM_GM         = "from_gm",         "From GM"


class WhatLearned(models.TextChoices):
    LEARNED_NAME        = "learned_name",        "Learned Name"
    LEARNED_DESCRIPTION = "learned_description", "Learned Description"
    LEARNED_UPV         = "learned_upv",         "Learned UPV"
    LEARNED_RPV         = "learned_rpv",         "Learned RPV"
    LEARNED_CATEGORY    = "learned_category",    "Learned Category"
    LEARNED_RARITY      = "learned_rarity",      "Learned Rarity"
    LEARNED_BIOME       = "learned_biome",       "Learned Biome"
    LEARNED_EFFECT      = "learned_effect",      "Learned Effect"


class MixResult(models.TextChoices):
    SUCCESS = "success", "Success"
    DUD     = "dud",     "Dud"


class CharacterReagentKnowledge(models.Model):
    """Current state of a character's knowledge about a specific reagent."""
    character       = models.ForeignKey("characters.Character", on_delete=models.CASCADE, related_name="reagent_knowledge")
    reagent         = models.ForeignKey("reagents.Reagent",     on_delete=models.PROTECT, related_name="character_knowledge")
    knows_name        = models.BooleanField(default=False)
    knows_description = models.BooleanField(default=False)
    knows_upv         = models.BooleanField(default=False)
    knows_rpv         = models.BooleanField(default=False)
    knows_category    = models.BooleanField(default=False)
    knows_rarity      = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.character} — knowledge of {self.reagent}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["character", "reagent"], name="unique_character_reagent_knowledge")
        ]


class CharacterReagentEffect(models.Model):
    """Records that a character knows a specific reagent has a specific potion effect."""
    character = models.ForeignKey("characters.Character",    on_delete=models.CASCADE, related_name="reagent_effect_knowledge")
    reagent   = models.ForeignKey("reagents.Reagent",        on_delete=models.PROTECT, related_name="known_effects_by_characters")
    effect    = models.ForeignKey("reagents.PotionEffect",   on_delete=models.PROTECT, related_name="known_for_reagents")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.character} knows {self.reagent} → {self.effect}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["character", "reagent", "effect"], name="unique_character_reagent_effect")
        ]


class CharacterReagentBiome(models.Model):
    """Records that a character knows a specific reagent can be found in a specific biome."""
    character = models.ForeignKey("characters.Character", on_delete=models.CASCADE, related_name="reagent_biome_knowledge")
    reagent   = models.ForeignKey("reagents.Reagent",     on_delete=models.PROTECT, related_name="known_biomes_by_characters")
    biome     = models.ForeignKey("reagents.Biome",       on_delete=models.PROTECT, related_name="known_for_reagents")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.character} knows {self.reagent} in {self.biome}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["character", "reagent", "biome"], name="unique_character_reagent_biome")
        ]


class CharacterReagentMix(models.Model):
    """
    Permanent log of every reagent combination a character has attempted.
    Prevents players from wasting resources on repeat dud experiments.
    Reagents are stored in canonical order (lower PK in reagent_a) so the
    unique constraint catches (A, B) and (B, A) as the same mix.
    """
    character        = models.ForeignKey("characters.Character",  on_delete=models.CASCADE, related_name="reagent_mixes")
    reagent_a        = models.ForeignKey("reagents.Reagent",       on_delete=models.PROTECT, related_name="mixes_as_first")
    reagent_b        = models.ForeignKey("reagents.Reagent",       on_delete=models.PROTECT, related_name="mixes_as_second")
    mix_result       = models.CharField(max_length=10, choices=MixResult.choices)
    discovered_effect = models.ForeignKey("reagents.PotionEffect", on_delete=models.PROTECT, null=True, blank=True, related_name="discovered_via_mix")
    discovered_at    = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.reagent_a_id and self.reagent_b_id:
            if self.reagent_a_id == self.reagent_b_id:
                raise ValidationError("Cannot mix a reagent with itself.")
            # Normalize to canonical order so the unique constraint is reliable
            if self.reagent_a_id > self.reagent_b_id:
                self.reagent_a_id, self.reagent_b_id = self.reagent_b_id, self.reagent_a_id

        if self.mix_result == MixResult.DUD and self.discovered_effect_id is not None:
            raise ValidationError({"discovered_effect": "A dud mix cannot have a discovered effect."})
        if self.mix_result == MixResult.SUCCESS and self.discovered_effect_id is None:
            raise ValidationError({"discovered_effect": "A successful mix must have a discovered effect."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.character}: {self.reagent_a} + {self.reagent_b} → {self.get_mix_result_display()}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["character", "reagent_a", "reagent_b"], name="unique_character_mix")
        ]


class KnowledgeUnlockEvent(models.Model):
    """
    Immutable audit log — one row per atomic piece of knowledge gained.
    Every event references a reagent. Biome and effect are set only when
    what_learned is LEARNED_BIOME or LEARNED_EFFECT respectively.
    """
    character   = models.ForeignKey("characters.Character",  on_delete=models.CASCADE, related_name="knowledge_events")
    reagent     = models.ForeignKey("reagents.Reagent",      on_delete=models.PROTECT, related_name="knowledge_events")
    biome       = models.ForeignKey("reagents.Biome",        on_delete=models.PROTECT, null=True, blank=True, related_name="knowledge_events")
    effect      = models.ForeignKey("reagents.PotionEffect", on_delete=models.PROTECT, null=True, blank=True, related_name="knowledge_events")
    how_learned = models.CharField(max_length=20, choices=HowLearned.choices)
    what_learned = models.CharField(max_length=25, choices=WhatLearned.choices)
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    _REQUIRES_BIOME  = {WhatLearned.LEARNED_BIOME}
    _REQUIRES_EFFECT = {WhatLearned.LEARNED_EFFECT}

    def clean(self):
        super().clean()
        if self.what_learned in self._REQUIRES_BIOME and not self.biome_id:
            raise ValidationError({"biome": "LEARNED_BIOME events must reference a biome."})
        if self.what_learned not in self._REQUIRES_BIOME and self.biome_id:
            raise ValidationError({"biome": "Biome should only be set on LEARNED_BIOME events."})
        if self.what_learned in self._REQUIRES_EFFECT and not self.effect_id:
            raise ValidationError({"effect": "LEARNED_EFFECT events must reference an effect."})
        if self.what_learned not in self._REQUIRES_EFFECT and self.effect_id:
            raise ValidationError({"effect": "Effect should only be set on LEARNED_EFFECT events."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.character} — {self.get_what_learned_display()} via {self.get_how_learned_display()}"

    class Meta:
        ordering = ["-created_at"]
