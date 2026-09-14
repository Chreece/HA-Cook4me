from __future__ import annotations
import gzip,hashlib,json,re,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[1]; TOOLS=ROOT/'tools'; sys.path.insert(0,str(TOOLS))
import classify_nutrition_review_queue_v60 as classifier
import nutrition_review_holds_v60 as holds
import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver
import snapshot_nutrition_review_checkpoint_v60 as cp
SOURCES=['release_catalog_reviewed_nutrition_targets_044.v1.json', 'release_catalog_reviewed_nutrition_targets_044b.v1.json', 'release_catalog_reviewed_nutrition_targets_044c.v1.json', 'release_catalog_reviewed_nutrition_targets_044d.v1.json', 'release_catalog_reviewed_nutrition_targets_044e.v1.json', 'release_catalog_reviewed_nutrition_targets_044f.v1.json']; SOURCES=[TOOLS/x for x in SOURCES]
RULES=TOOLS/'release_catalog_nutrition_bulk_family_rules_batch40.v1.json'; FIXTURE=ROOT/'tests/fixtures/nutrition-batch40-retained-reference-v60.json.gz'
SOURCE_SHAS={'release_catalog_reviewed_nutrition_targets_044.v1.json': 'c0f706fd97e750259ba369bcb387074f5e49504fce5e522588c320ddf253b83e', 'release_catalog_reviewed_nutrition_targets_044b.v1.json': '9f808c7429547f8c5d89cc95edb215ca814641e2f100a8672ddb4fd4e839f6ea', 'release_catalog_reviewed_nutrition_targets_044c.v1.json': '3878be1b8960f6bb95368996e262365afaf500479f74d7da589fa810c8ac8b0f', 'release_catalog_reviewed_nutrition_targets_044d.v1.json': 'c1c785d35a7fe2e9ec90eb8bc25c7fb4bde242d77706e1771948d3bdfac07f1e', 'release_catalog_reviewed_nutrition_targets_044e.v1.json': 'e7f0be03b2c003cfc236f8ed2db49e6a1a5b9827a09effa96f6382139e12863a', 'release_catalog_reviewed_nutrition_targets_044f.v1.json': '316595cd3ff61363db9d4cabaca7b335c4fa5a803926e1ed5e1a7e7bc8ab6654'}; RULES_SHA='1f9cc8b052ae8e06ebe22bc26953ea16e159df739e150deb563fa2623ec76ed1'; FIXTURE_SHA='4d62f672b126228294a07997c3b3db4bf4234f4a4ebfed24033432a8ec4f1e5a'
EVIDENCE_SHA='e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac'; BASE_REVIEW_SHA='13f41ebdfa9a70e84dbdfd0a2b8319ef98863d529ad671d68cee176f335dd8a0'; BASE_BINDINGS_SHA='6b74fede8756a49b800100d3323bb243fd6f3ebe0f242b8cc9517f78d6ac2619'

class Batch40BulkFamilyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.docs=[json.loads(p.read_text()) for p in SOURCES]; cls.items=[r for d in cls.docs for r in d['items']]; cls.ids={r['reviewTargetId'] for r in cls.items}
  cls.rules_doc=json.loads(RULES.read_text()); cls.rules={r['ruleId']:r for r in cls.rules_doc['rules']}; cls.fixture=json.loads(gzip.decompress(FIXTURE.read_bytes()))
  cls.sources={r['reviewTargetId']:r for r in cls.fixture['sources']}; cls.targets={r['reviewTargetId']:r for r in cls.fixture['targets']}; cls.checkpoint=cp.build_checkpoint(TOOLS); cls.source_names={p.name for p in SOURCES}
 def test_exact_file_hashes_counts_tiers_and_usage(self):
  self.assertEqual({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES},SOURCE_SHAS); self.assertEqual(hashlib.sha256(RULES.read_bytes()).hexdigest(),RULES_SHA); self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),FIXTURE_SHA)
  self.assertEqual(len(self.items),110); self.assertEqual(len(self.ids),110); self.assertEqual(sum(r['usageCountAtReview'] for r in self.items),765); self.assertEqual(sum(r['bulkFamilyTier']=='A' for r in self.items),7); self.assertEqual(sum(r['bulkFamilyTier']=='B' for r in self.items),103)
 def test_exact_batch39_baseline_and_checkpoint_moves_to_5071(self):
  names={r['path'] for r in self.checkpoint['reviewFiles'] if r['path'] < 'release_catalog_reviewed_nutrition_targets_044'}; bindings=[r for r in self.checkpoint['recordedBindings'] if r['reviewFile'] in names]; reviews=[r for r in self.checkpoint['reviewFiles'] if r['path'] in names]
  self.assertEqual(len(bindings),4961); self.assertEqual(cp._digest(cp._encoded(bindings)),BASE_BINDINGS_SHA); self.assertEqual(cp._digest(cp._encoded(reviews)),BASE_REVIEW_SHA); self.assertEqual(len(bindings) + len(self.items),5071)
 def test_destinations_disjoint_holds_unchanged(self):
  others={r['reviewTargetId'] for r in self.checkpoint['recordedBindings'] if r['reviewFile'] not in self.source_names}; self.assertFalse(self.ids&others); held=holds.load_holds(); self.assertEqual(len(held['targets']),12); self.assertEqual(held['registrySha256'],self.fixture['holdRegistrySha256']); self.assertFalse(self.ids&set(held['targets'])); self.assertFalse(set(self.sources)&set(held['targets']))
 def test_each_row_matches_exactly_one_batch40_rule(self):
  for row in self.items:
   matches=[r for r in self.rules.values() if re.match(r['pattern'],row['canonicalEnglishName'],re.I)]; self.assertEqual(len(matches),1,row['reviewTargetId']); rule=matches[0]; self.assertEqual(row['bulkFamilyRuleId'],rule['ruleId']); self.assertEqual(row['bulkFamilyTier'],rule['tier']); self.assertEqual(row['fdcId'],rule['fdcId']); self.assertEqual(row['fdcDescription'],rule['fdcDescription']); self.assertGreater(len(row['notes']),350)
 def test_combined_rules_unique_anchored_non_approving(self):
  doc,compiled=classifier._load_rules(); self.assertIn(RULES.name,doc['registries']); ids=[r['ruleId'] for r,_ in compiled]; self.assertEqual(len(ids),len(set(ids))); self.assertTrue(all(r['pattern'].startswith('^') and r['pattern'].endswith('$') for r,_ in compiled)); self.assertFalse(doc['policy']['candidateRankIsIdentityProof']); self.assertTrue(doc['policy']['automaticRuleExpansionForbidden'])
 def test_fixture_pins_destinations_and_exact_reference_records(self):
  self.assertFalse(self.fixture['fullSnapshotIncluded']); self.assertTrue(self.fixture['sourceCandidatesAreExactOriginalRecords']); self.assertEqual(self.fixture['sourceEvidenceSha256'],EVIDENCE_SHA); self.assertEqual(len(self.targets),110)
  for row in self.items:
   target=self.targets[row['reviewTargetId']]; self.assertEqual(row['canonicalEnglishName'],target['canonicalEnglishName']); self.assertEqual(row['usageCountAtReview'],target['usageCountSum']); self.assertEqual(cp.retained_reference_mismatch(row,self.sources,EVIDENCE_SHA),'')
 def test_loader_preserves_rule_and_reference_receipts(self):
  loaded=resolver.load_reviews(TOOLS)
  for row in self.items:
   got=loaded[row['reviewTargetId']]
   for k in ('fdcId','bulkFamilyRuleId','bulkFamilyTier','sourceEvidenceTargetId','sourceEvidenceCandidateRank','sourceCandidateSha256'): self.assertEqual(got[k],row[k])
 def test_remaining_queue_exactly_1248(self):
  rem=self.fixture['remainingAfterTargetIds']; self.assertEqual(len(rem),1248); self.assertEqual(len(set(rem)),1248); self.assertFalse(set(rem)&self.ids); self.assertEqual(self.fixture['remainingBeforeCount'],1358); self.assertEqual(self.fixture['remainingAfterCount'],1248)
 def test_classifier_counts_four_batches_but_approves_zero(self):
  audit={'summary':{'recordedReviewTargetCount':5071,'heldReviewTargetCount':12},'heldTargets':[],'remainingUnheldCandidates':[],'reviewFilesSha256':'x','registrySha256':'y'}; original=cp._read
  def selective(path):
   if Path(path).name=='ignored': return {'source':True},EVIDENCE_SHA
   return original(path)
  with patch.object(holds,'audit',return_value=audit),patch.object(cp,'_read',side_effect=selective),patch.object(resolver,'load_reviews',return_value={}): result=classifier.classify(Path('ignored'),review_root=TOOLS)
  self.assertEqual(result['summary']['batch37ExplicitReviewCount'],106); self.assertEqual(result['summary']['batch38ExplicitReviewCount'],111); self.assertEqual(result['summary']['batch39ExplicitReviewCount'],122); self.assertEqual(result['summary']['batch40ExplicitReviewCount'],110); self.assertEqual(result['summary']['explicitBulkReviewCount'],449); self.assertEqual(result['summary']['bindingsApprovedByClassifier'],0)
 def test_known_ambiguous_families_stay_out(self):
  names={r['canonicalEnglishName'] for r in self.items}
  for name in ('Pepper','Rice','Curry','Potato starch','Starch','Crème fraîche','Thick crème fraîche','Garam masala','Mixed herbs','Washed basmati rice'): self.assertNotIn(name,names)
 def test_rehydrated_and_mixed_context_variants_stay_out(self):
  names={r['canonicalEnglishName'] for r in self.items}
  for name in ('Knotted kombu, rehydrated in water','Starch slurry (starch:water 1:1)','Oil, mixed with yogurt','Butter, melted with the chocolate','Salted water'): self.assertNotIn(name,names)
 def test_generic_fallbacks_are_medium_and_explicitly_limited(self):
  rows=[r for r in self.items if r['bulkFamilyTier']=='B']; self.assertTrue(rows); self.assertTrue(all(r['confidence']=='medium' for r in rows)); self.assertTrue(all('not certified' in r['notes'] or 'not a claim' in r['notes'] for r in rows))
 def test_tier_a_is_small_and_direct(self):
  rows=[r for r in self.items if r['bulkFamilyTier']=='A']; self.assertEqual(len(rows),7); self.assertTrue(all(r['confidence']=='high' for r in rows)); self.assertEqual({r['bulkFamilyRuleId'] for r in rows},{'b40-chocolate-sprinkles','b40-shrimp-raw','b40-sorbet','b40-maraschino','b40-praline','b40-dulce-de-leche','b40-lamb-rib-raw'})
 def test_rule_match_without_review_row_remains_unapproved(self):
  _,compiled=classifier._load_rules(); rows=[{'reviewTargetId':'synthetic:salad','canonicalEnglishName':'Mesclun salad','candidates':[{'fdcId':2709792}]}]; matched,b,c=classifier._partition_remaining(rows,compiled); self.assertEqual(len(matched),1); self.assertEqual(b,[]); self.assertEqual(c,[]); self.assertNotIn('synthetic:salad',self.ids)
 def test_reference_rank_or_hash_drift_fails_closed(self):
  row=self.items[0]; self.assertEqual(cp.retained_reference_mismatch({**row,'sourceEvidenceCandidateRank':999},self.sources,EVIDENCE_SHA),'retained_reference_candidate_metadata_differs'); self.assertEqual(cp.retained_reference_mismatch({**row,'sourceCandidateSha256':'0'*64},self.sources,EVIDENCE_SHA),'retained_reference_candidate_bytes_differ')
 def test_no_nutrient_values_or_mass_conversions_are_committed(self):
  forbidden={'calories','protein','carbs','fat','fiber','sodium','density','gramsPerPiece','edibleYield','cookingYield','hydrationFactor'}
  for row in self.items: self.assertFalse(forbidden & set(row))
 def test_policy_never_treats_search_rank_as_identity_proof(self):
  for doc in self.docs: self.assertFalse(doc['policy']['searchResultAutoAccepted']); self.assertFalse(doc['policy']['candidateSearchIsIdentityProof']); self.assertTrue(doc['policy']['exactFdcBindingRequired']); self.assertFalse(doc['policy']['providerIdentityInference'])
 def test_rule_registry_provenance_matches_fixture(self):
  self.assertEqual(self.rules_doc['sourceEvidenceSha256'],self.fixture['sourceEvidenceSha256']); self.assertEqual(self.rules_doc['referenceManifestSha256'],self.fixture['referenceManifestSha256']); self.assertEqual(self.rules_doc['batch'],40); self.assertEqual(self.fixture['baseRecordedBindingCount'],4961); self.assertEqual(self.fixture['baseReviewFileCount'],254)

if __name__=='__main__': unittest.main()
