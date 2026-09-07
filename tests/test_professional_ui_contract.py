from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v32.js"
PANEL = ROOT / "custom_components" / "cook4me" / "panel.py"
MANIFEST = ROOT / "custom_components" / "cook4me" / "manifest.json"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_professional_ui_visual_language_contract():
    text = _text(JS)
    assert 'COUNTRY_BY_LANGUAGE' in text
    assert 'MEAL_VISUALS' in text
    assert 'rx-language-choice' in text
    assert 'rx-meal-choice' in text
    assert 'rx-nutrition-chip' in text
    assert 'details.rx-advanced' in text
    assert 'rx-plan-summary' in text
    assert 'ha-icon icon="mdi:' in text


def test_background_job_cards_and_cancellation_contract():
    text = _text(JS)
    assert 'cook4meJobStack' in text
    assert 'rx-job-card' in text
    assert '_processStart(title,detail="",options={})' in text
    assert 'token.cancelled=true' in text
    assert 'jobCancelRequested' in text
    assert '_hydrateVisibleNutrition(items)' in text
    assert 'while(cursor<rows.length&&!job.cancelled)' in text
    for name in (
        '_loadIngredientCatalog',
        '_loadNutritionSettings',
        '_loadTodayOptions',
        '_loadBookState',
        '_ensureScanCatalog',
        '_handleBarcode',
        '_openLocal',
        '_selectRecipeLanguage',
        '_selectServing',
    ):
        assert name in text


def test_v32_is_active_and_versioned():
    panel = _text(PANEL)
    manifest = _text(MANIFEST)
    assert 'cook4me-recipe-hub-panel-v32' in panel
    assert 'cook4me-panel-v32.js' in panel
    assert '?v=2026.9.7.11' in panel
    assert '"version": "2026.9.7.11"' in manifest
