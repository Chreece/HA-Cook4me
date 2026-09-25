"""Restored provider guidance in the real picker and package-opening editor."""
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_lifecycle_v237 import MAPPINGS, NAMES, PACKAGES, SEASONS, actual_choice, catalog, opening
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    ids = set(MAPPINGS) | {r[0] for r in SEASONS}
    catalogs = {}
    for lang in ('el', 'de'):
        rows = catalog.ingredient_choices(lang)
        catalogs[lang] = list({actual_choice(rows, ident)['id']: actual_choice(rows, ident) for ident in ids}.values())
    cases = [PACKAGES[0], PACKAGES[2], PACKAGES[-1], ('M_FOOD_269', '', '', 'milk', 3, 3, ('pasteurized_or_uht',))]
    rules = {code: opening.opening_rules({'ingredientId': ident}, {'brand': brand, 'barcode': code})
             for ident, brand, code, *_ in cases}
    html = local_html(ROOT).replace('_api(type,data={}){\n  this.calls.push',
        '_api(type,data={}){\n  if(type.endsWith("/opening_guidance"))return super._api(type,data);\n  this.calls.push')
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
        for width, height in ((390, 844), (1440, 980)):
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.clock.install(time=datetime(2026, 9, 25, 12, tzinfo=timezone.utc))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_default_timeout(6000)
            page.set_content(html);page.wait_for_function('window.ready')
            page.evaluate("""async ({catalogs,rules}) => {
                app._ingredientCatalog=catalogs.el;app._ingredientCatalogLanguage='el';
                app._v79Settings={country:'DE',supermarketLanguage:'de'};
                app._hass.connection.sendMessagePromise=async msg=>{
                    if(msg.type.endsWith('/job_run'))return app._hass.connection.sendMessagePromise(msg.request);
                    if(msg.type.endsWith('/ingredient_catalog'))return {items:catalogs[msg.language]};
                    if(msg.type.endsWith('/opening_guidance'))return {rules:rules[msg.lot_metadata.barcode]||[]};
                    return {};
                };
                await app._v140LoadSupermarketCatalog(true);app.show('profile');
            }""", {'catalogs': catalogs, 'rules': rules})
            section = page.locator('[data-v84-catalog]')
            for month in (4, 5, 6, 10, 11, 12):
                page.clock.set_system_time(datetime(2026, month, 15, 12, tzinfo=timezone.utc))
                section.locator('[data-v223-toggle]').uncheck();section.locator('[data-v223-toggle]').check()
                for ident, months in SEASONS:
                    name = actual_choice(catalogs['el'], ident)['name']
                    expect(section.locator('option').filter(has_text=name)).to_have_count(int(month in months))
            section.locator('[data-v223-toggle]').uncheck()
            for ident, name, _ in NAMES:
                ingredient = actual_choice(catalogs['el'], ident)
                label = re.compile('^' + re.escape(ingredient['name']) + r'(?: \(|$)')
                expect(section.locator('option').filter(has_text=label)).to_contain_text(name)
            page.clock.set_system_time(datetime(2026, 9, 25, 12, tzinfo=timezone.utc))
            for ident, brand, code, rule, _, maximum, conditions in cases:
                ingredient = actual_choice(catalogs['el'], ident)
                page.evaluate("""async ({ingredient,brand,code}) => {
                    await app._v78Open('manual');
                    Object.assign(app._v78Draft,{brand,barcode:code,productName:ingredient.name,
                        quantity:250,unit:'g',ingredient,ingredientLinks:[ingredient],editorOpen:true,bestBefore:'2099-12-31'});
                    app._v78RenderCapture();
                }""", {'ingredient': ingredient, 'brand': brand, 'code': code})
                page.locator('main [data-draft="useWithinDays"]').locator('xpath=ancestor::details').locator('summary').click()
                select = page.locator('[data-v222-rule]')
                expect(select.locator(f'option[value="{rule}"]')).to_have_count(1)
                select.select_option(rule)
                expect(page.locator('[data-v222-opened]')).to_be_disabled()
                if conditions:
                    expect(page.locator('[data-v222-editor]')).to_contain_text('μεταλλικό' if rule.startswith('dmbio') else 'Παστεριωμένο')
                assert not page.evaluate('Boolean(app._v78Draft.openedAt)')
                page.locator('[data-v222-conditions]').check()
                page.locator('[data-v222-apply]').check();page.locator('[data-v222-opened]').check()
                expect(page.locator('main [data-draft="useWithinDays"]')).to_have_value(str(maximum))
                assert page.evaluate("app._v78Draft.openedAt==='2026-09-25'&&app._v78Draft.applyOpeningExpiry")
                page.evaluate('app._v78Close(true)')
            assert not errors, errors
            print(f'PASS {width}: provider guidance, seasonal months, supermarket names and storage/form confirmation')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
