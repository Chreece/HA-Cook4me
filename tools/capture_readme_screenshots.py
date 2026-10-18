#!/usr/bin/env python3
"""Capture the real Cook4Me UI with synthetic fixture data only.

No real Home Assistant, cooker, external photo service, household stock,
credentials, camera or cloud endpoint is accessed.
"""
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
import shutil
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from ui_offline_loader_v203 import local_html

OUT = ROOT / ".github" / "assets" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

def save(page, name, selector=None):
    raw = (page.locator(selector).screenshot(animations="disabled", timeout=15000)
           if selector else page.screenshot(animations="disabled"))
    with Image.open(BytesIO(raw)) as im:
        im.convert("RGB").save(OUT / (name + ".webp"), "WEBP", quality=83, method=6)
    file = OUT / (name + ".webp")
    print(f"SCREENSHOT {file.relative_to(ROOT)} {file.stat().st_size} bytes", flush=True)

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which("chromium") or None,
                              args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1440,"height":900},
                          reduced_motion="reduce",color_scheme="dark")
    errors=[]
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.set_default_timeout(12000)
    page.set_content(local_html(ROOT))
    page.wait_for_function("window.ready")

    page.evaluate("app.show('official')")
    page.wait_for_timeout(200)
    save(page,"recipes-discover")

    page.evaluate("app.show('week')")
    page.wait_for_timeout(200)
    save(page,"weekly-meal-planner")

    page.evaluate("app.show('today')")
    page.locator("[data-v66-photo]").first.click()
    page.wait_for_function("app._v63RecipeDialog?.isConnected")
    page.wait_for_timeout(170)
    save(page,"recipe-details")
    page.locator("[data-modal-close]").click()

    page.evaluate("app.show('profile')")
    page.wait_for_timeout(140)
    page.evaluate("""() => {
      const extra=[
       {key:'salt',name:'Αλάτι',unlimited:true},
       {key:'yogurt',name:'Γιαούρτι',unit:'g',quantity:400,lots:[
         {id:'demo-yogurt',productName:'Γιαούρτι φυσικό',quantity:400,
          storageLocationId:'fridge',bestBefore:'2026-11-15'}]}
      ];
      app._houseIngredients.push(...extra);
      app._entry().profile.houseIngredients=app._houseIngredients;
      app._v78State.houseIngredients=app._houseIngredients;
      app._renderTab();
      const stock=app.shadowRoot.querySelector('#houseInventoryRows');
      for(let parent=stock?.parentElement;parent;parent=parent.parentElement)
       if(parent.tagName==='DETAILS')parent.open=true;
      const pane=app.shadowRoot.querySelector('[data-v78-section="stock"]');
      if(pane)pane.hidden=false;
    }""")
    page.wait_for_timeout(150)
    save(page,"kitchen-stock",'[data-v78-section="stock"]')

    today=date.today()
    items=[
      {"lotId":"demo-yogurt","identity":"k:yogurt","productName":"Γιαούρτι φυσικό",
       "ingredientName":"Γιαούρτι","quantity":400,"unit":"g",
       "bestBefore":(today+timedelta(days=3)).isoformat(),
       "effectiveBestBefore":(today+timedelta(days=3)).isoformat(),
       "daysRemaining":3,"storageName":"Ψυγείο"},
      {"lotId":"lot-rice","identity":"k:rice","productName":"Ρύζι μπασμάτι",
       "ingredientName":"Ρύζι","quantity":500,"unit":"g",
       "bestBefore":(today+timedelta(days=6)).isoformat(),
       "effectiveBestBefore":(today+timedelta(days=6)).isoformat(),
       "daysRemaining":6,"storageName":"Ντουλάπι"},
    ]
    page.evaluate("""items=>{
      app._v142StockSummary={...app._v142StockSummary,expiring:items};
      app._v142PaintStockSummary();
    }""",items)
    page.wait_for_timeout(100)
    save(page,"expiring-products","[data-v142-expiry]")

    page.evaluate("app._v78Open('manual')")
    page.wait_for_function('app._v78Dialog?.querySelector("[data-v196-save]")')
    page.wait_for_timeout(100)
    save(page,"product-editor")
    page.evaluate("app._v78Close(true)")
    if errors:
        raise RuntimeError("Browser JavaScript errors: " + " | ".join(errors[:5]))
    browser.close()
print("README_SCREENSHOTS=PASS",flush=True)
