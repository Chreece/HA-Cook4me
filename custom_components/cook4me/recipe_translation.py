"""Exact saved/bundled recipe translations. Never invokes an AI service."""
from copy import deepcopy
import re
import unicodedata


# Assistant-authored complete phrases. Unknown instructions are never guessed
# or reconstructed from ingredient lists; the original recipe remains visible.
PHRASES = (
    ("Prepare the ingredients", "Ετοιμάστε τα υλικά", "Zutaten vorbereiten", "Préparer les ingrédients"),
    ("Add the ingredients", "Προσθέστε τα υλικά", "Zutaten hinzufügen", "Ajouter les ingrédients"),
    ("Mix the ingredients", "Ανακατέψτε τα υλικά", "Zutaten vermischen", "Mélanger les ingrédients"),
    ("Mix well", "Ανακατέψτε καλά", "Gut vermischen", "Bien mélanger"),
    ("Stir", "Ανακατέψτε", "Umrühren", "Remuer"),
    ("Add water", "Προσθέστε νερό", "Wasser hinzufügen", "Ajouter l'eau"),
    ("Add the oil", "Προσθέστε το λάδι", "Öl hinzufügen", "Ajouter l'huile"),
    ("Add the vegetables", "Προσθέστε τα λαχανικά", "Gemüse hinzufügen", "Ajouter les légumes"),
    ("Add the rice", "Προσθέστε το ρύζι", "Reis hinzufügen", "Ajouter le riz"),
    ("Close the lid", "Κλείστε το καπάκι", "Deckel schließen", "Fermer le couvercle"),
    ("Open the lid", "Ανοίξτε το καπάκι", "Deckel öffnen", "Ouvrir le couvercle"),
    ("Pressure cooking", "Μαγείρεμα υπό πίεση", "Garen unter Druck", "Cuisson sous pression"),
    ("Start cooking", "Ξεκινήστε το μαγείρεμα", "Garvorgang starten", "Lancer la cuisson"),
    ("Brown the onions", "Σοτάρετε τα κρεμμύδια", "Zwiebeln anbraten", "Faire dorer les oignons"),
    ("Season to taste", "Προσθέστε καρυκεύματα κατά προτίμηση", "Nach Geschmack würzen", "Assaisonner à votre goût"),
    ("Season with salt and pepper", "Αλατοπιπερώστε", "Mit Salz und Pfeffer würzen", "Saler et poivrer"),
    ("Serve", "Σερβίρετε", "Servieren", "Servir"),
    ("Serve hot", "Σερβίρετε ζεστό", "Heiß servieren", "Servir chaud"),
    ("Serve immediately", "Σερβίρετε αμέσως", "Sofort servieren", "Servir immédiatement"),
    ("Enjoy", "Καλή όρεξη", "Guten Appetit", "Bon appétit"),
    ("Let cool", "Αφήστε να κρυώσει", "Abkühlen lassen", "Laisser refroidir"),
    ("Keep warm", "Διατηρήστε το φαγητό ζεστό", "Warm halten", "Maintenir au chaud"),
    ("Drain", "Στραγγίστε", "Abgießen", "Égoutter"),
    ("Rice", "Ρύζι", "Reis", "Riz"),
    ("Vegetable soup", "Σούπα λαχανικών", "Gemüsesuppe", "Soupe de légumes"),
    ("Lentil soup", "Σούπα με φακές", "Linsensuppe", "Soupe de lentilles"),
    ("Tomato soup", "Ντοματόσουπα", "Tomatensuppe", "Soupe de tomates"),
    ("Pumpkin soup", "Κολοκυθόσουπα", "Kürbissuppe", "Soupe de potiron"),
    ("Mushroom risotto", "Ριζότο με μανιτάρια", "Pilzrisotto", "Risotto aux champignons"),
    ("Mashed potatoes", "Πουρές πατάτας", "Kartoffelpüree", "Purée de pommes de terre"),
    ("Rice pudding", "Ρυζόγαλο", "Milchreis", "Riz au lait"),
    ("Apple compote", "Κομπόστα μήλου", "Apfelkompott", "Compote de pommes"),
)
LANGUAGES = ("en", "el", "de", "fr")


def normalized(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or "")).casefold()).strip(" .!\n\t")


def step_text(step):
    if isinstance(step, str):
        return step
    return str(step.get("instruction") or step.get("applicationDescription") or step.get("applianceDescription")
        or step.get("text") or step.get("description") or "\n".join(step.get("instructions") or []) or "")


def bundled_translation(recipe, target):
    if target not in LANGUAGES or not recipe.get("steps"):
        return None
    position = LANGUAGES.index(target)
    mapping = {normalized(source): row[position] for row in PHRASES for source in row}
    title = mapping.get(normalized(recipe.get("title"))) or mapping.get(normalized(recipe.get("canonicalName")))
    if target == "en":
        title = recipe.get("canonicalName") or title
    steps = [mapping.get(normalized(step_text(step))) for step in recipe["steps"]]
    if not title or not all(steps):
        return None
    return {"title": title, "steps": steps, "method": "assistant_authored_phrases"}


def apply_saved_translation(recipe, translated, target):
    """Change display text only; preserve source IDs, amounts, steps and proof."""
    steps = recipe.get("steps") or []
    texts = translated.get("steps") or []
    if not isinstance(texts, list) or not steps or len(steps) != len(texts) or not isinstance(translated.get("title"), str) or not translated["title"].strip() or not all(isinstance(text, str) and text.strip() for text in texts):
        return None
    for original, text in zip(steps, texts):
        # Quantities, timings and temperatures in instructions must survive.
        numbers = lambda value: sorted(re.findall(r"\d+(?:[.,]\d+)?", value.replace(",", ".")))
        if numbers(step_text(original)) != numbers(text):
            return None
    result = deepcopy(recipe)
    result["originalTitle"] = recipe.get("originalTitle") or recipe.get("title")
    result["title"] = translated["title"]
    result["translatedTo"] = target
    result["translationMethod"] = translated.get("method") or "saved_translation"
    result["steps"] = []
    for step, text in zip(steps, texts):
        source = deepcopy(step) if isinstance(step, dict) else {}
        source["originalInstruction"] = step_text(step)
        source["instruction"] = text
        result["steps"].append(source)
    return result
