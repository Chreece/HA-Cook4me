from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import gzip
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import prepare_nutrition_target_context_v60 as mod
import compile_release_catalog_semantics_v60 as sem
import snapshot_nutrition_review_checkpoint_v60 as cp
import prepare_nutrition_review_worklist_v60 as work

FIXTURE = ROOT / "tests/fixtures/nutrition-batch36-context-subset-v60.json.gz"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"
BASE_FILES_SHA = "9c9edddfad6f70a3783b5ab7c3cd2c35c04f53b888a0bb8521a17ac5ec7c66d8"
BASE_BINDINGS_SHA = "87b67adfc767731219ace6aa1d4909980c64f89e9b434873d3dff2565bc944d7"


def synthetic_capture(context):
    """Schema-faithful synthetic data, not a user recipe capture."""
    local_target = next(r for r in context['targets'] if r['reviewTargetKind'] == 'semantic-concept')
    source = local_target['sourceLabels'][0]
    provider_target = next(r for r in context['targets'] if r['reviewTargetKind'] == 'provider-identity')
    local = source['ingredientId']
    provider = provider_target['reviewTargetId']
    return {
        'schemaVersion': 1, 'catalogVersion': '2026-09-11-v60-capture3',
        'credentials': {'token': 'NOT_FOR_EXPORT'},
        'ingredients': [
            {'id': local, 'conceptId': local_target['reviewTargetId'], 'canonicalName': local_target['canonicalEnglishName'], 'nutrition': {'private': 'NOT_FOR_EXPORT'}},
            {'id': provider, 'key': provider, 'canonicalName': provider_target['canonicalEnglishName']},
        ],
        'recipes': [{'groupingFunctionalId': 'G-TEST', 'title': 'NOT_FOR_EXPORT', 'variants': [
            {'variantId': 'V-TEST', 'ingredients': [
                {'ingredientId': local, 'conceptId': local_target['reviewTargetId'], 'semanticSourceName': source['source'], 'originalLanguage': source['language'], 'originalName': source['source'], 'quantity': 0, 'unit': 'g', 'token': 'NOT_FOR_EXPORT'},
                {'ingredientId': provider, 'key': provider, 'originalName': provider_target['canonicalEnglishName'], 'quantity': 'as needed', 'unit': 'spoon'},
            ]},
        ]}],
    }


class SourceContextBatch36Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
        cls.evidence = cls.fixture['evidenceSubset']
        cls.ledger = cp._read(work.LEDGER)[0]
        cls.requirements = work.validate_ledger(cls.ledger, cls.evidence, EVIDENCE_SHA)
        cls.context = mod.collect_context(cls.requirements, cls.evidence)
        cls.findings = cp._read(mod.FINDINGS)[0]
        cls.version = cls.evidence['catalogVersion']

    def test_fixture_is_labeled_exact_row_subset_not_full_capture(self):
        self.assertFalse(self.fixture['fullSnapshotIncluded'])
        self.assertTrue(self.fixture['rowsAreExactOriginalRows'])
        self.assertEqual(self.fixture['sourceEvidenceSha256'], EVIDENCE_SHA)
        self.assertEqual(len(self.evidence['items']), 28)
        self.assertEqual(set(self.requirements), {r['reviewTargetId'] for r in self.evidence['items']})

    def test_28_targets_resolve_to_183_labels_and_10_missing_provider_reviews(self):
        rows = self.context['targets']
        self.assertEqual(len(rows), 28)
        self.assertEqual(sum(bool(r['sourceLabels']) for r in rows), 18)
        self.assertEqual(sum(len(r['sourceLabels']) for r in rows), 183)
        self.assertEqual(sum(r['contextStatus'] == 'exact-provider-review-not-retained' for r in rows), 10)
        self.assertTrue(all(not r['nutritionApprovalGranted'] for r in rows))
        self.assertTrue(all(not r['measurementBasisEstablished'] for r in rows))

    def test_235_historical_sources_4622_bindings_and_holds_remain_unchanged(self):
        value = cp.build_checkpoint(TOOLS)
        earlier = [r for r in value['reviewFiles'] if r['path'] < 'release_catalog_reviewed_nutrition_targets_041']
        self.assertEqual(len(earlier), 235)
        self.assertEqual(cp._digest(cp._encoded(earlier)), BASE_FILES_SHA)
        names = {r['path'] for r in earlier}
        records = [r for r in value['recordedBindings'] if r['reviewFile'] in names]
        self.assertEqual(len(records), 4622)
        self.assertEqual(cp._digest(cp._encoded(records)), BASE_BINDINGS_SHA)
        held = mod.holds.load_holds()
        self.assertEqual(len(held['targets']), 12)
        self.assertEqual(held['registrySha256'], self.fixture['holdRegistrySha256'])

    def test_every_source_label_has_full_id_and_exact_row_receipt(self):
        for target in self.context['targets']:
            for source in target['sourceLabels']:
                self.assertEqual(sem.source_local_ingredient_id(source['language'], source['source']), source['ingredientId'])
                payload, digest = cp._read(TOOLS / source['reviewFile'])
                raw = payload['items'][source['reviewItemIndex']]
                self.assertEqual(digest, source['reviewFileSha256'])
                self.assertEqual(cp._digest(cp._encoded(raw)), source['reviewItemSha256'])
                self.assertEqual(sem._semantic_concept_id('food', source['reviewedEnglish']), target['reviewTargetId'])

    def test_all_semantic_membership_counts_match_the_retained_targets(self):
        for target in self.context['targets']:
            self.assertEqual(len(target['memberIngredientIds']), target['memberCount'])
            self.assertEqual(len(set(target['memberIngredientIds'])), target['memberCount'])

    def test_rice_finding_preserves_soaking_text_and_exact_identity(self):
        findings = mod.validate_findings(self.findings, self.context, EVIDENCE_SHA)
        self.assertEqual(len(findings), 1)
        row = findings[0]
        self.assertEqual(row['ingredientId'], 'local:ja:1439324e0ea7e7f84313')
        self.assertEqual(row['source'], '米(洗って30分吸水し ザルにあげる)')
        self.assertEqual(row['reviewedEnglish'], 'Rice')
        self.assertIn('soaked for 30 minutes', row['observedPreparationEnglish'])
        self.assertEqual(row['status'], 'unresolved-source-semantics')
        rice = next(t for t in self.context['targets'] if t['reviewTargetId'] == row['reviewTargetId'])
        self.assertEqual(len(rice['sourceLabels']), 14)

    def test_findings_do_not_rewrite_compiler_or_approve_a_profile(self):
        row = self.findings['items'][0]
        source = next(s for r in self.context['targets'] for s in r['sourceLabels'] if s['ingredientId'] == row['ingredientId'])
        self.assertEqual(sem._semantic_concept_id('food', source['reviewedEnglish']), row['reviewTargetId'])
        self.assertTrue(all(v is False for v in mod.POLICY.values()))
        self.assertNotIn('fdcId', row)

    def test_findings_fail_on_source_hash_text_or_index_drift(self):
        for key, bad in [('source', '米'), ('ingredientId', 'local:ja:wrong'), ('reviewItemIndex', -1), ('reviewFileSha256', 'a'*64), ('reviewItemSha256', 'a'*64), ('reviewedEnglish', 'Cooked rice')]:
            value = deepcopy(self.findings)
            value['items'][0][key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                mod.validate_findings(value, self.context, EVIDENCE_SHA)

    def test_findings_reject_duplicates_binding_fields_and_numeric_policy(self):
        values = []
        v = deepcopy(self.findings); v['items'].append(deepcopy(v['items'][0])); values.append(v)
        v = deepcopy(self.findings); v['items'][0]['fdcId'] = 123; values.append(v)
        v = deepcopy(self.findings); v['policy']['bindingsApproved'] = 0; values.append(v)
        for value in values:
            with self.assertRaises(ValueError): mod.validate_findings(value, self.context, EVIDENCE_SHA)

    def test_frozen_target_membership_drift_fails_closed(self):
        value = deepcopy(self.evidence)
        value['items'][0]['memberCount'] -= 1
        with self.assertRaisesRegex(ValueError, 'member count'):
            mod.collect_context(self.requirements, value)

    def test_provider_same_name_is_not_replaced_by_semantic_labels(self):
        rows = self.context['targets']
        rice = next(r for r in rows if r['reviewTargetId'] == 'M_FOOD_421')
        self.assertEqual(rice['canonicalEnglishName'], 'Rice')
        self.assertEqual(rice['sourceLabels'], [])
        self.assertEqual(rice['memberIngredientIds'], ['M_FOOD_421'])
        self.assertEqual(rice['contextStatus'], 'exact-provider-review-not-retained')

    def test_semantic_source_loader_rejects_rows_instead_of_skipping(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/sem.BASE_REVIEW.name
            for raw in [None, {}, {'language':'ja','source':'米','english':'Rice','classification':'WRONG'}, {'language':'ja','source':'米','english':'Rice','classification':'food','confidence':True}]:
                path.write_text(json.dumps({'kind':'cook4me-reviewed-keyless-ingredient-semantics','items':[raw]}))
                with self.subTest(raw=raw), self.assertRaises(ValueError): mod._read_sources(Path(d))

    def test_capture_projection_keeps_zero_and_text_quantity_without_interpretation(self):
        payload = synthetic_capture(self.context)
        before = deepcopy(payload)
        result = mod.extract_capture_context(payload, self.context, self.version)
        lines = [l for t in result['targets'] for l in t['recipeLines']]
        self.assertEqual(len(lines),2)
        self.assertEqual(lines[0]['fields']['quantity'],0)
        self.assertEqual(lines[1]['fields']['quantity'],'as needed')
        self.assertEqual(lines[1]['fields']['unit'],'spoon')
        self.assertEqual(payload,before)
        self.assertTrue(all(not t['massBasisInferred'] for t in result['targets']))

    def test_capture_omits_unknown_fields_tokens_nutrition_and_recipe_titles(self):
        result = mod.extract_capture_context(synthetic_capture(self.context), self.context, self.version)
        self.assertNotIn('NOT_FOR_EXPORT', json.dumps(result))
        self.assertFalse(result['unknownFieldsCopied'])
        self.assertFalse(result['captureCompletenessCertified'])

    def test_capture_receipts_pin_full_original_rows_including_omitted_fields(self):
        payload = synthetic_capture(self.context)
        result = mod.extract_capture_context(payload, self.context, self.version)
        local = next(r for r in result['targets'] if r['recipeLines'] and r['recipeLines'][0]['ingredientId'].startswith('local:'))
        self.assertEqual(local['recipeLines'][0]['sourceRowSha256'],cp._digest(cp._encoded(payload['recipes'][0]['variants'][0]['ingredients'][0])))
        self.assertEqual(local['globalRows'][0]['sourceRowSha256'],cp._digest(cp._encoded(payload['ingredients'][0])))

    def test_capture_does_not_match_names_or_concept_id_without_ingredient_id(self):
        payload = synthetic_capture(self.context)
        for row in payload['ingredients']:
            for key in ('id','key'): row.pop(key,None)
        for row in payload['recipes'][0]['variants'][0]['ingredients']:
            for key in ('ingredientId','key'): row.pop(key,None)
        result = mod.extract_capture_context(payload,self.context,self.version)
        self.assertEqual(result['summary']['recipeLineCount'],0)

    def test_capture_rejects_conflicting_keys_missing_provider_key_and_wrong_types(self):
        for mode in ['conflict','missing','wrong_type','local_flag']:
            payload = synthetic_capture(self.context)
            row = payload['ingredients'][1]
            if mode == 'conflict': row['foodKey'] = 'M_FOOD_OTHER'
            elif mode == 'missing': row.pop('key')
            elif mode == 'wrong_type': row['foodKey'] = 42
            else: row['sourceLocalIdentity'] = True
            with self.subTest(mode=mode),self.assertRaises(ValueError): mod.extract_capture_context(payload,self.context,self.version)

    def test_capture_local_source_must_reproduce_exact_id_and_concept(self):
        for field,value in [('semanticSourceName','unrelated'),('originalLanguage','xx'),('conceptId','concept:food:other'),('key','local:key')]:
            payload = synthetic_capture(self.context)
            payload['recipes'][0]['variants'][0]['ingredients'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError): mod.extract_capture_context(payload,self.context,self.version)

    def test_capture_local_identity_never_promoted_to_provider_key(self):
        payload=synthetic_capture(self.context)
        payload['ingredients'][0]['key']=payload['ingredients'][0]['id']
        with self.assertRaisesRegex(ValueError,'local context'): mod.extract_capture_context(payload,self.context,self.version)

    def test_capture_rejects_duplicate_globals_and_missing_target_global(self):
        for duplicate in (True,False):
            payload=synthetic_capture(self.context)
            if duplicate: payload['ingredients'].append(deepcopy(payload['ingredients'][0]))
            else: payload['ingredients'].pop(0)
            with self.subTest(duplicate=duplicate),self.assertRaises(ValueError): mod.extract_capture_context(payload,self.context,self.version)

    def test_repeated_exact_recipe_lines_are_retained_not_deduplicated_or_summed(self):
        payload=synthetic_capture(self.context)
        lines=payload['recipes'][0]['variants'][0]['ingredients']
        lines.append(deepcopy(lines[0]));lines[-1]['quantity']=5
        result=mod.extract_capture_context(payload,self.context,self.version)
        out=[l for t in result['targets'] for l in t['recipeLines']]
        self.assertEqual(len(out),3)
        self.assertEqual({l['lineIndex'] for l in out},{0,1,2})

    def test_missing_recipe_context_is_reported_as_missing_not_zero_consumption(self):
        payload=synthetic_capture(self.context);payload['recipes']=[]
        result=mod.extract_capture_context(payload,self.context,self.version)
        self.assertEqual(result['summary']['recipeLineCount'],0)
        self.assertTrue(all(t['status']=='no-exact-recipe-lines-in-supplied-capture' for t in result['targets']))

    def test_capture_rejects_wrong_version_schema_or_missing_lists(self):
        for key,bad in [('catalogVersion','other'),('schemaVersion',True),('recipes',{}),('ingredients',None)]:
            payload=synthetic_capture(self.context);payload[key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):mod.extract_capture_context(payload,self.context,self.version)

    def test_capture_does_not_silently_drop_unrepresentable_measurements(self):
        for bad in [True,{},[],float('nan'),float('inf')]:
            payload=synthetic_capture(self.context);payload['recipes'][0]['variants'][0]['ingredients'][0]['quantity']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):mod.extract_capture_context(payload,self.context,self.version)

    def test_plain_and_gzip_capture_have_same_decoded_hash_separate_file_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'capture.json';z=Path(d)/'capture.json.gz'
            raw=cp._encoded(synthetic_capture(self.context));p.write_bytes(raw);z.write_bytes(gzip.compress(raw,mtime=0))
            a=mod._capture(p);b=mod._capture(z)
            self.assertEqual(a[0],b[0]);self.assertEqual(a[2],b[2]);self.assertNotEqual(a[1],b[1])

    def test_capture_rejects_symlink_duplicate_keys_nonfinite_and_oversized_gzip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'capture.json';link=Path(d)/'link.json';p.write_text('{}');link.symlink_to(p)
            with self.assertRaises(ValueError):mod._capture(link)
            for raw in ['{"x":1,"x":2}','{"x":NaN}']:
                p.write_text(raw)
                with self.assertRaises(ValueError):mod._capture(p)
            z=Path(d)/'capture.json.gz';z.write_bytes(gzip.compress(b' '*1000,mtime=0))
            with patch.object(mod,'MAX_CAPTURE_BYTES',100),self.assertRaises(ValueError):mod._capture(z)

    def test_cli_returns_two_for_unresolved_findings_and_refuses_output_overwrite(self):
        summary={'remainingEvidenceTargetCount':1697,'heldReviewTargetCount':12,'unheldProvenanceMismatchCount':0,'documentedSourceContextFindingCount':1}
        outputs={'summary.json':summary,'context.json':{'policy':mod.POLICY}}
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'report';args=['--evidence','not-read.json','--output',str(output)]
            with patch.object(mod,'build_outputs',return_value=outputs) as build,redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
                self.assertEqual(mod.main(args),2);before=(output/'summary.json').read_bytes()
                self.assertEqual(mod.main(args),1);self.assertEqual(build.call_count,1)
            self.assertEqual(before,(output/'summary.json').read_bytes())

    def test_cli_does_not_write_output_on_validation_failure(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'report'
            with patch.object(mod,'build_outputs',side_effect=ValueError('invalid')),redirect_stderr(io.StringIO()):
                self.assertEqual(mod.main(['--evidence','x','--output',str(output)]),1)
            self.assertFalse(output.exists())

    def test_context_is_deterministic_and_inputs_are_not_mutated(self):
        before=deepcopy(self.evidence),deepcopy(self.requirements)
        self.assertEqual(self.context,mod.collect_context(self.requirements,self.evidence))
        self.assertEqual(before,(self.evidence,self.requirements))

    def test_output_guard_detects_semantic_file_changes_during_extraction(self):
        # A synthetic subset replaces the full evidence only in this mocked audit test.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'tools';root.mkdir()
            paths=[*sem._review_paths(TOOLS),TOOLS/mod.PROVIDER_REVIEW,work.LEDGER,mod.FINDINGS,mod.holds.REGISTRY,*TOOLS.glob(cp.REVIEW_GLOB)]
            for p in paths:shutil.copyfile(p,root/p.name)
            ep=Path(d)/'synthetic-evidence.json';ep.write_bytes(cp._encoded(self.evidence));sha=cp._read(ep)[1]
            for name in (work.LEDGER.name,mod.FINDINGS.name):
                value=cp._read(root/name)[0];value['sourceEvidenceSha256']=sha;(root/name).write_bytes(cp._encoded(value))
            baseline=cp.build_checkpoint(root)
            audit={'evidenceSha256':sha,'reviewFilesSha256':baseline['reviewFilesSha256'],'registrySha256':cp._read(root/mod.holds.REGISTRY.name)[1],
                   'remainingUnheldCandidates':self.evidence['items'],'heldTargets':[], 'readyForManualReview':False,
                   'summary':{'remainingEvidenceTargetCount':28,'heldReviewTargetCount':0,'unheldProvenanceMismatchCount':0}}
            original=mod.collect_context
            def mutate(*args,**kwargs):
                out=original(*args,**kwargs)
                p=root/sem.BASE_REVIEW.name;p.write_bytes(p.read_bytes()+b'\n')
                return out
            # Findings are checked before the final source fingerprint guard; receipt
            # bytes remain old, so the original finding still validates, then drift fails.
            with patch.object(mod.holds,'audit',return_value=audit),patch.object(mod,'collect_context',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'source file changed'):mod.build_outputs(ep,review_root=root)


if __name__ == '__main__':
    unittest.main()
