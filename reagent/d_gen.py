import random
import inflect

p = inflect.engine()

# Biome weights of item types
biome_weights = {
    "Desert": {"plant": 0.2, "creature": 0.2, "mineral": 0.6},
    "Forest": {"plant": 0.4, "creature": 0.4, "mineral": 0.2},
    "Jungle": {"plant": 0.5, "creature": 0.4, "mineral": 0.1},
    "Freshwater": {"plant": 0.4, "creature": 0.2, "mineral": 0.4},
    "Mountain": {"plant": 0.3, "creature": 0.2, "mineral": 0.5},
    "Ocean": {"plant": 0.4, "creature": 0.5, "mineral": 0.1},
    "Plains": {"plant": 0.4, "creature": 0.4, "mineral": 0.2},
    "Swamp": {"plant": 0.6, "creature": 0.3, "mineral": 0.1},
    "Tundra": {"plant": 0.3, "creature": 0.2, "mineral": 0.5},
    "Underground": {"plant": 0.2, "creature": 0.3, "mineral": 0.5},
    "Urban": {"plant": 0.2, "creature": 0.6, "mineral": 0.2},
    "Volcanic": {"plant": 0.2, "creature": 0.1, "mineral": 0.7},
}

# Lists of objects and descriptions
PLANTS = {
    "WET": {
        "variant of mangrove": {
            "parts": ["root", "strips of bark", "leaf", "seed"],
            "textures": ["waxy", "fibrous"],
        },
        "vine": {
            "parts": ["leaf", "stem", "fruit", "bean"],
            "textures": ["waxy", "fibrous", "velvety"],
        },
    },
    "DRY": {
        "cactus": {
            "parts": ["pad", "flower", "fruit", "spine cluster"],
            "textures": ["waxy", "brittle"],
        }
    },
    "EITHER": {
        "tree": {
            "parts": ["leaf", "strips of bark", "root", "nut"],
            "textures": ["woody", "fibrous", "papery"],
        },
        "shrub": {
            "parts": ["leaf", "stem", "flower", "berry", "seed"],
            "textures": ["fibrous", "papery"],
        },
        "bush": {"parts": ["leaf", "berry", "seed"], "textures": ["fibrous", "waxy"]},
        "standalone": {
            "parts": ["flower", "mushroom", "fungus", "reed"],
            "textures": ["soft", "velvety"],
        },
    },
}
MASS_NOUNS = ["strips of bark", "fungus", "mossy growth", "fur", "skin"]

CREATURES = {
    "MAMMALS": {
        "creatures": [
            "mouse",
            "rat",
            "squirrel",
            "mole",
            "rabbit",
            "rodent",
            "cat",
            "fox",
            "weasel",
        ],
        "textures": ["fuzzy", "fluffy", "sleek", "smooth", "coarse", "soft"],
    },
    "BUGS": {
        "creatures": [
            "worm",
            "slug",
            "caterpillar",
            "inchworm",
            "flatworm",
            "leech",
            "spider",
            "scorpion",
            "centipede",
            "millipede",
            "beetle",
            "butterfly",
            "moth",
            "wasp",
            "bee",
            "ant",
        ],
        "textures": [
            "chitinous",
            "spiny",
            "bristly",
            "plated",
            "bumpy",
            "rigid",
            "waxy",
        ],
    },
    "REPTILES": {
        "creatures": ["snake", "lizard", "gekko", "iguana"],
        "textures": ["leathery", "smooth", "rough", "sleek"],
    },
    "AMPHIBIANS": {
        "creatures": ["frog", "toad"],
        "textures": ["slimy", "smooth", "slick", "soft", "greasy"],
    },
    "BIRDS": {
        "creatures": ["finch", "crow", "hawk", "owl", "duck"],
        "textures": ["sleek", "smooth", "soft", "fuzzy", "greasy"],
    },
    "FISH": {
        "creatures": [
            "minnow",
            "perch",
            "trout",
            "carp",
            "bass",
            "sunfish",
            "catfish",
            "eel",
        ],
        "textures": ["slimy", "smooth", "slick", "greasy", "sleek"],
    },
}

MINERALS = {
    "objects": ["stone", "rock shard", "ore chunk", "mineral"],
    "textures": [
        "jagged",
        "chalky",
        "smooth",
        "glassy",
        "porous",
        "metallic",
        "rough",
        "faceted",
        "powdery",
    ],
    "sheen": [
        "metallic",
        "pearly",
        "lustrous",
        "iridescent",
        "rainbow",
        "silvery",
        "golden",
        "coppery",
    ],
}

WARM_COLORS = [
    "red",
    "rust-colored",
    "amber",
    "golden",
    "burnt orange",
    "crimson",
    "scarlet",
    "copper",
    "bronze",
    "ochre",
    "vermillion",
]
COOL_COLORS = [
    "blue",
    "bluish-purple",
    "green",
    "teal",
    "pale cyan",
    "azure",
    "cobalt",
    "turquoise",
    "mint",
    "sage",
    "lavender",
]
NEUTRAL_COLORS = [
    "gray",
    "dark gray",
    "whitish",
    "off-white",
    "brown",
    "beige",
    "tan",
    "charcoal",
    "ash",
    "silver",
]
BASIC_COLORS = [
    "red",
    "red-orange",
    "orange",
    "yellow",
    "yellow-green",
    "green",
    "blue-green",
    "blue",
    "violet",
    "purple",
    "indigo",
    "pink",
]

PATTERN_OPTIONS = ["tones", "spots", "stripes", "speckles", "rings", "bands"]
PATTERN_OPTIONS_ED = [
    "toned",
    "spotted",
    "striped",
    "speckled",
    "ringed",
    "banded",
    "splotched",
]

SMELL_OPTIONS = [
    "acrid",
    "sweet",
    "musty",
    "citrusy",
    "earthy",
    "pungent",
    "fragrant",
    "sulfurous",
    "putrid",
]
BUG_OBJECTS = ["a leaf", "a twig", "an acorn", "a flower", "a coin", "a crystal"]

SHAPES = {
    "ORGANIC": {
        "2D": ["heart", "teardrop", "crescent", "spade", "fan"],
        "3D": ["spherical", "conical", "bell", "cup", "cone", "bulb", "dome"],
    },
    "INORGANIC": {
        "2D": [
            "triangle",
            "hexagon",
            "diamond",
            "square",
            "pentagon",
            "octagon",
            "chevron",
        ],
        "3D": ["cubic", "pyramidal", "cylindrical", "angular"],
    },
}
SIZES = ["tiny", "small", "modestly sized", "large", "huge"]
BODY_ADJECTIVES = [
    "thin",
    "stocky",
    "fat",
    "scrawny",
    "slender",
    "stout",
    "bulky",
    "petite",
    "spindly",
    "robust",
    "delicate",
]


# choose which type object and then form of sentence to output based on biome
def sen_gen(biome, skill_check):

    # define various options
    objects = list(biome_weights[biome].keys())
    weights = list(biome_weights[biome].values())
    object_type = random.choices(objects, weights=weights, k=1)[0]
    descriptor_dict = dict_of_descriptor(biome, object_type)

    # Decide which funtion to output sentence and then return it
    if object_type == "plant":
        base_chance = 6
    elif object_type == "creature":
        base_chance = 7
    else:  # Mineral
        base_chance = 5

    # Adjust chance based on skill check with random ranges
    if skill_check >= 30:
        bonus = random.randint(10, 14)  # Very high skill
    elif skill_check >= 25:
        bonus = random.randint(7, 12)
    elif skill_check >= 20:
        bonus = random.randint(5, 9)
    elif skill_check >= 15:
        bonus = random.randint(3, 7)
    elif skill_check >= 10:
        bonus = random.randint(1, 4)
    elif skill_check <= 5:
        bonus = random.randint(-5, -2)  # Penalty for low skill
    else:  # 6-9
        bonus = random.randint(-2, 1)

    premade_chance = max(2, min(base_chance + bonus, 19))  # Capped 2-19 (10%-95%)

    roll = random.randint(1, 20)

    if roll <= premade_chance:
        sentence = generate_premade_sentence(descriptor_dict, object_type)
    else:
        sentence = generate_random_sentence(descriptor_dict, object_type)

    return sentence


# Function for predetermined sentences
def generate_premade_sentence(descriptor_dict, object_type):

    # Picking some likely global variables.
    color1 = random.choice(descriptor_dict["colors"])
    color2 = random.choice(descriptor_dict["colors"])
    while color2 == color1:
        color2 = random.choice(descriptor_dict["colors"])
    basicolor = random.choice(BASIC_COLORS)
    num1 = random.randint(2, 8)
    num2 = num1 + random.randint(2, 4)
    size1 = random.choice(SIZES)
    texture = random.choice(descriptor_dict["textures"])
    pattern = random.choice(PATTERN_OPTIONS)
    article_color = p.a(f"{color1}")
    body = random.choice(BODY_ADJECTIVES)

    if object_type == "plant" or object_type == "creature":
        shape1 = random.choice(SHAPES["ORGANIC"]["2D"])
        shape2 = random.choice(SHAPES["ORGANIC"]["3D"])
        article_shape = p.a(f"{shape1}")
    else:  # Minerals
        shape1 = random.choice(SHAPES["INORGANIC"]["2D"])
        shape2 = random.choice(SHAPES["INORGANIC"]["3D"])
        article_shape = p.a(f"{shape1}")

    # managing plants variables
    if object_type == "plant":
        plant = descriptor_dict["other"][0]
        while plant == "standalone":
            plant = random.choice(list(PLANTS["EITHER"].keys()))
        smell = random.choice(SMELL_OPTIONS)
        mammal = p.plural(random.choice(CREATURES["MAMMALS"]["creatures"]))
        neutral = random.choice(NEUTRAL_COLORS)
        size2 = random.choice(SIZES)

        biome_type = random.choice(random.choice(descriptor_dict["texture_parts"]))

        # Plant sentences options
        PLANT_SENTENCES = {
            "WET": [
                [3, f"A {body} {plant} with {basicolor} flowers that have {num1}~{num2} bony spikes protruding from the tip of each petal. Painful to touch, like a cactus."],
                [8, f"{body.capitalize()} reeds growing to about {num1} feet tall with {texture} {color1} stalks. The roots form dense tangles underwater."],
                [4, f"{texture.capitalize()} {color1} roots from a unique mangrove that form tangled networks above the waterline. A root segment is {num1}~{num2} inches thick."],
                [5, f"{color1.capitalize()} {texture} bean pods that hang in clusters of {num1}~{num2}. Each pod is roughly {shape1}-shaped and smells {smell}."],
                [7, f"A {random.choice(["hunk", "chunk", "collection", "handful"])} of {random.choice(["light", "dark", "vibrant", "pale", "deep"])} green moss that has a {texture} texture. Causes {random.choice(["itchyness", "mild irritation", "rash", "sweating", "a tingling sensation"])} when touched."],
                [3, f"{texture.capitalize()} bamboo shoots that emerge in clusters of {num1}~{num2}. Each shoot is {color1} with {basicolor} rings and grows rapidly in moist soil."],
            ],
            "DRY": [
                [5, f"A {body} {plant} with {basicolor} flowers that have {num1}~{num2} bony spikes protruding from the tip of each petal. Painful to touch, like a cactus."],
                [5, f"{texture.capitalize()} seed pods that split open when dry, revealing {num1}~{num2} {color1} seeds inside. Each pod is {shape2}-shaped."],
                [7, f"{texture.capitalize()} {color1} cactus pads shaped like {shape1}s. Surface covered in clusters of {num1}~{num2} {basicolor} spines."],
            ],
            "EITHER": [
                [8, f"A {plant} {num1}-feet tall with {texture}, {color1} {shape1}-shaped leaves. {shape2.capitalize()}-shaped protrusions stick out from the center."],
                [4, f"Knee-high {color1} grass with very {texture} edges. Smells slightly {smell}."],
                [4, f"A {shape2} shaped flower with {num2}-inch long {color1} petals and a feather-like stamen which sticks out about {num1} inches from the flower."],
                [7, f"Clusters of small {shape1} leaves in bundles of {num1}~{num2} terminate at the ends of these {color1}, {texture}, {body} plants. Smells very {smell}."],
                [3, f"{body.capitalize()} {shape2} shaped {color1} flowers of {num1}~{num2} petals which hang upside-down. Grows from a {plant}."],
                [3, f"{size1.capitalize()}, {texture} {color1} berries with tiny {neutral} seeds around its surface that grow in {size2} clusters. Attracts {mammal}."],
                [9, f"A flower with {num1}-petals, {num1}~{num2} inches in diameter with {article_color} center. {color2.capitalize()} {pattern} towards the edges."],
                [5, f"A {size1} mushroom with {texture} {color1} cap marked with {color2} {pattern}. The {basicolor} stem is {num1}~{num2} inches tall."],
                [6, f"A {random.choice(["lighter", "darker", "more oblong", "more brittle", "heavier", "lumpier"])} variant of a {random.choice(["chestnut", "hazelnut", "walnut", "beech nut", "pecan", "cashew", "macadamia nut", "pistachio nut"])}. Outer shell is tinted slightly {basicolor}."],
                [4, f"Some {smell}-smelling {basicolor} berries that have a {texture} texture to them. The pulp and juice is {random.choice(["light", "dark"])} {basicolor}."],
                [7, f"A {color1} {num2}-petaled {random.choice(["radial", "tulip-shaped", "lily-like"])} flower with a {body} stem and {color2} center. Petals are long and {texture}."],
                [4, f"Clusters of {num1}~{num2} {size2} mushrooms with {body} {shape1}-shaped caps. {color1.capitalize()} on top, {basicolor} gills underneath."],
            ],
        }

        sentences_choices = PLANT_SENTENCES[biome_type]
        final = weighted_sentence_choice(sentences_choices)

    # managing creature variables
    if object_type == "creature":
        sentences_choices = []
        creature = random.choice(descriptor_dict["objects"])
        pattern2 = random.choice(PATTERN_OPTIONS_ED)

        # Possible sentence based on subtye of creature
        creature_subtypes = descriptor_dict["other"][0]

        sentences_subtypes = {
            "REPTILES": [
                [5, f"{article_color.capitalize()} to {color2} {creature} about {num1}~{num2} inches in length with a bright {basicolor} underbelly."],
                [3, f"A {size1} {creature} with a {body} {color1} body and a neck frill that is bright {basicolor} when opened. The frill is about {num1}~{num2} inches around."],
                [6, f"A {creature} with {color1} scales that fade to {color2} near the tail. Has a {size1} head with {basicolor} eyes and measures roughly {num1}~{num2} inches from snout to tail tip."],
            ],
            "BIRDS": [
                [4, f"A {basicolor}-eyed {creature}, slightly smaller than {random.choice(["a plum", "an apple", "an orange", "a small melon", "a child's ball"])}. Feathers are {color1} at the root and gradually turn {color2} at the tip."],
                [3, f"{color1.capitalize()}, {pattern2} eggs with an uneven shape. The shell has a {texture} texture."],
                [5, f"A {size1} {creature} with {color1} plumage and a {basicolor} crest. Its call is {random.choice(["sharp and distinctive.", "a low warble","a harsh screech","a melodic trill","a repetitive chirp"])}."],
            ],
            "BUGS": [
                [8, f"A bug that resembles a {color1} {creature} but with a {body} build and {texture} surface."],
                [2, f"{article_color.capitalize()} insect that can mimic the appearance of {random.choice(BUG_OBJECTS)}. Its {body} shape and {pattern2} markings complete the disguise."],
                [4, f"A {size1} {creature} covered in {texture} segments. Highly sensitive to {random.choice(["light", "smoke", "heat", "cold", "salt", "vinegar"])} and will flee when it detects it nearby."],
            ],
            "FISH": [
                [4, f"A {size1} {color1} {creature} that smells {random.choice(SMELL_OPTIONS)} when removed from the water. Usually found in small schools."],
                [4, f"A {size1} {creature} with {color1} and {color2} {pattern} across its fins. Known for its {texture} scales and tendency to swim in {shape1} formations."],
                [8, f"A {body} {creature} with {color1} scales and skin. Its head is {size1} and {shape1}-shaped, with {color2} eyes. Its fins have light {basicolor} {pattern} on them."],
            ],
            "MAMMALS": [
                [6, f"A {creature} with {color1} fur and a noticeable {basicolor} patch on its back in the shape of {article_shape}. It is {size1} compared to others like it."],
                [2, f"A {size1} rodent with {random.choice(["oily", "matted", "slick", "silky", "dirty"])} {random.choice(["brown", "tan", "cream-colored", "blonde", "gray"])} fur and {num1}~{num2} small, {color1} {random.choice(["spines", "dots", "stripes", "bumps"])} going down the length of its back."],
                [4, f"{article_color.capitalize()} {creature} with a {texture} tail ending in {article_shape} shape. It often {random.choice(["stands up on its hind legs","drums its front paws rapidly when excited","curls into a tight ball when scared", "marks its territory with a distinct musky odor"])}."],
                [8, f"{article_color.capitalize()} {creature} featuring {color2} {pattern2} markings across its back. Known for its {texture} coat and sharp {basicolor} eyes."],
            ],
            "AMPHIBIANS": [
                [5, f"A {size1} {creature} with {color1} skin covered in {basicolor} {pattern}. Its throat pouch inflates when threatened."],
                [7, f"{article_color.capitalize()} {creature} about {num1}~{num2} inches long with {texture} skin and {color2} eyes. Often found near water sources."],
                [6, f"A {creature} with a {body} build and {color1} coloration. Has distinctive {basicolor} markings behind its eyes and webbed feet."],
            ],
        }

        # select sentence from list
        final = weighted_sentence_choice(sentences_subtypes[creature_subtypes])

    # Mineral sentence consturction
    if object_type == "mineral":
        weight = random.choice(["lighter", "heavier"])
        pattern2 = random.choice(PATTERN_OPTIONS_ED)
        sentences_choices = [
            [6, f"{shape2.capitalize()} translucent {color1} stones which have a {color2} {shape1}-shaped metal bit in their center."],
            [1, f"A mix of {color1} and {color2} sand which begins to glow {basicolor} in the proximity of {random.choice(["moonlight", "sunlight", "fire", "water", "heat", "cold", "salt", "iron"])}."],
            [5, f"{color1.capitalize()} {pattern2} metal which forms into {shape1} shapes. {weight.capitalize()} than expected."],
            [2, f"{color1.capitalize()} crystal shards with {color2} {pattern} running through them. They emit {basicolor} sparks when struck together."],
            [3, f"Magnetic {color1} sand that clumps together when disturbed. The clumps have a {texture} texture and {basicolor} sheen."],
            [4, f"A geode with a {shape2} shape and rough {color1} exterior. When cracked open, the interior reveals {basicolor} crystalline formations."],
            [7, f"{color1.capitalize()} stones with natural {shape1}-shaped faces. The surface is {texture} and shows {color2} veining along the edges."],
        ]

        final = weighted_sentence_choice(sentences_choices)

    return final

def weighted_sentence_choice(sentence_list):
 # Extract weights and calculate total
    weights = [item[0] for item in sentence_list]
    total = sum(weights)
    
    # Pick a random number in the range
    num = random.randint(0, total)
    
    # Iterate through and subtract weights until we hit our item
    for i, weight in enumerate(weights):
        num -= weight
        if num <= 0:
            return sentence_list[i][1]  # Return the sentence
    
    # Fallback (should never reach here)
    return sentence_list[-1][1]


# Function to pick random item and give random descriptions
def generate_random_sentence(descriptor_dict, object_type):

    # Select random things for sentence, still need function
    thing = random.choice(descriptor_dict["objects"])
    descriptor1, type1 = descriptor_builder(descriptor_dict, object_type)
    descriptor2, type2 = descriptor_builder(descriptor_dict, object_type)

    # Checks descriptors dont match
    # Force descriptor1 to be texture (not color)
    while type1 == "colors":
        descriptor1, type1 = descriptor_builder(descriptor_dict, object_type)

    # Then ensure descriptor2 is different from descriptor1
    while type1 == type2:
        descriptor2, type2 = descriptor_builder(descriptor_dict, object_type)

    # Some grammar fixes for articles
    article_thing = p.a(f"{thing}")
    if thing in MASS_NOUNS:
        plural_thing = thing
        article_thing = thing
    else:
        plural_thing = p.plural(thing)

    last_word = descriptor1.split()[-1]
    if (
        p.singular_noun(last_word) or last_word in MASS_NOUNS
    ):  # Returns False if already singular
        article_descriptor = descriptor1  # No article for plural
    else:
        article_descriptor = p.a(descriptor1)  # It's singular, needs article

    # Special set up for plant sentences
    if object_type == "plant":
        SCENT_PHRASES = [
            "Gives off {article_smell} scent",
            "Emits {article_smell} aroma",
            "Has {article_smell} smell",
            "Produces {article_smell} odor",
            "Carries {article_smell} fragrance",
            "Noted for {article_smell} scent",
        ]
        plant_type = random.choice(descriptor_dict["other"])
        if plant_type == "standalone":
            plant_phrase = ""
        else:
            plant_phrase = f" from a {plant_type}"
        smell = random.choice(SMELL_OPTIONS)
        article_smell = p.a(f"{smell}")
        smell_phrase = random.choice(SCENT_PHRASES).format(article_smell=article_smell)
    else:
        plant_phrase = ""

    # Define sentences
    # Put together parts for sentence 1
    if object_type == "creature":
        sentence1 = f"{article_thing.capitalize()} with {article_descriptor}."
        is_plural = False
    else:  # Plant or Mineral
        sentence1_options = [
            f"{article_thing.capitalize()}{plant_phrase} with {article_descriptor}.",
            f"Some {plural_thing}{plant_phrase} that have {article_descriptor}.",
        ]
        sentence1_choice = random.randint(0, len(sentence1_options) - 1)
        sentence1 = sentence1_options[sentence1_choice]
        is_plural = (sentence1_choice in [1, 2]) if thing not in MASS_NOUNS else False

    # Determine if plural (options 1 and 2 are plural)
    possessive = "their" if is_plural else "its"
    plural_suffix = " each" if is_plural else ""

    # Sentence 2 construction
    NOTABLE_PHRASES = [
        "Notable for",
        "Distinctive for",
        "Remarkable for",
        "Noteworthy for",
        "Characterized by",
        "Defined by",
        "Recognized by",
        "Distinguished by",
    ]
    COMPARISON_PHRASES = [
        "Comparable in {comparison} to",
        "Similar in {comparison} to",
        "About the {comparison} of",
        "Roughly the {comparison} of",
        "Approximately the {comparison} of",
        "Close in {comparison} to",
        "Nearly the {comparison} of",
    ]
    STANDOUT_PHRASES = [
        "stands out",
        "is striking",
        "is distinctive",
        "catches the eye",
        "is noticeable",
        "draws attention",
        "is prominent",
    ]

    # Prepare descriptor2 variations
    notable_phrase = random.choice(NOTABLE_PHRASES)
    standout_phrase = random.choice(STANDOUT_PHRASES)

    # Create parts and put together Sentences 2
    words = descriptor2.split()
    last_word = words[-1]
    if p.singular_noun(last_word):
        phrase_words = standout_phrase.split()
        phrase_words[0] = p.plural_verb(phrase_words[0], 2)  # 2 = plural
        standout_phrase = " ".join(phrase_words)

    sentence2_options = [
        f"{notable_phrase} {possessive} {descriptor2}.",
        f"{possessive.capitalize()} {descriptor2} {standout_phrase}.",
    ]

    if object_type == "plant":
        # Add plant-specific sentence
        sentence2_options.append(f"{smell_phrase}.")
    
    # Comparison sentence for minerals and bugs only
    elif object_type == "mineral" or thing in CREATURES["BUGS"]["creatures"]:
        COMPARISON_TYPES = ["size", "weight"]
        SIZE_OBJECTS = [
            "a loaf of bread",
            "a wine bottle",
            "a skull",
            "a clay pot",
            "an apple",
            "a large book",
            "a handball",
        ]
        WEIGHT_OBJECTS = [
            "a brick",
            "a boot",
            "a hand axe",
            "a kettle",
            "a clay mug",
            "a dagger",
            "a wedge of cheese",
            "a gold ingot",
        ]

        if thing in CREATURES["BUGS"]["creatures"]:
            comparison = "shape"
            common_object = random.choice(BUG_OBJECTS)
            modifier = random.choice(["sturdier", "more fragile", "more delicate"])
            comparison_endings = [f" and {modifier} than it appears"] 
        else:  # mineral
            comparison = random.choice(COMPARISON_TYPES)
            comparison_endings = [f" and {random.choice(['awkward', 'difficult', 'easy', 'comfortable'])} to grip", ""]
            if comparison == "size":
                common_object = random.choice(SIZE_OBJECTS)
                comparison_endings.extend([f" and {random.choice(['easier', 'harder'])} to lift than it looks"])
            else:  # weight
                common_object = random.choice(WEIGHT_OBJECTS)
                comparison_endings.extend([f" {random.choice(["but", "yet"])} feels {random.choice(['unexpectedly hollow', 'oddly balanced', 'unevenly weighted'])}"])
              
        comparison_phrase = random.choice(COMPARISON_PHRASES).format(comparison=comparison)
        
        # Add comparison sentence
        sentence2_options.append(
            f"{comparison_phrase} {common_object}{plural_suffix}{random.choice(comparison_endings)}."
        )

    # Choose second sentence
    sentence2 = random.choice(sentence2_options)

    # output final sentences
    final = f"{sentence1} {sentence2}"
    return final


def descriptor_builder(dict, object_type):

    # set up the prhase number of words and choose which type of words
    phrase = ""
    key1 = random.choice(["textures", "colors"])

    # choose words based on number of words.
    # Collect unique words, texture can only have one
    # Build the phrase
    if key1 == "colors":
        used_words = []
        phrase_length = random.randint(1, 2)
        while len(used_words) < phrase_length:
            word = random.choice(dict[key1])
            if word not in used_words:
                used_words.append(word)
        phrase = p.join(used_words)
        pattern = random.choice(PATTERN_OPTIONS)
        phrase += f" {pattern}"
    else:  # textures
        word = random.choice(dict[key1])
        try:
            texture_part = random.choice(dict["texture_parts"])
        except (KeyError, IndexError):
            pass

        if object_type == "plant":
            phrase = f"{word} texture"
        elif object_type == "creature":
            phrase = f"{word} {texture_part}"
        else:  # minerals
            phrase = random.choice([f"{word} surface", f"{texture_part} sheen"])

    return phrase, key1


def dict_of_descriptor(biome, object_type):

    descriptions_dict = {
        "colors": [],
        "textures": [],
        "objects": [],
        "other": [],
        "texture_parts": [],
    }

    # if x biome, include y lists
    BIOME_COLORS = {
        "Freshwater": ["neutral"],
        "Mountain": ["neutral"],
        "Swamp": ["neutral"],
        "Underground": ["neutral"],
        "Urban": ["neutral"],
        "Plains": ["neutral", "warm"],
        "Volcanic": ["neutral", "warm"],
        "Desert": ["neutral", "warm"],
        "Tundra": ["neutral", "cool"],
        "Forest": ["neutral", "cool"],
        "Jungle": ["neutral", "warm", "cool"],
        "Ocean": ["neutral", "warm", "cool"],
    }

    BIOME_CREATURE_SUBTYPES = {
        "Desert": ["REPTILES", "BUGS", "BIRDS", "MAMMALS"],
        "Forest": ["MAMMALS", "BIRDS", "BUGS", "AMPHIBIANS"],
        "Jungle": ["MAMMALS", "BIRDS", "BUGS", "REPTILES", "AMPHIBIANS"],
        "Freshwater": ["FISH", "AMPHIBIANS", "BUGS", "BIRDS"],
        "Mountain": ["MAMMALS", "BIRDS", "REPTILES", "BUGS"],
        "Ocean": ["FISH"],
        "Plains": ["MAMMALS", "BIRDS", "BUGS", "REPTILES"],
        "Swamp": ["AMPHIBIANS", "BUGS", "REPTILES", "FISH", "BIRDS"],
        "Tundra": ["MAMMALS", "BIRDS"],
        "Underground": ["BUGS", "MAMMALS", "REPTILES"],
        "Urban": ["MAMMALS", "BIRDS", "BUGS"],
        "Volcanic": ["BUGS", "REPTILES"],
    }

    texture_part = {
        "MAMMALS": ["fur"],
        "BUGS": ["body"],
        "REPTILES": ["scales"],
        "BIRDS": ["feathers"],
        "FISH": ["scales"],
        "AMPHIBIANS": ["skin"],
    }

    BIOME_MOISTURE = {
        "WET": ["Swamp", "Jungle", "Ocean", "Freshwater"],
        "DRY": ["Desert", "Volcanic", "Tundra"],
        "EITHER": ["Forest", "Plains", "Mountain", "Underground", "Urban"],
    }

    color_groups = BIOME_COLORS[biome]
    if "neutral" in color_groups:
        descriptions_dict["colors"].extend(NEUTRAL_COLORS)
    if "warm" in color_groups:
        descriptions_dict["colors"].extend(WARM_COLORS)
    if "cool" in color_groups:
        descriptions_dict["colors"].extend(COOL_COLORS)

    # if x object type include z lists
    if object_type == "plant":

        # Determine valid moisture groups
        valid_moisture_groups = ["EITHER"]

        if biome in BIOME_MOISTURE["WET"]:
            if biome == "Ocean":
                valid_moisture_groups.clear()
            valid_moisture_groups.append("WET")
        elif biome in BIOME_MOISTURE["DRY"]:
            valid_moisture_groups.append("DRY")

        # Build plant pool from valid moisture groups
        plant_pool = {}
        for group in valid_moisture_groups:
            plant_pool.update(PLANTS[group])

        # Choose plant type
        plant = random.choice(list(plant_pool.keys()))
        plant_data = plant_pool[plant]

        # Store options for later selection
        descriptions_dict["objects"].extend(plant_data["parts"])
        descriptions_dict["textures"].extend(plant_data["textures"])

        # Contextual info for later sentence logic
        descriptions_dict["other"].append(plant)
        descriptions_dict["texture_parts"].append(valid_moisture_groups)

    elif object_type == "creature":
        valid_subtypes = BIOME_CREATURE_SUBTYPES[biome]
        creature_group = random.choice(valid_subtypes)

        descriptions_dict["objects"].extend(CREATURES[creature_group]["creatures"])
        descriptions_dict["textures"].extend(CREATURES[creature_group]["textures"])
        descriptions_dict["other"].append(creature_group)
        descriptions_dict["texture_parts"].extend(texture_part[creature_group])

        # Make mammals only neutral colored
        if creature_group == "MAMMALS":
            descriptions_dict["colors"].clear()
            descriptions_dict["colors"].extend(NEUTRAL_COLORS)

    elif object_type == "mineral":
        descriptions_dict["objects"].extend(MINERALS["objects"])
        descriptions_dict["textures"].extend(MINERALS["textures"])
        descriptions_dict["texture_parts"].extend(MINERALS["sheen"])

    return descriptions_dict


def main():

    biome = random.choice(list(biome_weights.keys()))
    skill_check = random.randint(1, 40)
    sentence = sen_gen(biome, skill_check)
    print(f"Biome: {biome} Skill Check: {skill_check}")
    print(sentence)


if __name__ == "__main__":
    main()