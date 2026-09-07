from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V39 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v39.js"
PANEL = ROOT / "custom_components" / "cook4me" / "panel.py"
MANIFEST = ROOT / "custom_components" / "cook4me" / "manifest.json"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v39_contains_refresh_to_one_fixed_icon_box():
    text = _text(V39)
    assert 'refresh.replaceChildren(icon)' in text
    assert '#refresh.rx-v38-refresh{' in text
    assert 'max-width:40px!important' in text
    assert 'max-height:40px!important' in text
    assert 'overflow:hidden!important' in text
    assert 'line-height:0!important' in text


def test_v39_today_controls_wrap_without_content_escape():
    text = _text(V39)
    assert 'grid-template-columns:repeat(auto-fit,minmax(180px,1fr))!important' in text
    assert '.rx-today-row>*{box-sizing:border-box!important;min-width:0!important;max-width:100%!important}' in text
    assert 'grid-template-columns:auto minmax(0,1fr) auto!important' in text
    assert 'text-overflow:ellipsis!important' in text
    assert '.rx-today-actions{' in text
    assert 'grid-column:span 2!important' in text
    assert '.rx-today-actions .btn>span{' in text
    assert '.rx-today-actions .btn>ha-icon{' in text
    assert '@media(max-width:720px)' in text
    assert '.rx-today-actions{grid-column:1/-1!important}' in text


def test_v39_is_active_and_versioned():
    panel = _text(PANEL)
    manifest = _text(MANIFEST)
    assert 'cook4me-recipe-hub-panel-v39' in panel
    assert 'cook4me-panel-v39.js' in panel
    assert '?v=2026.9.7.18' in panel
    assert '"version": "2026.9.7.18"' in manifest
