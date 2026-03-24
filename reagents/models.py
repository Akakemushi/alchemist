from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    uses_cluster_dice = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Rarity(models.Model):
    name = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(max_length=20, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
class Reagent(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    upv = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(9)])
    rpv = models.PositiveSmallIntegerField(validators=[MinValueValidator(2), MaxValueValidator(10)])
    description = models.TextField(blank=True, null=True)
    search_dc = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(60)])
    refine_dc = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(60)])
    cluster_dice_count = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(10)])
    cluster_dice_sides = models.PositiveSmallIntegerField(
        blank=True,
        null=True, 
        choices=[(4, "d4"), (6, "d6"), (8, "d8"), (10, "d10"), (12, "d12"), (20, "d20")]
        )
    category = models.ForeignKey(Category, related_name='reagents', on_delete=models.PROTECT)
    rarity = models.ForeignKey(Rarity, related_name='reagents', on_delete=models.PROTECT)
    image = models.ImageField(upload_to="reagents/", blank=True, null=True)
    poisonous = models.BooleanField(default=False)
    vibration = models.BooleanField(default=False)
    light_source = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    def clean(self):
        super().clean()
        # --- RPV must be greater than UPV ---
        if self.upv is not None and self.rpv is not None:
            if self.rpv <= self.upv:
                raise ValidationError({
                    "rpv": "RPV must be greater than UPV."
                })
        # Make sure that the dice equasion is complete (contains both number of dice and dice size)
        if (self.cluster_dice_count is None) != (self.cluster_dice_sides is None):
            raise ValidationError("Cluster dice must include both count and sides (or neither).")

        if self.category:
            # For foraging (aka non-carves): require the cluster dice to be set.
            if self.category.uses_cluster_dice:
                if self.cluster_dice_count is None or self.cluster_dice_sides is None:
                    raise ValidationError("This category requires cluster dice.")
            else:
                # If it's in the carve category, prevent the cluster dice from being set or hard coded
                if self.cluster_dice_count is not None or self.cluster_dice_sides is not None:
                    raise ValidationError("This category must not define cluster dice.")
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(rpv__gt=models.F("upv")),
                name="reagent_rpv_greater_than_upv",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(cluster_dice_count__isnull=True, cluster_dice_sides__isnull=True) |
                    models.Q(cluster_dice_count__isnull=False, cluster_dice_sides__isnull=False)
                ),
                name="reagent_cluster_dice_both_or_neither",
            ),
        ]

class BiomeName(models.TextChoices):
    DESERT      = ("desert",      "Desert")
    FOREST      = ("forest",      "Forest")
    FRESHWATER  = ("freshwater",  "Freshwater")
    JUNGLE      = ("jungle",      "Jungle")
    MOUNTAIN    = ("mountain",    "Mountain")
    OCEAN       = ("ocean",       "Ocean")
    PLAINS      = ("plains",      "Plains")
    SWAMP       = ("swamp",       "Swamp")
    TUNDRA      = ("tundra",      "Tundra")
    UNDERGROUND = ("underground", "Underground")
    URBAN       = ("urban",       "Urban")
    VOLCANIC    = ("volcanic",    "Volcanic")


class Biome(models.Model):
    name = models.CharField(max_length=15, choices=BiomeName.choices, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    reagents = models.ManyToManyField(Reagent, related_name="biomes")
    # Dice rolled in Part 1 of the foraging algorithm to determine base potential count (e.g. 1d6, 1d12).
    biome_dice_count = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    biome_dice_sides = models.PositiveSmallIntegerField(
        choices=[(4, "d4"), (6, "d6"), (8, "d8"), (10, "d10"), (12, "d12")],
        default=6,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
class PotionEffect(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    reagents = models.ManyToManyField(Reagent, related_name="potion_effects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class PotionEffectLevel(models.Model):
    potion_effect = models.ForeignKey(PotionEffect, on_delete=models.CASCADE, related_name="effect_levels")
    level = models.PositiveSmallIntegerField(validators=[MaxValueValidator(10), MinValueValidator(1)])
    rules_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.potion_effect} - level {self.level}"
    
    class Meta:
        ordering = ["potion_effect", "level"]
        constraints = [models.UniqueConstraint(fields=["potion_effect", "level"], name="unique_level_per_effect")]

# class CreatureSizeChoices(models.TextChoices):
#     TINY = ("tiny", "Tiny")
#     SMALL = ("small", "Small")
#     MEDIUM = ("medium", "Medium")
#     LARGE = ("large", "Large")
#     HUGE = ("huge", "Huge")
#     GARGANTUAN = ("gargantuan", "Gargantuan")
#     COLOSSAL = ("colossal", "Colossal")

# class MonsterType(models.Model):
#     name = models.CharField(max_length=50, unique=True)
#     slug = models.SlugField(max_length=50, unique=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name
    
#     class Meta:
#         ordering = ["name"]

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)
    
# class Monster(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     slug = models.SlugField(max_length=100, unique=True, blank=True)
#     types = models.ManyToManyField(MonsterType, related_name="monsters")
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name
    
#     class Meta:
#         ordering = ["name"]

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)
    
# class Encounter(models.Model):
#     monster = models.ForeignKey("Monster", on_delete=models.PROTECT, related_name="encounters")
#     size = models.CharField(max_length=20, choices=CreatureSizeChoices.choices)
#     occurred_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.monster.name} ({self.get_size_display()})"
    
#     class Meta:
#         ordering = ["-occurred_at"]

# class EncounterReagentAward(models.Model):
#     encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="awards")
#     reagent = models.ForeignKey("Reagent", on_delete=models.PROTECT, related_name="encounter_awards")
#     quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.encounter} -> {self.reagent} x{self.quantity}"

#     class Meta:
#         constraints = [models.UniqueConstraint(fields=["encounter", "reagent"], name="uniq_award_encounter_reagent")]
#         ordering = ["encounter_id", "reagent__name"]
    

