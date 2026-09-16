#!/usr/bin/env python3
"""Compile reviewed keyless Cook4Me labels into conservative semantic concepts.

Provider identity, source-local identity, and semantic concept identity remain
separate. High-confidence reviewed rows may merge automatically only by exact
reviewed English + classification. Medium-confidence rows stay source-local
unless an exact, explicitly recorded confirmation approves a merge.

Two confirmation lanes exist:
1. exact reviewed-English confirmations with an explicit target concept ID;
2. explicitly whitelisted syntactic normalizations for exact source-local IDs.

Neither lane assigns or infers an M_FOOD provider key.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
BASE_REVIEW = TOOLS / "release_catalog_reviewed_keyless_ingredients.v1.json"
CONFIRMATION_FILE = TOOLS / "release_catalog_semantic_confirmations.v1.json"
SYNTAX_CONFIRMATION_FILE = (
    TOOLS / "release_catalog_semantic_syntactic_confirmation_ids.v1.txt"
)

_ALLOWED_CLASSIFICATIONS = {"food", "equipment", "other", "ambiguous"}
_MERGEABLE_CLASSIFICATIONS = {"food", "equipment", "other"}
_CONFIRMATION_KIND = "cook4me-semantic-ingredient-confirmations"
_CONFIRMATION_POLICY = {
    "providerIdentityAssigned": False,
    "exactReviewedEnglishAndClassificationOnly": True,
    "sourceLocalIdentityPreserved": True,
    "manualConfirmationRequired": True,
}
_SECTION_PREFIX = re.compile(r"^[A-C]\s*[-–—:]\s*", re.IGNORECASE)
_MALFORMED_QUANTITY_PREFIX = re.compile(r"^/\d+(?:[.,]\d+)?\s+")
_REVIEW_ONLY_ANNOTATION = re.compile(
    r"\s*\((source (?:spelling|grammar|wording))\)\s*$",
    re.IGNORECASE,
)
_SOURCE_TYPO_ONLY = re.compile(
    r"\s*\(source typo\)\s*$",
    re.IGNORECASE,
)
_QUALIFIED_SOURCE_TYPO = re.compile(
    r"\s*\(([^()]*)\s*;\s*source typo\)\s*$",
    re.IGNORECASE,
)
_QUANTITY_ONLY_ANNOTATION = re.compile(
    r"\s*\(quantity fragment:\s*[^()]+\)\s*$",
    re.IGNORECASE,
)
_QUALIFIED_QUANTITY_ANNOTATION = re.compile(
    r"\s*\(([^()]*)\s*;\s*quantity fragment:\s*[^()]+\)\s*$",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        unicodedata.normalize("NFKC", _text(value)),
    ).casefold()


def _structural_punctuation_key(value: Any) -> str:
    """Case-insensitive text key that removes punctuation but preserves letters.

    This is deliberately narrower than fuzzy or accent-folded matching. It is
    used only inside the explicit source-ID syntactic-confirmation lane.
    """
    text = unicodedata.normalize("NFKC", _text(value)).casefold()
    out: list[str] = []
    pending_space = False
    for char in text:
        if char.isalnum():
            if pending_space and out:
                out.append(" ")
            out.append(char)
            pending_space = False
        else:
            pending_space = True
    return "".join(out).strip()


def _sha_text(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def source_local_ingredient_id(language: str, source: str) -> str:
    """Return the exact source-local ID used by assembly-prep v2."""
    language = _text(language).lower()
    source = _text(source)
    return (
        "local:"
        + language
        + ":"
        + _sha_text(
            "cook4me-local-ingredient-v2",
            language,
            _norm(source),
        )[:20]
    )


def _semantic_concept_id(classification: str, english: str) -> str:
    return (
        "concept:"
        + classification
        + ":"
        + _sha_text(
            "cook4me-semantic-ingredient-v1",
            classification,
            _norm(english),
        )[:20]
    )


def _source_concept_id(language: str, source: str) -> str:
    return (
        "concept:source:"
        + _sha_text(
            "cook4me-source-ingredient-concept-v1",
            source_local_ingredient_id(language, source),
        )[:20]
    )


def _review_paths(tools_dir: Path = TOOLS) -> list[Path]:
    extras = sorted(
        path
        for path in tools_dir.glob(
            "release_catalog_reviewed_keyless_ingredients_*.v1.json"
        )
        if path.name != BASE_REVIEW.name
    )
    base = tools_dir / BASE_REVIEW.name
    return ([base] if base.exists() else []) + extras


def _load_payload(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    if value.get("kind") != "cook4me-reviewed-keyless-ingredient-semantics":
        raise RuntimeError(f"{path}: unexpected review kind")
    return value


def _load_confirmation_payload(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    if value.get("schemaVersion") != 1:
        raise RuntimeError(f"{path}: unsupported confirmation schemaVersion")
    if value.get("kind") != _CONFIRMATION_KIND:
        raise RuntimeError(f"{path}: unexpected confirmation kind")
    policy = value.get("policy")
    if not isinstance(policy, dict) or any(
        policy.get(key) is not expected
        for key, expected in _CONFIRMATION_POLICY.items()
    ):
        raise RuntimeError(f"{path}: unsafe semantic confirmation policy")
    items = value.get("items")
    if not isinstance(items, list):
        raise RuntimeError(f"{path}: confirmation items must be a list")
    return value


def _load_syntax_confirmation_ids(path: Path) -> set[str]:
    seen: set[str] = set()
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        if not value.startswith("local:") or any(char.isspace() for char in value):
            raise RuntimeError(
                f"{path}: line {line_number}: invalid source-local identity"
            )
        if value in seen:
            raise RuntimeError(
                f"{path}: line {line_number}: duplicate source-local identity"
            )
        seen.add(value)
    if not seen:
        raise RuntimeError(f"{path}: no syntactic confirmation identities")
    return seen


def iter_review_rows(
    payloads: Iterable[tuple[str, dict[str, Any]]]
) -> Iterable[dict[str, Any]]:
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for review_file, payload in payloads:
        for raw in payload.get("items") or []:
            if not isinstance(raw, dict):
                continue
            language = _text(raw.get("language")).lower()
            source = _text(raw.get("source"))
            english = _text(raw.get("english"))
            classification = _text(raw.get("classification")).lower()
            confidence = _text(raw.get("confidence")).lower() or "reviewed"
            if (
                not language
                or not source
                or not english
                or classification not in _ALLOWED_CLASSIFICATIONS
            ):
                continue

            row = {
                "language": language,
                "source": source,
                "english": english,
                "classification": classification,
                "confidence": confidence,
                "reviewFile": review_file,
            }
            if notes := _text(raw.get("notes")):
                row["notes"] = notes

            key = (language, _norm(source))
            previous = seen.get(key)
            if previous is not None:
                if (
                    _norm(previous["english"]) != _norm(english)
                    or previous["classification"] != classification
                ):
                    raise RuntimeError(
                        "conflicting reviewed semantics for "
                        f"{language}/{source}: "
                        f"{previous['english']!r}/{previous['classification']} vs "
                        f"{english!r}/{classification}"
                    )
                continue
            seen[key] = row
            yield row


def _rows_by_source_id(
    review_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in review_rows:
        source_id = source_local_ingredient_id(row["language"], row["source"])
        if source_id in out:
            raise RuntimeError(f"duplicate source-local identity: {source_id}")
        out[source_id] = row
    return out


def _high_confidence_concepts(
    review_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    concepts: dict[str, dict[str, Any]] = {}
    for row in review_rows:
        if (
            row["confidence"] != "high"
            or row["classification"] not in _MERGEABLE_CLASSIFICATIONS
        ):
            continue
        concept_id = _semantic_concept_id(row["classification"], row["english"])
        previous = concepts.get(concept_id)
        if previous is not None and (
            previous["classification"] != row["classification"]
            or _norm(previous["english"]) != _norm(row["english"])
        ):
            raise RuntimeError(
                f"high-confidence semantic collision for {concept_id}"
            )
        concepts.setdefault(concept_id, row)
    return concepts


def _exact_confirmation_map(
    review_rows: list[dict[str, Any]],
    confirmation_payload: dict[str, Any] | None,
    *,
    confirmation_file: str = "",
) -> dict[str, dict[str, str]]:
    if confirmation_payload is None:
        return {}

    if confirmation_payload.get("schemaVersion") != 1:
        raise RuntimeError("unsupported confirmation schemaVersion")
    if confirmation_payload.get("kind") != _CONFIRMATION_KIND:
        raise RuntimeError("unexpected confirmation kind")
    policy = confirmation_payload.get("policy")
    if not isinstance(policy, dict) or any(
        policy.get(key) is not expected
        for key, expected in _CONFIRMATION_POLICY.items()
    ):
        raise RuntimeError("unsafe semantic confirmation policy")
    items = confirmation_payload.get("items")
    if not isinstance(items, list):
        raise RuntimeError("confirmation items must be a list")

    rows_by_source_id = _rows_by_source_id(review_rows)
    high_concepts = _high_confidence_concepts(review_rows)
    out: dict[str, dict[str, str]] = {}
    for index, raw in enumerate(items, 1):
        if not isinstance(raw, dict):
            raise RuntimeError(f"confirmation item {index}: expected object")
        source_id = _text(raw.get("sourceIngredientId"))
        concept_id = _text(raw.get("confirmedConceptId"))
        if not source_id.startswith("local:") or not concept_id.startswith(
            "concept:"
        ):
            raise RuntimeError(f"confirmation item {index}: invalid identity")
        if source_id in out:
            raise RuntimeError(
                f"duplicate semantic confirmation for {source_id}"
            )

        source_row = rows_by_source_id.get(source_id)
        if source_row is None:
            raise RuntimeError(
                "semantic confirmation source is not a reviewed identity: "
                f"{source_id}"
            )
        if source_row["confidence"] == "high":
            raise RuntimeError(
                "semantic confirmation is redundant for high-confidence source: "
                f"{source_id}"
            )
        if source_row["classification"] not in _MERGEABLE_CLASSIFICATIONS:
            raise RuntimeError(
                "semantic confirmation cannot merge classification "
                f"{source_row['classification']!r}: {source_id}"
            )

        expected_concept = _semantic_concept_id(
            source_row["classification"], source_row["english"]
        )
        if concept_id != expected_concept:
            raise RuntimeError(
                "semantic confirmation does not preserve exact reviewed "
                f"English/classification for {source_id}: "
                f"{concept_id} != {expected_concept}"
            )

        target_row = high_concepts.get(concept_id)
        if target_row is None:
            raise RuntimeError(
                "semantic confirmation target lacks high-confidence evidence: "
                f"{concept_id}"
            )
        if (
            target_row["classification"] != source_row["classification"]
            or _norm(target_row["english"]) != _norm(source_row["english"])
        ):
            raise RuntimeError(
                f"semantic confirmation target meaning differs for {source_id}"
            )

        out[source_id] = {
            "confirmedConceptId": concept_id,
            "confirmationFile": confirmation_file or "<inline>",
            "confirmationMethod": "explicit-reviewed-english-classification",
        }
    return out


def _safe_syntactic_english(value: str) -> str:
    """Normalize only review syntax; never rewrite food semantics.

    This helper is never an automatic approval mechanism. It is called only for
    source IDs present in the explicit syntactic-confirmation whitelist.
    """
    text = _text(value)
    while True:
        before = text
        text = _SECTION_PREFIX.sub("", text, count=1).strip()
        text = _MALFORMED_QUANTITY_PREFIX.sub("", text, count=1).strip()
        text = _REVIEW_ONLY_ANNOTATION.sub("", text, count=1).strip()
        source_typo = _QUALIFIED_SOURCE_TYPO.search(text)
        if source_typo:
            qualifier = _text(source_typo.group(1))
            text = (
                text[: source_typo.start()]
                + (f" ({qualifier})" if qualifier else "")
                + text[source_typo.end() :]
            ).strip()
        else:
            text = _SOURCE_TYPO_ONLY.sub("", text, count=1).strip()
        text = _QUANTITY_ONLY_ANNOTATION.sub("", text, count=1).strip()
        match = _QUALIFIED_QUANTITY_ANNOTATION.search(text)
        if match:
            qualifier = _text(match.group(1))
            if qualifier:
                text = (
                    text[: match.start()]
                    + f" ({qualifier})"
                    + text[match.end() :]
                ).strip()
        if text == before:
            return text


def _syntactic_confirmation_map(
    review_rows: list[dict[str, Any]],
    source_ids: set[str] | None,
    *,
    confirmation_file: str = "",
) -> dict[str, dict[str, str]]:
    if not source_ids:
        return {}

    rows_by_source_id = _rows_by_source_id(review_rows)
    high_concepts = _high_confidence_concepts(review_rows)
    out: dict[str, dict[str, str]] = {}

    for source_id in sorted(source_ids):
        source_row = rows_by_source_id.get(source_id)
        if source_row is None:
            raise RuntimeError(
                "syntactic confirmation source is not a reviewed identity: "
                f"{source_id}"
            )
        if source_row["confidence"] == "high":
            raise RuntimeError(
                "syntactic confirmation is redundant for high-confidence source: "
                f"{source_id}"
            )
        if source_row["classification"] not in _MERGEABLE_CLASSIFICATIONS:
            raise RuntimeError(
                "syntactic confirmation cannot merge classification "
                f"{source_row['classification']!r}: {source_id}"
            )

        normalized_english = _safe_syntactic_english(source_row["english"])
        if not normalized_english:
            raise RuntimeError(
                "syntactic confirmation produced empty reviewed English: "
                f"{source_id}"
            )

        concept_id = _semantic_concept_id(
            source_row["classification"], normalized_english
        )
        target_row = high_concepts.get(concept_id)

        if target_row is None:
            # Explicitly whitelisted section/header labels may differ from the
            # reviewed target only by structural punctuation or case. Require one
            # and only one high-confidence concept in the same classification.
            punctuation_key = _structural_punctuation_key(normalized_english)
            matches = [
                (candidate_id, candidate)
                for candidate_id, candidate in high_concepts.items()
                if candidate["classification"] == source_row["classification"]
                and _structural_punctuation_key(candidate["english"])
                == punctuation_key
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    "syntactic confirmation lacks a unique punctuation-only "
                    f"high-confidence target: {source_id} -> {normalized_english!r} "
                    f"matches={len(matches)}"
                )
            concept_id, target_row = matches[0]
        elif _norm(normalized_english) == _norm(source_row["english"]):
            raise RuntimeError(
                "syntactic confirmation does not remove approved syntax noise: "
                f"{source_id}"
            )

        if target_row["classification"] != source_row["classification"]:
            raise RuntimeError(
                f"syntactic confirmation target classification differs for {source_id}"
            )

        target_exact = _norm(target_row["english"]) == _norm(normalized_english)
        target_punctuation_only = (
            _structural_punctuation_key(target_row["english"])
            == _structural_punctuation_key(normalized_english)
        )
        if not target_exact and not target_punctuation_only:
            raise RuntimeError(
                f"syntactic confirmation target meaning differs for {source_id}"
            )

        out[source_id] = {
            "confirmedConceptId": concept_id,
            "confirmationFile": confirmation_file or "<inline-syntax>",
            "confirmationMethod": "explicit-reviewed-syntactic-normalization",
        }
    return out


def _confirmation_map(
    review_rows: list[dict[str, Any]],
    confirmation_payload: dict[str, Any] | None,
    *,
    confirmation_file: str = "",
    syntax_confirmation_ids: set[str] | None = None,
    syntax_confirmation_file: str = "",
) -> tuple[dict[str, dict[str, str]], int, int]:
    exact = _exact_confirmation_map(
        review_rows,
        confirmation_payload,
        confirmation_file=confirmation_file,
    )
    syntactic = _syntactic_confirmation_map(
        review_rows,
        syntax_confirmation_ids,
        confirmation_file=syntax_confirmation_file,
    )
    overlap = set(exact) & set(syntactic)
    if overlap:
        raise RuntimeError(
            "same source identity appears in exact and syntactic confirmations: "
            + ", ".join(sorted(overlap))
        )
    return {**exact, **syntactic}, len(exact), len(syntactic)


def compile_semantic_concepts(
    payloads: Iterable[tuple[str, dict[str, Any]]],
    *,
    confirmation_payload: dict[str, Any] | None = None,
    confirmation_file: str = "",
    syntax_confirmation_ids: set[str] | None = None,
    syntax_confirmation_file: str = "",
) -> dict[str, Any]:
    """Compile review rows without promoting semantic equality to provider ID."""
    concepts: dict[str, dict[str, Any]] = {}
    source_identity_to_concept: dict[str, str] = {}
    review_rows = list(iter_review_rows(payloads))
    high_concepts = _high_confidence_concepts(review_rows)
    confirmations, exact_count, syntactic_count = _confirmation_map(
        review_rows,
        confirmation_payload,
        confirmation_file=confirmation_file,
        syntax_confirmation_ids=syntax_confirmation_ids,
        syntax_confirmation_file=syntax_confirmation_file,
    )

    for row in review_rows:
        language = row["language"]
        source = row["source"]
        english = row["english"]
        classification = row["classification"]
        confidence = row["confidence"]
        source_id = source_local_ingredient_id(language, source)
        confirmation = confirmations.get(source_id)

        mergeable = (
            confidence == "high"
            and classification in _MERGEABLE_CLASSIFICATIONS
        )
        explicitly_confirmed = confirmation is not None
        if explicitly_confirmed:
            concept_id = confirmation["confirmedConceptId"]
            canonical_english = high_concepts[concept_id]["english"]
        elif mergeable:
            concept_id = _semantic_concept_id(classification, english)
            canonical_english = english
        else:
            concept_id = _source_concept_id(language, source)
            canonical_english = english

        concept_mergeable = mergeable or explicitly_confirmed
        merge_policy = (
            "reviewed-high-exact-english"
            if concept_mergeable
            else "source-local-conservative"
        )

        concept = concepts.setdefault(
            concept_id,
            {
                "conceptId": concept_id,
                "canonicalEnglish": canonical_english,
                "classification": classification,
                "mergePolicy": merge_policy,
                "providerIdentityAssigned": False,
                "nutritionEligible": classification == "food",
                "dietEligible": classification == "food",
                "allergenEligible": classification == "food",
                "needsSemanticConfirmation": not concept_mergeable,
                "aliases": {},
                "sourceIdentities": [],
            },
        )
        if (
            concept["classification"] != classification
            or _norm(concept["canonicalEnglish"]) != _norm(canonical_english)
        ):
            raise RuntimeError(
                f"semantic concept collision for {concept_id}: "
                f"{concept['canonicalEnglish']!r}/{concept['classification']} vs "
                f"{canonical_english!r}/{classification}"
            )

        aliases: dict[str, list[str]] = concept["aliases"]
        aliases.setdefault(language, [])
        if source not in aliases[language]:
            aliases[language].append(source)
        aliases.setdefault("en", [])
        for english_alias in (canonical_english, english):
            if english_alias not in aliases["en"]:
                aliases["en"].append(english_alias)

        identity = {
            "ingredientId": source_id,
            "language": language,
            "source": source,
            "confidence": confidence,
            "reviewFile": row["reviewFile"],
            "providerIdentityAssigned": False,
        }
        if notes := row.get("notes"):
            identity["notes"] = notes
        if confirmation is not None:
            identity["semanticConfirmationFile"] = confirmation[
                "confirmationFile"
            ]
            identity["semanticConfirmationMethod"] = confirmation[
                "confirmationMethod"
            ]
        concept["sourceIdentities"].append(identity)
        source_identity_to_concept[source_id] = concept_id

    for concept in concepts.values():
        concept["aliases"] = {
            language: sorted(set(values), key=lambda value: _norm(value))
            for language, values in sorted(concept["aliases"].items())
        }
        concept["sourceIdentities"].sort(
            key=lambda row: (
                row["language"],
                _norm(row["source"]),
                row["ingredientId"],
            )
        )

    ordered = sorted(
        concepts.values(),
        key=lambda row: (
            row["classification"],
            _norm(row["canonicalEnglish"]),
            row["conceptId"],
        ),
    )
    classification_counts: dict[str, int] = defaultdict(int)
    confidence_counts: dict[str, int] = defaultdict(int)
    for row in review_rows:
        classification_counts[row["classification"]] += 1
        confidence_counts[row["confidence"]] += 1

    needs_confirmation_sources = sum(
        len(row["sourceIdentities"])
        for row in ordered
        if row.get("needsSemanticConfirmation") is True
    )
    return {
        "schemaVersion": 1,
        "kind": "cook4me-semantic-ingredient-concepts",
        "identityPolicy": {
            "providerIdentityAssigned": False,
            "sourceLocalIdentityPreserved": True,
            "highConfidenceExactEnglishMerge": True,
            "explicitSemanticConfirmationMerge": True,
            "explicitSyntacticConfirmationMerge": True,
            "mediumConfidenceCrossLanguageMerge": False,
            "mediumConfidenceAutomaticCrossLanguageMerge": False,
            "ambiguousCrossLanguageMerge": False,
            "providerKeyInference": False,
        },
        "summary": {
            "reviewedSourceLabels": len(review_rows),
            "semanticConcepts": len(ordered),
            "crossLanguageConcepts": sum(
                len({item["language"] for item in row["sourceIdentities"]}) > 1
                for row in ordered
            ),
            "confirmedSourceLabels": len(confirmations),
            "exactConfirmedSourceLabels": exact_count,
            "syntacticConfirmedSourceLabels": syntactic_count,
            "needsSemanticConfirmationSourceLabels": (
                needs_confirmation_sources
            ),
            "classificationCounts": dict(
                sorted(classification_counts.items())
            ),
            "confidenceCounts": dict(sorted(confidence_counts.items())),
        },
        "sourceIdentityToConcept": dict(
            sorted(source_identity_to_concept.items())
        ),
        "concepts": ordered,
    }


def compile_from_paths(
    paths: Iterable[Path],
    *,
    confirmation_path: Path | None = None,
    syntax_confirmation_path: Path | None = None,
) -> dict[str, Any]:
    path_list = list(paths)
    payloads = [(path.name, _load_payload(path)) for path in path_list]

    review_dir: Path | None = None
    if path_list:
        parents = {path.parent.resolve() for path in path_list}
        if len(parents) == 1:
            review_dir = next(iter(parents))

    if confirmation_path is None and review_dir is not None:
        candidate = review_dir / CONFIRMATION_FILE.name
        if candidate.exists():
            confirmation_path = candidate

    if syntax_confirmation_path is None and review_dir is not None:
        candidate = review_dir / SYNTAX_CONFIRMATION_FILE.name
        if candidate.exists():
            syntax_confirmation_path = candidate

    confirmation_payload = None
    confirmation_file = ""
    if confirmation_path is not None:
        confirmation_payload = _load_confirmation_payload(confirmation_path)
        confirmation_file = confirmation_path.name

    syntax_confirmation_ids: set[str] | None = None
    syntax_confirmation_file = ""
    if syntax_confirmation_path is not None:
        syntax_confirmation_ids = _load_syntax_confirmation_ids(
            syntax_confirmation_path
        )
        syntax_confirmation_file = syntax_confirmation_path.name

    return compile_semantic_concepts(
        payloads,
        confirmation_payload=confirmation_payload,
        confirmation_file=confirmation_file,
        syntax_confirmation_ids=syntax_confirmation_ids,
        syntax_confirmation_file=syntax_confirmation_file,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=str(TOOLS / "release_catalog_semantic_ingredients_v60.json"),
    )
    parser.add_argument(
        "--reviews-dir",
        default=str(TOOLS),
        help="Directory containing reviewed keyless ingredient files",
    )
    parser.add_argument(
        "--confirmations",
        default="",
        help=(
            "Optional exact semantic confirmation JSON. When omitted, "
            "release_catalog_semantic_confirmations.v1.json is loaded from "
            "the reviews directory when present."
        ),
    )
    parser.add_argument(
        "--syntax-confirmations",
        default="",
        help=(
            "Optional source-ID whitelist for reviewed syntactic "
            "normalizations. When omitted, "
            "release_catalog_semantic_syntactic_confirmation_ids.v1.txt is "
            "loaded from the reviews directory when present."
        ),
    )
    args = parser.parse_args()

    review_dir = Path(args.reviews_dir).expanduser()
    paths = _review_paths(review_dir)
    if not paths:
        raise SystemExit(f"no reviewed keyless ingredient files in {review_dir}")

    confirmation_path = (
        Path(args.confirmations).expanduser() if args.confirmations else None
    )
    syntax_confirmation_path = (
        Path(args.syntax_confirmations).expanduser()
        if args.syntax_confirmations
        else None
    )
    payload = compile_from_paths(
        paths,
        confirmation_path=confirmation_path,
        syntax_confirmation_path=syntax_confirmation_path,
    )
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                **payload["summary"],
                "output": str(output),
                "reviewFiles": len(paths),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
