"""Real navigation CSS/handlers in the current frontend; HA/API use v203 fixtures."""
from pathlib import Path
import re
import shutil

from playwright.sync_api import sync_playwright
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ('today', 'week', 'official', 'book', 'mine', 'shopping', 'profile')
GEOMETRY = """button => {
 const strip = button.closest('#tabs'), b = button.getBoundingClientRect();
 const p = strip.getBoundingClientRect(), s = getComputedStyle(button);
 const top = p.top + strip.clientTop;
 const outset = button.matches(':focus-visible')
   ? Math.max(0, parseFloat(s.outlineWidth) + parseFloat(s.outlineOffset)) : 0;
 return {top:b.top, bottom:b.bottom, width:b.width, height:b.height,
   clipped:b.top-outset < top-0.1 || b.bottom+outset > top+strip.clientHeight+0.1,
   transform:s.transform, outline:s.outlineWidth, offset:s.outlineOffset,
   focused:button.matches(':focus-visible'), selected:button.getAttribute('aria-pressed'),
   verticalOverflow:strip.scrollHeight-strip.clientHeight,
   transition:s.transitionDuration};
}"""


def run():
    panel = (ROOT/'custom_components/cook4me/panel.py').read_text()
    active = re.search(r'_PANEL_ELEMENT = "([^"]+)"', panel)[1]
    assert int(re.search(r'runtime-v(\d+)$', active)[1]) >= 205, active
    html = local_html(ROOT)
    # Exercise the actual delivered constructor, not an older compatibility alias.
    html, count = re.subn(
        r"const Base=customElements.get\('cook4me-recipe-hub-panel-v180-runtime-v\d+'\);",
        f"const Base=customElements.get('{active}');", html)
    assert count == 1, 'The frontend fixture no longer exposes its constructor'
    scenarios = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium') or None,
                                    args=['--no-sandbox'])
        for width, height in ((390, 844), (844, 390), (1749, 800)):
            for light in (False, True):
                for motion in ('no-preference', 'reduce'):
                    page = browser.new_page(viewport={'width':width, 'height':height},
                                            reduced_motion=motion)
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.set_default_timeout(5000)
                    page.set_content(html)
                    page.wait_for_function('window.ready')
                    page.evaluate('(light)=>{document.body.classList.toggle("light", light); app._hass.themes.darkMode=!light; app.show("today");}', light)
                    page.wait_for_timeout(100)
                    assert page.locator('#tabs .tab').count() == len(VIEWS)
                    for key in VIEWS:
                        button = page.locator(f'#tabs .tab[data-tab="{key}"]')
                        button.scroll_into_view_if_needed()
                        page.mouse.move(0, 0)
                        page.wait_for_timeout(180)
                        before = button.evaluate(GEOMETRY)
                        button.hover()
                        page.wait_for_timeout(180)
                        hovered = button.evaluate(GEOMETRY)
                        assert not hovered['clipped'], (width, light, motion, key, hovered)
                        assert hovered['transform'] == 'none', (key, hovered)
                        for dim in ('top', 'bottom', 'width', 'height'):
                            assert abs(before[dim]-hovered[dim]) < .1, (key, dim, before, hovered)
                        assert hovered['selected'] == ('true' if key == 'today' else 'false')
                        assert hovered['verticalOverflow'] <= 1, (key, hovered)
                        # Keyboard modality plus a real focus event; no synthetic
                        # class masquerading as the browser's focus-visible state.
                        page.keyboard.press('Tab')
                        button.focus()
                        focused = button.evaluate(GEOMETRY)
                        assert focused['focused'] and not focused['clipped'], (key, focused)
                        assert float(focused['outline'].removesuffix('px')) >= 2
                        assert focused['offset'] == '-3px', focused
                        if motion == 'reduce':
                            assert all(float(v.strip().removesuffix('s')) == 0
                                       for v in focused['transition'].split(','))
                        scenarios += 1
                    # Overflow must remain horizontally scrollable on narrow screens.
                    if width == 390:
                        strip = page.locator('#tabs')
                        assert strip.evaluate('(n)=>n.scrollWidth>n.clientWidth && getComputedStyle(n).overflowX==="auto"')
                        assert strip.evaluate('(n)=>{n.scrollLeft=n.scrollWidth;return n.scrollLeft>0}')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    page.evaluate('window.originalTabs=[...app.shadowRoot.querySelectorAll("#tabs .tab")];app._ui203Page();app._ui203Page();')
                    assert page.evaluate('originalTabs.every((n,i)=>n===app.shadowRoot.querySelectorAll("#tabs .tab")[i])')
                    # Original click handler changes view; hover never does.
                    page.locator('#tabs [data-tab=week]').click()
                    page.wait_for_function('app._tab === "week"')
                    page.locator('#tabs [data-tab=today]').click()
                    page.wait_for_function('app._tab === "today"')
                    assert page.locator('#v180Styles').count() == 1
                    assert not errors, errors
                    print(f'PASS: {width}x{height}, {"light" if light else "dark"}, {motion}: seven hover/focus states, stable geometry, original navigation', flush=True)
                    page.close()
        browser.close()
    print(f'PASS: {scenarios} navigation hover/focus scenarios in the current frontend chain')


if __name__ == '__main__':
    run()
