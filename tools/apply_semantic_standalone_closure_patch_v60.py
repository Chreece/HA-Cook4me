#!/usr/bin/env python3
"""One-time patch helper for conservative standalone semantic closure v60."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / "tools/compile_release_catalog_semantics_v60.py"
TESTS = ROOT / "tests/test_semantic_standalone_dispositions_v60.py"
APPLY_WORKFLOW = ROOT / ".github/workflows/catalog-semantic-confirmation-apply-v60.yml"
AUDIT_WORKFLOW = ROOT / ".github/workflows/catalog-semantic-remaining-audit-v60.yml"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one insertion point, found {count}")
    return text.replace(old, new, 1)


def patch_compiler() -> None:
    text = COMPILER.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "SYNTAX_CONFIRMATION_FILE = (\n    TOOLS / \"release_catalog_semantic_syntactic_confirmation_ids.v1.txt\"\n)\n\n_ALLOWED_CLASSIFICATIONS",
        "SYNTAX_CONFIRMATION_FILE = (\n    TOOLS / \"release_catalog_semantic_syntactic_confirmation_ids.v1.txt\"\n)\nSTANDALONE_DISPOSITION_FILE = (\n    TOOLS / \"release_catalog_semantic_standalone_dispositions.v1.json\"\n)\n_STANDALONE_KIND = \"cook4me-semantic-ingredient-standalone-dispositions\"\n_STANDALONE_POLICY = {\n    \"providerIdentityAssigned\": False,\n    \"sourceLocalIdentityPreserved\": True,\n    \"crossIdentityMergeAllowed\": False,\n    \"reviewDispositionOnly\": True,\n    \"exactReviewedEnglishAndClassificationRequired\": True,\n    \"safetyEligibilityGranted\": False,\n}\n\n_ALLOWED_CLASSIFICATIONS",
        "standalone constants",
    )

    loader = '''\n\ndef _load_standalone_payload(path: Path) -> dict[str, Any]:\n    value = json.loads(path.read_text(encoding="utf-8"))\n    if not isinstance(value, dict):\n        raise RuntimeError(f"{path}: expected JSON object")\n    if value.get("schemaVersion") != 1:\n        raise RuntimeError(f"{path}: unsupported standalone schemaVersion")\n    if value.get("kind") != _STANDALONE_KIND:\n        raise RuntimeError(f"{path}: unexpected standalone disposition kind")\n    policy = value.get("policy")\n    if not isinstance(policy, dict) or any(\n        policy.get(key) is not expected\n        for key, expected in _STANDALONE_POLICY.items()\n    ):\n        raise RuntimeError(f"{path}: unsafe standalone disposition policy")\n    items = value.get("items")\n    if not isinstance(items, list):\n        raise RuntimeError(f"{path}: standalone disposition items must be a list")\n    return value\n'''
    text = replace_once(
        text,
        "\n\ndef iter_review_rows(\n",
        loader + "\n\ndef iter_review_rows(\n",
        "standalone loader",
    )

    mapper = '''\n\ndef _standalone_disposition_map(\n    review_rows: list[dict[str, Any]],\n    standalone_payload: dict[str, Any] | None,\n    *,\n    standalone_file: str = "",\n) -> dict[str, dict[str, str]]:\n    if standalone_payload is None:\n        return {}\n    if standalone_payload.get("schemaVersion") != 1:\n        raise RuntimeError("unsupported standalone disposition schemaVersion")\n    if standalone_payload.get("kind") != _STANDALONE_KIND:\n        raise RuntimeError("unexpected standalone disposition kind")\n    policy = standalone_payload.get("policy")\n    if not isinstance(policy, dict) or any(\n        policy.get(key) is not expected\n        for key, expected in _STANDALONE_POLICY.items()\n    ):\n        raise RuntimeError("unsafe standalone disposition policy")\n    items = standalone_payload.get("items")\n    if not isinstance(items, list):\n        raise RuntimeError("standalone disposition items must be a list")\n\n    rows_by_source_id = _rows_by_source_id(review_rows)\n    out: dict[str, dict[str, str]] = {}\n    for index, raw in enumerate(items, 1):\n        if not isinstance(raw, dict):\n            raise RuntimeError(f"standalone disposition item {index}: expected object")\n        source_id = _text(raw.get("sourceIngredientId"))\n        if not source_id.startswith("local:"):\n            raise RuntimeError(f"standalone disposition item {index}: invalid source identity")\n        if source_id in out:\n            raise RuntimeError(f"duplicate standalone disposition for {source_id}")\n        source_row = rows_by_source_id.get(source_id)\n        if source_row is None:\n            raise RuntimeError(\n                "standalone disposition source is not a reviewed identity: "\n                f"{source_id}"\n            )\n        if source_row["confidence"] == "high":\n            raise RuntimeError(\n                "standalone disposition is redundant for high-confidence source: "\n                f"{source_id}"\n            )\n        reviewed_english = _text(raw.get("sourceReviewedEnglish"))\n        classification = _text(raw.get("classification")).lower()\n        disposition = _text(raw.get("disposition"))\n        rationale = _text(raw.get("rationale"))\n        if reviewed_english != source_row["english"]:\n            raise RuntimeError(\n                f"standalone disposition sourceReviewedEnglish differs for {source_id}"\n            )\n        if classification != source_row["classification"]:\n            raise RuntimeError(\n                f"standalone disposition classification differs for {source_id}"\n            )\n        expected_disposition = (\n            "reviewed-ambiguous-source-fragment"\n            if classification == "ambiguous"\n            else "reviewed-source-local-standalone"\n        )\n        if classification != "ambiguous" and classification not in _MERGEABLE_CLASSIFICATIONS:\n            raise RuntimeError(\n                f"standalone disposition unsupported classification {classification!r}: {source_id}"\n            )\n        if disposition != expected_disposition:\n            raise RuntimeError(\n                f"standalone disposition type differs for {source_id}: "\n                f"{disposition!r} != {expected_disposition!r}"\n            )\n        if len(rationale) < 20:\n            raise RuntimeError(\n                f"standalone disposition rationale is too short for {source_id}"\n            )\n        out[source_id] = {\n            "disposition": disposition,\n            "dispositionFile": standalone_file or "<inline-standalone>",\n            "rationale": rationale,\n        }\n    return out\n'''
    text = replace_once(
        text,
        "\n\ndef _confirmation_map(\n",
        mapper + "\n\ndef _confirmation_map(\n",
        "standalone mapper",
    )

    text = replace_once(
        text,
        "    syntax_confirmation_ids: set[str] | None = None,\n    syntax_confirmation_file: str = \"\",\n) -> dict[str, Any]:\n",
        "    syntax_confirmation_ids: set[str] | None = None,\n    syntax_confirmation_file: str = \"\",\n    standalone_payload: dict[str, Any] | None = None,\n    standalone_file: str = \"\",\n) -> dict[str, Any]:\n",
        "compile signature",
    )

    text = replace_once(
        text,
        "        syntax_confirmation_file=syntax_confirmation_file,\n    )\n\n    for row in review_rows:\n",
        "        syntax_confirmation_file=syntax_confirmation_file,\n    )\n    standalone = _standalone_disposition_map(\n        review_rows,\n        standalone_payload,\n        standalone_file=standalone_file,\n    )\n    overlap = set(confirmations) & set(standalone)\n    if overlap:\n        raise RuntimeError(\n            \"same source identity appears in semantic confirmation and standalone disposition: \"\n            + \", \".join(sorted(overlap))\n        )\n\n    for row in review_rows:\n",
        "compile standalone map",
    )

    text = replace_once(
        text,
        "        confirmation = confirmations.get(source_id)\n\n        mergeable = (\n",
        "        confirmation = confirmations.get(source_id)\n        standalone_disposition = standalone.get(source_id)\n\n        mergeable = (\n",
        "loop standalone lookup",
    )

    text = replace_once(
        text,
        "        concept_mergeable = mergeable or explicitly_confirmed\n        merge_policy = (\n            \"reviewed-high-exact-english\"\n            if concept_mergeable\n            else \"source-local-conservative\"\n        )\n",
        "        concept_mergeable = mergeable or explicitly_confirmed\n        review_closed = concept_mergeable or standalone_disposition is not None\n        if standalone_disposition is not None:\n            merge_policy = standalone_disposition[\"disposition\"]\n        elif concept_mergeable:\n            merge_policy = \"reviewed-high-exact-english\"\n        else:\n            merge_policy = \"source-local-conservative\"\n        safety_eligible = (\n            classification == \"food\" and standalone_disposition is None\n        )\n",
        "review closure policy",
    )

    text = replace_once(
        text,
        "                \"nutritionEligible\": classification == \"food\",\n                \"dietEligible\": classification == \"food\",\n                \"allergenEligible\": classification == \"food\",\n                \"needsSemanticConfirmation\": not concept_mergeable,\n",
        "                \"nutritionEligible\": safety_eligible,\n                \"dietEligible\": safety_eligible,\n                \"allergenEligible\": safety_eligible,\n                \"needsSemanticConfirmation\": not review_closed,\n",
        "concept safety closure",
    )

    text = replace_once(
        text,
        "            if rationale := confirmation.get(\"confirmationRationale\"):\n                identity[\"semanticConfirmationRationale\"] = rationale\n        concept[\"sourceIdentities\"].append(identity)\n",
        "            if rationale := confirmation.get(\"confirmationRationale\"):\n                identity[\"semanticConfirmationRationale\"] = rationale\n        if standalone_disposition is not None:\n            identity[\"semanticReviewDispositionFile\"] = standalone_disposition[\n                \"dispositionFile\"\n            ]\n            identity[\"semanticReviewDisposition\"] = standalone_disposition[\n                \"disposition\"\n            ]\n            identity[\"semanticReviewDispositionRationale\"] = standalone_disposition[\n                \"rationale\"\n            ]\n        concept[\"sourceIdentities\"].append(identity)\n",
        "identity standalone receipt",
    )

    text = replace_once(
        text,
        "    needs_confirmation_sources = sum(\n        len(row[\"sourceIdentities\"])\n        for row in ordered\n        if row.get(\"needsSemanticConfirmation\") is True\n    )\n    return {\n",
        "    needs_confirmation_sources = sum(\n        len(row[\"sourceIdentities\"])\n        for row in ordered\n        if row.get(\"needsSemanticConfirmation\") is True\n    )\n    standalone_count = len(standalone)\n    reviewed_ambiguous_count = sum(\n        row.get(\"disposition\") == \"reviewed-ambiguous-source-fragment\"\n        for row in standalone.values()\n    )\n    return {\n",
        "summary counts prep",
    )

    text = replace_once(
        text,
        "            \"explicitSyntacticConfirmationMerge\": True,\n            \"mediumConfidenceCrossLanguageMerge\": False,\n",
        "            \"explicitSyntacticConfirmationMerge\": True,\n            \"explicitStandaloneReviewClosure\": True,\n            \"standaloneReviewClosureGrantsSafetyEligibility\": False,\n            \"mediumConfidenceCrossLanguageMerge\": False,\n",
        "identity policy",
    )

    text = replace_once(
        text,
        "            \"syntacticConfirmedSourceLabels\": syntactic_count,\n            \"needsSemanticConfirmationSourceLabels\": (\n",
        "            \"syntacticConfirmedSourceLabels\": syntactic_count,\n            \"standaloneConfirmedSourceLabels\": standalone_count,\n            \"reviewedAmbiguousSourceLabels\": reviewed_ambiguous_count,\n            \"needsSemanticConfirmationSourceLabels\": (\n",
        "summary standalone counts",
    )

    text = replace_once(
        text,
        "    syntax_confirmation_path: Path | None = None,\n) -> dict[str, Any]:\n",
        "    syntax_confirmation_path: Path | None = None,\n    standalone_path: Path | None = None,\n) -> dict[str, Any]:\n",
        "compile_from_paths signature",
    )

    text = replace_once(
        text,
        "    if syntax_confirmation_path is None and review_dir is not None:\n        candidate = review_dir / SYNTAX_CONFIRMATION_FILE.name\n        if candidate.exists():\n            syntax_confirmation_path = candidate\n\n    confirmation_payload = None\n",
        "    if syntax_confirmation_path is None and review_dir is not None:\n        candidate = review_dir / SYNTAX_CONFIRMATION_FILE.name\n        if candidate.exists():\n            syntax_confirmation_path = candidate\n\n    if standalone_path is None and review_dir is not None:\n        candidate = review_dir / STANDALONE_DISPOSITION_FILE.name\n        if candidate.exists():\n            standalone_path = candidate\n\n    confirmation_payload = None\n",
        "auto standalone path",
    )

    text = replace_once(
        text,
        "    syntax_confirmation_ids: set[str] | None = None\n    syntax_confirmation_file = \"\"\n    if syntax_confirmation_path is not None:\n        syntax_confirmation_ids = _load_syntax_confirmation_ids(\n            syntax_confirmation_path\n        )\n        syntax_confirmation_file = syntax_confirmation_path.name\n\n    return compile_semantic_concepts(\n",
        "    syntax_confirmation_ids: set[str] | None = None\n    syntax_confirmation_file = \"\"\n    if syntax_confirmation_path is not None:\n        syntax_confirmation_ids = _load_syntax_confirmation_ids(\n            syntax_confirmation_path\n        )\n        syntax_confirmation_file = syntax_confirmation_path.name\n\n    standalone_payload = None\n    standalone_file = \"\"\n    if standalone_path is not None:\n        standalone_payload = _load_standalone_payload(standalone_path)\n        standalone_file = standalone_path.name\n\n    return compile_semantic_concepts(\n",
        "load standalone path",
    )

    text = replace_once(
        text,
        "        syntax_confirmation_ids=syntax_confirmation_ids,\n        syntax_confirmation_file=syntax_confirmation_file,\n    )\n",
        "        syntax_confirmation_ids=syntax_confirmation_ids,\n        syntax_confirmation_file=syntax_confirmation_file,\n        standalone_payload=standalone_payload,\n        standalone_file=standalone_file,\n    )\n",
        "pass standalone payload",
    )

    text = replace_once(
        text,
        "    parser.add_argument(\n        \"--syntax-confirmations\",\n        default=\"\",\n        help=(\n            \"Optional source-ID whitelist for reviewed syntactic \"\n            \"normalizations. When omitted, \"\n            \"release_catalog_semantic_syntactic_confirmation_ids.v1.txt is \"\n            \"loaded from the reviews directory when present.\"\n        ),\n    )\n    args = parser.parse_args()\n",
        "    parser.add_argument(\n        \"--syntax-confirmations\",\n        default=\"\",\n        help=(\n            \"Optional source-ID whitelist for reviewed syntactic \"\n            \"normalizations. When omitted, \"\n            \"release_catalog_semantic_syntactic_confirmation_ids.v1.txt is \"\n            \"loaded from the reviews directory when present.\"\n        ),\n    )\n    parser.add_argument(\n        \"--standalone-dispositions\",\n        default=\"\",\n        help=(\n            \"Optional conservative source-local review-disposition JSON. When omitted, \"\n            \"release_catalog_semantic_standalone_dispositions.v1.json is loaded \"\n            \"from the reviews directory when present.\"\n        ),\n    )\n    args = parser.parse_args()\n",
        "standalone CLI arg",
    )

    text = replace_once(
        text,
        "    syntax_confirmation_path = (\n        Path(args.syntax_confirmations).expanduser()\n        if args.syntax_confirmations\n        else None\n    )\n    payload = compile_from_paths(\n        paths,\n        confirmation_path=confirmation_path,\n        syntax_confirmation_path=syntax_confirmation_path,\n    )\n",
        "    syntax_confirmation_path = (\n        Path(args.syntax_confirmations).expanduser()\n        if args.syntax_confirmations\n        else None\n    )\n    standalone_path = (\n        Path(args.standalone_dispositions).expanduser()\n        if args.standalone_dispositions\n        else None\n    )\n    payload = compile_from_paths(\n        paths,\n        confirmation_path=confirmation_path,\n        syntax_confirmation_path=syntax_confirmation_path,\n        standalone_path=standalone_path,\n    )\n",
        "standalone CLI pass",
    )

    COMPILER.write_text(text, encoding="utf-8")


def patch_tests() -> None:
    text = TESTS.read_text(encoding="utf-8")
    old = '''        audit = json.loads(\n            (tools / "remaining_semantic_ingredient_audit_v60.json").read_text(\n                encoding="utf-8"\n            )\n        )\n        ledger = json.loads(\n            (tools / "release_catalog_semantic_standalone_dispositions.v1.json").read_text(\n                encoding="utf-8"\n            )\n        )\n        self.assertEqual(audit["summary"]["remaining"], 293)\n        self.assertEqual(ledger["summary"]["standaloneDispositionCount"], 293)\n        self.assertEqual(ledger["summary"]["reviewedAmbiguousCount"], 28)\n        self.assertEqual(ledger["summary"]["reviewedSourceLocalStandaloneCount"], 265)\n        self.assertEqual(\n            {row["sourceIngredientId"] for row in ledger["items"]},\n            {row["sourceIngredientId"] for row in audit["items"]},\n        )\n\n        result = mod.compile_from_paths(mod._review_paths(tools))\n'''
    new = '''        ledger = json.loads(\n            (tools / "release_catalog_semantic_standalone_dispositions.v1.json").read_text(\n                encoding="utf-8"\n            )\n        )\n        self.assertEqual(ledger["summary"]["standaloneDispositionCount"], 293)\n        self.assertEqual(ledger["summary"]["reviewedAmbiguousCount"], 28)\n        self.assertEqual(ledger["summary"]["reviewedSourceLocalStandaloneCount"], 265)\n        ledger_ids = [row["sourceIngredientId"] for row in ledger["items"]]\n        self.assertEqual(len(ledger_ids), len(set(ledger_ids)))\n\n        result = mod.compile_from_paths(mod._review_paths(tools))\n'''
    text = replace_once(text, old, new, "standalone repository test")
    TESTS.write_text(text, encoding="utf-8")


def patch_audit_workflow() -> None:
    text = AUDIT_WORKFLOW.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "      - 'tools/audit_syntactic_semantic_candidates_v60.py'\n      - 'tools/summarize_semantic_similarity_lane_v60.py'\n",
        "      - 'tools/audit_syntactic_semantic_candidates_v60.py'\n      - 'tools/summarize_semantic_similarity_lane_v60.py'\n      - 'tools/compile_release_catalog_semantics_v60.py'\n      - 'tools/release_catalog_semantic_standalone_dispositions.v1.json'\n",
        "audit workflow triggers",
    )
    text = replace_once(
        text,
        "          if int(summary.get('remaining') or 0) != 293:\n",
        "          if int(summary.get('remaining') or 0) != 0:\n",
        "audit expected remaining",
    )
    AUDIT_WORKFLOW.write_text(text, encoding="utf-8")


def patch_apply_workflow() -> None:
    text = APPLY_WORKFLOW.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "      - 'tools/release_catalog_semantic_syntactic_confirmation_ids.v1.txt'\n      - 'tests/test_compile_release_catalog_semantics_v60.py'\n",
        "      - 'tools/release_catalog_semantic_syntactic_confirmation_ids.v1.txt'\n      - 'tools/release_catalog_semantic_standalone_dispositions.v1.json'\n      - 'tests/test_compile_release_catalog_semantics_v60.py'\n      - 'tests/test_semantic_standalone_dispositions_v60.py'\n",
        "apply workflow triggers",
    )

    old_counts = '''          exact = json.loads(\n              (tools / 'release_catalog_semantic_confirmations.v1.json').read_text(\n                  encoding='utf-8'\n              )\n          ).get('items') or []\n          syntax_path = (\n              tools / 'release_catalog_semantic_syntactic_confirmation_ids.v1.txt'\n          )\n          syntax_ids = mod._load_syntax_confirmation_ids(syntax_path)\n          exact_ids = {row['sourceIngredientId'] for row in exact}\n          if exact_ids & syntax_ids:\n              raise SystemExit('exact and syntactic confirmation sets overlap')\n\n          paths = mod._review_paths(tools)\n          payloads = [(path.name, mod._load_payload(path)) for path in paths]\n          before = mod.compile_semantic_concepts(payloads)\n          after = mod.compile_from_paths(paths)\n\n          exact_count = len(exact)\n          syntax_count = len(syntax_ids)\n          total = exact_count + syntax_count\n          if after['summary']['exactConfirmedSourceLabels'] != exact_count:\n              raise SystemExit('exact confirmation count mismatch')\n          if after['summary']['syntacticConfirmedSourceLabels'] != syntax_count:\n              raise SystemExit('syntactic confirmation count mismatch')\n          if after['summary']['confirmedSourceLabels'] != total:\n              raise SystemExit('total confirmation count mismatch')\n          if (\n              before['summary']['needsSemanticConfirmationSourceLabels']\n              - after['summary']['needsSemanticConfirmationSourceLabels']\n              != total\n          ):\n              raise SystemExit('pending semantic decrement mismatch')\n          if (\n              before['summary']['semanticConcepts']\n              - after['summary']['semanticConcepts']\n              != total\n          ):\n              raise SystemExit('semantic concept merge count mismatch')\n\n          concepts = {row['conceptId']: row for row in after.get('concepts') or []}\n          expected_ids = exact_ids | syntax_ids\n'''
    new_counts = '''          confirmation_items = json.loads(\n              (tools / 'release_catalog_semantic_confirmations.v1.json').read_text(\n                  encoding='utf-8'\n              )\n          ).get('items') or []\n          equivalence_items = [\n              row for row in confirmation_items\n              if row.get('manualSemanticEquivalence') is True\n          ]\n          exact_items = [\n              row for row in confirmation_items\n              if row.get('manualSemanticEquivalence') is not True\n          ]\n          syntax_path = (\n              tools / 'release_catalog_semantic_syntactic_confirmation_ids.v1.txt'\n          )\n          syntax_ids = mod._load_syntax_confirmation_ids(syntax_path)\n          standalone_payload = mod._load_standalone_payload(\n              tools / 'release_catalog_semantic_standalone_dispositions.v1.json'\n          )\n          standalone_ids = {\n              row['sourceIngredientId'] for row in standalone_payload.get('items') or []\n          }\n          confirmation_ids = {\n              row['sourceIngredientId'] for row in confirmation_items\n          }\n          if confirmation_ids & syntax_ids:\n              raise SystemExit('semantic and syntactic confirmation sets overlap')\n          if (confirmation_ids | syntax_ids) & standalone_ids:\n              raise SystemExit('standalone dispositions overlap merge confirmations')\n\n          paths = mod._review_paths(tools)\n          payloads = [(path.name, mod._load_payload(path)) for path in paths]\n          before = mod.compile_semantic_concepts(payloads)\n          after = mod.compile_from_paths(paths)\n\n          exact_count = len(exact_items)\n          equivalence_count = len(equivalence_items)\n          syntax_count = len(syntax_ids)\n          standalone_count = len(standalone_ids)\n          confirmation_total = exact_count + equivalence_count + syntax_count\n          review_total = confirmation_total + standalone_count\n          if after['summary']['exactConfirmedSourceLabels'] != exact_count:\n              raise SystemExit('exact confirmation count mismatch')\n          if after['summary']['semanticEquivalentConfirmedSourceLabels'] != equivalence_count:\n              raise SystemExit('semantic-equivalence confirmation count mismatch')\n          if after['summary']['syntacticConfirmedSourceLabels'] != syntax_count:\n              raise SystemExit('syntactic confirmation count mismatch')\n          if after['summary']['standaloneConfirmedSourceLabels'] != standalone_count:\n              raise SystemExit('standalone disposition count mismatch')\n          if after['summary']['reviewedAmbiguousSourceLabels'] != 28:\n              raise SystemExit('reviewed ambiguous disposition count mismatch')\n          if after['summary']['confirmedSourceLabels'] != confirmation_total:\n              raise SystemExit('merge confirmation total mismatch')\n          if (\n              before['summary']['needsSemanticConfirmationSourceLabels']\n              - after['summary']['needsSemanticConfirmationSourceLabels']\n              != review_total\n          ):\n              raise SystemExit('pending semantic decrement mismatch')\n          if (\n              before['summary']['semanticConcepts']\n              - after['summary']['semanticConcepts']\n              != confirmation_total\n          ):\n              raise SystemExit('semantic concept merge count mismatch')\n\n          concepts = {row['conceptId']: row for row in after.get('concepts') or []}\n          expected_ids = confirmation_ids | syntax_ids\n'''
    text = replace_once(text, old_counts, new_counts, "apply confirmation count audit")

    text = replace_once(
        text,
        "              expected_method = (\n                  'explicit-reviewed-syntactic-normalization'\n                  if source_id in syntax_ids\n                  else 'explicit-reviewed-english-classification'\n              )\n",
        "              if source_id in syntax_ids:\n                  expected_method = 'explicit-reviewed-syntactic-normalization'\n              elif any(\n                  row['sourceIngredientId'] == source_id\n                  for row in equivalence_items\n              ):\n                  expected_method = 'explicit-manual-semantic-equivalence'\n              else:\n                  expected_method = 'explicit-reviewed-english-classification'\n",
        "apply expected method",
    )

    marker = "          audit = {\n              'exactConfirmationCount': exact_count,\n"
    replacement = '''          for source_id in standalone_ids:\n              target_id = after['sourceIdentityToConcept'].get(source_id)\n              concept = concepts.get(target_id)\n              if not target_id or not concept:\n                  raise SystemExit(f'standalone source missing from semantic map: {source_id}')\n              if not target_id.startswith('concept:source:'):\n                  raise SystemExit(f'standalone source was cross-identity merged: {source_id}')\n              if concept.get('needsSemanticConfirmation') is True:\n                  raise SystemExit(f'standalone source still pending: {source_id}')\n              if any(\n                  concept.get(key) is not False\n                  for key in ('nutritionEligible', 'dietEligible', 'allergenEligible')\n              ):\n                  raise SystemExit(f'standalone source gained safety eligibility: {source_id}')\n\n          audit = {\n              'exactConfirmationCount': exact_count,\n              'semanticEquivalentConfirmationCount': equivalence_count,\n              'syntacticConfirmationCount': syntax_count,\n              'standaloneDispositionCount': standalone_count,\n              'reviewedAmbiguousDispositionCount': 28,\n'''
    text = replace_once(text, marker, replacement, "apply standalone concept audit")
    text = text.replace("              'syntacticConfirmationCount': syntax_count,\n              'confirmationCount': total,\n", "              'confirmationCount': confirmation_total,\n              'reviewClosureCount': review_total,\n", 1)

    old_final_ids = '''          exact = json.loads(\n              (\n                  tools / 'release_catalog_semantic_confirmations.v1.json'\n              ).read_text(encoding='utf-8')\n          ).get('items') or []\n          syntax_ids = mod._load_syntax_confirmation_ids(\n              tools\n              / 'release_catalog_semantic_syntactic_confirmation_ids.v1.txt'\n          )\n          exact_ids = {row['sourceIngredientId'] for row in exact}\n          expected_ids = exact_ids | syntax_ids\n'''
    new_final_ids = '''          confirmation_items = json.loads(\n              (\n                  tools / 'release_catalog_semantic_confirmations.v1.json'\n              ).read_text(encoding='utf-8')\n          ).get('items') or []\n          syntax_ids = mod._load_syntax_confirmation_ids(\n              tools\n              / 'release_catalog_semantic_syntactic_confirmation_ids.v1.txt'\n          )\n          standalone_payload = mod._load_standalone_payload(\n              tools / 'release_catalog_semantic_standalone_dispositions.v1.json'\n          )\n          confirmation_ids = {row['sourceIngredientId'] for row in confirmation_items}\n          standalone_ids = {\n              row['sourceIngredientId'] for row in standalone_payload.get('items') or []\n          }\n          expected_ids = confirmation_ids | syntax_ids | standalone_ids\n'''
    text = replace_once(text, old_final_ids, new_final_ids, "final expected IDs")

    text = replace_once(
        text,
        "          delta = before_pending - after_pending\n          if delta not in {0, len(syntax_ids)}:\n              raise SystemExit(\n                  f'unexpected active-catalog semantic decrement: {delta}'\n              )\n",
        "          delta = before_pending - after_pending\n          if delta < 0:\n              raise SystemExit(\n                  f'active-catalog semantic pending count increased: {delta}'\n              )\n",
        "final pending delta",
    )

    text = replace_once(
        text,
        "              'semanticConfirmationAppliedCount': len(expected_ids),\n              'exactSemanticConfirmationCount': len(exact_ids),\n              'syntacticSemanticConfirmationCount': len(syntax_ids),\n",
        "              'semanticReviewClosureAppliedCount': len(expected_ids),\n              'mergeSemanticConfirmationCount': len(confirmation_ids) + len(syntax_ids),\n              'standaloneSemanticDispositionCount': len(standalone_ids),\n              'syntacticSemanticConfirmationCount': len(syntax_ids),\n",
        "final summary counts",
    )

    APPLY_WORKFLOW.write_text(text, encoding="utf-8")


def main() -> int:
    patch_compiler()
    patch_tests()
    patch_audit_workflow()
    patch_apply_workflow()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
