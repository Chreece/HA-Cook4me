#!/usr/bin/env python3
"""Reconcile committed semantic reviews with the latest exact-ID nutrition.

Maintenance only, offline, no provider requests. The existing builders remain
responsible for provenance checks and regenerated search/safety indexes. Refuse
missing or changed source identities; never replace cooking instructions.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_release_catalog_v60 as builder
import compile_release_catalog_semantics_v60 as semantics
import compact_release_catalog_runtime_v60 as compactor


def reconcile(payload, compiled):
    original = deepcopy(payload)
    source_map, concepts = builder._core._semantic_maps(compiled)
    old_local = {r['id'] for r in original['ingredients'] if str(r['id']).startswith('local:')}
    if old_local != set(source_map):
        raise ValueError('Semantic review IDs must exactly match the shipped source-local ingredient IDs')
    updated = []
    for row in original['ingredients']:
        ident = row['id']
        if ident not in source_map:
            updated.append(deepcopy(row))
            continue
        concept = concepts[source_map[ident]]
        evidence = builder._core._concept_source_identity(concept, ident)
        if not evidence or semantics.source_local_ingredient_id(evidence['language'], evidence['source']) != ident:
            raise ValueError('Review source cannot reproduce ingredient identity: ' + ident)
        replacement = builder._core._source_local_global_row(
            source_id=ident, source_name=evidence['source'],
            source_language=evidence['language'], concept=concept,
        )
        # Nutrition is never copied between ingredients/concepts. The existing
        # exact-ID provenance validator will accept or reject this same-ID row.
        if row.get('nutrition'):
            replacement['nutrition'] = deepcopy(row['nutrition'])
        updated.append(replacement)
    staged = deepcopy(original)
    staged['ingredients'] = updated
    source = staged['source']
    source.update(
        reviewedSemanticConceptCount=len(concepts),
        semanticConceptsUsedByRecipes=len({r.get('conceptId') for r in updated if r.get('conceptId')}),
        semanticReviewClosureAppliedCount=compiled['summary']['confirmedSourceLabels'] + compiled['summary']['standaloneConfirmedSourceLabels'] + compiled['summary']['standaloneEquivalentSourceLabels'],
        standaloneSemanticEquivalenceCount=compiled['summary']['standaloneEquivalentSourceLabels'],
        standaloneSemanticDispositionCount=compiled['summary']['standaloneConfirmedSourceLabels'],
        needsSemanticConfirmationCount=sum(bool(r.get('needsSemanticConfirmation')) for r in updated),
        branchConsolidationReviewVersion=197,
    )
    cache = {r['id']: deepcopy(r['nutrition']) for r in original['ingredients'] if r.get('nutrition')}
    final = builder.apply_reviewed_nutrition(staged, cache)
    final, compact_report = compactor.compact(final)
    if original['recipes'] != final['recipes']:
        raise ValueError('Recipe instructions, quantities, variants or send identities changed')
    if {r['id'] for r in original['ingredients']} != {r['id'] for r in final['ingredients']}:
        raise ValueError('Ingredient identity set changed')
    after = {r['id']: r for r in final['ingredients']}
    for ident, profile in cache.items():
        actual = after[ident].get('nutrition')
        if actual and any(actual.get(k) != profile.get(k) for k in ('values', 'source', 'sourceId', 'ingredientId')):
            raise ValueError('Existing exact-ID nutrient evidence changed: ' + ident)
    summary = {
        'recipesUnchanged': True, 'ingredientIdsUnchanged': True,
        'recipeCount': len(final['recipes']), 'ingredientCount': len(final['ingredients']),
        'beforeNutritionProfiles': len(cache),
        'afterNutritionProfiles': sum(bool(r.get('nutrition')) for r in final['ingredients']),
        'removedIneligibleOrUnprovenProfiles': [ident for ident in cache if not after[ident].get('nutrition')],
        'semanticReview': compiled['summary'], 'compaction': compact_report,
        'networkRequests': 0,
    }
    return final, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    compiled = semantics.compile_from_paths(semantics._review_paths())
    result, report = reconcile(json.loads(args.catalog.read_bytes()), compiled)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'removedIneligibleOrUnprovenProfiles','compaction'}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
