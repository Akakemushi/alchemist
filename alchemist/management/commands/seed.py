from django.core.management.base import BaseCommand
from alchemist.models import Biome, Reagent
from django.db import transaction

class Command(BaseCommand):
    help = "Seed the database with initial biomes and reagents"

    @transaction.atomic
    def handle(self, *args, **options):
        forest, _ = Biome.objects.get_or_create(name="Forest")
        swamp, _ = Biome.objects.get_or_create(name="Swamp")

        Reagent.objects.get_or_create(name="Mooncap Mushroom", defaults={"biome": forest})
        Reagent.objects.get_or_create(name="Bog Lilies", defaults={"biome": swamp})

        self.stdout.write(self.style.SUCCESS("✅ Database seeded."))