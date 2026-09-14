from __future__ import annotations

from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tools'
if str(TOOLS) not in sys.path: sys.path.insert(0,str(TOOLS))
import classify_nutrition_review_queue_v60 as classifier
import nutrition_review_holds_v60 as holds
import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver
import snapshot_nutrition_review_checkpoint_v60 as cp

EVIDENCE_SHA='e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac'
SOURCES=tuple(TOOLS/name for name in ('release_catalog_reviewed_nutrition_targets_042.v1.json', 'release_catalog_reviewed_nutrition_targets_042b.v1.json', 'release_catalog_reviewed_nutrition_targets_042c.v1.json', 'release_catalog_reviewed_nutrition_targets_042d.v1.json', 'release_catalog_reviewed_nutrition_targets_042e.v1.json', 'release_catalog_reviewed_nutrition_targets_042f.v1.json'))
RULES=TOOLS/'release_catalog_nutrition_bulk_family_rules_batch38.v1.json'
FIXTURE=ROOT/'tests/fixtures/nutrition-batch38-retained-reference-v60.json.gz'
SOURCE_SHAS={'release_catalog_reviewed_nutrition_targets_042.v1.json': 'f36930e86dfb47dd7505639c3a559622a933e937a660957e9a7008298128207b', 'release_catalog_reviewed_nutrition_targets_042b.v1.json': '34774620bb840a594e168e9ba9bb6f0506b60e3f1dffdfcd7a29de8c0230d26a', 'release_catalog_reviewed_nutrition_targets_042c.v1.json': '0f3fd7c6a77206297ce02890e3f42a9ed6b34cc0b45f1474aa726710b7e25ccd', 'release_catalog_reviewed_nutrition_targets_042d.v1.json': '5e1f6fe64b778a622ef33ea50f526dd703b50777dc682bc327960d0d190dace6', 'release_catalog_reviewed_nutrition_targets_042e.v1.json': '71b7108da772836fb0f85b1e7f2ccda038ba2c87c9e246fc4d364731ed930b1a', 'release_catalog_reviewed_nutrition_targets_042f.v1.json': 'a17c0ec0cec65a2a55c9bd30e0d6dc2e073ea802e24bc45bc30670451c47f438'}
RULES_SHA='9f922d8e2039aadc4456315cfb34e146284d6e0a720d192c682d6204535d833b'
FIXTURE_SHA='b3141930a1b3424f1162069ce152028fc99fd991aa5e9388a1127247fc4bb7d4'
BASE_BINDINGS_SHA='3bfcede03a735700516dc5d59c88a6979fe01616fa693ddaf882ee71e088bec4'

class Batch38BulkFamilyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.documents=[json.loads(p.read_text()) for p in SOURCES]
  cls.items=[r for d in cls.documents for r in d['items']]
  cls.ids={r['reviewTargetId'] for r in cls.items}
  cls.rules_doc=json.loads(RULES.read_text())
  cls.rules={r['ruleId']:r for r in cls.rules_doc['rules']}
  cls.fixture=json.loads(gzip.decompress(FIXTURE.read_bytes()))
  cls.sources={r['reviewTargetId']:r for r in cls.fixture['sources']}
  cls.targets={r['reviewTargetId']:r for r in cls.fixture['targets']}
  cls.checkpoint=cp.build_checkpoint(TOOLS)
  cls.source_names={p.name for p in SOURCES}

 def test_exact_file_bytes_counts_and_usage(self):
  self.assertEqual({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES},SOURCE_SHAS)
  self.assertEqual(hashlib.sha256(RULES.read_bytes()).hexdigest(),RULES_SHA)
  self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),FIXTURE_SHA)
  self.assertEqual(len(self.items),111); self.assertEqual(len(self.ids),111)
  self.assertEqual(sum(r['usageCountAtReview'] for r in self.items),2571)
  self.assertEqual(sum(r['bulkFamilyTier']=='A' for r in self.items),10)
  self.assertEqual(sum(r['bulkFamilyTier']=='B' for r in self.items),101)

 def test_batch37_baseline_is_exact_and_checkpoint_is_at_least_4839(self):
  names={r['path'] for r in self.checkpoint['reviewFiles'] if r['path'] < 'release_catalog_reviewed_nutrition_targets_042'}
  bindings=[r for r in self.checkpoint['recordedBindings'] if r['reviewFile'] in names]
  self.assertEqual(len(bindings),4728)
  self.assertEqual(cp._digest(cp._encoded(bindings)),BASE_BINDINGS_SHA)
  self.assertGreaterEqual(self.checkpoint['summary']['recordedReviewTargetCount'],4839)

 def test_destinations_disjoint_from_every_other_review_row(self):
  others={r['reviewTargetId'] for r in self.checkpoint['recordedBindings'] if r['reviewFile'] not in self.source_names}
  self.assertFalse(self.ids & others)

 def test_holds_and_provenance_guard_remain_separate(self):
  held=holds.load_holds(); self.assertEqual(len(held['targets']),12)
  self.assertEqual(held['registrySha256'],self.fixture['holdRegistrySha256'])
  self.assertFalse(self.ids & set(held['targets'])); self.assertFalse(set(self.sources)&set(held['targets']))

 def test_every_row_matches_exactly_one_batch38_rule(self):
  for row in self.items:
   matches=[r for r in self.rules.values() if re.match(r['pattern'],row['canonicalEnglishName'],re.I)]
   self.assertEqual(len(matches),1,row['reviewTargetId']); rule=matches[0]
   self.assertEqual(row['bulkFamilyRuleId'],rule['ruleId']); self.assertEqual(row['fdcId'],rule['fdcId'])
   self.assertEqual(row['bulkFamilyTier'],rule['tier']); self.assertEqual(row['fdcDescription'],rule['fdcDescription'])
   self.assertGreater(len(row['notes']),350)

 def test_combined_rule_loader_is_unique_anchored_and_safe(self):
  doc,compiled=classifier._load_rules()
  self.assertIn('release_catalog_nutrition_bulk_family_rules.v1.json',doc['registries'])
  self.assertIn(RULES.name,doc['registries'])
  ids=[r['ruleId'] for r,_ in compiled]; self.assertEqual(len(ids),len(set(ids)))
  for r,rx in compiled:
   self.assertTrue(r['pattern'].startswith('^')); self.assertTrue(r['pattern'].endswith('$'))
  self.assertFalse(doc['policy']['candidateRankIsIdentityProof']); self.assertTrue(doc['policy']['automaticRuleExpansionForbidden'])

 def test_fixture_pins_exact_destination_and_locator_records(self):
  self.assertFalse(self.fixture['fullSnapshotIncluded']); self.assertTrue(self.fixture['sourceCandidatesAreExactOriginalRecords'])
  self.assertEqual(self.fixture['sourceEvidenceSha256'],EVIDENCE_SHA); self.assertEqual(len(self.targets),111)
  for row in self.items:
   target=self.targets[row['reviewTargetId']]
   self.assertEqual(row['canonicalEnglishName'],target['canonicalEnglishName']); self.assertEqual(row['usageCountAtReview'],target['usageCountSum'])
   self.assertEqual(cp.retained_reference_mismatch(row,self.sources,EVIDENCE_SHA),'')

 def test_loader_preserves_rule_and_reference_receipts(self):
  loaded=resolver.load_reviews(TOOLS)
  for row in self.items:
   got=loaded[row['reviewTargetId']]
   for k in ('fdcId','bulkFamilyRuleId','bulkFamilyTier','sourceEvidenceTargetId','sourceEvidenceCandidateRank','sourceCandidateSha256'):
    self.assertEqual(got[k],row[k])

 def test_remaining_queue_is_1480_unique_and_disjoint(self):
  remaining=self.fixture['remainingAfterTargetIds']; self.assertEqual(len(remaining),1480); self.assertEqual(len(set(remaining)),1480)
  self.assertFalse(set(remaining)&self.ids); self.assertEqual(self.fixture['remainingBeforeCount'],1591); self.assertEqual(self.fixture['remainingAfterCount'],1480)

 def test_classifier_validates_both_bulk_batches_but_approves_zero(self):
  audit={'summary':{'recordedReviewTargetCount':4839,'heldReviewTargetCount':12},'heldTargets':[], 'remainingUnheldCandidates':[], 'reviewFilesSha256':'x','registrySha256':'y'}
  evidence={'source':True}
  original_read=cp._read
  def selective_read(path):
   if Path(path).name=='ignored': return evidence,EVIDENCE_SHA
   return original_read(path)
  with patch.object(holds,'audit',return_value=audit), patch.object(cp,'_read',side_effect=selective_read), patch.object(resolver,'load_reviews',return_value={}), patch.object(classifier.worklist,'validate_ledger',return_value={}):
   # Rule registries/review rows remain real; only the synthetic evidence path is mocked.
   result=classifier.classify(Path('ignored'),review_root=TOOLS)
  self.assertEqual(result['summary']['batch37ExplicitReviewCount'],106)
  self.assertEqual(result['summary']['batch38ExplicitReviewCount'],111)
  self.assertGreaterEqual(result['summary']['explicitBulkReviewCount'],217)
  self.assertEqual(result['summary']['bindingsApprovedByClassifier'],0)

 def test_rule_match_without_explicit_review_is_still_unapproved(self):
  _,compiled=classifier._load_rules()
  rows=[{'reviewTargetId':'synthetic:bacon','canonicalEnglishName':'Bacon','candidates':[{'fdcId':168277}]}]
  matched,b,c=classifier._partition_remaining(rows,compiled)
  self.assertEqual(len(matched),1); self.assertEqual(b,[]); self.assertEqual(c,[])
  self.assertNotIn('synthetic:bacon',self.ids)

 def test_high_impact_ambiguous_families_are_not_batch38_rules(self):
  _,compiled=classifier._load_rules()
  for name in ('Rice','Washed basmati rice','Pepper','Potato starch','Crème fraîche','Garam masala','Mixed herbs','Curry','Curry paste'):
   self.assertEqual(classifier._matches(name,compiled),[],name)

 def test_bacon_is_explicitly_generic_not_meat_type_proof(self):
  rows=[r for r in self.items if r['bulkFamilyRuleId']=='b38-bacon-unprepared']
  self.assertEqual(len(rows),12); self.assertTrue(all(r['bulkFamilyTier']=='B' for r in rows))
  self.assertTrue(all('not proof' in r['notes'].lower() or 'not a claim' in r['notes'].lower() for r in rows))

 def test_mint_extract_and_fruit_garnish_are_not_swept_in(self):
  _,compiled=classifier._load_rules()
  for name in ('Peppermint essence','Fruit (for garnish; berries, mint, etc.)'):
   self.assertEqual(classifier._matches(name,compiled),[])

 def test_pasta_rule_excludes_lentil_and_konjac_noodles(self):
  _,compiled=classifier._load_rules()
  for name in ('Lentil fusilli','Konjac noodles'):
   self.assertEqual(classifier._matches(name,compiled),[])

 def test_tofu_skin_is_not_plain_tofu(self):
  _,compiled=classifier._load_rules(); self.assertEqual(classifier._matches('Thick tofu skin, cut into small pieces',compiled),[])

 def test_curry_is_explicitly_deferred_despite_usage(self):
  self.assertNotIn('concept:food:d50d92d6a2f826754901',self.ids); self.assertNotIn('M_FOOD_161',self.ids)

 def test_generic_fallback_notes_do_not_claim_exact_formulation(self):
  tierb=[r for r in self.items if r['bulkFamilyTier']=='B']; self.assertEqual(len(tierb),101)
  self.assertTrue(all(r['confidence']=='medium' for r in tierb)); self.assertTrue(all('not a claim' in r['notes'] or 'not certified' in r['notes'] for r in tierb))

 def test_direct_tier_a_is_small_and_specific(self):
  tiera=[r for r in self.items if r['bulkFamilyTier']=='A']; self.assertEqual(len(tiera),10)
  ids={r['bulkFamilyRuleId'] for r in tiera}
  self.assertEqual(ids,{'b38-fresh-mint-explicit','b38-minced-meat-nfs','b38-beef-stew-meat','b38-shimeji-beech-mushroom','b38-baking-soda-prep-text'})

 def test_reference_drift_fails_closed(self):
  row=self.items[0]; self.assertEqual(cp.retained_reference_mismatch({**row,'sourceEvidenceCandidateRank':999},self.sources,EVIDENCE_SHA),'retained_reference_candidate_metadata_differs')

 def test_cli_remains_non_approving_and_refuses_overwrite(self):
  result={'schemaVersion':1,'kind':'cook4me-nutrition-review-tier-classification-v60','summary':{'remainingReviewTargetCount':1480},'tierBManual':[],'tierCContext':[]}
  with tempfile.TemporaryDirectory() as tmp, patch.object(classifier,'classify',return_value=result) as mocked:
   out=Path(tmp)/'out'; self.assertEqual(classifier.main(['--evidence','ignored','--output',str(out)]),2)
   before=(out/'classification.json').read_bytes(); self.assertEqual(classifier.main(['--evidence','ignored','--output',str(out)]),1); self.assertEqual(before,(out/'classification.json').read_bytes()); self.assertEqual(mocked.call_count,1)

if __name__=='__main__': unittest.main()
