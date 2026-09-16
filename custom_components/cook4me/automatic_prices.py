"""Country-scoped observed prices and automatic recipe costing.

Read-only Open Prices API; no receipt uploads, retailer scraping or AI-made prices.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from functools import partial
import time

from .currency_markets import COUNTRY_CURRENCIES, CURRENCIES
from .costs import _cost_for_amount, _country, _currency, _number, cost_store_for_bridge, lookup_open_prices
from .inventory import inventory_identity, convert_amount
from .recipe_cost_cache import recipe_cost_cache_for_bridge
from .price_units import price_ingredient
from .price_measurements import price_options
from .price_snapshot import snapshot_observations
from .price_identity import pricing_name, is_cost_heading

# Exact English catalog names only. Prepared/mixed foods are never collapsed into
# a raw ingredient by fuzzy matching. Category matches remain estimates.
_RECIPE_WAIT_SECONDS = 2
_CATEGORIES = {}
for tag, kind, names in (
    ('tomatoes', 'CATEGORY', 'tomato|tomatoes'), ('potatoes', 'CATEGORY', 'potato|potatoes'),
    ('onions', 'CATEGORY', 'onion|onions'), ('carrots', 'CATEGORY', 'carrot|carrots'),
    ('zucchini', 'CATEGORY', 'courgette|courgettes|zucchini'), ('aubergines', 'CATEGORY', 'aubergine|aubergines|eggplant'),
    ('broccoli', 'CATEGORY', 'broccoli'), ('cauliflowers', 'CATEGORY', 'cauliflower'),
    ('cucumbers', 'CATEGORY', 'cucumber|cucumbers'), ('leeks', 'CATEGORY', 'leek|leeks'),
    ('spinachs', 'CATEGORY', 'spinach'), ('garlic', 'CATEGORY', 'garlic'),
    ('lemons', 'CATEGORY', 'lemon|lemons'), ('apples', 'CATEGORY', 'apple|apples'),
    ('bananas', 'CATEGORY', 'banana|bananas'), ('oranges', 'CATEGORY', 'orange|oranges'),
    ('rices', 'PRODUCT', 'rice'), ('basmati-rices', 'PRODUCT', 'basmati rice'),
    ('pastas', 'PRODUCT', 'pasta'), ('spaghetti', 'PRODUCT', 'spaghetti'),
    ('olive-oils', 'PRODUCT', 'olive oil'), ('sunflower-oils', 'PRODUCT', 'sunflower oil'),
    ('butters', 'PRODUCT', 'butter'), ('milks', 'PRODUCT', 'milk'),
    ('wheat-flours', 'PRODUCT', 'wheat flour'), ('sugars', 'PRODUCT', 'sugar'),
    ('salts', 'PRODUCT', 'salt'), ('eggs', 'PRODUCT', 'egg|eggs'),
    ('red-lentils', 'PRODUCT', 'red lentils'), ('green-lentils', 'PRODUCT', 'green lentils'),
    ('chickpeas', 'PRODUCT', 'chickpea|chickpeas'), ('plain-tofu', 'PRODUCT', 'tofu'),
    # Explicit food forms verified against the Open Food Facts taxonomy.
    ('wheat-flours', 'PRODUCT', 'all-purpose flour|plain flour'),
    ('extra-virgin-olive-oils', 'PRODUCT', 'extra virgin olive oil|extra-virgin olive oil'),
    ('brown-rices', 'PRODUCT', 'brown rice'), ('jasmine-rice', 'PRODUCT', 'jasmine rice'),
    ('rices-for-risotto', 'PRODUCT', 'risotto rice|arborio rice|carnaroli rice'),
    ('lentils', 'PRODUCT', 'lentils|dried lentils'),
    ('canned-lentils', 'PRODUCT', 'canned lentils|canned cooked lentils'),
    ('canned-chickpeas', 'PRODUCT', 'canned chickpeas'),
    ('canned-tomatoes', 'PRODUCT', 'canned tomatoes|canned chopped tomatoes|chopped canned tomatoes'),
    ('tomato-pastes', 'PRODUCT', 'tomato paste'),
    ('coconut-milks', 'PRODUCT', 'coconut milk'),
    ('yogurts', 'PRODUCT', 'yogurt|yoghurt|plain yogurt|plain yoghurt'),
    ('greek-style-yogurts-plain', 'PRODUCT', 'greek yogurt|greek yoghurt'),
    ('creams', 'PRODUCT', 'cream|cooking cream'),
    ('feta', 'PRODUCT', 'feta|feta cheese'), ('mozzarella', 'PRODUCT', 'mozzarella'),
    ('cheddar-cheese', 'PRODUCT', 'cheddar|cheddar cheese'),
    ('honeys', 'PRODUCT', 'honey'), ('soy-sauces', 'PRODUCT', 'soy sauce'),
    ('ground-black-peppers', 'PRODUCT', 'ground black pepper'),
    ('paprika', 'PRODUCT', 'paprika'), ('cumin', 'PRODUCT', 'cumin'),
    ('mushrooms', 'CATEGORY', 'mushroom|mushrooms|button mushroom|button mushrooms'),
    ('sweet-potatoes', 'CATEGORY', 'sweet potato|sweet potatoes'),
    ('green-peas', 'CATEGORY', 'green peas|fresh peas'),
    ('green-beans', 'CATEGORY', 'green bean|green beans'),
    ('red-bell-peppers', 'CATEGORY', 'red bell pepper|red bell peppers'),
    # v84: frequent release-catalog names, checked against the OFF taxonomy.
    ('ginger', 'CATEGORY', 'ginger'),
    ('parsley', 'CATEGORY', 'parsley'),
    ('shallots', 'CATEGORY', 'shallot'),
    ('basils', 'CATEGORY', 'basil'),
    ('mint', 'CATEGORY', 'mint'),
    ('limes', 'CATEGORY', 'lime'),
    ('thyme', 'CATEGORY', 'thyme'),
    ('asparagus', 'CATEGORY', 'asparagus'),
    ('celery', 'CATEGORY', 'celery'),
    ('pears', 'CATEGORY', 'pear'),
    ('chives', 'CATEGORY', 'chives'),
    ('almonds', 'CATEGORY', 'almond'),
    ('cherry-tomatoes', 'CATEGORY', 'cherry tomato'),
    ('beetroot', 'CATEGORY', 'beetroot'),
    ('fennel', 'CATEGORY', 'fennel'),
    ('turnip', 'CATEGORY', 'turnip'),
    ('dill', 'CATEGORY', 'dill'),
    ('pine-nuts', 'CATEGORY', 'pine nut'),
    ('cabbages', 'CATEGORY', 'cabbage'),
    ('strawberries', 'CATEGORY', 'strawberry'),
    ('pineapples', 'CATEGORY', 'pineapple'),
    ('walnuts', 'CATEGORY', 'walnut'),
    ('pumpkins', 'CATEGORY', 'pumpkin'),
    ('celeriac', 'CATEGORY', 'celeriac'),
    ('green-cabbage', 'CATEGORY', 'green cabbage'),
    ('rosemary', 'CATEGORY', 'rosemary'),
    ('peaches', 'CATEGORY', 'peach'),
    ('oregano', 'CATEGORY', 'oregano'),
    ('sage', 'CATEGORY', 'sage'),
    ('chestnuts', 'CATEGORY', 'chestnut'),
    ('avocados', 'CATEGORY', 'avocado'),
    ('mangoes', 'CATEGORY', 'mango'),
    ('raspberries', 'CATEGORY', 'raspberry'),
    ('butternut-squashes', 'CATEGORY', 'butternut squash'),
    ('shiitake-mushrooms', 'CATEGORY', 'shiitake mushroom'),
    ('green-asparagus', 'CATEGORY', 'green asparagus'),
    ('tarragon', 'CATEGORY', 'tarragon'),
    ('pistachios', 'CATEGORY', 'pistachio'),
    ('cashew-nuts', 'CATEGORY', 'cashew nut'),
    ('brussels-sprouts', 'CATEGORY', 'brussels sprouts'),
    ('lettuces', 'CATEGORY', 'lettuce'),
    ('dates', 'CATEGORY', 'date'),
    ('red-cabbage', 'CATEGORY', 'red cabbage'),
    ('blueberries', 'CATEGORY', 'blueberry'),
    ('parsnip', 'CATEGORY', 'parsnip'),
    ('chards', 'CATEGORY', 'chard'),
    ('hazelnuts', 'CATEGORY', 'hazelnut'),
    ('radishes', 'CATEGORY', 'radish'),
    ('rocket', 'CATEGORY', 'rocket'),
    ('lemon-zest', 'CATEGORY', 'lemon zest'),
    ('white-wines', 'PRODUCT', 'white wine'),
    ('lemon-juice', 'PRODUCT', 'lemon juice'),
    ('beef', 'PRODUCT', 'beef'),
    ('tomato-purees', 'PRODUCT', 'tomato purée'),
    ('cinnamon', 'PRODUCT', 'cinnamon'),
    ('baking-powders', 'PRODUCT', 'baking powder'),
    ('prawns', 'PRODUCT', 'prawns'),
    ('turmeric', 'PRODUCT', 'turmeric'),
    ('sesame-oils', 'PRODUCT', 'sesame oil'),
    ('egg-yolk', 'PRODUCT', 'egg yolk'),
    ('pork', 'PRODUCT', 'pork'),
    ('chicken-thighs', 'PRODUCT', 'chicken thigh'),
    ('mustards', 'PRODUCT', 'mustard'),
    ('salmons', 'PRODUCT', 'salmon'),
    ('mixed-herbs', 'PRODUCT', 'mixed herbs'),
    ('chocolates', 'PRODUCT', 'chocolate'),
    ('breads', 'PRODUCT', 'bread'),
    ('brown-sugars', 'PRODUCT', 'brown sugar'),
    ('chicken-breasts', 'PRODUCT', 'chicken breast'),
    ('red-wines', 'PRODUCT', 'red wine'),
    ('raisins', 'PRODUCT', 'raisin'),
    ('hams', 'PRODUCT', 'ham'),
    ('bacon', 'PRODUCT', 'bacon'),
    ('quinoa', 'PRODUCT', 'quinoa'),
    ('corn-starch', 'PRODUCT', 'corn starch'),
    ('nutmeg', 'PRODUCT', 'nutmeg'),
    ('black-olives', 'PRODUCT', 'black olive'),
    ('vanilla-pods', 'PRODUCT', 'vanilla pod'),
    ('whipped-creams', 'PRODUCT', 'whipped cream'),
    ('saffron', 'PRODUCT', 'saffron'),
    ('tomato-sauces', 'PRODUCT', 'tomato sauce'),
    ('green-olives', 'PRODUCT', 'green olive'),
    ('cider-vinegars', 'PRODUCT', 'cider vinegar'),
    ('vanilla', 'PRODUCT', 'vanilla'),
    ('curry-pastes', 'PRODUCT', 'curry paste'),
    ('sour-creams', 'PRODUCT', 'sour cream'),
    ('orange-juices', 'PRODUCT', 'orange juice'),
    ('mascarpone', 'PRODUCT', 'mascarpone'),
    ('ricotta', 'PRODUCT', 'ricotta'),
    ('mayonnaises', 'PRODUCT', 'mayonnaise'),
    ('vinegars', 'PRODUCT', 'vinegar'),
    ('cods', 'PRODUCT', 'cod'),
    ('rice-vinegars', 'PRODUCT', 'rice vinegar'),
    ('tomato-ketchup', 'PRODUCT', 'tomato ketchup'),
    ('caramels', 'PRODUCT', 'caramel'),
    ('egg-white', 'PRODUCT', 'egg white'),
    ('sausages', 'PRODUCT', 'sausage'),
    ('tunas', 'PRODUCT', 'tuna'),
    ('ground-almonds', 'PRODUCT', 'ground almonds'),
    ('olives', 'PRODUCT', 'olive'),
    ('mussels', 'PRODUCT', 'mussels'),
    ('capers', 'PRODUCT', 'caper'),
    ('chorizo', 'PRODUCT', 'chorizo'),
    ('mirin', 'PRODUCT', 'mirin'),
    ('biscuits', 'PRODUCT', 'biscuit'),
    ('whole-milks', 'PRODUCT', 'whole milk'),
    ('dried-tomatoes', 'PRODUCT', 'dried tomato'),
    ('yeast', 'PRODUCT', 'yeast'),
    ('condensed-milks', 'PRODUCT', 'condensed milk'),
    ('pestos', 'PRODUCT', 'pesto'),
    ('beers', 'PRODUCT', 'beer'),
    ('buckwheat', 'PRODUCT', 'buckwheat'),
    ('herbes-de-provence', 'PRODUCT', 'herbes de provence'),
    ('coconut-oils', 'PRODUCT', 'coconut oil'),
    ('pumpkin-seeds', 'PRODUCT', 'pumpkin seeds'),
    ('gnocchi', 'PRODUCT', 'gnocchi'),
    ('cloves', 'PRODUCT', 'clove'),
    ('lamb-shoulder', 'PRODUCT', 'lamb shoulder'),
    ('margarines', 'PRODUCT', 'margarine'),
    ('balsamic-vinegars', 'PRODUCT', 'balsamic vinegar'),
    ('fresh-goat-cheese', 'PRODUCT', 'fresh goat cheese'),
    ('chickens', 'PRODUCT', 'chicken'),
    ('rolled-oats', 'PRODUCT', 'rolled oats'),
    ('peanut-butters', 'PRODUCT', 'peanut butter'),
    ('chicken-drumsticks', 'PRODUCT', 'chicken drumstick'),
    ('oyster-sauces', 'PRODUCT', 'oyster sauce'),
    ('misos', 'PRODUCT', 'miso'),
    ('tahini', 'PRODUCT', 'tahini'),
    ('smoked-bacon', 'PRODUCT', 'smoked bacon'),
    ('maple-syrups', 'PRODUCT', 'maple syrup'),
    ('croutons', 'PRODUCT', 'crouton'),
    ('butters', 'PRODUCT', 'salted butter & unsalted butter|salted butter|unsalted butter'),
    ('wheat-flours', 'PRODUCT', 'flour'),
    ('potatoes', 'CATEGORY', 'white potatoes'),
    ('cremes-fraiches', 'PRODUCT', 'crème fraîche|creme fraiche|thick crème fraîche'),
    ('creams', 'PRODUCT', 'liquid cream'),
    ('scallions', 'CATEGORY', 'spring onion|spring onions|welsh onion'),
    ('powdered-sugars', 'PRODUCT', 'icing sugar|powdered sugar'),
    ('bread-crumbs', 'PRODUCT', 'breadcrumbs|bread crumbs'),
    ('lamb-meat', 'PRODUCT', 'lamb'),
    ('ground-beef-meats', 'PRODUCT', 'minced beef|ground beef'),
    ('sesame', 'PRODUCT', 'sesame seed|sesame seeds'),
    ('nuoc-mam-sauce', 'PRODUCT', 'fish sauce'),
    ('peanut-oils', 'PRODUCT', 'groundnut oil|peanut oil'),
    ('scallop', 'PRODUCT', 'scallops'),
    ('corn-starch', 'PRODUCT', 'cornflour'),
    ('bulgur', 'PRODUCT', 'bulgur wheat|bulgur'),
    ('vegetable-bouillon-cubes', 'PRODUCT', 'vegetable stock cube'),
    ('curry-powders', 'PRODUCT', 'curry powder'),
    ('red-bell-peppers', 'CATEGORY', 'red pepper'),
):
    for name in names.split('|'):
        _CATEGORIES[name] = ('en:' + tag, kind)


# v85: reviewed exact taxonomy names; no fuzzy or parent-category fallback.
for category, kind, names in (
    ('en:peas', 'CATEGORY', 'peas'),
    ('xx:sake', 'PRODUCT', 'sake'),
    ('en:vegetable-oils', 'PRODUCT', 'vegetable oil'),
    ('en:corn', 'PRODUCT', 'corn'),
    ('en:allspices', 'PRODUCT', 'allspice'),
    ('en:potato-starches', 'PRODUCT', 'potato starch'),
    ('en:black-peppers', 'PRODUCT', 'black pepper'),
    ('en:pork-belly', 'PRODUCT', 'pork belly'),
    ('en:ketchup', 'PRODUCT', 'ketchup'),
    ('en:green-lentils', 'PRODUCT', 'green lentil'),
    ('en:coconut-creams', 'PRODUCT', 'coconut cream'),
    ('en:garam-masalas', 'PRODUCT', 'garam masala'),
    ('en:marjoram', 'CATEGORY', 'marjoram'),
    ('en:apricots', 'CATEGORY', 'apricot'),
    ('en:cream-cheeses', 'PRODUCT', 'cream cheese'),
    ('en:bouquet-garni', 'PRODUCT', 'bouquet garni'),
    ('en:peanuts', 'PRODUCT', 'peanuts'),
    ('en:artichokes', 'CATEGORY', 'artichoke'),
    ('en:sausage-meat', 'PRODUCT', 'sausage meat'),
    ('en:anchovy', 'PRODUCT', 'anchovy'),
    ('en:rums', 'PRODUCT', 'rum'),
    ('en:star-anise', 'PRODUCT', 'star anise'),
    ('en:long-grain-rices', 'PRODUCT', 'long grain rice'),
    ('en:vanilla-sugars', 'PRODUCT', 'vanilla sugar'),
    ('en:rice-pasta', 'PRODUCT', 'rice pasta'),
    ('en:millet', 'PRODUCT', 'millet'),
    ('en:chinese-cabbage', 'CATEGORY', 'chinese cabbage'),
    ('en:pancetta', 'PRODUCT', 'pancetta'),
    ('en:smoked-salmons', 'PRODUCT', 'smoked salmon'),
    ('en:cognac', 'PRODUCT', 'cognac'),
    ('en:pork-tenderloin', 'PRODUCT', 'pork tenderloin'),
    ('en:cherries', 'CATEGORY', 'cherries'),
    ('en:squid', 'PRODUCT', 'squid'),
    ('en:plums', 'CATEGORY', 'plum'),
    ('en:barley', 'PRODUCT', 'barley'),
    ('en:passion-fruits', 'CATEGORY', 'passion fruit'),
    ('en:wheats', 'PRODUCT', 'wheat'),
    ('en:granulated-sugars', 'PRODUCT', 'granulated sugar'),
    ('en:gorgonzolas', 'PRODUCT', 'gorgonzola'),
    ('en:smoked-bacon-lardons', 'PRODUCT', 'smoked bacon lardon'),
    ('en:ras-el-hanout', 'PRODUCT', 'ras el hanout'),
    ('en:pomegranates', 'CATEGORY', 'pomegranate'),
    ('en:dark-chocolates', 'PRODUCT', 'dark chocolate'),
    ('en:duck-legs', 'PRODUCT', 'duck leg'),
    ('en:coconuts', 'CATEGORY', 'coconut'),
    ('en:daikon-radishes', 'CATEGORY', 'daikon radish'),
    ('en:broad-beans', 'CATEGORY', 'broad bean'),
    ('en:artichoke-hearts', 'PRODUCT', 'artichoke heart'),
    ('en:white-chocolates', 'PRODUCT', 'white chocolate'),
    ('en:trouts', 'PRODUCT', 'trout'),
    ('en:agave-syrups', 'PRODUCT', 'agave syrup'),
    ('en:pork-shoulders', 'PRODUCT', 'pork shoulder'),
    ('en:cardamom', 'PRODUCT', 'cardamom'),
    ('en:grana-padano', 'PRODUCT', 'grana padano'),
    ('en:jams', 'PRODUCT', 'jam'),
    ('en:chicken-wings', 'PRODUCT', 'chicken wing'),
    ('en:raisins', 'PRODUCT', 'raisins'),
    ('en:rabbit-leg', 'PRODUCT', 'rabbit leg'),
    ('en:porcini-mushrooms', 'CATEGORY', 'porcini mushroom'),
    ('en:seitan', 'PRODUCT', 'seitan'),
    ('en:ghee', 'PRODUCT', 'ghee'),
    ('en:squash', 'CATEGORY', 'squash'),
    ('en:bread-crumbs', 'PRODUCT', 'bread crumb'),
    ('en:rapeseed-oils', 'PRODUCT', 'rapeseed oil'),
    ('en:vanilla-extract', 'PRODUCT', 'vanilla extract'),
    ('en:grapes', 'CATEGORY', 'grape'),
    ('en:bamboo-shoots', 'PRODUCT', 'bamboo shoot'),
    ('en:sauerkrauts', 'PRODUCT', 'sauerkraut'),
    ('en:mandarins', 'CATEGORY', 'mandarin'),
    ('en:goat-milks', 'PRODUCT', 'goat milk'),
    ('en:smoked-sausages', 'PRODUCT', 'smoked sausage'),
    ('en:shrimps', 'PRODUCT', 'shrimp'),
    ('en:clam', 'PRODUCT', 'clam'),
    ('en:juniper-berries', 'PRODUCT', 'juniper berries'),
    ('en:tomato-juices', 'PRODUCT', 'tomato juice'),
    ('en:gingerbreads', 'PRODUCT', 'gingerbread'),
    ('en:cherry-tomatoes', 'CATEGORY', 'cherry tomatoes'),
    ('en:watercress', 'CATEGORY', 'watercress'),
    ('en:veal-fillets', 'PRODUCT', 'veal fillet'),
    ('en:dried-fruits', 'PRODUCT', 'dried fruit'),
    ('en:turkeys', 'PRODUCT', 'turkey'),
    ('en:lime-juices', 'PRODUCT', 'lime juice'),
    ('en:pecan-nuts', 'PRODUCT', 'pecan nut'),
    ('en:pork-loin', 'PRODUCT', 'pork loin'),
    ('en:rice-flours', 'PRODUCT', 'rice flour'),
    ('en:cured-hams', 'PRODUCT', 'cured ham'),
    ('en:gelatin', 'PRODUCT', 'gelatin'),
    ('en:melons', 'CATEGORY', 'melon'),
    ('en:chili-powders', 'PRODUCT', 'chili powder'),
    ('en:pork-filet-mignon', 'PRODUCT', 'pork filet mignon'),
    ('en:white-cabbage', 'CATEGORY', 'white cabbage'),
    ('en:apple-juices', 'PRODUCT', 'apple juice'),
    ('en:shortbread', 'PRODUCT', 'shortbread'),
    ('en:brioches', 'PRODUCT', 'brioche'),
    ('en:jerusalem-artichoke', 'CATEGORY', 'jerusalem artichoke'),
    ('en:rhubarb', 'CATEGORY', 'rhubarb'),
    ('en:worcestershire-sauces', 'PRODUCT', 'worcestershire sauce'),
    ('en:kimchi', 'PRODUCT', 'kimchi'),
    ('en:red-onions', 'CATEGORY', 'red onion'),
    ('en:sunflower-seeds', 'PRODUCT', 'sunflower seed'),
    ('en:wine-vinegars', 'PRODUCT', 'wine vinegar'),
    ('en:roast-veal', 'PRODUCT', 'roast veal'),
    ('en:pork-ribs', 'PRODUCT', 'pork ribs'),
    ('en:semi-skimmed-milks', 'PRODUCT', 'semi-skimmed milk'),
    ('en:ground-white-peppers', 'PRODUCT', 'ground white pepper'),
    ('en:dried-apricots', 'PRODUCT', 'dried apricot'),
    ('fr:gruyere', 'PRODUCT', 'gruyère'),
    ('en:figs', 'CATEGORY', 'fig'),
    ('en:lards', 'PRODUCT', 'lard'),
    ('en:pickled-gherkins', 'PRODUCT', 'pickled gherkin'),
    ('en:hazelnut-oils', 'PRODUCT', 'hazelnut oil'),
    ('en:pink-peppercorns', 'PRODUCT', 'pink peppercorn'),
    ('en:tomato-pulps', 'PRODUCT', 'tomato pulp'),
    ('en:rice-wines', 'PRODUCT', 'rice wine'),
    ('en:baker-s-yeast', 'PRODUCT', "baker's yeast"),
    ('en:morteau-sausages', 'PRODUCT', 'morteau sausage'),
    ('en:clementines', 'CATEGORY', 'clementine'),
    ('en:whisky', 'PRODUCT', 'whisky'),
    ('en:cranberries', 'CATEGORY', 'cranberries'),
    ('en:blackberries', 'CATEGORY', 'blackberries'),
    ('en:ducks', 'PRODUCT', 'duck'),
    ('en:beef-cheek', 'PRODUCT', 'beef cheek'),
    ('en:vegetarian-sausages', 'PRODUCT', 'vegetarian sausage'),
    ('en:cinnamon-sticks', 'PRODUCT', 'cinnamon stick'),
    ('en:linguine', 'PRODUCT', 'linguine'),
    ('en:mimolette-cheese', 'PRODUCT', 'mimolette cheese'),
    ('en:chicken-wings', 'PRODUCT', 'chicken wings'),
    ('en:white-asparagus', 'CATEGORY', 'white asparagus'),
    ('en:grated-coconut', 'PRODUCT', 'grated coconut'),
    ('en:beef-steaks', 'PRODUCT', 'beef steak'),
    ('en:haddock', 'PRODUCT', 'haddock'),
    ('en:calvados', 'PRODUCT', 'calvados'),
    ('en:camemberts', 'PRODUCT', 'camembert'),
    ('en:edamame', 'PRODUCT', 'edamame'),
    ('en:apple-compotes', 'PRODUCT', 'apple compote'),
    ('en:watermelons', 'CATEGORY', 'watermelon'),
    ('en:cuttlefish', 'PRODUCT', 'cuttlefish'),
    ('en:chopped-garlics', 'PRODUCT', 'chopped garlic'),
    ('en:beef-knuckle', 'PRODUCT', 'beef knuckle'),
    ('en:kohlrabi', 'CATEGORY', 'kohlrabi'),
    ('en:mackerel', 'PRODUCT', 'mackerel'),
    ('en:orange-blossom', 'PRODUCT', 'orange blossom'),
    ('en:grapefruits', 'CATEGORY', 'grapefruit'),
    ('en:cloves', 'PRODUCT', 'cloves'),
    ('en:anise', 'PRODUCT', 'anise'),
    ('en:rice-vermicelli', 'PRODUCT', 'rice vermicelli'),
    ('en:orange-blossom-waters', 'PRODUCT', 'orange blossom water'),
    ('en:pomegranate-seeds', 'PRODUCT', 'pomegranate seeds'),
    ('en:veal-shoulder', 'PRODUCT', 'veal shoulder'),
    ('en:turkey-fillets', 'PRODUCT', 'turkey fillet'),
    ('en:chocolate-sauce', 'PRODUCT', 'chocolate sauce'),
    ('en:grape-juices', 'PRODUCT', 'grape juice'),
    ('en:quinces', 'CATEGORY', 'quince'),
    ('en:papayas', 'CATEGORY', 'papaya'),
    ('en:chocolate-spreads', 'PRODUCT', 'chocolate spread'),
    ('en:sea-salts', 'PRODUCT', 'sea salt'),
    ('en:erythritol', 'PRODUCT', 'erythritol'),
    ('en:processed-cheeses', 'PRODUCT', 'processed cheese'),
    ('en:grated-carrots', 'PRODUCT', 'grated carrot'),
    ('en:liquid-caramel', 'PRODUCT', 'liquid caramel'),
    ('en:chili-peppers', 'PRODUCT', 'chili pepper'),
    ('en:chicken-drumsticks', 'PRODUCT', 'chicken drumsticks'),
    ('en:surimi', 'PRODUCT', 'surimi'),
    ('en:yakitori-sauces', 'PRODUCT', 'yakitori sauce'),
    ('en:bresaola', 'PRODUCT', 'bresaola'),
    ('en:pollocks', 'PRODUCT', 'pollock'),
    ('en:strained-tomatoes', 'PRODUCT', 'strained tomatoes'),
    ('en:cockles', 'PRODUCT', 'cockle'),
    ('en:lemon-curds', 'PRODUCT', 'lemon curd'),
    ('en:raviolis', 'PRODUCT', 'ravioli'),
    ('en:poultry-liver', 'PRODUCT', 'poultry liver'),
    ('en:white-vinegars', 'PRODUCT', 'white vinegar'),
    ('en:oyster-mushrooms', 'CATEGORY', 'oyster mushrooms'),
    ('en:crab', 'PRODUCT', 'crab'),
    ('en:dry-sausages', 'PRODUCT', 'dry sausage'),
    ('en:black-peppercorns', 'PRODUCT', 'black peppercorns'),
    ('en:italian-hams', 'PRODUCT', 'italian ham'),
    ('en:cocoa-powders', 'PRODUCT', 'cocoa powder'),
    ('en:caster-sugars', 'PRODUCT', 'caster sugar'),
    ('en:lychees-in-syrup', 'PRODUCT', 'lychees in syrup'),
    ('en:nori-seaweeds', 'PRODUCT', 'nori seaweed'),
    ('en:montbeliard-sausages', 'PRODUCT', 'montbéliard sausage'),
    ('en:clarified-butter', 'PRODUCT', 'clarified butter'),
    ('en:coriander-seeds', 'PRODUCT', 'coriander seeds'),
    ('en:glutinous-rices', 'PRODUCT', 'glutinous rice'),
    ('en:swordfish', 'PRODUCT', 'swordfish'),
    ('en:frozen-mixed-vegetables', 'PRODUCT', 'frozen mixed vegetables'),
    ('en:teriyaki-sauces', 'PRODUCT', 'teriyaki sauce'),
    ('en:candied-fruits', 'PRODUCT', 'candied fruit'),
    ('en:pine-nuts', 'PRODUCT', 'pine nuts'),
    ('en:cayenne-peppers', 'PRODUCT', 'cayenne pepper'),
    ('en:dried-shiitake-mushrooms', 'PRODUCT', 'dried shiitake mushrooms'),
    ('en:lobsters', 'PRODUCT', 'lobster'),
    ('en:shortcrust-pastry', 'PRODUCT', 'shortcrust pastry'),
    ('en:buckwheat-flours', 'PRODUCT', 'buckwheat flour'),
    ('en:cottage-cheeses', 'PRODUCT', 'cottage cheese'),
    ('en:spelts', 'PRODUCT', 'spelt'),
    ('en:lobster-bisque', 'PRODUCT', 'lobster bisque'),
    ('en:dried-mushrooms', 'PRODUCT', 'dried mushrooms'),
    ('en:black-pudding', 'PRODUCT', 'black pudding'),
    ('en:celery-stalk', 'CATEGORY', 'celery stalk'),
    ('en:hake', 'PRODUCT', 'hake'),
    ('en:mackerel-fillets', 'PRODUCT', 'mackerel fillet'),
    ('en:chili-flakes', 'PRODUCT', 'chili flakes'),
    ('en:lychees', 'CATEGORY', 'lychee'),
    ('en:ciders', 'PRODUCT', 'cider'),
    ('en:chicken-thighs', 'PRODUCT', 'chicken thighs'),
    ('en:barbecue-sauces', 'PRODUCT', 'barbecue sauce'),
    ('en:salmon-fillets', 'PRODUCT', 'salmon fillet'),
    ('en:pumpkin-seed-oils', 'PRODUCT', 'pumpkin seed oil'),
    ('en:veal-escalopes', 'PRODUCT', 'veal escalope'),
    ('en:pitted-dates', 'PRODUCT', 'pitted dates'),
    ('en:rose-waters', 'PRODUCT', 'rose water'),
    ('en:white-rices', 'PRODUCT', 'white rice'),
    ('en:pancake-mixes', 'PRODUCT', 'pancake mix'),
    ('en:black-vinegars', 'PRODUCT', 'black vinegar'),
    ('en:peppercorns', 'PRODUCT', 'peppercorns'),
    ('en:peeled-tomatoes', 'PRODUCT', 'peeled tomatoes'),
    ('en:black-beans', 'PRODUCT', 'black beans'),
    ('en:dijon-mustards', 'PRODUCT', 'dijon mustard'),
    ('en:chocolate-sprinkles', 'PRODUCT', 'chocolate sprinkles'),
    ('en:almonds', 'PRODUCT', 'almonds'),
    ('en:chestnut-flours', 'PRODUCT', 'chestnut flour'),
    ('en:dried-thyme', 'PRODUCT', 'dried thyme'),
    ('en:blueberries', 'PRODUCT', 'blueberries'),
    ('en:figs', 'PRODUCT', 'figs'),
    ('en:lasagna-sheets', 'PRODUCT', 'lasagna sheets'),
    ('en:pomelos', 'CATEGORY', 'pomelo'),
    ('en:beef-ribs', 'PRODUCT', 'beef ribs'),
    ('en:chicken-liver', 'PRODUCT', 'chicken liver'),
    ('en:cumin-powders', 'PRODUCT', 'cumin powder'),
    ('en:romaine-lettuce', 'CATEGORY', 'romaine lettuce'),
    ('en:baldo-rices', 'PRODUCT', 'baldo rice'),
    ('en:white-breads', 'PRODUCT', 'white bread'),
    ('en:white-wine-vinegars', 'PRODUCT', 'white wine vinegar'),
    ('en:spring-rolls', 'PRODUCT', 'spring roll'),
    ('en:crispbreads', 'PRODUCT', 'crispbread'),
    ('en:tapioca', 'PRODUCT', 'tapioca'),
    ('en:dried-mint', 'PRODUCT', 'dried mint'),
    ('en:blackcurrants', 'PRODUCT', 'blackcurrant'),
    ('en:quail', 'PRODUCT', 'quail'),
    ('en:white-onions', 'CATEGORY', 'white onion'),
    ('en:madeira-wine', 'PRODUCT', 'madeira wine'),
    ('en:hemp-seeds', 'PRODUCT', 'hemp seeds'),
    ('en:hijiki-seaweeds', 'PRODUCT', 'hijiki seaweed'),
    ('en:abalone', 'PRODUCT', 'abalone'),
    ('en:mortadella', 'PRODUCT', 'mortadella'),
    ('en:pickled-cucumbers', 'PRODUCT', 'pickled cucumbers'),
    ('en:ratatouille', 'PRODUCT', 'ratatouille'),
    ('en:mint', 'CATEGORY', 'fresh mint'),
    ('en:green-olives', 'PRODUCT', 'green olives'),
    ('en:cornmeal', 'PRODUCT', 'cornmeal'),
    ('en:sriracha-sauces', 'PRODUCT', 'sriracha sauce'),
    ('en:frozen-green-peas', 'PRODUCT', 'frozen green peas'),
    ('en:croutons', 'PRODUCT', 'croutons'),
    ('en:red-wine-vinegars', 'PRODUCT', 'red wine vinegar'),
    ('en:burrata', 'PRODUCT', 'burrata'),
    ('en:walnuts', 'PRODUCT', 'walnuts'),
    ('en:colas', 'PRODUCT', 'cola'),
    ('en:mustard-seeds', 'PRODUCT', 'mustard seeds'),
    ('en:black-rices', 'PRODUCT', 'black rice'),
    ('en:red-pestos', 'PRODUCT', 'red pesto'),
    ('en:shallots', 'CATEGORY', 'shallots'),
    ('en:almond-butters', 'PRODUCT', 'almond butter'),
    ('en:red-quinoa', 'PRODUCT', 'red quinoa'),
    ('en:spelt-flours', 'PRODUCT', 'spelt flour'),
    ('en:millet-flours', 'PRODUCT', 'millet flour'),
    ('en:dried-figs', 'PRODUCT', 'dried figs'),
    ('en:kombu-seaweeds', 'PRODUCT', 'kombu seaweed'),
    ('en:milk-powders', 'PRODUCT', 'milk powder'),
    ('en:tripe', 'PRODUCT', 'tripe'),
    ('en:noodles', 'PRODUCT', 'noodles'),
    ('en:toulouse-sausages', 'PRODUCT', 'toulouse sausage'),
    ('en:hearts-of-palm', 'PRODUCT', 'hearts of palm'),
    ('en:truffles', 'PRODUCT', 'truffle'),
    ('en:meringues', 'PRODUCT', 'meringues'),
    ('en:kirsch', 'PRODUCT', 'kirsch'),
    ('en:vinaigrettes', 'PRODUCT', 'vinaigrette'),
    ('en:madeleines', 'PRODUCT', 'madeleine'),
    ('en:soybean-flours', 'PRODUCT', 'soybean flour'),
    ('en:corn-starch', 'PRODUCT', 'cornstarch'),
    ('en:ground-cumin-seeds', 'PRODUCT', 'ground cumin'),
    ('en:chicken-breasts', 'PRODUCT', 'chicken fillet'),
    ('en:penne', 'PRODUCT', 'dried penne pasta'),
    ('en:fusilli', 'PRODUCT', 'dried fusilli pasta'),
    ('en:corn-semolinas-for-polenta', 'PRODUCT', 'polenta'),
    ('en:dried-prunes', 'PRODUCT', 'prune'),
    ('en:snow-peas', 'CATEGORY', 'mangetout'),
    ('en:scallions', 'CATEGORY', 'green onion'),
    ('en:paprika', 'PRODUCT', 'ground paprika'),
    ('en:goat-cheeses', 'PRODUCT', 'goat’s cheese'),
    ('en:dried-yeasts', 'PRODUCT', "dry yeast|dried yeast|dried baker's yeast|active dry yeast"),
):
    for name in names.split('|'):
        _CATEGORIES[name] = (category, kind)


# Reviewed gaps. Private tags are named reference products/tariffs and must never
# become broad Open Prices queries (especially powdered vs prepared stock).
for tag, kind, names in (
    ('cook4me:tap-water', 'REFERENCE', 'water|tap water'),
    ('cook4me:vegetable-stock', 'REFERENCE', 'vegetable stock|vegetable stock cube'),
    ('cook4me:cheese', 'REFERENCE', 'cheese'),
    ('cook4me:poppy-seeds', 'REFERENCE', 'poppy seeds|poppy seed|ground poppy seeds'),
    ('en:vegetable-oils', 'PRODUCT', 'oil'),
    ('en:parmigiano-reggiano', 'PRODUCT', 'parmesan|parmesan cheese|grated parmesan'),
    ('en:durum-wheat-macaroni', 'PRODUCT', 'macaroni'),
    ('en:fresh-coriander-leaves', 'CATEGORY', 'coriander|fresh coriander|coriander leaves'),
    ('en:mint', 'CATEGORY', 'mint|fresh mint'),
    ('en:curry-powders', 'PRODUCT', 'curry'),
):
    for name in names.split('|'):
        _CATEGORIES[name] = (tag, kind)


def country_currency(country):
    return next(iter(COUNTRY_CURRENCIES.get(country, [])), '')


def validate_market(country, currency):
    if country not in COUNTRY_CURRENCIES or currency not in CURRENCIES:
        raise ValueError('Choose a valid country and currency')


async def price_settings(bridge):
    store = await cost_store_for_bridge(bridge)
    settings = store.settings
    country = settings.get('country') or _country(getattr(bridge.hass.config, 'country', ''))
    currency = settings.get('currency') or country_currency(country)
    if country != settings.get('country') or currency != settings.get('currency'):
        await store.async_set_settings(country=country, currency=currency)
    return store.settings


def category_for(ingredient):
    if not isinstance(ingredient, dict):
        return None
    # Callers supply the server catalog row, never a model's category guess.
    name = pricing_name(ingredient)
    return _CATEGORIES.get(name)


def canonical_recipe(recipe, catalog):
    lookup = {}
    for row in catalog:
        for key in (row.get('key'), row.get('foodKey'), row.get('id'), row.get('ingredientId')):
            if key:
                lookup[str(key)] = row
    result = deepcopy(recipe)
    rows = []
    for raw in recipe.get('ingredients') or []:
        if not isinstance(raw, dict):
            rows.append({'name': str(raw)})
            continue
        key = str(raw.get('key') or raw.get('foodKey') or raw.get('ingredientId') or raw.get('id') or '')
        match = lookup.get(key, {})
        if is_cost_heading({**raw, 'key': key}):
            continue
        rows.append(price_ingredient({**raw, **({'key': match.get('key') or match.get('ingredientId') or match.get('id') or key} if key else {}),
                     'name': raw.get('name') or raw.get('foodName') or match.get('name') or key,
                     'canonicalName': match.get('canonicalName') or match.get('name') or raw.get('canonicalName') or raw.get('name') or raw.get('foodName')}))
    result['ingredients'] = rows
    return result


def _fresh(reference):
    if not reference:
        return False
    if not str(reference.get('source', '')).startswith('open_prices') and reference.get('source') not in {'retail_snapshot', 'utility_snapshot'}:
        return True
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(reference['updatedAt'])).total_seconds() < 86400
    except (KeyError, TypeError, ValueError):
        return False


async def _observations(bridge, *, barcode='', category='', category_type='CATEGORY', unit='', settings, refresh_since=None, prefer_snapshot=False):
    """Coalesce repeated requests; bound concurrency and cache misses for an hour."""
    if (prefer_snapshot and refresh_since is None) or category.startswith('cook4me:'):
        rows = snapshot_observations(barcode=barcode, category=category,
            country=settings['country'], currency=settings['currency'], unit=unit)
        if rows:
            return {'ok': True, 'items': rows, 'usableCount': len(rows), 'source': 'offline_snapshot'}
        if category.startswith('cook4me:'):
            return {'ok': True, 'items': [], 'usableCount': 0, 'source': 'offline_snapshot'}
    if not hasattr(bridge, '_price_queries'):
        bridge._price_queries = {}
        bridge._price_query_lock = asyncio.Lock()
        bridge._price_slots = asyncio.Semaphore(3)
    basis = next((candidate for candidate in ('g', 'ml', 'pcs') if unit and convert_amount(1, unit, candidate) is not None), unit)
    key = (barcode, category, category_type, settings['country'], settings['currency'], basis)
    async with bridge._price_query_lock:
        cached = bridge._price_queries.get(key)
        if cached and (not cached[1].done() or (cached[0] > time.monotonic() and
                (refresh_since is None or len(cached) > 2 and cached[2] >= refresh_since))):
            task = cached[1]
        else:
            async def fetch():
                async with bridge._price_slots:
                    result = await bridge.hass.async_add_executor_job(partial(lookup_open_prices, barcode,
                        category=category, category_type=category_type,
                        country=settings['country'], currency=settings['currency'], unit=unit,
                        prefer_snapshot=prefer_snapshot and refresh_since is None))
                    if not result.get('ok'):
                        cached_query = bridge._price_queries.get(key)
                        if cached_query and cached_query[1] is asyncio.current_task():
                            bridge._price_queries[key] = (time.monotonic() + 60, cached_query[1], cached_query[2])
                    return result
            task = bridge.hass.async_create_background_task(fetch(), 'Cook4Me price observation')
            bridge._price_queries[key] = (time.monotonic() + 3600, task, time.monotonic())
            while len(bridge._price_queries) > 500:
                bridge._price_queries.pop(next(iter(bridge._price_queries)))
    return deepcopy(await asyncio.shield(task))


async def _store_observation(store, identity, row, *, generic=False):
    source = row['source'] if row.get('source') in {'retail_snapshot', 'utility_snapshot'} else 'open_prices_category' if generic else 'open_prices'
    existing = next((ref for ref in store._data.get('references', {}).values()
                     if ref.get('identity') == identity and ref.get('source') == source
                     and ref.get('country') == row['country'] and ref.get('currency') == row['currency']
                     and ref.get('basisUnit') == row['basisUnit']), None)
    if _fresh(existing) and all(existing.get(key) == row.get(key) for key in
            ('amount', 'currency', 'basisQuantity', 'basisUnit', 'country', 'location', 'date', 'barcode')) \
            and existing.get('observationId') == (row.get('id') or row.get('observationId')):
        return deepcopy(existing)
    return await store.async_set_reference(identity, amount=row['amount'], currency=row['currency'],
        basis_quantity=row['basisQuantity'], basis_unit=row['basisUnit'],
        source=source, confidence='external_observation',
        country=row['country'], location=row.get('location', ''), date=row.get('date', ''),
        barcode=row.get('barcode', ''), observation_id=row.get('id') or row.get('observationId'),
        source_url=row.get('sourceUrl', ''), product_name=row.get('productName', ''), note=row.get('note', ''))


async def product_price(bridge, *, barcode='', ingredient=None, quantity=None, unit='', settings=None, refresh_since=None):
    settings = settings or await price_settings(bridge)
    store = await cost_store_for_bridge(bridge)
    country, currency = settings['country'], settings['currency']
    identity = inventory_identity(ingredient) if ingredient else ''
    reference = store.barcode_reference(barcode, country=country, currency=currency, unit=unit) if barcode else None
    kind = 'barcode'
    fallback = store.best_reference(identity, country=country, currency=currency, unit=unit) if identity else None
    if reference is None and barcode and fallback and fallback.get('barcode') == barcode:
        reference = fallback
    reason = 'no_observation'
    lookup_failed = False
    compatible_unit = not unit or any(convert_amount(1, unit, basis) is not None for basis in ('g', 'ml', 'pcs'))
    if (settings.get('autoGlobalPrices') or refresh_since is not None) and country and currency and compatible_unit:
        async def lookup(**kwargs):
            nonlocal reason, lookup_failed
            data = await _observations(bridge, settings=settings, refresh_since=refresh_since, unit=unit, **kwargs)
            if not data.get('ok'):
                reason = 'source_unavailable'
                lookup_failed = True
            elif data.get('searchLimited'):
                reason = 'search_limited'
            rows = [row for row in data.get('items', []) if row.get('usable')
                    and row.get('country') == country and row.get('currency') == currency
                    and (not unit or convert_amount(1, unit, row.get('basisUnit')) is not None)]
            if not rows and any(row.get('usable') for row in data.get('items', [])) and not lookup_failed:
                reason = 'basis_missing'
            return max(rows, key=lambda row: row.get('date', ''), default=None)
        if barcode and (refresh_since is not None or not _fresh(reference)):
            row = await lookup(barcode=barcode, prefer_snapshot=reference is None)
            if row:
                await _store_observation(store, 'barcode:' + barcode, row)
                reference = store.barcode_reference(barcode, country=country, currency=currency, unit=unit)
        if reference is None and (refresh_since is not None or not _fresh(fallback)):
            category = category_for(ingredient)
            if category:
                row = await lookup(category=category[0], category_type=category[1], prefer_snapshot=fallback is None)
                if row is None and not lookup_failed:
                    # Loose and packaged observations can exist for the same food.
                    other = 'PRODUCT' if category[1] == 'CATEGORY' else 'CATEGORY'
                    row = await lookup(category=category[0], category_type=other, prefer_snapshot=fallback is None)
                if row:
                    await _store_observation(store, identity, row, generic=True)
                    fallback = store.best_reference(identity, country=country, currency=currency, unit=unit)
            elif not barcode and fallback is None:
                reason = 'category_unmapped'
    elif not compatible_unit:
        reason = 'basis_missing'
    elif not country or not currency:
        reason = 'choose_country'
    else:
        reason = 'automatic_disabled'
    if reference is None:
        reference, kind = fallback, 'ingredient'
    amount = _cost_for_amount(reference, quantity, unit) if reference else None
    return {'settings': settings, 'reference': reference, 'matchKind': kind,
            'estimate': round(amount, 2) if amount is not None else None, 'lookupFailed': lookup_failed,
            'status': 'priced' if amount is not None else 'basis_missing' if reference else reason}


def validate_paid_price(raw):
    if raw is None:
        return None
    amount = _number(raw.get('amount'))
    currency = _currency(raw.get('currency'))
    if amount is None or currency not in CURRENCIES:
        raise ValueError('Enter a non-negative price and a three-letter currency')
    return {'amount': amount, 'currency': currency, 'country': _country(raw.get('country')),
            'location': str(raw.get('location') or '')[:300]}


async def save_product_prices(bridge, ingredient, lot_id, msg, metadata):
    """Only an explicitly entered paid amount is exact; observations stay estimates."""
    store = await cost_store_for_bridge(bridge)
    settings = await price_settings(bridge)
    paid = validate_paid_price(msg.get('paid_price'))
    identity = inventory_identity(ingredient)
    if paid:
        args = dict(amount=paid['amount'], currency=paid['currency'], basis_quantity=msg['quantity'],
            basis_unit=msg['unit'], country=paid['country'] or settings['country'], location=paid['location'],
            date=metadata.get('purchaseDate') or datetime.now(timezone.utc).date().isoformat(), barcode=metadata.get('barcode', ''))
        await store.async_set_reference('lot:' + lot_id, **args, source='purchase', confidence='exact_purchase')
        # The same purchase is an estimate for future quantities, not another paid lot.
        await store.async_set_reference(identity, **args, source='purchase_reference', confidence='user_entered')
    elif metadata.get('barcode'):
        reference = store.barcode_reference(metadata['barcode'], country=settings['country'], currency=settings['currency'])
        if reference:
            await _store_observation(store, identity, reference)


async def recipe_price(bridge, recipe, catalog, *, refresh_since=None):
    settings = await price_settings(bridge)
    store = await cost_store_for_bridge(bridge)
    recipe = canonical_recipe(recipe, catalog)
    inventory = bridge.recipe_hub.profile.get('houseIngredients') or []
    tasks, seen, lookup_status = [], set(), {}
    identities = {}
    if not hasattr(bridge, '_price_hydrations'):
        bridge._price_hydrations = {}
    skipped = False
    for item in recipe.get('ingredients', []):
        identity = inventory_identity(item)
        weight = item.get('weight') if isinstance(item.get('weight'), dict) else {}
        amount = item.get('quantity') if item.get('quantity') is not None else weight.get('quantity')
        unit = item.get('unit') or weight.get('unit', '')
        options = price_options(item)
        supported = [option for option in options if any(
            convert_amount(1, option['unit'], basis) is not None for basis in ('g', 'ml', 'pcs'))]
        if supported:
            category = category_for(item)
            chosen = next((option for option in supported if
                store.best_reference(identity, country=settings['country'], currency=settings['currency'], unit=option['unit'])
                or category and snapshot_observations(category=category[0], country=settings['country'],
                    currency=settings['currency'], unit=option['unit'])), supported[0])
            amount, unit = chosen['quantity'], chosen['unit']
        if amount is None or not unit:
            lookup_status[identity] = 'recipe_amount_unknown'
            continue
        if (identity, unit) in seen:
            continue
        seen.add((identity, unit))
        codes = {lot.get('barcode') for row in inventory if inventory_identity(row) == identity
                 for lot in row.get('lots', []) if lot.get('barcode')}
        if not codes:
            # Confirmed product->ingredient evidence remains usable after stock is consumed.
            ref = store.best_reference(identity, country=settings['country'], currency=settings['currency'])
            codes = {ref['barcode']} if ref and ref.get('barcode') and ref.get('source') not in {'open_prices_category', 'retail_snapshot', 'utility_snapshot'} else {''}
        for code in sorted(codes):
            if len(tasks) >= 24:
                skipped = True
                lookup_status.setdefault(identity, 'lookup_limit')
                break
            async def hydrate(item=item, code=code, identity=identity, unit=unit, amount=amount):
                result = await product_price(bridge, barcode=code, ingredient=item,
                    quantity=amount, unit=unit, settings=settings,
                    refresh_since=refresh_since)
                # Stock barcodes and saved ingredient links are confirmed mappings.
                # Preserve a fresh generic estimate when the last package is gone.
                if result.get('reference') and result.get('matchKind') == 'barcode':
                    await _store_observation(store, identity, result['reference'])
                return result
            key = (identity, code, unit, settings['country'], settings['currency'])
            task = bridge._price_hydrations.get(key)
            if task is None or task.done():
                if len(bridge._price_hydrations) >= 500:
                    skipped = True
                    lookup_status[identity] = 'lookup_limit'
                    continue
                task = bridge.hass.async_create_background_task(hydrate(), 'Cook4Me ingredient price')
                bridge._price_hydrations[key] = task
                def cleanup(done, key=key):
                    if bridge._price_hydrations.get(key) is done:
                        bridge._price_hydrations.pop(key, None)
                    if not done.cancelled():
                        done.exception()  # Observe provider errors even after the caller leaves.
                task.add_done_callback(cleanup)
            tasks.append(task)
            identities[task] = identity
    # Returning a partial total must not cancel the work that fills its gaps.
    # Subsequent visible-recipe polls share these jobs, never force a new lookup.
    done, pending = await asyncio.wait(tasks, timeout=_RECIPE_WAIT_SECONDS) if tasks else (set(), set())
    failures = 0
    for task in done:
        if task.cancelled() or task.exception():
            failures += 1
            lookup_status[identities[task]] = 'source_unavailable'
        else:
            result = task.result()
            failures += bool(result.get('lookupFailed') or result.get('status') == 'source_unavailable')
            lookup_status[identities[task]] = result.get('status')
    for task in pending:
        lookup_status[identities[task]] = 'lookup_pending'
    cache = await recipe_cost_cache_for_bridge(bridge)
    cost = await cache.async_cost(recipe, inventory, store, country=settings['country'], currency=settings['currency'], force=refresh_since is not None)
    for row in cost.get('ingredients', []):
        if row.get('coverage', 0) < 1:
            row['priceStatus'] = ('recipe_amount_unknown' if row.get('reason') == 'recipe_amount_unknown'
                                  else lookup_status.get(row['identity']) or ('source_unavailable' if failures else 'no_observation'))
    cost.update(settings=settings, priceLookupIncomplete=bool(failures), priceLookupPending=bool(pending), priceSource='Public price observations',
                originalIngredients=True, ingredientLimitReached=skipped,
                checkedAt=datetime.now(timezone.utc).isoformat(), refreshed=refresh_since is not None,
                refreshPolicy={'observationsSeconds': 86400, 'missSeconds': 3600, 'failureSeconds': 60,
                               'onDemand': True, 'maximumObservationDays': 180})
    return cost


async def offline_recipe_price(bridge, recipe, catalog):
    """Immediate card preview from local evidence, without provider requests.

    Use an ephemeral reference set: scrolling through cards must not rewrite the
    user's price store or turn a generic product into a confirmed barcode link.
    """
    from copy import copy
    settings = await price_settings(bridge)
    saved = await cost_store_for_bridge(bridge)
    store = copy(saved)
    store._data = deepcopy(saved._data)
    recipe = canonical_recipe(recipe, catalog)
    if settings.get('autoGlobalPrices'):
        for item in recipe.get('ingredients', []):
            category = category_for(item)
            if not category:
                continue
            identity = inventory_identity(item)
            for option in price_options(item):
                if store.best_reference(identity, country=settings['country'], currency=settings['currency'], unit=option['unit']):
                    continue
                rows = snapshot_observations(category=category[0], country=settings['country'],
                    currency=settings['currency'], unit=option['unit'])
                if rows:
                    row = max(rows, key=lambda row: row.get('date', ''))
                    store._data['references']['preview:' + identity + ':' + option['unit']] = {
                        **row, 'identity': identity, 'source': row['source'] if row.get('source') in {'retail_snapshot', 'utility_snapshot'} else 'open_prices_category',
                        'observationId': row['id'], 'updatedAt': datetime.now(timezone.utc).isoformat()}
    from .costing import calculate_recipe_cost
    cost = calculate_recipe_cost(recipe, bridge.recipe_hub.profile.get('houseIngredients') or [], store,
        country=settings['country'], currency=settings['currency'])
    for row in cost.get('ingredients', []):
        if row.get('coverage', 0) < 1:
            row['priceStatus'] = 'recipe_amount_unknown' if row.get('reason') == 'recipe_amount_unknown' else 'offline_price_missing'
    cost.update(settings=settings, offlinePreview=True, priceLookupPending=False,
                checkedAt=datetime.now(timezone.utc).isoformat())
    return cost
