from django.contrib import admin
from .models import Item, CharacterItem, RollType, ItemModifier

admin.site.register(Item)
admin.site.register(CharacterItem)
admin.site.register(ItemModifier)
# Register your models here.
