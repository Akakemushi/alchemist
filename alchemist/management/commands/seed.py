from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps

class Command(BaseCommand):
    help = "Seed the database with initial Biomes, Reagents, and PotionEffects."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing PotionEffects, Biomes, and Reagents before seeding (DEV ONLY).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # App name corrected to 'alchemist'
        Reagent = apps.get_model("alchemist", "Reagent")
        Biome = apps.get_model("alchemist", "Biome")
        PotionEffect = apps.get_model("alchemist", "PotionEffect")

        if options["flush"]:
            self.stdout.write(self.style.WARNING(
                "⚠️  Flushing tables (PotionEffect → Biome → Reagent)..."
            ))
            PotionEffect.objects.all().delete()
            Biome.objects.all().delete()
            Reagent.objects.all().delete()

        # -------------------------
        # 1) Reagents
        # -------------------------
        reagent_seed = [
            {"name": "Mooncap Mushroom", "upv": 6, "rpv": 3},
            {"name": "Bog Lily", "upv": 4, "rpv": 5},
            {"name": "Frost Thistle", "upv": 7, "rpv": 2},
        ]

        reagents_by_name = {}
        for r in reagent_seed:
            reagent, created = Reagent.objects.update_or_create(
                name=r["name"],
                defaults={
                    "upv": r["upv"],
                    "rpv": r["rpv"],
                },
            )
            reagents_by_name[reagent.name] = reagent
            self.stdout.write(f"{'➕' if created else '✔️'} Reagent: {reagent.name}")

        # -------------------------
        # 2) Biomes
        # -------------------------
        biome_seed = {
            "Forest": ["Mooncap Mushroom", "Frost Thistle"],
            "Swamp": ["Bog Lily"],
            "Mountain": ["Frost Thistle"],
        }

        for biome_name, reagent_names in biome_seed.items():
            biome, created = Biome.objects.update_or_create(
                name=biome_name,
                defaults={},
            )

            missing = [n for n in reagent_names if n not in reagents_by_name]
            if missing:
                raise ValueError(
                    f"Biome '{biome_name}' references missing reagents: {missing}"
                )

            biome.reagents.set([reagents_by_name[n] for n in reagent_names])

            self.stdout.write(
                f"{'➕' if created else '✔️'} Biome: {biome.name}"
            )

        # -------------------------
        # 3) Potion Effects
        # -------------------------
        effects_seed = [
            {
                "name": "Healing",
                "lvls": {
                    1: "Heal a small wound.",
                    2: "Restore minor stamina.",
                    3: "Close deep cuts.",
                    4: "Regrow minor tissue.",
                    5: "Restore significant vitality.",
                    6: "Mend broken bones slowly.",
                    7: "Cleanse infection and poison.",
                    8: "Major regeneration over time.",
                    9: "Near-miraculous restoration.",
                    10: "Bring someone back from the brink.",
                },
                "reagents": ["Mooncap Mushroom", "Bog Lily"],
            },
        ]

        for e in effects_seed:
            lvls = e["lvls"]
            effect, created = PotionEffect.objects.update_or_create(
                name=e["name"],
                defaults={
                    "lvl1": lvls[1],
                    "lvl2": lvls[2],
                    "lvl3": lvls[3],
                    "lvl4": lvls[4],
                    "lvl5": lvls[5],
                    "lvl6": lvls[6],
                    "lvl7": lvls[7],
                    "lvl8": lvls[8],
                    "lvl9": lvls[9],
                    "lvl10": lvls[10],
                },
            )

            missing = [n for n in e["reagents"] if n not in reagents_by_name]
            if missing:
                raise ValueError(
                    f"PotionEffect '{e['name']}' references missing reagents: {missing}"
                )

            effect.reagents.set([reagents_by_name[n] for n in e["reagents"]])

            self.stdout.write(
                f"{'➕' if created else '✔️'} PotionEffect: {effect.name}"
            )

        self.stdout.write(self.style.SUCCESS("✅ Seeding complete."))