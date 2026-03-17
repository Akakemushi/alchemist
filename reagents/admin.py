from django.contrib import admin
from .models import Reagent, Biome, PotionEffect

admin.site.register(Reagent)
admin.site.register(Biome)
admin.site.register(PotionEffect)