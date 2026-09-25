"""Render backend-deduplicated choices and resolve previously saved amount IDs."""
from pathlib import Path
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_amounts_v225 import presentation
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    payload = {'ingredients': [
        {'id': 'rice', 'key': 'rice', 'canonicalName': 'Rice', 'translations': {'de': 'Reis'}},
        {'id': 'rice-cup', 'canonicalName': '1 cup Rice'},
        {'id': 'rice-weight', 'canonicalName': '250 g Rice'},
        {'id': 'water', 'key': 'water', 'canonicalName': 'Water', 'translations': {'de': 'Wasser'}},
    ]}
    catalogs = {lang: presentation.ingredient_choices(payload, lang) for lang in ('el', 'de')}
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
                await app._v140LoadSupermarketCatalog(true);
                app.show('profile');
            }""", catalogs)
            section = page.locator('[data-v84-catalog]')
            assert section.locator('option').count() == 3  # two foods and placeholder
            assert section.locator('option').filter(has_text='Ρύζι (Reis)').count() == 1
            assert page.evaluate("app._v140MarketNames.get('rice-cup')") == 'Reis'
            section.locator('[data-v84-search]').fill('250 g')
            assert section.locator('option').count() == 2
            section.locator('[data-v84-search]').fill('')

            # An existing product may link to several former amount variants.
            page.evaluate("""async () => {
                await app._v78Open('manual');
                const d=app._v78Draft;
                d.ingredient={ingredientId:'rice-cup',name:'1 cup Rice'};
                d.ingredientLinks=[d.ingredient,{ingredientId:'rice-weight',name:'250 g Rice'}];
                d.quantity=500;d.unit='g';
                app._v78IngredientOptions();
            }""")
            picker = page.locator('[data-v114-links]')
            assert picker.locator('[data-v114-link]').count() == 2
            selected = picker.locator('label').filter(has_text='Ρύζι (Reis)').locator('input')
            expect(selected).to_be_checked()
            assert picker.locator('[data-v114-link]:checked').count() == 1
            assert '250 g' not in picker.inner_text() and '1 cup' not in picker.inner_text()
            assert page.evaluate("app._v78Draft.quantity===500 && app._v78Draft.unit==='g'")
            assert page.evaluate("app._v114Links().length===1 && app._v114Links()[0].key==='rice'")
            assert not errors, errors
            print(f'PASS {width}: clean catalog, old search terms, supermarket aliases, saved links and package quantity')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
