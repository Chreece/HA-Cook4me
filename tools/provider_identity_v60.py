#!/usr/bin/env python3
"""Provider-identity contract shared by Cook4Me v60 release tooling.

The SEB provider key itself is authoritative.  No provider namespace prefix is
invented or inferred: a provider-backed ingredient is valid only when an
explicit provider key exists and the persisted ingredient identity equals that
key exactly.  ``local:`` remains reserved for reviewed source-local identity.
"""
from __future__ import annotations

import re
from typing import Any


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def provider_key(row: dict[str, Any]) -> str:
    """Return explicit provider identity evidence without inferring from labels."""
    return _text(
        row.get("key")
        or row.get("foodKey")
        or row.get("providerIngredientId")
        or row.get("providerFoodKey")
    )


def preserved_provider_identity(row: dict[str, Any], identity: Any = "") -> bool:
    """True only when the exact explicit provider key is the persisted identity."""
    key = provider_key(row)
    ident = _text(
        identity
        or row.get("id")
        or row.get("ingredientId")
        or row.get("key")
        or row.get("foodKey")
    )
    return bool(key and ident and ident == key and not ident.startswith("local:"))
