"""Exercise the delivered UI with document and HA shadow-host scrolling."""
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]

READ = """() => ({
 page:window.scrollOwner.scrollTop,
 dialog:app._v78Dialog?.scrollTop||0,
 list:app.shadowRoot.querySelector('.v114-link-list')?.scrollTop||0,
 suggestions:app.shadowRoot.querySelector('[data-v194-list]')?.scrollTop||0
})"""


def unchanged(before, after, context):
    assert all(abs(before[key] - after[key]) <= 2 for key in before), (context, before, after)


def click_here(page, locator):
    # Locator.click() performs its own scroll before clicking, which would
    # confound the measured UI movement. Click where the user sees the control.
    box=locator.bounding_box()
    x,y=box['x']+box['width']/2,box['y']+box['height']/2
    assert 0 <= y <= page.viewport_size['height'],box
    page.mouse.click(x,y)


def scanner(page):
    page.evaluate("""async () => {
        await app._v78Open('manual');
        app._ingredientCatalog=Array.from({length:3293},(_,i)=>({
            key:'item-'+i,ingredientId:'item-'+i,name:'Ingredient '+String(i).padStart(4,'0'),
            presentationVersion:63,displayLanguage:'el'
        }));
        app._v78IngredientOptions();
    }""")
    assert page.locator('[data-v114-link]').count() == 3293
    first=page.locator('.v114-link-list label:has-text("Ingredient 1500") input')
    first.scroll_into_view_if_needed()
    before=page.evaluate(READ)
    assert before['list'] > 1000
    first.check()
    unchanged(before, page.evaluate(READ), 'first assignment')
    assert first.evaluate('(n)=>n.getRootNode().activeElement===n')
    # An adjacent ingredient stays available, and Space can undo its selection.
    second=page.locator('.v114-link-list label:has-text("Ingredient 1501") input')
    click_here(page,second)
    assert second.is_checked()
    unchanged(before, page.evaluate(READ), 'second assignment')
    page.keyboard.press('Space')
    assert not second.is_checked() and first.is_checked()
    unchanged(before, page.evaluate(READ), 'keyboard deselection')
    assert page.evaluate('app._v114Links().length') == 1

    # Native disclosures at the bottom must neither reset the dialog nor list.
    summary=page.locator('.v78-capture details').last.locator('summary')
    summary.scroll_into_view_if_needed()
    before=page.evaluate(READ)
    click_here(page,summary)
    page.wait_for_timeout(80)
    unchanged(before, page.evaluate(READ), 'open section')
    assert summary.evaluate('(n)=>n.parentElement.open')
    page.evaluate('app._v78RenderCapture()')
    page.wait_for_timeout(80)
    unchanged(before, page.evaluate(READ), 'existing form refresh')
    assert page.locator('.v78-capture details').last.evaluate('(n)=>n.open')
    assert first.is_checked()

    # A delayed product/price refresh must preserve an actively edited field.
    search=page.locator('[data-v78-search]')
    search.fill('Ingredient 15')
    before=page.evaluate(READ)
    page.evaluate('app._v78RenderCapture()')
    page.wait_for_timeout(80)
    unchanged(before, page.evaluate(READ), 'search field refresh')
    assert search.input_value() == 'Ingredient 15'
    assert search.evaluate('(n)=>n.getRootNode().activeElement===n')
    search.fill('')

    # A queued layout correction must yield to a subsequent user scroll.
    page.evaluate("""() => {
        app._v78RenderCapture();
        app._v78Dialog.dispatchEvent(new WheelEvent('wheel',{bubbles:true,composed:true}));
        app._v78Dialog.scrollTop+=35;
    }""")
    before=page.evaluate(READ)
    page.wait_for_timeout(80)
    unchanged(before,page.evaluate(READ),'user scroll supersedes pending restoration')

    # The suggestions list has its own scroll owner and selection controls.
    page.evaluate("""() => {
        app._v78Draft.suggestions=app._ingredientCatalog.slice(0,90).map(ingredient=>({ingredient,reason:'name'}));
        app._v78IngredientOptions();
    }""")
    suggestion=page.locator('[data-v194-index="60"]')
    suggestion.scroll_into_view_if_needed()
    before=page.evaluate(READ)
    click_here(page,suggestion)
    unchanged(before, page.evaluate(READ), 'suggestion assignment')
    assert suggestion.get_attribute('aria-pressed') == 'true'

    # Validation is a deliberate destination; preserving the view must not
    # suppress error disclosure or focusing the invalid field.
    page.evaluate("app._v196Issue({field:'quantity',message:'quantity'})")
    page.wait_for_timeout(100)
    assert page.locator('main [data-draft="quantity"]').get_attribute('aria-invalid') == 'true'
    assert page.locator('main [data-draft="quantity"]').evaluate('(n)=>n.getRootNode().activeElement===n')
    page.evaluate('app._v78Dirty=false;app._v78Close()')


def page_views(page):
    page.evaluate("app.show('profile')")
    page.wait_for_timeout(80)
    page.evaluate("""() => {
        scrollOwner.scrollTop=Math.min(220,scrollOwner.scrollHeight-scrollOwner.clientHeight);
    }""")
    page.wait_for_timeout(80)
    before=page.evaluate(READ)
    assert before['page'] > 20, before
    page.evaluate('app._renderTab()')
    page.wait_for_timeout(80)
    unchanged(before, page.evaluate(READ), 'stock tab refresh')

    # Network completion captures the current place, not where work started.
    page.evaluate("""() => {
        setTimeout(()=>app._renderTab(),60);
        scrollOwner.scrollTop+=40;
    }""")
    before=page.evaluate(READ)
    page.wait_for_timeout(100)
    unchanged(before, page.evaluate(READ), 'late refresh after user scroll')

    page.evaluate("app._selectV52Tab('today')")
    page.wait_for_timeout(80)
    page.evaluate("app._selectV52Tab('profile')")
    page.wait_for_timeout(80)
    unchanged(before, page.evaluate(READ), 'return to stock tab')

    # Profile sections, recipe details and weekly folds use the same policy.
    inventory=page.locator('#houseInventoryRows').locator('xpath=ancestor::details[1]').locator(':scope > summary')
    inventory.scroll_into_view_if_needed()
    before=page.evaluate(READ)
    click_here(page,inventory)
    page.wait_for_timeout(80)
    unchanged(before, page.evaluate(READ), 'stock disclosure')
    page.evaluate('app._renderTab()')
    page.wait_for_timeout(80)
    unchanged(before, page.evaluate(READ), 'stock disclosure refresh')
    assert inventory.evaluate('(n)=>n.parentElement.open')

    page.evaluate("app.show('week')")
    page.wait_for_timeout(80)
    fold=page.locator('[data-v179-fold-button="summary"]')
    fold.scroll_into_view_if_needed()
    before=page.evaluate(READ)
    click_here(page,fold)
    page.wait_for_timeout(80)
    unchanged(before, page.evaluate(READ), 'weekly disclosure')
    assert fold.get_attribute('aria-expanded') == 'true'


def run():
    html=local_html(ROOT)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
        for width,height in ((390,844),(1440,980)):
            for host_scroll in (False,True):
                page=browser.new_page(viewport={'width':width,'height':height})
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.set_default_timeout(6000)
                page.set_content(html)
                page.wait_for_function('window.ready')
                page.evaluate("""hostScroll => {
                    if(hostScroll){
                        const host=document.createElement('div');
                        host.attachShadow({mode:'open'}).innerHTML='<div style="height:100vh;overflow:auto"></div>';
                        document.body.append(host);
                        window.scrollOwner=host.shadowRoot.firstElementChild;
                        scrollOwner.append(app);
                    }else window.scrollOwner=document.scrollingElement;
                    app.show('profile');
                }""",host_scroll)
                scanner(page)
                page_views(page)
                assert not errors,errors
                print(f'PASS {width} / {"HA shadow host" if host_scroll else "document"}: assignment, focus, disclosures, refresh, navigation, validation',flush=True)
                page.close()
        browser.close()


if __name__ == '__main__':
    run()
