"""Batch 28: actual pumpkin season picker, stock names and opening controls."""
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_lifecycle_v244 import PACKAGES, DRY_IDS, NAMES, actual_choice, catalog, opening
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    ids = {row[0] for row in NAMES} | set(DRY_IDS) | {'M_FOOD_145'}
    catalogs = {}
    for lang in ('el', 'de'):
        rows = catalog.ingredient_choices(lang)
        catalogs[lang] = list({actual_choice(rows, ident)['id']: actual_choice(rows, ident) for ident in ids}.values())
    scenarios = []
    for _, ident, code, rule, _ in PACKAGES:
        for target, barcode, brand in ((ident, code, 'Lacroix'), ('M_FOOD_50', code, 'Lacroix'),
                                       (ident, code, 'Other'), (ident, '4066447992373', 'Lacroix')):
            lot = {'brand': brand, 'barcode': barcode}
            scenarios.append({'ingredient': actual_choice(catalogs['el'], target), 'lot': lot, 'rule': rule,
                              'rules': opening.opening_rules({'ingredientId': target}, lot)})
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
                    expect(option('M_FOOD_399')).to_have_count(int(country != 'DE' or month >= 8))
                    for ident in ids - {'M_FOOD_399'}:
                        expect(option(ident)).to_have_count(1)
            section.locator('[data-v223-toggle]').uncheck()
            for ident, name, _ in NAMES:
                expect(option(ident)).to_contain_text(name)
            expect(option('M_FOOD_399')).not_to_contain_text('Zierkürbis')
            page.clock.set_system_time(datetime(2026, 9, 26, 12, tzinfo=timezone.utc))
            for scenario in scenarios:
                page.evaluate("""async ({ingredient,lot,rules}) => {
                    window.offeredRules=rules;await app._v78Open('manual');
                    Object.assign(app._v78Draft,{...lot,productName:ingredient.name,quantity:400,unit:'ml',
                        ingredient,ingredientLinks:[ingredient],editorOpen:true,bestBefore:'2099-12-31'});
                    app._v78RenderCapture();
                }""", scenario)
                page.locator('main [data-draft="useWithinDays"]').locator('xpath=ancestor::details').locator('summary').click()
                selected = page.locator('[data-v222-rule]')
                expect(selected.locator('option[value="' + scenario['rule'] + '"]')).to_have_count(int(bool(scenario['rules'])))
                if scenario['rules']:
                    selected.select_option(scenario['rule'])
                    expect(page.locator('[data-v222-opened]')).to_be_disabled()
                    assert not page.evaluate('Boolean(app._v78Draft.openedAt)')
                    page.locator('[data-v222-conditions]').check()
                    page.locator('[data-v222-apply]').check();page.locator('[data-v222-opened]').check()
                    expect(page.locator('main [data-draft="useWithinDays"]')).to_have_value('2')
                    assert page.evaluate("app._v78Draft.openedAt==='2026-09-26'&&app._v78Draft.applyOpeningExpiry")
                page.evaluate('app._v78Close(true)')
            assert not errors, errors
            print(f'PASS {width}: twelve-month pumpkin filters, supermarket names, four exact stock packages, dry-form exclusions and opening confirmation')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
