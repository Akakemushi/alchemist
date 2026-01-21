import random
import inflect
p = inflect.engine()

#Lists of objects and descriptions
PLANT_PARTS_BY_PLANT = {
    "shrub": ["leaf", "stem", "bark", "flower", "berry","seed", "nut", "root", "mossy growth"],
    "bush": ["leaf", "stem", "bark", "flower", "berry","seed", "nut", "root", "mossy growth"],
    "vine": ["leaf", "stem", "flower", "fruit","bean", "bulb", "mossy growth"],
    "tree": ["leaf", "bark", "root", "seed","nut", "mossy growth", "mushroom", "fungus"],
    "standalone": ["flower", "reed", "mushroom", "fungus"]
}

CREATURE_BUG = ["worm", "slug", "caterpillar", "inchworm", "flatworm", "leech", "crab", "spider", "scorpion","centipede", "millipede", "beetle", "butterfly", "moth", "wasp", "bee", "ant"]
CREATURES = ["mouse", "rat", "squirrel", "mole", "rabbit", "rodent", "cat", "fox", "weasel", "snake", "lizard", "gekko", "iguana", "frog", "toad", "finch", "crow", "hawk", "owl", "duck" ]
ROCK_FORMS = ["stone", "rock shard", "crystal shard", "ore chunk"]

MASS_NOUNS = ["bark", "fungus", "mossy growth"]
    
WARM_COLORS = ["red", "rust-colored", "amber", "golden", "burnt orange", "crimson", "scarlet", "copper", "bronze", "terracotta", "ochre", "vermillion", "coral", "peach", "salmon"]
COOL_COLORS = ["blue", "bluish-purple", "green", "teal", "pale cyan", "azure", "cobalt", "turquoise", "mint", "sage", "olive", "periwinkle", "lavender", "seafoam"]
NEUTRAL_COLORS = ["gray", "dark gray", "whitish", "off-white", "brown", "beige", "tan", "taupe", "charcoal", "ash", "silver", "pearl", "ivory", "cream", "sepia", "slate"]

PLANT_TEXTURES = ["waxy", "fibrous", "velvety", "brittle", "sappy", "thorny", "woody", "papery","prickly", "succulent", "stringy", "pulpy"]
BUG_TEXTURES = ["chitinous","segmented","spiny","bristly","plated","bumpy","ridged","waxy",]
CREATURE_TEXTURES = ["leathery","fuzzy","slimy","scaly","furry","sleek","smooth","coarse","rough","soft","slick","oily"]
MINERAL_TEXTURES = ["grainy", "jagged", "chalky", "smooth", "glassy", "porous", "flaky", "metallic", "polished", "rough", "faceted", "striated", "powdery", "glossy"]

LIGHTING_OPTIONS = ["sheen", "tones", "glow", "spots", "stripes", "speckles", "rings", "bands"]
SMELL_OPTIONS = ["acrid", "sweet", "musty", "earthy", "pungent", "fragrant", "sulfurous", "putrid"]

COMPARISON_TYPES = ["size", "weight"]
SIZE_OBJECTS = ["a loaf of bread","a wine bottle","a skull","a clay pot","a wooden bowl","a large book","a boot"]
WEIGHT_OBJECTS = ["a brick","a sack of flour","a hand axe","a kettle","a wooden club","a large stone","an iron ingot"]
BUG_OBJECTS = ["a coin","a large button","a spoon","a small pouch","a pendant","a leaf","a playing card","a small stone","a brooch"]

NOTABLE_PHRASES = ["Notable for","Distinctive for","Remarkable for","Noteworthy for","Characterized by", "Defined by", "Recognized by", "Distinguished by"]
COMPARISON_PHRASES = ["Comparable in {comparison} to", "Similar in {comparison} to", "About the {comparison} of", "Roughly the {comparison} of","Approximately the {comparison} of", "Close in {comparison} to","Nearly the {comparison} of"]
SCENT_PHRASES = ["Gives off {article_smell} scent","Emits {article_smell} aroma","Has {article_smell} smell","Produces {article_smell} odor","Carries {article_smell} fragrance","Noted for {article_smell} scent"]
STANDOUT_PHRASES = ["stands out","is striking","is distinctive","catches the eye","is noticeable","draws attention","is prominent"]

def sen_gen():

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
            "mineral": 0.2
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

    #define various options
    biome = random.choice(list(biome_weights.keys()))
    objects = list(biome_weights[biome].keys())
    weights = list(biome_weights[biome].values())
    object_type = random.choices(objects, weights=weights, k=1)[0] 
    descriptor_dict = dict_of_descriptor(biome, object_type)
    
    #Select random things for sentence, still need function
    thing = random.choice(descriptor_dict["objects"])
    descriptor1 = descriptor_builder(descriptor_dict)
    descriptor2 = descriptor_builder(descriptor_dict)
    color = random.choice(descriptor_dict["colors"])

    #Checks descriptors dont match
    ending1 = descriptor1.split()[-1]

    while True:
        ending2 = descriptor2.split()[-1]

        if descriptor1.endswith("texture") and descriptor2.endswith("texture"):
            descriptor2 = descriptor_builder(descriptor_dict)
            continue

        if ending1 in LIGHTING_OPTIONS and ending2 in LIGHTING_OPTIONS:
            descriptor2 = descriptor_builder(descriptor_dict)
            continue

        break

    #Some grammar fixes for articles
    article_thing = p.a(f"{color} {thing}")
    if thing in MASS_NOUNS:
        plural_thing = thing
    else:
        plural_thing = p.plural(thing)

    last_word = descriptor1.split()[-1]
    if p.singular_noun(last_word):  # Returns False if already singular
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
    descriptor1_words = descriptor1.split()
    descriptor1_short = " ".join(descriptor1_words[:-1])
    sentence1_options = [
        f"{article_thing.capitalize()}{plant_phrase} with {article_descriptor}.",
        f"Some {plural_thing}{plant_phrase} that have {article_descriptor}.",
        f"{descriptor1_short.capitalize()} {plural_thing}{plant_phrase}."
    ]
    sentence1_choice = random.randint(0, len(sentence1_options) - 1)
    sentence1 = sentence1_options[sentence1_choice]

    # Determine if plural (options 1 and 2 are plural)
    is_plural = sentence1_choice in [1, 2]
    if is_plural:  
        possessive = "their"
        plural = " each." 
    else:
        possessive ="its"
        plural = "."

    #Create parts and put together Sentences 2  
    notable_phrase = random.choice(NOTABLE_PHRASES)
    
    words = descriptor2.split()
    last_word = words[-1]
    if p.singular_noun(last_word):
        standout_phrase = random.choice(STANDOUT_PHRASES)
        phrase_words = standout_phrase.split()
        phrase_words[0] = p.plural_verb(phrase_words[0], 2)  # 2 = plural
        standout_phrase = " ".join(phrase_words)
    else:
        standout_phrase = random.choice(STANDOUT_PHRASES)
    
    if object_type == "plant":
        sentence2 = random.choice([f"{notable_phrase} {possessive} {descriptor2}.", 
                                   f"{smell_phrase}.", 
                                   f"{possessive.capitalize()} {descriptor2} {standout_phrase}."])
    else: # Creature or Mineral
        comparison = random.choice(COMPARISON_TYPES)
        if thing in CREATURE_BUG:
             common_object = random.choice(BUG_OBJECTS)
        elif comparison == "size":
            common_object = random.choice(SIZE_OBJECTS)
        else:  # weight
            common_object = random.choice(WEIGHT_OBJECTS)
        
        comparison_phrase = random.choice(COMPARISON_PHRASES).format(comparison=comparison)
        
        sentence2 = random.choice([f"{comparison_phrase} {common_object}{plural}", 
                                   f"{notable_phrase} {possessive} {descriptor2}.", 
                                   f"{possessive.capitalize()} {descriptor2} {standout_phrase}."])

    #output sentence
    final = (f"{sentence1} {sentence2}")
    return final

def descriptor_builder(dict):
    
    #set up the prhase number words and choose which type of words
    phrase = ""
    phrase_length = random.randint(1, 3)
    key1 = random.choice(["textures", "colors"])
    used_words = []
    
    # choose words based on number of words. 
    # Collect unique words, texture can only have one
    if key1 == "textures":
        phrase_length = 1
    
    while len(used_words) < phrase_length:
        word = random.choice(dict[key1])
        if word not in used_words:
            used_words.append(word)

    # Build the phrase
    phrase = p.join(used_words)
    
    if key1 == "colors": 
        lighting = random.choice(LIGHTING_OPTIONS)
        phrase += " " + lighting
    else:
        phrase += " texture"

    return phrase
          
def dict_of_descriptor(biome, object_type):

    descriptions_dict = {
    "colors": [],
    "textures": [],
    "objects": [],
    "other": []
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

    color_groups = BIOME_COLORS[biome]
    if "neutral" in color_groups:
        descriptions_dict["colors"].extend(NEUTRAL_COLORS)
    if "warm" in color_groups:
        descriptions_dict["colors"].extend(WARM_COLORS)
    if "cool" in color_groups:
        descriptions_dict["colors"].extend(COOL_COLORS)

    #if x object type include z lists
    if object_type == "plant":
        plant = random.choice(list(PLANT_PARTS_BY_PLANT.keys()))
        plant_part = random.choice(PLANT_PARTS_BY_PLANT[plant]) 
        descriptions_dict["objects"].append(plant_part)
        descriptions_dict["textures"].extend(PLANT_TEXTURES)
        descriptions_dict["other"].append(plant)
             
    elif object_type == "creature":
        creature_group = random.choice(["creature", "bug"])
        if creature_group == "creature":
            descriptions_dict["objects"].extend(CREATURES)
            descriptions_dict["textures"].extend(CREATURE_TEXTURES)
        else:  # bug
            descriptions_dict["objects"].extend(CREATURE_BUG)
            descriptions_dict["textures"].extend(BUG_TEXTURES)
       
    elif object_type == "mineral": 
        descriptions_dict["objects"].extend(ROCK_FORMS)
        descriptions_dict["textures"].extend(MINERAL_TEXTURES)

    return descriptions_dict

def main():
    sentence =sen_gen()
    print(sentence)
        
if __name__ == "__main__":
    main()