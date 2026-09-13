from __future__ import annotations

"""Common official SEB recipe-detail path used by the active Recipe Hub.

Keep SEB-provided nutrition evidence separate from Cook4Me's calculated meal
nutrition. Flat SEB nutrient quantities with no stated basis remain evidence,
not inputs for recipe totals.
"""

from typing import Any

from .vendor.cook4me_recipe_detail_enriched import recipe_detail as _recipe_detail


def recipe_detail(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    variant_id: str,
    *,
    country: str = "DE",
    language: str = "de",
    configured_language: str | None = None,
    app_version: str = "36.0.0-RC3",
    pcfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _recipe_detail(
        cfg,
        tokens,
        variant_id,
        country=country,
        language=language,
        configured_language=configured_language,
        app_version=app_version,
        pcfg=pcfg,
    )
