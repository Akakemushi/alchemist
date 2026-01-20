import random
import inflect
p = inflect.engine()

#Lists of objects and descriptions
plant_parts = ["leaf","root","stem","bulb","mossy growth", "flower"]
small_creature_parts = ["feather","scale","tiny bone","fin fragment","egg", "beetle","larva","moth","winged insect","carapace fragment"]
rock_forms = ["stone","sand","dust","shard", "ore chunk"]
    
WARM_COLORS = ["red", "rust-colored", "amber", "golden", "burnt orange", "crimson", "scarlet", "copper", "bronze", "terracotta", "ochre", "vermillion", "coral", "peach", "salmon"]
COOL_COLORS = ["blue", "bluish-purple", "green", "teal", "pale cyan", "azure", "cobalt", "turquoise", "mint", "sage", "olive", "periwinkle", "lavender", "seafoam"]
NEUTRAL_COLORS = ["gray", "dark gray", "whitish", "off-white", "brown", "beige", "tan", "taupe", "charcoal", "ash", "silver", "pearl", "ivory", "cream", "sepia", "slate"]
plant_textures = ["waxy", "fibrous", "velvety", "brittle", "sappy", "thorny", "mossy", "woody", "papery", "feathery", "prickly", "succulent", "leafy", "stringy", "pulpy"]
creature_textures = ["chitinous", "leathery", "fuzzy", "slimy", "segmented", "scaly", "furry", "rubbery", "gelatinous", "spiny", "bristly", "plated", "mucous", "bumpy", "ridged"]
mineral_textures = ["grainy", "jagged", "chalky", "smooth", "crystalline", "glassy", "porous", "flaky", "metallic", "polished", "rough", "faceted", "striated", "powdery", "glossy"]

LIGHTING_OPTIONS = ["reflection", "sheen", "tones", "glow", "spots", "stripes", "speckles", "rings", "bands"]
SMELL_OPTIONS = ["acrid", "sweet", "musty", "earthy", "pungent", "fragrant", "sulfurous", "putrid"]
COMPARISON_TYPES = ["size", "weight"]
SMALL_OBJECTS = ["a coin", "a marble", "a clenched fist", "a pebble", "a walnut", "a chicken egg"]
AMOUNT_OBJECTS = ["a handful", "a pinch", "a small pouch", "a vial"]
AMOUNT_ITEMS = ["dust", "sand"]

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
    while descriptor1.endswith("texture") and descriptor2.endswith("texture"):
        descriptor2 = descriptor_builder(descriptor_dict)

    #Some grammar fixes for articles
    article_thing = p.a(f"{color} {thing}")
    plural_thing = p.plural(thing)

    last_word = descriptor1.split()[-1]
    if p.singular_noun(last_word):  # Returns False if already singular
        article_descriptor = descriptor1  # No article for plural
    else:
        article_descriptor = p.a(descriptor1) # It's singular, needs article
  
    #Define sentences  
    sentence1 = random.choice([f"{article_thing.capitalize()} with {article_descriptor}.", f"Some {plural_thing} that have {article_descriptor}."])
    
    if object_type == "plant":
        smell = random.choice(SMELL_OPTIONS)
        sentence2 = random.choice([f"Notable for its {descriptor2}.", f"It gives off a {smell} scent."])
    else:
        comparison = random.choice(COMPARISON_TYPES)
        common_object = random.choice(SMALL_OBJECTS)
        if thing in AMOUNT_ITEMS:
            comparison = "amount"
            common_object = random.choice(AMOUNT_OBJECTS)
        sentence2 = random.choice([f"Comparable in {comparison} to {common_object}.", f"Notable for its {descriptor2}."])

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
    # Collect unique words
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
    "objects": []
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
        descriptions_dict["objects"].extend(plant_parts)
        descriptions_dict["textures"].extend(plant_textures)
     
    elif object_type == "creature":
        descriptions_dict["objects"].extend(small_creature_parts)
        descriptions_dict["textures"].extend(creature_textures)
        
    elif object_type == "mineral": 
        descriptions_dict["objects"].extend(rock_forms)
        descriptions_dict["textures"].extend(mineral_textures)

    return descriptions_dict

def main():
    sentence =sen_gen()
    print(sentence)
        
if __name__ == "__main__":
    main()