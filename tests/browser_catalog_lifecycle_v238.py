"""Real fresh/dried choices and seasonal boundaries in both catalog languages."""
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil

from playwright.sync_api import expect, sync_playwright
from test_catalog_lifecycle_v238 import DRIED, NAMES, SEASONS, STAPLES, actual_choice, catalog
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]


def run():
    ids = set(SEASONS) | set(STAPLES) | {row[0] for row in DRIED}
    catalogs = {}
    for lang in ('el', 'de'):
        rows = catalog.ingredient_choices(lang)
        catalogs[lang] = list({actual_choice(rows, ident)['id']: actual_choice(rows, ident) for ident in ids}.values())
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
        for width, height in ((390, 844), (1440, 980)):
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.clock.install(time=datetime(2026, 9, 25, 12, tzinfo=timezone.utc))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_default_timeout(6000)
            page.set_content(local_html(ROOT));page.wait_for_function('window.ready')
            page.evaluate("""async catalogs => {
                app._ingredientCatalog=catalogs.el;app._ingredientCatalogLanguage='el';
                app._v79Settings={country:'DE',supermarketLanguage:'de'};
                app._hass.connection.sendMessagePromise=async msg=>{
                    if(msg.type.endsWith('/job_run'))return app._hass.connection.sendMessagePromise(msg.request);
                    if(msg.type.endsWith('/ingredient_catalog'))return {items:catalogs[msg.language]};
                    return {};
                };
                await app._v140LoadSupermarketCatalog(true);app.show('profile');
            }""", catalogs)
            section = page.locator('[data-v84-catalog]')

            def option(ident):
                name = actual_choice(catalogs['el'], ident)['name']
                return section.locator('option').filter(has_text=re.compile('^' + re.escape(name) + r'(?: \(|$)'))

            for month in range(1, 13):
                page.clock.set_system_time(datetime(2026, month, 15, 12, tzinfo=timezone.utc))
                section.locator('[data-v223-toggle]').uncheck();section.locator('[data-v223-toggle]').check()
                for ident, (_, months, _) in SEASONS.items():
                    expect(option(ident)).to_have_count(int(month in months))
                for ident in (*STAPLES, *(row[0] for row in DRIED)):
                    expect(option(ident)).to_have_count(1)
            section.locator('[data-v223-toggle]').uncheck()
            for ident, name, _ in NAMES:
                expect(option(ident)).to_contain_text(name)
            for ident, _, name in DRIED:
                expect(option(ident)).to_contain_text(name)
            expect(option(DRIED[2][0])).not_to_contain_text('πρέζα')
            expect(option('M_FOOD_308')).not_to_contain_text('Getrocknete')
            page.evaluate("app._v79Settings.country='GR';app.show('profile')")
            section.locator('[data-v223-toggle]').check()
            for ident in SEASONS:
                expect(option(ident)).to_have_count(1)
            assert not errors, errors
            print(f'PASS {width}: fresh/dried choices, 12 monthly boundaries, country fallback, German labels and amount-free mint')
            page.close()
        browser.close()


if __name__ == '__main__':
    run()
