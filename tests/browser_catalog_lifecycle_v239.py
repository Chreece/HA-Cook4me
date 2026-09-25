"""Pantry forms, two herb seasons and exact satay opening guidance in the UI."""
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_lifecycle_v239 import CODE, NAMES, PANTRY, SEASONS, actual_choice, catalog, opening
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    ids = set(SEASONS) | set(PANTRY) | {'M_FOOD_534', 'M_FOOD_329'}
    catalogs = {}
    for lang in ('el', 'de'):
        rows = catalog.ingredient_choices(lang)
        catalogs[lang] = list({actual_choice(rows, ident)['id']: actual_choice(rows, ident) for ident in ids}.values())
    rules = opening.opening_rules({'ingredientId': 'M_FOOD_534'}, {'brand': 'dmBio', 'barcode': CODE})
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
            page.evaluate("""async ({catalogs,rules,code}) => {
                app._ingredientCatalog=catalogs.el;app._ingredientCatalogLanguage='el';
                app._v79Settings={country:'DE',supermarketLanguage:'de'};
                app._hass.connection.sendMessagePromise=async msg=>{
                    if(msg.type.endsWith('/job_run'))return app._hass.connection.sendMessagePromise(msg.request);
                    if(msg.type.endsWith('/ingredient_catalog'))return {items:catalogs[msg.language]};
                    if(msg.type.endsWith('/opening_guidance'))return {rules:msg.lot_metadata.barcode===code?rules:[]};
                    return {};
                };
                await app._v140LoadSupermarketCatalog(true);app.show('profile');
            }""", {'catalogs': catalogs, 'rules': rules, 'code': CODE})
            section = page.locator('[data-v84-catalog]')

            def option(ident):
                name = actual_choice(catalogs['el'], ident)['name']
                return section.locator('option').filter(has_text=re.compile('^' + re.escape(name) + r'(?: \(|$)'))

            for month in range(1, 13):
                page.clock.set_system_time(datetime(2026, month, 15, 12, tzinfo=timezone.utc))
                section.locator('[data-v223-toggle]').uncheck();section.locator('[data-v223-toggle]').check()
                for ident, (_, months, _, _) in SEASONS.items():
                    expect(option(ident)).to_have_count(int(month in months))
                for ident in PANTRY:
                    expect(option(ident)).to_have_count(1)
            section.locator('[data-v223-toggle]').uncheck()
            for ident, name, _ in NAMES:
                expect(option(ident)).to_contain_text(name)
            page.clock.set_system_time(datetime(2026, 9, 25, 12, tzinfo=timezone.utc))
            for code, offered in ((CODE, True), ('4066447948271', False)):
                ingredient = actual_choice(catalogs['el'], 'M_FOOD_534')
                page.evaluate("""async ({ingredient,code}) => {
                    await app._v78Open('manual');
                    Object.assign(app._v78Draft,{brand:'dmBio',barcode:code,productName:ingredient.name,
                        quantity:325,unit:'ml',ingredient,ingredientLinks:[ingredient],editorOpen:true,bestBefore:'2099-12-31'});
                    app._v78RenderCapture();
                }""", {'ingredient': ingredient, 'code': code})
                page.locator('main [data-draft="useWithinDays"]').locator('xpath=ancestor::details').locator('summary').click()
                selected = page.locator('[data-v222-rule]')
                expect(selected.locator('option[value="dmbio_peanut_sauce"]')).to_have_count(int(offered))
                if offered:
                    selected.select_option('dmbio_peanut_sauce')
                    expect(page.locator('[data-v222-opened]')).to_be_disabled()
                    assert not page.evaluate('Boolean(app._v78Draft.openedAt)')
                    page.locator('[data-v222-conditions]').check()
                    page.locator('[data-v222-apply]').check();page.locator('[data-v222-opened]').check()
                    expect(page.locator('main [data-draft="useWithinDays"]')).to_have_value('3')
                    assert page.evaluate("app._v78Draft.openedAt==='2026-09-25'&&app._v78Draft.applyOpeningExpiry")
                page.evaluate('app._v78Close(true)')
            assert not errors, errors
            print(f'PASS {width}: herb months, whole/ground nuts, paste names and exact satay package opening')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
