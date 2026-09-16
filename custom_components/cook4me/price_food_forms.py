"""Reject incompatible prepared foods and ambiguous per-package observations.

Provider categories include parent tags; membership alone does not establish the
recipe food form. These guards are shared by online lookup and offline builds.
"""
import re

_RAW_PRODUCE = set(('onions carrots potatoes white-potatoes tomatoes cherry-tomatoes zucchini aubergines broccoli cauliflowers cucumbers leeks spinachs garlics garlic apples bananas oranges lemons limes peas green-peas green-beans mushrooms radishes artichokes artichoke-hearts beetroots cabbages raspberries strawberries blueberries cranberries peaches plums asparagus').split())
_RAW_PROTEIN = set(('chickens chicken-breasts beef pork lambs salmons salmon-fillets pollocks pollock-fillets trouts prawns shrimps mussels tuna cods cod-fillets').split())
_GRAINS = set(('rices basmati-rices jasmine-rice long-grain-rices brown-rices wheats spelts oats lentils green-lentils red-lentils chickpeas').split())
_NUTS = set(('almonds hazelnuts cashew-nuts walnuts pistachios peanuts').split())
_SPICES = set(('paprika cumin-seeds ground-cumin-seeds ground-turmeric cinnamon black-peppers ground-black-peppers').split())
# Explicitly reviewed provider misclassifications; retain other valid categories.
_BAD = {
 '26061283': {'en:lentils', 'en:green-lentils'},  # grilled peppers, observation 283018
 '4751003926779': {'en:mussels'},  # mackerel, 290880
 '4056489351733': {'en:chickens'},  # turkey, 328658
 '4316268732925': {'en:camemberts'},  # brie, 330302
 '8000430135060': {'en:burrata'},  # mozzarella, 280882
 '42436195': {'en:vanilla-extract'},  # vanilla paste, 279565
 '40081236': {'en:strained-tomatoes'},  # chopped tomatoes, 301731
 '4335619353992': {'en:yogurts'},  # skyr, 300934
 '4061459172249': {'en:soy-sauces'},  # barbecue sauce, 323908
 '4013200780234': {'en:white-breads'},  # corn wraps, 314979
 '4014500522012': {'en:yogurts'},  # coconut dessert, 331337
}


def compatible_food_form(row, category):
    product = row.get('product') if isinstance(row.get('product'), dict) else {}
    tags = set(product.get('categories_tags') or [])
    name = str(row.get('product_name') or product.get('product_name') or '').casefold()
    cat = category.removeprefix('en:')
    if category in _BAD.get(str(row.get('product_code') or ''), set()):
        return False
    if cat in _RAW_PRODUCE:
        if any(tag.startswith(('en:canned-', 'en:dried-', 'en:pickled-', 'en:prepared-', 'en:fruit-chips')) for tag in tags):
            return False
        if tags & {'en:meals', 'en:soups', 'en:stews', 'en:crisps'} or re.search(r'vak\s*\d|mariniert|gewürzgurk|in öl|gekocht|fruchtchips', name):
            return False
        if cat == 'cabbages' and 'kohlrabi' in name:
            return False
    if cat in _RAW_PROTEIN:
        if any(tag.startswith(('en:smoked-', 'en:canned-', 'en:prepared-', 'en:cured-', 'de:marinierte-')) for tag in tags):
            return False
        if tags & {'en:meals', 'en:sausages', 'en:salami'} or re.search(r'schlemmerfilet|gewürzt|gegart|geräuchert|marin[.]|nugget|paniert|graved|dressing|knoblauch-petersilie', name):
            return False
    if cat in _GRAINS and (tags & {'en:breads', 'en:meals', 'en:soups', 'en:crisps'} or 'express' in name):
        return False
    if cat in _NUTS and ('en:mixed-nuts' in tags or len(tags & {'en:almonds', 'en:hazelnuts', 'en:walnuts', 'en:cashew-nuts'}) > 1):
        return False
    if cat in _SPICES and tags & {'en:snacks', 'en:crisps', 'en:meals'}:
        return False
    if cat.endswith('-oils') and tags & {'en:honeys', 'en:spreads', 'en:margarines'}:
        return False
    if cat == 'sugars' and ('gelier' in name or 'vanill' in name or tags & {'fr:sucres-gelifiant', 'en:vanilla-sugars', 'en:icing-sugars'}):
        return False
    if cat == 'milks' and any('condensed' in tag or tag in {'en:milk-powders', 'en:skimmed-milk-powders', 'en:whole-milk-powders'} or 'flavoured' in tag for tag in tags):
        return False
    if cat == 'yogurts' and (any('flavoured' in tag or 'fruit-yogurt' in tag for tag in tags) or re.search(r'mango|kokos|erdbeer|stracciatella|vanille|kirsch', name)):
        return False
    if cat == 'tomato-sauces' and tags & {'en:ketchup', 'en:tomato-ketchup'}:
        return False
    if cat == 'white-breads' and 'wrap' in name:
        return False
    if cat == 'vanilla' and 'paste' in name:
        return False
    if cat.endswith('vinegars') and ('essenz' in name or 'essence' in name):
        return False
    return True


# A dedicated UNIT field may price a bag, punnet or jar. Require a clear weight
# or an individually sold whole-food category, never infer one berry/egg/pack.
_SINGLE = {'en:avocados', 'en:aubergines', 'en:cucumbers', 'en:cauliflowers',
           'en:lettuces', 'en:iceberg-lettuces', 'en:pineapples', 'en:mangoes',
           'en:lemons', 'en:limes', 'en:melons', 'en:watermelons'}
_PACK = re.compile(r'(?<![\d.,])(\d+(?:[.,]\d{1,2})?)\s*(kg|g|ml|cl|l)(?=vke|$|[^a-z])', re.I)


def category_unit_basis(row):
    name = str(row.get('product_name') or '').strip()
    matches = list(_PACK.finditer(name))
    if len(matches) == 1 and not re.search(r'\d\s*[x×]|ab[t]?ropf|drained|\d[.,]\d{3}', name, re.I):
        match = matches[0]
        amount = float(match[1].replace(',', '.'))
        if amount > 0:
            return amount, match[2].lower()
    if matches or re.search(r'pack|beutel|bund|schale|netz|vke|\d\s*[x×]', name, re.I):
        return None, ''
    if row.get('category_tag') in _SINGLE or re.search(r'\b1\s*(stück|st[.]?|piece)\b', name, re.I):
        return 1.0, 'pcs'
    return None, ''


def compatible_category_basis(row, category, unit):
    # PRODUCT 1 pcs frequently describes one whole package, not one ingredient.
    return not (row.get('type') == 'PRODUCT' and unit == 'pcs'
                and category not in {'en:eggs', 'en:sausages', 'en:vanilla'})


def consistent_package_basis(row, quantity, unit):
    """A receipt's explicit pack label must not contradict provider metadata."""
    if row.get('type') != 'PRODUCT' or row.get('price_per') == 'KILOGRAM':
        return True
    name = str(row.get('product_name') or '')
    matches = list(_PACK.finditer(name))
    if len(matches) != 1 or quantity is None:
        return True
    match = matches[0]
    amount = float(match[1].replace(',', '.'))
    multiplier = re.search(r'(\d+)\s*[x×]\s*$', name[:match.start()], re.I)
    if multiplier:
        amount *= int(multiplier[1])
    units = {'g': ('mass', 1), 'kg': ('mass', 1000), 'ml': ('volume', 1), 'cl': ('volume', 10), 'l': ('volume', 1000)}
    left, right = units.get(unit), units.get(match[2].lower())
    if not left or not right:
        return True
    return left[0] == right[0] and abs(float(quantity) * left[1] - amount * right[1]) < .01
