"""Batch 30: fresh okra filters, distinct cooked forms and manual paste opening dates."""
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_lifecycle_v246 import MONTHS, NAMES, actual_choice, catalog, opening
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    ids = {row[0] for row in NAMES}
    catalogs = {}
    for lang in ('el', 'de'):
        rows = catalog.ingredient_choices(lang)
        catalogs[lang] = list({actual_choice(rows, ident)['id']: actual_choice(rows, ident) for ident in ids}.values())
    scenarios = []
    for ident, brand, barcode in (('M_FOOD_316', 'Arche', '4020943134149'),
                                 ('M_FOOD_239', 'BioGourmet', '4039057412876')):
        lot = {'brand': brand, 'barcode': barcode}
        scenarios.append({'ingredient': actual_choice(catalogs['el'], ident), 'lot': lot,
                          'rules': opening.opening_rules({'ingredientId': ident}, lot)})
    html = local_html(ROOT).replace('_api(type,data={}){\n  this.calls.push',
        '_api(type,data={}){\n  if(type.endsWith("/opening_guidance"))return super._api(type,data);\n  this.calls.push')
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
        for width, height in ((390, 844), (1440, 980)):
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.clock.install(time=datetime(2026, 9, 26, 12, tzinfo=timezone.utc))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_default_timeout(6000)
            page.set_content(html);page.wait_for_function('window.ready')
            page.evaluate("""async catalogs => {
                app._ingredientCatalog=catalogs.el;app._ingredientCatalogLanguage='el';
                app._v79Settings={country:'DE',supermarketLanguage:'de'};
                app._hass.connection.sendMessagePromise=async msg=>{
                    if(msg.type.endsWith('/job_run'))return app._hass.connection.sendMessagePromise(msg.request);
                    if(msg.type.endsWith('/ingredient_catalog'))return {items:catalogs[msg.language]};
                    if(msg.type.endsWith('/opening_guidance'))return {rules:window.offeredRules||[]};
                    return {};
                };
                await app._v140LoadSupermarketCatalog(true);app.show('profile');
            }""", catalogs)
            section = page.locator('[data-v84-catalog]')

            def option(ident):
                name = actual_choice(catalogs['el'], ident)['name']
                return section.locator('option').filter(has_text=re.compile('^' + re.escape(name) + r'(?: \(|$)'))

            for country in ('DE', 'GR'):
                page.evaluate("country=>{app._v79Settings.country=country;app.show('profile');}", country)
                for month in range(1, 13):
                    page.clock.set_system_time(datetime(2026, month, 15, 12, tzinfo=timezone.utc))
                    section.locator('[data-v223-toggle]').uncheck();section.locator('[data-v223-toggle]').check()
                    expect(option('M_FOOD_669')).to_have_count(int(country != 'GR' or month in MONTHS))
                    for ident in ids - {'M_FOOD_669'}:
                        expect(option(ident)).to_have_count(1)
            section.locator('[data-v223-toggle]').uncheck()
            for ident, name, _ in NAMES:
                expect(option(ident)).to_contain_text(name)
            page.clock.set_system_time(datetime(2026, 9, 26, 12, tzinfo=timezone.utc))
            for scenario in scenarios:
                page.evaluate("""async ({ingredient,lot,rules}) => {
                    window.offeredRules=rules;await app._v78Open('manual');
                    Object.assign(app._v78Draft,{...lot,productName:ingredient.name,quantity:210,unit:'g',
                        ingredient,ingredientLinks:[ingredient],editorOpen:true,bestBefore:'2099-12-31'});
                    app._v78RenderCapture();
                }""", scenario)
                page.locator('main [data-draft="useWithinDays"]').locator('xpath=ancestor::details').locator('summary').click()
                selected = page.locator('[data-v222-rule]')
                expect(selected.locator('option')).to_have_count(1)
                expect(page.locator('[data-v222-opened]')).to_be_disabled()
                assert not page.evaluate('Boolean(app._v78Draft.openedAt)')
                page.locator('main [data-draft="useWithinDays"]').fill('7')
                expect(page.locator('[data-v222-opened]')).to_be_enabled()
                page.locator('[data-v222-apply]').check();page.locator('[data-v222-opened]').check()
                assert page.evaluate("app._v78Draft.openedAt==='2026-09-26'&&app._v78Draft.applyOpeningExpiry")
                expect(page.locator('[data-v222-expiry]')).to_contain_text('2026-10-03')
                page.evaluate('app._v78Close(true)')
            assert not errors, errors
            print(f'PASS {width}: twelve-month regional okra filters, cooked/frozen/dried exclusions, supermarket names and manual paste opening dates')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
