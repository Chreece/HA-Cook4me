"""Exercise real dialog renderers, scrolling, and original action bindings offline."""
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = """() => {
 app._v72Draft={enabled:true,recipe:true,steps:true,state:true,connection:true,players:['media_player.kitchen'],tts:'tts.fixture',language:'el',voice:'voice-1',ai:'ai_task.vision'};
 app._v72Data={settings:structuredClone(app._v72Draft),choices:{players:Array.from({length:12},(_,i)=>({id:i?'media_player.room_'+i:'media_player.kitchen',name:i?'Δωμάτιο '+i:'Κουζίνα',announce:true})),tts:[{id:'tts.fixture',name:'Εκφώνηση ανακοινώσεων',languages:['el','de','en'],voices:{el:[{id:'voice-1',name:'Ελληνική φωνή'}]}}],ai:[{id:'ai_task.vision',name:'AI Task'}]}};
 const original=app._api.bind(app);
 app._api=(type,data={})=>{
  if(type.endsWith('/device_settings')){app.calls.push({type,data:structuredClone(data)});return Promise.resolve(structuredClone(app._v72Data));}
  if(type.endsWith('/ingredient_info'))return Promise.resolve({ingredientInfoContract:'offline-ingredient-info-v62',ingredient:{name:'Ρύζι'},stock:{quantity:1200,unit:'g',lots:Array.from({length:20},(_,i)=>({quantity:60,unit:'g',productName:'Συσκευασία '+i}))}});
  return original(type,data);
 };
 app._v72RenderSettings();
}"""


def layout(page, selector):
    dialog = page.locator(selector)
    page.wait_for_timeout(100)
    result = dialog.evaluate("""d => {
      const body=d.querySelector('.ui234-dialog-body'),footer=d.querySelector('.ui234-dialog-footer'),header=d.querySelector('.ui234-dialog-header');
      const box=d.getBoundingClientRect(),f=footer?.getBoundingClientRect(),b=body.getBoundingClientRect(),h=header.getBoundingClientRect();
      return {inside:box.left>=0&&box.right<=innerWidth+1&&box.top>=0&&box.bottom<=innerHeight+1,
        docked:Math.abs(box.bottom-(f?.bottom??b.bottom))<=2,
        separate:b.bottom<=(f?.top??box.bottom)+1&&b.top>=h.bottom-1,
        fits:d.scrollWidth<=d.clientWidth+1&&body.scrollWidth<=body.clientWidth+1,
        cardDoesNotScroll:d.scrollHeight<=d.clientHeight+1,
        footer:f?.top??box.bottom,header:h.top};
    }""")
    for key in ['inside', 'docked', 'separate', 'fits', 'cardDoesNotScroll']:
        if not result[key]:
            page.screenshot(path='/tmp/cook4me-dialog-failure.png')
        assert result[key], (selector, key, result)
    dialog.locator('.ui234-dialog-body').evaluate('(b)=>b.scrollTop=b.scrollHeight')
    after = dialog.evaluate("""d => ({footer:d.querySelector('.ui234-dialog-footer')?.getBoundingClientRect().top??d.getBoundingClientRect().bottom,header:d.querySelector('.ui234-dialog-header').getBoundingClientRect().top})""")
    assert abs(result['footer'] - after['footer']) < 1, (selector, 'footer moved')
    assert abs(result['header'] - after['header']) < 1, (selector, 'header moved')


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
    html = local_html(ROOT)
    for width, height in [(360, 800), (390, 844), (680, 700), (844, 390), (1440, 1000)]:
        page = browser.new_page(viewport={'width': width, 'height': height}, reduced_motion='reduce')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_default_timeout(5000)
        page.set_content(html)
        page.wait_for_function('window.ready')
        page.evaluate(SETTINGS)
        page.wait_for_timeout(100)
        announcement = '[data-device-settings] .rx-dialog'
        layout(page, announcement)
        # Expanding speakers and re-rendering language choices must retain docking.
        page.locator('.v72-players > summary').click()
        layout(page, announcement)
        page.locator('[data-setting=language]').select_option('de')
        layout(page, announcement)
        page.locator('[data-setting=connection]').uncheck()
        page.locator('[data-v72-test]').click()
        page.wait_for_function("app.calls.some(c=>c.type.endsWith('/announcement_test'))")
        page.locator('[data-v72-save]').click()
        page.wait_for_function("app.calls.filter(c=>c.type.endsWith('/device_settings')).length===2")
        assert page.evaluate("app.calls.filter(c=>c.type.endsWith('/device_settings')).every(c=>c.data.settings.language==='de'&&c.data.settings.connection===false)")
        # Keyboard focus can reach the last form field without scrolling the footer.
        page.locator('[data-setting=ai]').focus()
        layout(page, announcement)
        page.locator('[data-v72-close]').focus()
        page.keyboard.press('Shift+Tab')
        assert page.evaluate("app.shadowRoot.activeElement.hasAttribute('data-v72-save')")
        page.keyboard.press('Tab')
        assert page.evaluate("app.shadowRoot.activeElement.hasAttribute('data-v72-close')")
        page.locator('[data-v72-close]').click()

        # All filter variants, including the household source picker and dynamic
        # selected-first lists, use the same layout without losing their listeners.
        for key in ['languages', 'meals', 'home', 'nutrition', 'cost', 'diet', 'dietProfile', 'ingredients']:
            page.evaluate('(key)=>app._showFilter(key)', key)
            selector = '[data-filter-dialog] .rx-dialog'
            layout(page, selector)
            if key in ['languages', 'meals', 'ingredients']:
                boxes = page.locator('[data-filter-dialog] input[data-list]')
                boxes.last.check()
                layout(page, selector)
                assert page.evaluate("(()=>{const d=app.shadowRoot.querySelector('[data-filter-dialog]'),a=[...d.querySelectorAll('input[data-list]')];return a.slice(0,a.filter(n=>n.checked).length).every(n=>n.checked)&&a.every(n=>!!n.closest('.ui234-dialog-body'))})()")
            if key == 'cost':
                page.locator('[data-field=maxCost]').fill('7')
            page.locator('[data-filter-dialog] [data-apply]').click()
            assert page.locator('[data-filter-dialog]').count() == 0
            if key == 'cost':
                assert float(page.evaluate('app._filters().maxCost')) == 7

        # Long history editors cover the intermediate tablet grid as well as the
        # smallest phone. Adding a usage must extend only the scrolling area.
        page.evaluate("""() => {app._v131OpenHistoryEditor({id:'meal-fixture',title:'Δοκιμή γεύματος',servings:2,allocations:[{name:'Household',servings:2}],ingredients:Array.from({length:12},()=>({identity:'k:rice',name:'Ρύζι',quantity:50,unit:'g'}))});}""")
        history = '.v131-history-dialog'
        layout(page, history)
        count = page.locator('[data-v131-history-usage]').count()
        page.locator('[data-v131-add-usage]').click()
        assert page.locator('[data-v131-history-usage]').count() == count + 1
        layout(page, history)
        page.locator('[data-v131-remove-usage]').last.click()
        page.locator('[data-v131-save-history]').click()
        page.wait_for_function("app.calls.some(c=>c.type.endsWith('/history_update'))")
        assert page.locator(history).count() == 0

        # Package weighing has its own native dialog and original Apply/Cancel
        # handlers. Its buttons must stay visible in a short landscape viewport.
        page.evaluate("""async () => {app._v116Scale=structuredClone(app._fixtureScale);await app._v154OpenWeigh(app._houseIngredients[0],'lot-rice');}""")
        layout(page, 'dialog.v154-weigh')
        page.locator('dialog.v154-weigh [data-container]').select_option('jar-1')
        page.locator('dialog.v154-weigh [data-deduct]').check()
        page.locator('dialog.v154-weigh .ui234-dialog-footer [data-close]').click()
        assert page.locator('dialog.v154-weigh').count() == 0

        # Read-only dialogs have no bottom action bar, but their close controls
        # must also remain accessible while long content scrolls.
        page.evaluate('app._v81OpenInfo()')
        layout(page, 'dialog.v81-device-info')
        page.locator('[data-v81-close]').click()
        page.evaluate("app._showIngredientInfo({key:'rice',name:'Ρύζι'})")
        layout(page, '[data-ingredient-dialog] .rx-dialog')
        page.locator('[data-ingredient-dialog] [data-close]').click()
        page.evaluate("""async () => {
          const receipt={id:'layout-receipt',merchant:'Supermarket',processing:{state:'ready'},items:Array.from({length:20},(_,i)=>({id:'line-'+i,status:'pending',productName:'Ρύζι '+i,quantity:500,unit:'g',lineTotal:2}))};
          await app._r232Open(receipt);app._r232Rows=[{...receipt,pendingCount:20}];app._r232Paint();
        }""")
        layout(page, 'dialog.r232-dialog')
        page.locator('[data-r232-close]').click()
        assert not page.locator('dialog.r232-dialog').is_visible()

        # Theme and rotation must recompute the card without extra JS measuring.
        page.evaluate("app._v72RenderSettings();document.body.classList.add('light')")
        layout(page, announcement)
        page.set_viewport_size({'width': height, 'height': width})
        layout(page, announcement)
        page.set_viewport_size({'width': width, 'height': height})
        page.evaluate("document.body.classList.remove('light')")
        page.locator(announcement+' .ui234-dialog-body').evaluate('(b)=>b.scrollTop=0')
        page.screenshot(path=f'/tmp/cook4me-dialog-{width}.png')
        assert not errors, errors
        print(f'PASS {width}x{height}: announcements, eight filters, meal history, weighing, device/ingredient details, receipts, keyboard, theme and rotation')
        page.close()
    browser.close()
