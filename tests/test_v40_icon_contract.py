from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V40 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v40.js"
PANEL = ROOT / "custom_components" / "cook4me" / "panel.py"
MANIFEST = ROOT / "custom_components" / "cook4me" / "manifest.json"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v40_normalizes_today_actions_to_one_modernizer_icon():
    text = _text(V40)
    assert 'import "./cook4me-panel-v39.js"' in text
    assert '_normalizeTodayActionIcon(button,icon' in text
    assert 'String(child.tagName||"").toUpperCase()==="HA-ICON"' in text
    assert 'button.dataset.rxIcon=icon' in text
    assert 'this._normalizeTodayActionIcon(suggest,"chef-hat")' in text
    assert 'this._normalizeTodayActionIcon(reset,"backup-restore",{iconOnly:true})' in text
    assert '_modernizeButtons(root)' in text
    assert 'super._modernizeButtons(root)' in text
    assert 'queueMicrotask(()=>this._normalizeTodayActionButtons(c))' in text


def test_v40_is_active_and_versioned():
    panel = _text(PANEL)
    manifest = _text(MANIFEST)
    assert 'cook4me-recipe-hub-panel-v40' in panel
    assert 'cook4me-panel-v40.js' in panel
    assert '?v=2026.9.7.19' in panel
    assert '"version": "2026.9.7.19"' in manifest
