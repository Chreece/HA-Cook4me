"""Whole peppers and seasoning spices stay separate in the delivered frontend."""
import json
from pathlib import Path
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_amounts_v225 import presentation
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    payload = json.loads((ROOT/'custom_components/cook4me/catalog/merged_catalog.v1.json').read_bytes())
    ids = {'M_FOOD_389', 'M_FOOD_388', 'M_FOOD_377', 'M_FOOD_358'}
    catalogs = {lang: [row for row in presentation.ingredient_choices(payload, lang)
                      if ids.intersection(row['sourceIngredientIds'])] for lang in ('el', 'de')}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium') or None, args=['--no-sandbox'])
        for width, height in ((390, 844), (1440, 980)):
            page = browser.new_page(viewport={'width': width, 'height': height})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_default_timeout(6000)
            page.set_content(local_html(ROOT))
            page.wait_for_function('window.ready')
            page.evaluate("""async catalogs => {
                app._ingredientCatalog=catalogs.el;app._ingredientCatalogLanguage='el';
                app._v79Settings={country:'DE',supermarketLanguage:'de'};
                app._hass.connection.sendMessagePromise=async msg=>msg.type.endsWith('/ingredient_catalog')?{items:catalogs[msg.language]}:{};
                await app._v140LoadSupermarketCatalog(true);app.show('profile');
            }""", catalogs)
            options = page.locator('[data-v84-catalog] option')
            assert options.count() == 5
            for label in ('Πιπεριά (Paprika)', 'Πιπέρι (Pfeffer)', 'Πιπεριά τσίλι (Chilischote)', 'Πάπρικα (Paprikapulver)'):
                expect(options.filter(has_text=label)).to_have_count(1)

            page.evaluate("""async () => {
                await app._v78Open('manual');
                app._v78Draft.ingredient={ingredientId:'M_FOOD_389',name:'Paprika'};
                app._v78Draft.ingredientLinks=[app._v78Draft.ingredient];
                app._v78IngredientOptions();
            }""")
            picker = page.locator('[data-v114-links]')
            expect(picker.locator('label').filter(has_text='Πιπεριά (Paprika)').locator('input')).to_be_checked()
            expect(picker.locator('label').filter(has_text='Πιπέρι (Pfeffer)').locator('input')).not_to_be_checked()
            assert picker.locator('[data-v114-link]').count() == 4
            assert not errors, errors
            print(f'PASS {width}: vegetable Paprika and pepper/Paprika spices have distinct Greek names and selections')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
