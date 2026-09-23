"""Complete, review-only scanner suggestions; never assign stock or nutrients.

Uses catalog identities and multilingual aliases, not arbitrary word overlap.
Preparation variants are offered only within the same food/form. This module
is deliberately independent of the legacy auto-mapper and price matching.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import re
import unicodedata

# Only explicit spelling/plural variants, not prefix/fuzzy stemming.
_WORDS = dict(zip(
    'tomatoes potatoes carrots onions mushrooms eggs chickpeas lentils beans peas apples '
    'almonds hazelnuts walnuts peanuts pistachios dates leaves cloves slices pieces '
    'courgettes zucchinis aubergines eggplants yogurts yoghurts'.split(),
    'tomato potato carrot onion mushroom egg chickpea lentil bean pea apple '
    'almond hazelnut walnut peanut pistachio date leaf clove slice piece '
    'zucchini zucchini eggplant eggplant yogurt yogurt'.split()))
_WORDS.update({'courgette':'zucchini', 'aubergine':'eggplant', 'yoghurt':'yogurt',
    'datteln':'dattel', 'tomaten':'tomate', 'karotten':'karotte',
    'φιστικια':'φιστικι'})
_PREP = re.compile(r'\b(?:peeled|chopped|diced|sliced|minced|crushed|grated|rinsed|washed|trimmed|'
                   r'deseeded|pitted|halved|quartered|finely|roughly|thinly|coarsely)\b')
_MEASURE = re.compile(r'^(?:(?:\d+(?:[.,]\d+)?|[½¼¾])\s+)?(?:tablespoons?|teaspoons?|tbsp|tsp|cups?)\s+(?:of\s+)?')
_SUFFIX = re.compile(r'\b(?:cut into|cut in)\b.*$')
# Aliases here describe states, not interchangeable foods. Keep all qualifiers
# not explicitly enumerated below in the food identity (e.g. oat versus milk).
_FORMS = {
    'dried': 'dried dry getrocknet getrocknete trocken ξερο ξερα αποξηραμενο αποξηραμενα'.split(),
    'cooked': 'cooked boiled steamed gekocht gekochte βρασμενο βρασμενα μαγειρεμενο μαγειρεμενα'.split(),
    'canned': 'canned tinned konserven κονσερβασ κονσερβα'.split(),
    'fresh': 'fresh raw frisch frische roh rohe φρεσκο φρεσκα ωμο ωμα'.split(),
    'frozen': 'frozen tiefgekuhlt tiefgefroren gefroren κατεψυγμενο κατεψυγμενα'.split(),
    'pickled': 'pickled eingelegt eingelegte τουρσι'.split(),
    'smoked': 'smoked gerauchert geraucherte καπνιστο καπνιστα'.split(),
    'roasted': 'roasted toasted gerostet gerostete καβουρδισμενο καβουρδισμενα'.split(),
    'flour': 'flour mehl αλευρι'.split(),
    'powder': 'powder powdered pulver σκονη'.split(),
    'sauce': 'sauce sauces sosse sose σαλτσα'.split(),
    'soup': 'soup soups suppe suppen σουπα'.split(),
    'juice': 'juice juices saft χυμοσ'.split(),
    'paste': 'paste pastes παστα'.split(),
    'puree': 'puree purees pureed πουρεσ'.split(),
    'oil': 'oil oils ol λαδι ελαιο'.split(),
    'butter': 'butter βουτυρο'.split(),
    'drink': 'drink drinks beverage beverages getrank ροφημα'.split(),
    'chocolate': 'chocolate chocolates schokolade σοκολατα'.split(),
    'pudding': 'pudding dessert desserts επιδορπιο'.split(),
    'mix': 'mix mixed mixture blend mischung μειγμα'.split(),
    'sweetened': 'sweetened gesusst ζαχαρουχο'.split(),
    'unsweetened': 'unsweetened ungesusst αγλυκο'.split(),
}
_STATE = {'dried', 'cooked', 'canned', 'fresh', 'frozen', 'pickled', 'smoked', 'roasted'}
_TRANSFORMS = set(_FORMS) - _STATE - {'sweetened', 'unsweetened'}
_BROAD = {'food', 'foods', 'plant based foods', 'plant based foods and beverages',
          'fruit', 'fruits', 'vegetables', 'dairy', 'cereals', 'groceries', 'beverages',
          'legumes', 'legumes and their products', 'cereals and their products'}


def _text(value):
    return ' '.join(str(value or '').split())


@lru_cache(maxsize=8192)
def _norm(value):
    text = unicodedata.normalize('NFKD', value.casefold())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w%]+', ' ', text, flags=re.UNICODE).split())


def _words(value):
    return ' '.join(_WORDS.get(token, token) for token in _norm(value).split())


def _strings(value):
    if isinstance(value, str):
        if value.strip():
            yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from _strings(child)


def _forms(value):
    tokens = set(_norm(value).split())
    found = {kind for kind, words in _FORMS.items() if tokens.intersection(words)}
    if 'en canned' in _norm(value) or 'in der dose' in _norm(value):
        found.add('canned')
    return found


def _base(value):
    text = _MEASURE.sub('', value.casefold())
    text = _SUFFIX.sub('', text)
    text = _PREP.sub('', text)
    tokens = _words(text).split()
    removable = {word for kind in _STATE for word in _FORMS[kind]}
    # "and" can be removed only from preparation tails, not ingredient mixtures.
    tokens = [token for token in tokens if token not in removable]
    while tokens and tokens[-1] in {'and', 'then'}:
        tokens.pop()
    return ' '.join(tokens)


def _phrase(needle, haystack):
    return bool(needle and haystack and f' {needle} ' in f' {haystack} ')


def _compatible(candidate, source):
    c, s = _forms(candidate), _forms(source)
    # A processed product cannot stand for its named component or vice versa.
    if (c & _TRANSFORMS) != (s & _TRANSFORMS):
        return False
    if ('unsweetened' in c and 'sweetened' in s) or ('sweetened' in c and 'unsweetened' in s):
        return False
    cf, sf = c & _STATE, s & _STATE
    if 'canned' in sf:
        return not (cf & {'fresh', 'frozen', 'dried', 'pickled', 'smoked'})
    if 'canned' in cf:
        return False
    if 'dried' in cf and 'dried' not in sf:
        return False
    for exclusive in ('pickled', 'smoked', 'roasted'):
        if (exclusive in cf) != (exclusive in sf):
            return False
    if 'cooked' in sf and cf & {'fresh', 'dried', 'frozen'}:
        return False
    if 'cooked' in cf and 'cooked' not in sf:
        return False
    if ('frozen' in cf and 'frozen' not in sf) or ('fresh' in cf and 'frozen' in sf):
        return False
    if ('dried' in cf and sf & {'fresh', 'frozen', 'cooked'}) or ('dried' in sf and cf & {'fresh', 'frozen'}):
        return False
    return True


def _compound_conflict(canonical, names):
    """Reject named components even when the specific compound is not catalogued."""
    base = _base(canonical)
    text = ' '.join(_norm(name) for name in names)
    tokens = set(text.split())
    plants = {'coconut', 'almond', 'oat', 'soy', 'soya', 'rice', 'cashew',
              'kokos', 'mandel', 'hafer', 'soja', 'καρυδασ', 'αμυγδαλου', 'βρωμησ', 'σογιασ'}
    plant_compounds = ('haferdrink', 'mandeldrink', 'sojadrink', 'kokosmilch', 'hafermilch', 'mandelmilch', 'sojamilch')
    if base in {'milk', 'whole milk', 'skimmed milk', 'semi skimmed milk'}:
        if tokens & plants or any(word in tokens for word in plant_compounds):
            return True
    if base in {'butter', 'salted butter', 'unsalted butter'}:
        if tokens & (plants | {'peanut', 'peanuts', 'hazelnut', 'pistachio', 'nut', 'nuts'}) or any(
            word in text for word in ('erdnussbutter', 'mandelmus', 'φυστικοβουτυρο', 'φιστικοβουτυρο')):
            return True
    if base in {'yogurt', 'plain yogurt', 'natural yogurt', 'greek yogurt'}:
        flavours = {'strawberry', 'raspberry', 'blueberry', 'mango', 'vanilla', 'cherry',
                    'erdbeer', 'erdbeere', 'erdbeeren', 'vanille', 'kokos', 'kirsch',
                    'φραουλα', 'φραουλας', 'φραουλασ', 'βανιλια', 'βανιλιασ', 'καρυδα', 'καρυδασ'}
        if tokens & flavours or any(word in text for word in ('erdbeerjoghurt', 'vanillejoghurt', 'kokosjoghurt')):
            return True
    return False


def _row_identity(row):
    key = _text(row.get('key') or row.get('foodKey') or row.get('ingredientId') or row.get('id'))
    return ('k:' + key) if key else 'n:' + _norm(_text(row.get('name') or row.get('foodName')))


def suggest_catalog_matches(product, catalog, *, limit=None):
    """Return every evidenced compatible candidate by default, for user review.

    No package decomposition, guessed allergy suitability, arbitrary prefix
    matching, category-to-ingredient assignment or persisted side effects.
    """
    if not isinstance(product, dict):
        return []
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
        raise ValueError('Suggestion limit must be a non-negative integer or None')
    names = list(dict.fromkeys(_text(name) for field in (
        'genericName', 'ingredientName', 'productName', 'name', 'productNames', 'genericNames'
    ) for name in _strings(product.get(field)) if _text(name)))
    categories = list(dict.fromkeys(_text(value).split(':', 1)[-1].replace('-', ' ')
        for value in _strings(product.get('categoryTags') or product.get('categories'))))
    categories = [value for value in categories if _norm(value) not in _BROAD]
    category_words = {_words(value) for value in categories}
    if not names and not categories:
        return []
    # Category evidence adds food form; broad parents may not erase it.
    context = ' '.join([*names, *categories])
    context_forms = _forms(context)
    rows = []
    for raw in catalog or []:
        if not isinstance(raw, dict) or raw.get('classification', 'food') not in {'food', ''} or raw.get('needsSemanticConfirmation'):
            continue
        name = _text(raw.get('name') or raw.get('foodName'))
        canonical = _text(raw.get('canonicalName') or name)
        if not name or not canonical or _compound_conflict(canonical, names):
            continue
        aliases = {_text(alias) for field in ('name', 'canonicalName', 'searchAliases', 'aliases', 'translations')
                   for alias in _strings(raw.get(field)) if _text(alias)}
        aliases.add(canonical)
        best = None
        for alias in sorted(aliases):
            token = _words(alias)
            if not token or _norm(alias) in _BROAD:
                continue
            for source in names:
                normalized = _words(source)
                exact = token == normalized
                contained = _phrase(token, normalized)
                if not exact and not contained:
                    continue
                # Validate the canonical food form, not just a historic alias.
                candidate_forms = _forms(canonical) | _forms(alias)
                if not _compatible(' '.join([canonical, alias]), context):
                    continue
                if context_forms & _TRANSFORMS != candidate_forms & _TRANSFORMS:
                    continue
                score = 1.0 if exact else .96
                item = (score, len(token.split()), 'name_exact' if exact else 'name_phrase', alias)
                if best is None or item[:2] > best[:2]:
                    best = item
            if token in category_words and _compatible(' '.join([canonical, alias]), context):
                item = (.92, len(token.split()), 'category_exact', alias)
                if best is None or item[:2] > best[:2]:
                    best = item
        rows.append((raw, canonical, aliases, best))

    # Prefer a specific matched food over words naming its ingredients:
    # "peanut butter" is not peanuts; "coconut milk" is not dairy milk.
    anchors = sorted([(canonical, best) for _, canonical, _, best in rows if best], key=lambda entry: (-entry[1][0], entry[0], entry[1][3]))
    selected = []
    for raw, canonical, aliases, best in rows:
        if best is None:
            for anchor, evidence in anchors:
                if _base(canonical) and _base(canonical) == _base(anchor) and _compatible(canonical, ' '.join([anchor, context])):
                    best = (.90, len(_base(canonical).split()), 'preparation_variant', evidence[3])
                    break
        if best is None:
            continue
        base = _base(canonical)
        # Same-form subsets such as milk inside coconut milk need a second guard.
        if any(base != _base(other) and _phrase(base, _base(other))
               and evidence[1] > best[1] and evidence[0] >= best[0]
               for other, evidence in anchors):
            continue
        key = _text(raw.get('key') or raw.get('foodKey') or raw.get('ingredientId') or raw.get('id'))
        ingredient = {'name': _text(raw.get('name') or raw.get('foodName')), 'canonicalName': canonical}
        if key:
            ingredient['key'] = key
        for field in ('ingredientId', 'sourceIngredientIds', 'searchAliases', 'displayLanguage'):
            if raw.get(field) is not None:
                ingredient[field] = deepcopy(raw[field])
        selected.append({'ingredient': ingredient, 'score': best[0], 'reason': best[2],
            'matchedAlias': best[3], 'requiresConfirmation': True,
            'compatibility': 'review_candidate', 'matcherVersion': 194})
    selected.sort(key=lambda row: (-row['score'], _norm(row['ingredient']['name']), _row_identity(row['ingredient'])))
    unique = {}
    for row in selected:
        unique.setdefault(_row_identity(row['ingredient']), row)
    result = list(unique.values())
    return result if limit is None else result[:limit]


def confident_match(suggestions):
    """Recognition proposes; only a remembered/user-selected mapping assigns."""
    return None
