"""Recipe percentages in the top-right photo corner across every preview route."""
from pathlib import Path
import shutil

from playwright.sync_api import expect, sync_playwright
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
    for width, height in ((390, 844), (1440, 980)):
        page = browser.new_page(viewport={'width': width, 'height': height})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_default_timeout(6000)
        page.set_content(local_html(ROOT));page.wait_for_function('window.ready')
        page.evaluate("""() => {
            const rows=[...app._todayResults,...app._results,...app._bookState.favorites,...app._bookState.recipeList,...app._entry().recipes,...app._weekState.slots.map(s=>s.recipe)];
            rows.forEach(row=>{row.match.quantityCoverage=.75;row.match.quantityConfidence=1;});
            app._recommendations=[structuredClone(app._results[0])];
        }""")
        for tab in ('today', 'week', 'official', 'recommend', 'book', 'mine'):
            page.evaluate('tab=>app.show(tab)', tab)
            cards = page.locator('article.ui203-recipe')
            assert cards.count() > 0, tab
            assert page.evaluate("""() => [...app.shadowRoot.querySelectorAll('article.ui203-recipe')].every(card=>{
                const badges=card.querySelectorAll('[data-v241-stock]'),badge=badges[0],media=card.querySelector('.rx-v69-media');
                const b=badge?.getBoundingClientRect(),m=media.getBoundingClientRect();
                const cost=card.querySelector('[data-v82-card-cost]')?.getBoundingClientRect();
                return (!cost||cost.right<=b.left-1)&&badges.length===1&&badge.textContent==='75%'&&badge.getAttribute('aria-label').includes('Υλικά στο σπίτι')&&
                    Math.abs(m.right-b.right-10)<2&&Math.abs(b.top-m.top-10)<2&&b.left>=m.left&&b.bottom<=m.bottom&&card.scrollWidth<=card.clientWidth+1;
            })"""), (width, tab)
        # Re-rendering and expanded previews replace the badge rather than duplicate it.
        page.evaluate("app.show('today');app._todayResults[0].match.quantityCoverage=0;app._renderTab()")
        expect(page.locator('article.ui203-recipe [data-v241-stock]').first).to_have_text('0%')
        page.evaluate("app._todayResults[0].match.quantityCoverage=1;app._todayResults[0].match.quantityConfidence=0;app._renderTab()")
        expect(page.locator('article.ui203-recipe [data-v241-stock]').first).to_have_text('—')
        page.evaluate("app._todayResults[0].match.quantityCoverage=.75;app._todayResults[0].match.quantityConfidence=.5;app._renderTab()")
        expect(page.locator('article.ui203-recipe [data-v241-stock]').first).to_have_text('≈ 75%')
        # A substitution warning stays below the top-right percentage, unobscured.
        page.evaluate("app._todayResults[0].match.requiresSubstitutions=true;app._renderTab()")
        assert page.locator('article.ui203-recipe').first.evaluate("""card=>{
            const badge=card.querySelector('[data-v241-stock]').getBoundingClientRect(),diet=card.querySelector('[data-v76-diet-badge]').getBoundingClientRect();
            return diet.top>=badge.bottom&&diet.left>=card.getBoundingClientRect().left;
        }""")
        # The overlay doesn't intercept clicks or change the original photo action.
        photo=page.locator('article.ui203-recipe [data-v66-photo]').first
        photo.click(position={'x': photo.bounding_box()['width'] - 20, 'y': 20})
        page.wait_for_function('app._v63RecipeDialog?.isConnected')
        page.locator('[data-modal-close]').click()
        page.evaluate("app._todayResults[0]._v202Gap='processing_error';app._renderTab()")
        expect(page.locator('[data-v202-recipe-gap] [data-v241-stock]')).to_have_count(0)
        # The same renderer is also used by ingredient-usage and focused previews.
        page.evaluate("""() => {
            app._v66IgnoreTags=true;app._v66Context=null;
            const host=document.createElement('section');host.id='usage-stock-test';app.shadowRoot.querySelector('#content').append(host);
            const row=samples(40);row.match.quantityCoverage=1;row.match.quantityConfidence=1;
            host.innerHTML=app._recipeCard(row,false);
        }""")
        expect(page.locator('#usage-stock-test [data-v241-stock]')).to_have_text('100%')
        if width == 390:
            page.evaluate("app._todayResults[0]._v202Gap=null;app._todayResults[0].match.requiresSubstitutions=false;app.show('today')")
            page.locator('article.ui203-recipe').first.screenshot(path='/tmp/cook4me-stock-badge-v241.png')
        assert not errors, errors
        print(f'PASS {width}: all preview routes, top-right placement, unknown/partial values, warning coexistence and photo action')
        page.close()
    browser.close()
