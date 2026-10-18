"""
Expedition execution engine.

Call ``run_expedition(expedition)`` after the view has set the expedition's
approval_status to EXECUTED and saved it.  This function runs the three-part
foraging algorithm, creates InventoryEntry + ReagentSample rows for every item
found, and returns a plain summary dict (item counts per character) that the
view can pass to messages or redirect without needing stored roll data.

The results are intentionally limited to what was actually found: players have
no way to know what they missed.
"""

import random
from django.db import transaction
from inventory.models import InventoryEntry, Kind, ReagentSample


# ── Dice helpers ──────────────────────────────────────────────────────────────

def _roll(count, sides):
    return sum(random.randint(1, sides) for _ in range(count))


# ── Part 1 helpers ────────────────────────────────────────────────────────────

def _alchemy_to_nature_bonus(alchemy_result):
    """Bonus to the follow-up Nature check from a given Alchemy check result."""
    if alchemy_result < 10:
        return 0
    return 1 + (alchemy_result - 10) // 5


def _nature_lookup(nature_result):
    """Return (bonus_potentials, real_chance_pct) from the Nature check table."""
    if nature_result <= -1:
        return -1, 10
    elif nature_result <= 19:
        return 0, 20
    elif nature_result <= 24:
        return 1, 30
    elif nature_result <= 29:
        return 2, 40
    elif nature_result <= 34:
        return 3, 45
    elif nature_result <= 39:
        return 4, 50
    elif nature_result <= 44:
        return 5, 60
    elif nature_result <= 49:
        return 6, 65
    else:
        return 7, 70


# ── Part 2 helpers ────────────────────────────────────────────────────────────

def _rarity_roll():
    r = random.randint(1, 10)
    if r <= 7:
        return "Common"
    elif r <= 9:
        return "Uncommon"
    else:
        return "Rare"


def _generate_potentials(biome_display, by_rarity, real_chance_pct, leader_level):
    """
    Generate and return one potential item.

    Returns a dict with:
        is_real     bool
        reagent     Reagent object or None
        description str
        search_dc   int
        quantity    int
        is_luminous bool
        vibration   bool
    """
    from reagents.d_gen import sen_gen

    is_real = random.randint(1, 100) <= real_chance_pct

    if is_real:
        rarity = _rarity_roll()
        pool = by_rarity.get(rarity, [])
        # Fallback if no reagents of that rarity exist in this biome
        if not pool:
            for fallback in ("Common", "Uncommon", "Rare"):
                pool = by_rarity.get(fallback, [])
                if pool:
                    break
        if pool:
            reagent = random.choice(pool)
            quantity = (
                _roll(reagent.cluster_dice_count, reagent.cluster_dice_sides)
                if reagent.cluster_dice_count and reagent.cluster_dice_sides
                else 1
            )
            return {
                "is_real": True,
                "reagent": reagent,
                "category": reagent.category.name,
                "description": reagent.description or "",
                "search_dc": reagent.search_dc or 10,
                "quantity": quantity,
                "is_luminous": reagent.light_source,
                "vibration": reagent.vibration,
            }
        # No reagents at all in biome — fall through to dud
        is_real = False

    # Dud / false positive
    category, description = sen_gen(biome_display, random.randint(1, 40))
    quantity = _roll(1, random.choice([4, 6]))
    fake_dc = 10 + (leader_level // 2) + random.randint(1, 10)
    return {
        "is_real": False,
        "reagent": None,
        "category": category,
        "description": description,
        "search_dc": fake_dc,
        "quantity": quantity,
        "is_luminous": False,
        "vibration": False,
    }


# ── Part 3 helpers ────────────────────────────────────────────────────────────

def _perception_mod(character, potential, expedition):
    """
    Flat modifier to a character's perception roll for one potential item,
    based on expedition settings.
    """
    from campaigns.models import SearchSpeed

    mod = 0

    if potential["vibration"]:
        if character.has_tremorsense:
            mod += 5

    if expedition.search_speed == SearchSpeed.RUSH:
        mod -= 10

    if expedition.target_reagent_id:
        is_target = (
            potential["is_real"]
            and potential["reagent"] is not None
            and potential["reagent"].pk == expedition.target_reagent_id
        )
        mod += 10 if is_target else -10

    if expedition.search_at_night:
        luminous = potential["is_luminous"]
        if character.has_darkvision:
            pass                         # no modifier
        elif character.has_lowlightvision:
            mod += 3 if luminous else -3
        else:
            mod += 10 if luminous else -10

    return mod


def _attempt(character, potential, expedition):
    """
    Roll one perception check.  Returns (success: bool, total: int).
    """
    d20 = random.randint(1, 20)
    total = d20 + character.perception_bonus + _perception_mod(character, potential, expedition)
    return total >= potential["search_dc"], total


def _award(character, potential, biome, expedition):
    """Create InventoryEntry + ReagentSample for a found item."""
    entry = InventoryEntry.objects.create(
        character=character,
        kind=Kind.RAW_REAGENT,
        quantity=potential["quantity"],
    )
    ReagentSample.objects.create(
        inventory_entry=entry,
        true_reagent=potential["reagent"],        # None for duds
        is_mundane=not potential["is_real"],
        found_biome=biome,
        source_expedition=expedition,
        observed_description=potential["description"],
        observed_category=potential["category"],
    )


# ── Cycle ─────────────────────────────────────────────────────────────────────

def _run_cycle(expedition, all_characters, by_rarity, biome, biome_display):
    """Run one full foraging cycle (Parts 1–3)."""
    from campaigns.models import SearchMode

    leader = expedition.leader

    # ── Part 1 ───────────────────────────────────────────────────────────────
    biome_roll = _roll(biome.biome_dice_count, biome.biome_dice_sides)

    alchemy_result = random.randint(1, 20) + leader.alchemy_bonus
    nature_bonus_from_alchemy = _alchemy_to_nature_bonus(alchemy_result)
    targeted_bonus = 5 if expedition.target_reagent_id else 0
    nature_result = (
        random.randint(1, 20)
        + leader.nature_bonus
        + nature_bonus_from_alchemy
        + targeted_bonus
    )

    bonus_potentials, real_chance_pct = _nature_lookup(nature_result)
    total_potentials = max(0, biome_roll + bonus_potentials)

    # ── Part 2 ───────────────────────────────────────────────────────────────
    potentials = [
        _generate_potentials(biome_display, by_rarity, real_chance_pct, leader.level)
        for _ in range(total_potentials)
    ]

    # ── Part 3 ───────────────────────────────────────────────────────────────
    n = len(all_characters)

    if expedition.search_mode == SearchMode.TOGETHER:
        for pot in potentials:
            shuffled = list(all_characters)
            random.shuffle(shuffled)
            for char in shuffled:
                success, _ = _attempt(char, pot, expedition)
                if success:
                    _award(char, pot, biome, expedition)
                    break  # item found; no further rolls needed

    else:  # SPLITUP
        random.shuffle(potentials)
        # Deal potentials like cards, one per character in round-robin order
        for i, pot in enumerate(potentials):
            char = all_characters[i % n]
            success, _ = _attempt(char, pot, expedition)
            if success:
                _award(char, pot, biome, expedition)


# ── Public entry point ────────────────────────────────────────────────────────

@transaction.atomic
def run_expedition(expedition):
    """
    Execute the foraging algorithm for an expedition.

    The view is responsible for having already set approval_status = EXECUTED,
    executed_at, and saved the expedition before calling this function.

    Creates InventoryEntry + ReagentSample rows for every item found.
    Returns a dict: {character_id: items_found_count} for the calling view
    to use in a success message.
    """
    from campaigns.models import SearchMode, SearchSpeed

    biome = expedition.biome
    leader = expedition.leader

    all_characters = [leader] + [
        p.character
        for p in expedition.participants.select_related("character").all()
    ]
    n = len(all_characters)

    # Cycle count
    cycles = expedition.hours
    if expedition.search_mode == SearchMode.SPLITUP:
        cycles *= n
    if expedition.search_speed == SearchSpeed.RUSH:
        cycles *= 2

    # Biome reagent pool grouped by rarity (Carve items excluded — no cluster dice)
    by_rarity = {"Common": [], "Uncommon": [], "Rare": []}
    for reagent in biome.reagents.select_related("rarity", "category").filter(
        category__uses_cluster_dice=True
    ):
        rname = reagent.rarity.name
        if rname in by_rarity:
            by_rarity[rname].append(reagent)

    biome_display = biome.get_name_display()

    for _ in range(cycles):
        _run_cycle(expedition, all_characters, by_rarity, biome, biome_display)

    # Build a simple per-character found-item count for the success message
    from inventory.models import ReagentSample
    found_counts = {}
    for char in all_characters:
        count = ReagentSample.objects.filter(
            source_expedition=expedition,
            inventory_entry__character=char,
        ).count()
        found_counts[char.pk] = (char.name, count)

    return found_counts
