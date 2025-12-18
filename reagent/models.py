from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Reagent(models.Model):
    name = models.CharField(max_length=50, unique=True)
    upv = models.SmallIntegerField(
        validators=[MinValueValidator(1),
                    MaxValueValidator(10)
                    ]
    )
    rpv = models.SmallIntegerField()
    image = models.ImageField(upload_to="reagents/", blank=True, null=True)

    def __str__(self):
        return self.name

class Biome(models.Model):
    name = models.CharField(max_length=50, unique=True)
    reagents = models.ManyToManyField(
        Reagent,
        related_name="biomes"
    )

    def __str__(self):
        return self.name
    
class PotionEffect(models.Model):
    name = models.CharField(max_length=50, unique=True)
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
