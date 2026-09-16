from __future__ import annotations
import hashlib, json, unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; TOOLS=ROOT/'tools'; sys.path.insert(0,str(TOOLS))
import classify_nutrition_review_queue_v60 as classifier
import nutrition_review_history_v60 as history
import nutrition_review_holds_v60 as holds
import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver
import snapshot_nutrition_review_checkpoint_v60 as cp

SOURCE=TOOLS/'release_catalog_reviewed_nutrition_targets_045.v1.json'
FIXTURE=ROOT/'tests/fixtures/nutrition-batch42-retained-reference-v60.json'
SOURCE_SHA='08a4348a5434a75f1a72ad21b249f9c8f482492bb9eae9ad5bd1c4ffa739e827'
FIXTURE_SHA='95c9f54975c058d320f2a4a59cc397c948a819e8432da34078d2a51952962b3d'
EVIDENCE_SHA='e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac'
BASE_REVIEW_SHA='f3f7d95f933199496a57bfaad27005c53005b8cf009089273e80398027b6ff0d'
BASE_BINDINGS_SHA='930654b687a61a794283e33df4d811b6a2448dc514241dc5be989d3977b129fc'

class Batch42ExplicitReviews(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.doc=json.loads(SOURCE.read_text()); cls.items=cls.doc['items']
  cls.fixture=json.loads(FIXTURE.read_text())
  cls.checkpoint=history.historical_checkpoint(cp.build_checkpoint(TOOLS))
  cls.records=[r for r in cls.checkpoint['recordedBindings'] if r['reviewFile']==SOURCE.name]
  cls.targets={r['reviewTargetId']:r for r in cls.fixture['targets']}
  cls.sources={r['reviewTargetId']:{'reviewTargetId':r['reviewTargetId'],'candidates':[r['candidate']]} for r in cls.fixture['sourceCandidates']}

 def test_exact_files_counts_usage_and_baseline(self):
  self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),SOURCE_SHA)
  self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),FIXTURE_SHA)
  self.assertEqual(len(self.items),9); self.assertEqual(len({r['reviewTargetId'] for r in self.items}),9)
  self.assertEqual(sum(r['usageCountAtReview'] for r in self.items),16)
  prior_files=[r for r in self.checkpoint['reviewFiles'] if r['path']!=SOURCE.name]
  prior_names={r['path'] for r in prior_files}
  prior_bindings=[r for r in self.checkpoint['recordedBindings'] if r['reviewFile'] in prior_names]
  self.assertEqual(len(prior_files),260); self.assertEqual(len(prior_bindings),5071)
  self.assertEqual(cp._digest(cp._encoded(prior_files)),BASE_REVIEW_SHA)
  self.assertEqual(cp._digest(cp._encoded(prior_bindings)),BASE_BINDINGS_SHA)
  self.assertEqual(self.checkpoint['summary']['reviewFileCount'],261)
  self.assertEqual(self.checkpoint['summary']['recordedReviewTargetCount'],5080)

 def test_destination_identity_usage_and_holds(self):
  held=holds.load_holds(); self.assertEqual(len(held['targets']),12)
  self.assertFalse({r['reviewTargetId'] for r in self.items} & set(held['targets']))
  for row in self.items:
   target=self.targets[row['reviewTargetId']]
   for key in ('reviewTargetId','reviewTargetKind','canonicalEnglishName'): self.assertEqual(row[key],target[key])
   self.assertEqual(row['usageCountAtReview'],target['usageCountSum'])
   self.assertGreater(len(row['notes']),120)

 def test_every_retained_reference_receipt_matches_exact_candidate_projection(self):
  self.assertEqual(len(self.records),9)
  for row in self.records:
   self.assertEqual(row['sourceEvidenceSha256'],EVIDENCE_SHA)
   self.assertEqual(cp.retained_reference_mismatch(row,self.sources,EVIDENCE_SHA),'')

 def test_policy_and_loader_preserve_explicit_manual_decisions(self):
  self.assertEqual(self.doc['selectionMethod'],'explicit-semantic-review')
  self.assertEqual(self.doc['evidenceBindingScope'],cp.RETAINED_SCOPE)
  self.assertFalse(self.doc['policy']['searchResultAutoAccepted'])
  self.assertFalse(self.doc['policy']['candidateSearchIsIdentityProof'])
  self.assertFalse(self.doc['policy']['providerIdentityInference'])
  loaded=resolver.load_reviews(TOOLS)
  for row in self.records:
   got=loaded[row['reviewTargetId']]
   for key in ('fdcId','fdcDescription','fdcDataType','sourceEvidenceTargetId','sourceEvidenceCandidateRank','sourceCandidateSha256'): self.assertEqual(got[key],row[key])

 def test_selected_rows_are_exactly_pre_batch42_manual_and_counts_reconcile(self):
  _,compiled=classifier._load_rules()
  matched,manual,context=classifier._partition_remaining(
   self.fixture['selectedManualTargets'],compiled,has_candidates=lambda r:r['candidateCount']>0)
  self.assertEqual(matched,[]); self.assertEqual(context,[]); self.assertEqual(len(manual),9)
  self.assertEqual({r['reviewTargetId'] for r in manual},{r['reviewTargetId'] for r in self.items})
  self.assertEqual(self.fixture['manualBeforeCount']-len(self.items),self.fixture['expectedManualCount'])
  self.assertEqual(self.fixture['contextBeforeCount'],self.fixture['expectedContextCount'])
  self.assertEqual(self.fixture['remainingBeforeCount']-len(self.items),self.fixture['expectedRemainingCount'])
  self.assertEqual(self.fixture['expectedManualCount']+self.fixture['expectedContextCount'],self.fixture['expectedRemainingCount'])
  self.assertEqual(self.fixture['bindingsApprovedByClassifier'],0)

 def test_review_scope_is_narrow_and_no_conversion_fields_are_committed(self):
  expected={'Cooking chocolate','Salted pork (in 100 g pieces)','Salted pork (100 g pieces)',
   'Seitan steaks (100–125 g)','Chikuwa, cut diagonally in half','Kamaboko, cut 5 mm wide',
   'Hanpen, cut into bite-size pieces','Slice of crustless sandwich bread','Skate wing, halved'}
  self.assertEqual({r['canonicalEnglishName'] for r in self.items},expected)
  forbidden={'calories','protein','carbs','fat','fiber','sodium','density','gramsPerPiece','edibleYield','cookingYield','hydrationFactor'}
  for row in self.items:
   self.assertFalse(forbidden & set(row)); self.assertNotIn('bulkFamilyRuleId',row)

if __name__=='__main__': unittest.main()
