import random
import inflect
p = inflect.engine()

# Biome weights of item types
biome_weights = {
        "Desert":{
            "plant": 0.2,
            "creature": 0.2,
            "mineral": 0.6
            }, 
        "Forest":{
            "plant": 0.4,
            "creature": 0.4,
            "mineral": 0.2
            }, 
        "Jungle":{
            "plant": 0.5,
            "creature": 0.4,
            "mineral": 0.1
            }, 
        "Freshwater":{
            "plant": 0.4,
            "creature": 0.2,
            "mineral": 0.4
            }, 
        "Mountain":{
            "plant": 0.3,
            "creature": 0.2,
            "mineral": 0.5
            }, 
        "Ocean":{
            "plant": 0.4,
            "creature": 0.5,
            "mineral": 0.1
            }, 
        "Plains":{
            "plant": 0.4,
            "creature": 0.4,
            "mineral": 0.2
            },
        "Swamp":{
            "plant": 0.6,
            "creature": 0.3,
            "mineral": 0.1
        },
        "Tundra":{
            "plant": 0.3,
            "creature": 0.2,
            "mineral": 0.5
        }, 
        "Underground":{
            "plant": 0.2,
            "creature": 0.3,
            "mineral": 0.5
        }, 
        "Urban":{
            "plant": 0.2,
            "creature": 0.6,
            "mineral": 0.2
        }, 
        "Volcanic":{
            "plant": 0.2,
            "creature": 0.1,
            "mineral": 0.7
        }
    }

#Lists of objects and descriptions
PLANTS = {
    "WET": {
        "mangrove": {
            "parts": ["root", "strips of bark", "leaf", "seed"],
            "textures": ["waxy", "fibrous"]
        },
        "vine": {
            "parts": ["leaf", "stem", "fruit", "bean"],
            "textures": ["waxy", "fibrous", "velvety"]
        }
    },

    "DRY": {
        "cactus": {
            "parts": ["pad", "flower", "fruit", "spine cluster"],
            "textures": ["waxy", "brittle"]
        }
    },

    "EITHER": {
        "tree": {
            "parts": ["leaf", "strips of bark", "root", "nut"],
            "textures": ["woody", "fibrous", "papery"]
        },
        "shrub": {
            "parts": ["leaf", "stem", "flower", "berry", "seed"],
            "textures": ["fibrous", "papery"]
        },
        "bush": {
            "parts": ["leaf", "berry", "seed"],
            "textures": ["fibrous", "waxy"]
        },
        "standalone": {
            "parts": ["flower", "mushroom", "fungus", "reed"],
            "textures": ["soft", "velvety"]
        }
    }
}

SCENT_PHRASES = ["Gives off {article_smell} scent","Emits {article_smell} aroma","Has {article_smell} smell","Produces {article_smell} odor","Carries {article_smell} fragrance","Noted for {article_smell} scent"]
MASS_NOUNS = ["strips of bark", "fungus", "mossy growth"]

CREATURES = {
    "MAMMALS": {
        "creatures": ["mouse", "rat", "squirrel", "mole", "rabbit", "rodent", "cat", "fox", "weasel"],
        "textures": ["fuzzy", "furry", "sleek", "smooth", "coarse", "soft"],
    },
    "BUGS": {
        "creatures": ["worm", "slug", "caterpillar", "inchworm", "flatworm", "leech", "spider", "scorpion", "centipede", "millipede", "beetle", "butterfly", "moth", "wasp", "bee", "ant"],
        "textures": ["chitinous", "spiny", "bristly", "plated", "bumpy", "rigid", "waxy"]
        
    },
    "REPTILES": {
        "creatures": ["snake", "lizard", "gekko", "iguana"],
        "textures": ["leathery", "smooth", "rough", "sleek"]
    },
    "AMPHIBIANS": {
        "creatures": ["frog", "toad"],
        "textures": ["slimy", "smooth", "slick", "soft", "greasy"]
    },
    "BIRDS": {
        "creatures": ["finch", "crow", "hawk", "owl", "duck"],
        "textures": ["sleek", "smooth", "soft", "fuzzy", "greasy"]
    },
    "FISH": {
        "creatures": ["minnow", "perch", "trout", "carp", "bass", "sunfish", "catfish", "eel"],
        "textures": ["slimy", "smooth", "slick", "greasy", "sleek"]
    }
}

MINERALS = {
    "objects": ["stone", "rock shard", "ore chunk", "mineral"],
    "textures": ["grainy", "jagged", "chalky", "smooth", "glassy", "porous", "metallic", "rough", "faceted", "powdery"],
    "sheen": ["metallic", "pearly",  "lustrous", "iridescent", "rainbow", "silvery", "golden", "coppery"]
}

WARM_COLORS = ["red", "rust-colored", "amber", "golden", "burnt orange", "crimson", "scarlet", "copper", "bronze", "ochre", "vermillion"]
COOL_COLORS = ["blue", "bluish-purple", "green", "teal", "pale cyan", "azure", "cobalt", "turquoise", "mint", "sage", "lavender"]
NEUTRAL_COLORS = ["gray", "dark gray", "whitish", "off-white", "brown", "beige", "tan", "charcoal", "ash", "silver"]
BASIC_COLORS =  ["red", "red-orange", "orange", "yellow", "yellow-green", "green", "blue-green", "blue", "violet", "purple", "indigo", "pink"]

PATTERN_OPTIONS = ["tones", "spots", "stripes", "speckles", "rings", "bands"]
PATTERN_OPTIONS_ED = ["toned", "spotted", "striped", "speckled", "ringed", "banded", "splotched"]

SMELL_OPTIONS = ["acrid", "sweet", "musty", "citrusy", "earthy", "pungent", "fragrant", "sulfurous", "putrid"]

COMPARISON_TYPES = ["size", "weight"]
SIZE_OBJECTS = ["a loaf of bread","a wine bottle","a skull","a clay pot","a boot","a large book","a boot"]
WEIGHT_OBJECTS = ["a brick","a sack of flour","a hand axe","a kettle","a clay mug","a large stone","an iron ingot"]
BUG_OBJECTS = ["a leaf", "a twig","an acorn", "a flower", "a coin", "a crystal"]
NOTABLE_PHRASES = ["Notable for","Distinctive for","Remarkable for","Noteworthy for","Characterized by", "Defined by", "Recognized by", "Distinguished by"]
COMPARISON_PHRASES = ["Comparable in {comparison} to", "Similar in {comparison} to", "About the {comparison} of", "Roughly the {comparison} of","Approximately the {comparison} of", "Close in {comparison} to","Nearly the {comparison} of"]
STANDOUT_PHRASES = ["stands out","is striking","is distinctive","catches the eye","is noticeable","draws attention","is prominent"]

SHAPES2D = ["heart", "teardrop", "triangle", "star", "crescent", "oval", "arrowhead", "spade", "hexagon"]
SHAPES3D = ["spherical", "cubic", "conical", "cylindrical", "pyramidal"]
SIZES = ["tiny", "small", "modestly sized", "large", "huge"]
BODY_ADJECTIVES = ["thin", "stocky", "fat", "scrawny", "slender", "stout", "bulky", "petite", "spindly", "robust", "delicate"]

#choose which type object and then form of sentence to output based on biome
def sen_gen(biome):

    #define various options
    objects = list(biome_weights[biome].keys())
    weights = list(biome_weights[biome].values())
    object_type = random.choices(objects, weights=weights, k=1)[0] 
    descriptor_dict = dict_of_descriptor(biome, object_type)
   
   #Decide which funtion to output sentence and then return it
    roll = random.randint(1, 10)
    if object_type == "plant":
        premade_chance = 6
    elif object_type == "creature":
        premade_chance = 7
    else: #Mineral
        premade_chance = 5

    if roll <= premade_chance:
        sentence = generate_premade_sentence(descriptor_dict, object_type)
    else:
        sentence = generate_random_sentence(descriptor_dict, object_type)

    return sentence      

#Function for predetermined sentences
def generate_premade_sentence(descriptor_dict, object_type):

    #Picking some likely global variables.
    color1 = random.choice(descriptor_dict["colors"])
    color2 = random.choice(descriptor_dict["colors"])
    while color2 == color1:
        color2 = random.choice(descriptor_dict["colors"])
    basicolor = random.choice(BASIC_COLORS)
    num1 = random.randint(2, 8)
    num2 = num1 + random.randint(2, 4)
    shape1 = random.choice(SHAPES2D)
    article_shape = p.a(f"{shape1}")
    size1 = random.choice(SIZES)
    texture = random.choice(descriptor_dict["textures"])
    pattern = random.choice(PATTERN_OPTIONS)
    shape2 = random.choice(SHAPES3D)
    article_color = p.a(f"{color1}")
    body = random.choice(BODY_ADJECTIVES)

    #managing plants variables
    if object_type == "plant":
        plant = descriptor_dict["other"][0]
        while plant == "standalone":
            plant = random.choice(list(PLANTS["EITHER"].keys()))
        smell = random.choice(SMELL_OPTIONS)
        mammal = p.plural(random.choice(CREATURES["MAMMALS"]["creatures"]))
        neutral = random.choice(NEUTRAL_COLORS)
        size2 = random.choice(SIZES)

        biome_type = random.choice(random.choice(descriptor_dict["texture_parts"]))

    #Plant sentences options
        PLANT_SENTENCES = {
            "WET": [
                f"A {body} {plant} with {basicolor} flowers that have {num1}~{num2} bony spikes protruding from the tip of each petal. Painful to touch, like a cactus.",
                f"{body.capitalize()} reeds growing to about {num1} feet tall with {texture} {color1} stalks. The roots form dense tangles underwater.",
                f"{texture.capitalize()} {color1} mangrove roots that form tangled networks above the waterline. A root segment is {num1}~{num2} inches thick.",
                f"{color1.capitalize()} {texture} bean pods that hang in clusters of {num1}~{num2}. Each pod is roughly {shape1}-shaped and smells {smell}.",
                f"{texture.capitalize()} bamboo shoots that emerge in clusters of {num1}~{num2}. Each shoot is {color1} with {basicolor} rings and grows rapidly in moist soil."
            ],
            "DRY": [
                f"A {body} {plant} with {basicolor} flowers that have {num1}~{num2} bony spikes protruding from the tip of each petal. Painful to touch, like a cactus.",
                f"{texture.capitalize()} seed pods that split open when dry, revealing {num1}~{num2} {color1} seeds inside. Each pod is {shape2}-shaped.",
                f"{texture.capitalize()} {color1} cactus pads shaped like {shape1}s. Surface covered in clusters of {num1}~{num2} {basicolor} spines."
            ],
            "EITHER": [
                f"{num1}-foot tall {plant} with {texture}, {color1} {shape1}-shaped leaves. {shape2.capitalize()}-shaped protrusions stick out from the center.",
                f"Knee-high {color1} grass with very {texture} edges. Smells slightly {smell}.",
                f"{num2}-inch long {color1} {shape2} flower with {texture} petals and a feather-like stamen which sticks out about {num1} inches from the flower.",
                f"Clusters of small {shape1} leaves in bundles of {num1}~{num2} terminate at the ends of these {color1}, {texture}, {body} plants. Smells very {smell}.",
                f"{body.capitalize()} {shape2} {color1} flowers of {num1}~{num2} petals which hang upside-down. Grows from a {plant}.",
                f"{size1.capitalize()}, {texture} {color1} berries with tiny {neutral} seeds around its surface that grow in {size2} clusters. Attracts {mammal}.",
                f"{num1}-petaled flower, {num1}~{num2} inches in diameter with {article_color} center. {color2.capitalize()} {pattern} towards the edges.",
                f"{size1.capitalize()} mushroom with {texture} {color1} cap marked with {color2} {pattern}. The {basicolor} stem is {num1}~{num2} inches tall.",
                f"Clusters of {num1}~{num2} {size2} mushrooms with {body} {shape1}-shaped caps. {color1.capitalize()} on top, {basicolor} gills underneath."
                ]}
        
        sentences_choices = PLANT_SENTENCES[biome_type]                     
        final = random.choice(sentences_choices)

    #managing creature variables
    if object_type == "creature":
        sentences_choices = []
        smell = random.choice(SMELL_OPTIONS)
        object = random.choice(SIZE_OBJECTS)
        creature = (random.choice(descriptor_dict["objects"]))
        bug_obj = random.choice(BUG_OBJECTS)
        pattern2 = random.choice(PATTERN_OPTIONS_ED)
        element =  random.choice(["light", "smoke", "heat", "cold", "salt", "vinegar", "strong scents"])

        #Possible sentence based on subtye of creature
        creature_subtypes = descriptor_dict["other"][0]
        
        sentences_subtypes= {
        "REPTILES" : [f"{article_color.capitalize()} to {color2} {creature} about {num1}~{num2} inches in length with a bright {basicolor} underbelly.", 
                    f"A {size1} {creature} with a {body} {color1} body and a neck frill that is bright {basicolor} when opened. The frill is about {num1}~{num2} inches long.",
                    f"A {creature} with {color1} scales that fade to {color2} near the tail. Has a {size1} head with {basicolor} eyes and measures roughly {num1}~{num2} inches from snout to tail tip."],
        "BIRDS" : [f"A {basicolor}-eyed {creature}, slightly smaller than {object}. Feathers are {color1} at the root and gradually turn {color2} at the tip.",
                    f"{color1.capitalize()}, {pattern2} eggs with an uneven shape. The shell has a {texture} texture.",
                    f"A {size1} {creature} with {color1} plumage and a {basicolor} crest. Its call is sharp and distinctive."],
        "BUGS" : [f"Resembles a {color1} {creature} but with a {body} build and {texture} surface.",
                  f"{article_color.capitalize()} {creature} that can mimic the appearance of {bug_obj}. Its {body} shape and {pattern2} markings complete the disguise.",
                  f"{size1.capitalize()} {creature} covered in {texture} segments. Highly sensitive to {element} and will flee when it detects it nearby."],
        "FISH" : [f"{size1.capitalize()} {color1} {creature} that smells {smell} when removed from the water. Usually found in small schools.",
                  f"{size1.capitalize()} {creature} with {color1} and {color2} {pattern} across its fins. Known for its {texture} scales and tendency to swim in {shape1} formations.",
                f"A {body} {creature} with {color1} scales and skin. Its head is {size1} and {shape1}-shaped, with {color2} eyes. Its fins have light {basicolor} {pattern} on them."],
        "MAMMALS" : [ f"A {creature} with {color1} fur and a noticeable {basicolor} patch on its back in the shape of {article_shape}. It is {size1} compared to others like it.",
                    f"{article_color.capitalize()} {creature} with a {texture} tail ending in {article_shape} shape. It often stands up on its hind legs.",
                    f"{article_color.capitalize()} {creature} featuring {color2} {pattern2} markings across its back. Known for its {texture} coat and sharp {basicolor} eyes."],
        "AMPHIBIANS" : [f"A {size1} {creature} with {color1} skin covered in {basicolor} {pattern}. Its throat pouch inflates when threatened.",
                        f"{article_color.capitalize()} {creature} about {num1}~{num2} inches long with {texture} skin and {color2} eyes. Often found near water sources.",
                        f"A {creature} with a {body} build and {color1} coloration. Has distinctive {basicolor} markings behind its eyes and webbed feet." ]
                    }

        #select sentence from list
        final = random.choice(sentences_subtypes[creature_subtypes])
       
       #Mineral sentence consturction
    if object_type == "mineral":
        weight = random.choice(["lighter", "heavier"])
        element = random.choice(["moonlight", "sunlight", "fire", "water", "heat", "cold", "salt", "iron"])
        pattern2 = random.choice(PATTERN_OPTIONS_ED)
        sentences_choices = [
        f"{shape2.capitalize()} translucent {color1} stones which have a {color2} {shape1}-shaped metal bit in their center.",
        f"A mix of {color1} and {color2} sand which begins to glow {basicolor} in the proximity of {element}.",
        f"{color1.capitalize()} {pattern2} metal which forms into {shape1} shapes. {weight.capitalize()} than expected.", 
        f"{color1.capitalize()} crystal shards with {color2} {pattern} running through them. They emit {basicolor} sparks when struck together.",
        f"Magnetic {color1} sand that clumps together when disturbed. The clumps have a {texture} texture and {basicolor} sheen.",
        f"{shape2.capitalize()}-shaped geode with a rough {color1} exterior. When cracked open, the interior reveals {basicolor} crystalline formations.",
        f"{color1.capitalize()} stones with natural {shape1}-shaped faces. The surface is {texture} and shows {color2} veining along the edges."]

        final = random.choice(sentences_choices)

    return final


#Function to pick random item and give random descriptions
def generate_random_sentence(descriptor_dict, object_type):

    #Select random things for sentence, still need function
    thing = random.choice(descriptor_dict["objects"])
    descriptor1, type1 = descriptor_builder(descriptor_dict, object_type)
    descriptor2, type2 = descriptor_builder(descriptor_dict, object_type)
    color = random.choice(descriptor_dict["colors"])

    #Checks descriptors dont match
    # Force descriptor1 to be texture (not color)
    while type1 == "colors":
        descriptor1, type1 = descriptor_builder(descriptor_dict, object_type)

# Then ensure descriptor2 is different from descriptor1
    while type1 == type2:
        descriptor2, type2 = descriptor_builder(descriptor_dict, object_type)

    #Some grammar fixes for articles
    article_thing = p.a(f"{thing}")
    if thing in MASS_NOUNS:
        plural_thing = thing
        article_thing = thing
    else:
        plural_thing = p.plural(thing)

    last_word = descriptor1.split()[-1]
    if p.singular_noun(last_word) or last_word == "fur":  # Returns False if already singular
        article_descriptor = descriptor1  # No article for plural
    else:
        article_descriptor = p.a(descriptor1) # It's singular, needs article

    #Special set up for plant sentences
    if object_type == "plant":
        plant_type = (random.choice(descriptor_dict["other"]))
        if plant_type == "standalone":
            plant_phrase = ""
        else:
            plant_phrase = f" from a {plant_type}"
        smell = random.choice(SMELL_OPTIONS)
        article_smell = p.a(f"{smell}")
        smell_phrase = random.choice(SCENT_PHRASES).format(article_smell=article_smell)
    else:
        plant_phrase = ""
  
    #Define sentences
    #Put together parts for sentence 1
    if object_type == "creature":
        sentence1 = f"{article_thing.capitalize()} with {article_descriptor}."
        is_plural = False
    else: #Plant or Mineral
        descriptor1_words = descriptor1.split()
        descriptor1_short = " ".join(descriptor1_words[:-1])
        sentence1_options = [
            f"{article_thing.capitalize()}{plant_phrase} with {article_descriptor}.",
            f"Some {plural_thing}{plant_phrase} that have {article_descriptor}.",
            ]
        sentence1_choice = random.randint(0, len(sentence1_options) - 1)
        sentence1 = sentence1_options[sentence1_choice]
        is_plural = (sentence1_choice in [1, 2]) if thing not in MASS_NOUNS else False

    # Determine if plural (options 1 and 2 are plural)
    possessive = "their" if is_plural else "its"
    plural_suffix = " each," if is_plural else ","

    # Sentence 2 construction
    # Prepare descriptor2 variations
    notable_phrase = random.choice(NOTABLE_PHRASES)
    standout_phrase = random.choice(STANDOUT_PHRASES)

    #Create parts and put together Sentences 2  
    words = descriptor2.split()
    last_word = words[-1]
    if p.singular_noun(last_word):
        phrase_words = standout_phrase.split()
        phrase_words[0] = p.plural_verb(phrase_words[0], 2)  # 2 = plural
        standout_phrase = " ".join(phrase_words)
        
    if object_type == "plant":
        sentence2_options =[f"{notable_phrase} {possessive} {descriptor2}.", 
                            f"{smell_phrase}.", 
                            f"{possessive.capitalize()} {descriptor2} {standout_phrase}."]
        sentence2 = random.choice(sentence2_options)

    else: # Creature or Mineral
        comparison = random.choice(COMPARISON_TYPES)
        conj = random.choice(["but", "and", "yet"])
        if thing in CREATURES["BUGS"]["creatures"]:
            common_object = random.choice(BUG_OBJECTS)
            modifier = random.choice(["sturdier", "more fragile", "denser","more delicate"])
        elif comparison == "size":
            common_object = random.choice(SIZE_OBJECTS)
            modifier = random.choice(["heavier", "lighter", "denser", "less dense"])
        else:  # weight
            common_object = random.choice(WEIGHT_OBJECTS)
            modifier = random.choice(["larger", "smaller", "bulkier", "more compact"])
        
        comparison_phrase = random.choice(COMPARISON_PHRASES).format(comparison=comparison)
        
        sentence2_options = [f"{notable_phrase} {possessive} {descriptor2}.", 
                            f"{possessive.capitalize()} {descriptor2} {standout_phrase}.",
                            f"{comparison_phrase} {common_object}{plural_suffix} {conj} {modifier} than expected."]
        
        sentence2 = random.choice(sentence2_options)


    #output sentence
    final = (f"{sentence1} {sentence2}")
    return final

def descriptor_builder(dict, object_type):
  
    #set up the prhase number of words and choose which type of words
    phrase = ""
    key1 = random.choice(["textures", "colors"])
       
    # choose words based on number of words. 
    # Collect unique words, texture can only have one
    # Build the phrase
    if key1 == "colors": 
        used_words = []
        phrase_length = random.randint(1, 3)
        while len(used_words) < phrase_length:
            word = random.choice(dict[key1])
            if word not in used_words:
                used_words.append(word)
        phrase = p.join(used_words)             
        pattern = random.choice(PATTERN_OPTIONS)
        phrase += f" {pattern}"
    else: #textures
        word = random.choice(dict[key1])
        try:
            texture_part = random.choice(dict["texture_parts"])
        except (KeyError, IndexError):
            pass

        if object_type == "plant":
            phrase = f"{word} texture"
        elif object_type == "creature":
            phrase = f"{word} {texture_part}"
        else: #minerals          
            phrase = random.choice([f"{word} surface", f"{texture_part} sheen"])

    return phrase, key1        
      
def dict_of_descriptor(biome, object_type):

    descriptions_dict = {
    "colors": [],
    "textures": [],
    "objects": [],
    "other": [],
    "texture_parts": []
    }
    
    #if x biome, include y lists
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
        "Ocean": ["neutral", "warm", "cool"]
    }

    BIOME_CREATURE_SUBTYPES = {
    "Desert": ["REPTILES","BUGS","BIRDS","MAMMALS"],
    "Forest": ["MAMMALS","BIRDS","BUGS","AMPHIBIANS"],
    "Jungle": ["MAMMALS","BIRDS","BUGS","REPTILES","AMPHIBIANS"],
    "Freshwater": ["FISH","AMPHIBIANS","BUGS","BIRDS","MAMMALS"],
    "Mountain": ["MAMMALS","BIRDS","REPTILES","BUGS"],
    "Ocean": ["FISH"],
    "Plains": ["MAMMALS","BIRDS","BUGS","REPTILES"],
    "Swamp": ["AMPHIBIANS","BUGS","REPTILES","FISH","BIRDS"],
    "Tundra": ["MAMMALS","BIRDS"],
    "Underground": ["BUGS","MAMMALS","REPTILES"],
    "Urban": ["MAMMALS","BIRDS","BUGS"],
    "Volcanic": ["BUGS","REPTILES"]
    }

    texture_part = {
        "MAMMALS": ["fur"],
        "BUGS" : ["body"],
        "REPTILES": ["scales"],
        "BIRDS": ["feathers"],
        "FISH": ["scales"],
        "AMPHIBIANS": ["skin"]
    }

    BIOME_MOISTURE = {
    "WET": ["Swamp", "Jungle", "Ocean", "Freshwater"],
    "DRY": ["Desert", "Volcanic", "Tundra"],
    "EITHER": ["Forest", "Plains", "Mountain", "Underground", "Urban"]
    }

    color_groups = BIOME_COLORS[biome]
    if "neutral" in color_groups:
        descriptions_dict["colors"].extend(NEUTRAL_COLORS)
    if "warm" in color_groups:
        descriptions_dict["colors"].extend(WARM_COLORS)
    if "cool" in color_groups:
        descriptions_dict["colors"].extend(COOL_COLORS)

    #if x object type include z lists
    if object_type == "plant":
      
        # Determine valid moisture groups
        valid_moisture_groups = ["EITHER"]

        if biome in BIOME_MOISTURE["WET"]:
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
        
        #Make mammals only neutral colored
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
    sentence = sen_gen(biome)
    print(f"Biome: {biome}")
    print(sentence)
        
if __name__ == "__main__":
    main()