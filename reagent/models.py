from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

CREATURE_SIZE_CHOICES = [
    ("tiny", "Tiny (or minion)"),
    ("small", "Small"),
    ("medium", "Medium"),
    ("large", "Large"),
    ("huge", "Huge"),
    ("gargantuan", "Gargantuan"),
    ("colossal", "Colossal"),
]

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    uses_cluster_dice = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Rarity(models.Model):
    name = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(max_length=20, unique=True, blank=True)

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
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["name"]

class Biome(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    reagents = models.ManyToManyField(
        Reagent,
        related_name="biomes"
    )

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
    lvl1 = models.CharField(max_length=500)
    lvl2 = models.CharField(max_length=500)
    lvl3 = models.CharField(max_length=500)
    lvl4 = models.CharField(max_length=500)
    lvl5 = models.CharField(max_length=500)
    lvl6 = models.CharField(max_length=500)
    lvl7 = models.CharField(max_length=500)
    lvl8 = models.CharField(max_length=500)
    lvl9 = models.CharField(max_length=500)
    lvl10 = models.CharField(max_length=500)
    reagents = models.ManyToManyField(
        Reagent,
        related_name="potion_effects"
    )

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
class MonsterType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
class Monster(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    types = models.ManyToManyField(MonsterType, related_name="monsters")

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
class Encounter(models.Model):
    monster = models.ForeignKey("Monster", on_delete=models.PROTECT, related_name="encounters")
    size = models.CharField(max_length=20, choices=CREATURE_SIZE_CHOICES)
    occurred_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.monster.name} ({self.get_size_display()})"
    
    class Meta:
        ordering = ["-occurred_at"]

class EncounterReagentAward(models.Model):
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="awards")
    reagent = models.ForeignKey("Reagent", on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.encounter} -> {self.reagent} x{self.quantity}"

    class Meta:
        unique_together = ("encounter", "reagent")
        ordering = ["encounter_id", "reagent__name"]
    

