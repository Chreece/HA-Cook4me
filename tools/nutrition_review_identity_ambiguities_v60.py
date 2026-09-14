"""Additional fail-closed nutrition identity ambiguities for the v60 review queue."""
from __future__ import annotations

import re

GENERIC_SEAFOOD = re.compile(r"^seafood$", re.IGNORECASE)
GENERIC_STARCH = re.compile(r"^starch$", re.IGNORECASE)

RULES = (
    ("C-generic-seafood-identity-ambiguous", GENERIC_SEAFOOD),
    ("C-generic-starch-identity-ambiguous", GENERIC_STARCH),
)
