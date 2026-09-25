"""Actual catalog data reaches the seasonal picker and opening-guidance editor."""
from datetime import datetime, timezone
from pathlib import Path
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_lifecycle_v227 import catalog, opening
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    ids = {'M_FOOD_389', 'M_FOOD_624'}
    catalogs = {lang: [r for r in catalog.ingredient_choices(lang) if r.get('key') in ids] for lang in ('el', 'de')}
    lot = {'brand': 'dmBio', 'barcode': '4070765022803'}
    rules = opening.opening_rules({'ingredientId': 'M_FOOD_624'}, lot)
    assert len(rules) == 1
    html = local_html(ROOT).replace('_api(type,data={}){\n  this.calls.push',
        '_api(type,data={}){\n  if(type.endsWith("/opening_guidance"))return super._api(type,data);\n  this.calls.push')
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium') or None, args=['--no-sandbox'])
        for width, height in ((390, 844), (1440, 980)):
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.clock.install(time=datetime(2026, 9, 25, 12, tzinfo=timezone.utc))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_default_timeout(6000)
            page.set_content(html);page.wait_for_function('window.ready')
            page.evaluate("""async ({catalogs,rules,lot}) => {
                app._ingredientCatalog=catalogs.el;app._ingredientCatalogLanguage='el';
                app._v79Settings={country:'DE',supermarketLanguage:'de'};
                app._hass.connection.sendMessagePromise=async msg=>{
                    if(msg.type.endsWith('/job_run'))return app._hass.connection.sendMessagePromise(msg.request);
                    if(msg.type.endsWith('/ingredient_catalog'))return {items:catalogs[msg.language]};
                    if(msg.type.endsWith('/opening_guidance'))return {rules:msg.lot_metadata.barcode===lot.barcode?rules:[]};
                    return {};
                };
                await app._v140LoadSupermarketCatalog(true);app.show('profile');
            }""", {'catalogs': catalogs, 'rules': rules, 'lot': lot})
            section = page.locator('[data-v84-catalog]')
            section.locator('[data-v223-toggle]').check()
            assert section.locator('option').filter(has_text='Πιπεριά (Paprika)').count() == 1

            page.evaluate("""async lot => {
                await app._v78Open('manual');
                const ingredient=app._ingredientCatalog.find(r=>r.key==='M_FOOD_624');
                Object.assign(app._v78Draft,lot,{productName:'Soja natur',quantity:1000,unit:'ml',
                    ingredient,ingredientLinks:[ingredient],editorOpen:true,bestBefore:'2099-12-31'});
                app._v78RenderCapture();
            }""", lot)
            section = page.locator('main [data-draft="useWithinDays"]').locator('xpath=ancestor::details')
            section.locator('summary').click()
            select = page.locator('[data-v222-rule]')
            expect(select.locator('option[value="dmbio_soy_drink"]')).to_have_text('4 ημέρες · dmBio')
            select.select_option('dmbio_soy_drink')
            expect(page.locator('[data-v222-editor]')).to_contain_text('Διατήρηση σε όρθια θέση')
            expect(page.locator('[data-v222-opened]')).to_be_disabled()
            page.locator('[data-v222-conditions]').check()
            page.locator('[data-v222-apply]').check();page.locator('[data-v222-opened]').check()
            expect(page.locator('main [data-draft="useWithinDays"]')).to_have_value('4')
            assert page.evaluate("app._v78Draft.openedAt==='2026-09-25' && app._v78Draft.applyOpeningExpiry")
            assert not errors, errors
            print(f'PASS {width}: real September pepper season and verified soy-drink opening instructions')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
