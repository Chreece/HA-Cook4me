from __future__ import annotations

import gzip,hashlib,json,re,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tools'
if str(TOOLS) not in sys.path: sys.path.insert(0,str(TOOLS))
import classify_nutrition_review_queue_v60 as classifier
import compile_release_catalog_semantics_v60 as semantics
import nutrition_review_holds_v60 as holds
import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver
import snapshot_nutrition_review_checkpoint_v60 as cp

EVIDENCE_SHA='e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac'
SOURCES=tuple(TOOLS/name for name in ('release_catalog_reviewed_nutrition_targets_043.v1.json', 'release_catalog_reviewed_nutrition_targets_043b.v1.json', 'release_catalog_reviewed_nutrition_targets_043c.v1.json', 'release_catalog_reviewed_nutrition_targets_043d.v1.json', 'release_catalog_reviewed_nutrition_targets_043e.v1.json', 'release_catalog_reviewed_nutrition_targets_043f.v1.json', 'release_catalog_reviewed_nutrition_targets_043g.v1.json'))
RULES=TOOLS/'release_catalog_nutrition_bulk_family_rules_batch39.v1.json'
FIXTURE=ROOT/'tests/fixtures/nutrition-batch39-retained-reference-v60.json.gz'
SOURCE_SHAS={'release_catalog_reviewed_nutrition_targets_043.v1.json': '50c8e649652aeadc9d7d4c355edac33e2754e67e97661b1a4259ffeb50c9a086', 'release_catalog_reviewed_nutrition_targets_043b.v1.json': '6f11eff75ac3c992c829a14c1f4eca166507f020fe9bc4f2b50177bc845247f9', 'release_catalog_reviewed_nutrition_targets_043c.v1.json': 'a4829fa3a80adec528470e9fb03d532a25f7176ba16303611dc8e6ed93e518c3', 'release_catalog_reviewed_nutrition_targets_043d.v1.json': '53ca063af886c40a6dc3357d7fd23e41b85a017f5890e741ef410a1f51f0508a', 'release_catalog_reviewed_nutrition_targets_043e.v1.json': '6a3055d5b2171a877637c6664cd72b126039bab6dab9637d60556efbd0c2e940', 'release_catalog_reviewed_nutrition_targets_043f.v1.json': 'c236ce83f981c7cbb0543f0678e5e5fa5e5fe466a7a4431c2bbeda5fd14edf23', 'release_catalog_reviewed_nutrition_targets_043g.v1.json': '5fa39c0195a1599c4ef3f626d6de20df1aa723168bcb7b1dbaa7c8f38d013842'}
RULES_SHA='f50e6ea02d753a1a50f8907ec36df14c9be0bf49fcd2143ad92b9b5c213a4d76'
FIXTURE_SHA='e0bfc5e21965153678a7897c91b546a6cf39b11450c5e06a5428449d556e6d46'
BASE_BINDINGS_SHA='9bda62a97f363f4faca3a6960d6429fd5a646db2702d25edb07a4e1ab5e1404e'
BASE_REVIEW_SHA='7cdb923f673580f1771128eeafb04a7c25ae96048fe50c177875fce564aea94b'

class Batch39BulkFamilyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.documents=[json.loads(p.read_text()) for p in SOURCES]
  cls.items=[r for d in cls.documents for r in d['items']]
  cls.ids={r['reviewTargetId'] for r in cls.items}
  cls.rules_doc=json.loads(RULES.read_text()); cls.rules={r['ruleId']:r for r in cls.rules_doc['rules']}
  cls.fixture=json.loads(gzip.decompress(FIXTURE.read_bytes()))
  cls.sources={r['reviewTargetId']:r for r in cls.fixture['sources']}
  cls.targets={r['reviewTargetId']:r for r in cls.fixture['targets']}
  cls.checkpoint=cp.build_checkpoint(TOOLS); cls.source_names={p.name for p in SOURCES}

 def test_exact_file_bytes_counts_tiers_and_usage(self):
  self.assertEqual({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES},SOURCE_SHAS)
  self.assertEqual(hashlib.sha256(RULES.read_bytes()).hexdigest(),RULES_SHA); self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),FIXTURE_SHA)
  self.assertEqual(len(self.items),122); self.assertEqual(len(self.ids),122); self.assertEqual(sum(r['usageCountAtReview'] for r in self.items),1347)
  self.assertEqual(sum(r['bulkFamilyTier']=='A' for r in self.items),9); self.assertEqual(sum(r['bulkFamilyTier']=='B' for r in self.items),113)

 def test_exact_batch38_baseline_and_checkpoint_moves_to_4961(self):
  names={r['path'] for r in self.checkpoint['reviewFiles'] if r['path'] < 'release_catalog_reviewed_nutrition_targets_043'}
  bindings=[r for r in self.checkpoint['recordedBindings'] if r['reviewFile'] in names]
  reviews=[r for r in self.checkpoint['reviewFiles'] if r['path'] in names]
  self.assertEqual(len(bindings),4839); self.assertEqual(cp._digest(cp._encoded(bindings)),BASE_BINDINGS_SHA)
  self.assertEqual(cp._digest(cp._encoded(reviews)),BASE_REVIEW_SHA); self.assertGreaterEqual(self.checkpoint['summary']['recordedReviewTargetCount'],4961)

 def test_destinations_are_disjoint_and_holds_unchanged(self):
  others={r['reviewTargetId'] for r in self.checkpoint['recordedBindings'] if r['reviewFile'] not in self.source_names}
  self.assertFalse(self.ids & others); held=holds.load_holds(); self.assertEqual(len(held['targets']),12); self.assertEqual(held['registrySha256'],self.fixture['holdRegistrySha256'])
  self.assertFalse(self.ids & set(held['targets'])); self.assertFalse(set(self.sources)&set(held['targets']))

 def test_every_row_matches_exactly_one_batch39_rule(self):
  for row in self.items:
   matches=[r for r in self.rules.values() if re.match(r['pattern'],row['canonicalEnglishName'],re.I)]
   self.assertEqual(len(matches),1,row['reviewTargetId']); rule=matches[0]
   self.assertEqual(row['bulkFamilyRuleId'],rule['ruleId']); self.assertEqual(row['bulkFamilyTier'],rule['tier']); self.assertEqual(row['fdcId'],rule['fdcId']); self.assertEqual(row['fdcDescription'],rule['fdcDescription']); self.assertGreater(len(row['notes']),350)

 def test_combined_rule_loader_is_unique_anchored_and_non_approving(self):
  doc,compiled=classifier._load_rules(); self.assertIn(RULES.name,doc['registries'])
  ids=[r['ruleId'] for r,_ in compiled]; self.assertEqual(len(ids),len(set(ids)))
  for r,_ in compiled: self.assertTrue(r['pattern'].startswith('^') and r['pattern'].endswith('$'))
  self.assertFalse(doc['policy']['candidateRankIsIdentityProof']); self.assertTrue(doc['policy']['automaticRuleExpansionForbidden'])

 def test_fixture_pins_all_destinations_and_reference_records(self):
  self.assertFalse(self.fixture['fullSnapshotIncluded']); self.assertTrue(self.fixture['sourceCandidatesAreExactOriginalRecords']); self.assertEqual(self.fixture['sourceEvidenceSha256'],EVIDENCE_SHA); self.assertEqual(len(self.targets),122)
  for row in self.items:
   target=self.targets[row['reviewTargetId']]; self.assertEqual(row['canonicalEnglishName'],target['canonicalEnglishName']); self.assertEqual(row['usageCountAtReview'],target['usageCountSum']); self.assertEqual(cp.retained_reference_mismatch(row,self.sources,EVIDENCE_SHA),'')

 def test_loader_preserves_rule_and_reference_receipts(self):
  loaded=resolver.load_reviews(TOOLS)
  for row in self.items:
   got=loaded[row['reviewTargetId']]
   for k in ('fdcId','bulkFamilyRuleId','bulkFamilyTier','sourceEvidenceTargetId','sourceEvidenceCandidateRank','sourceCandidateSha256'): self.assertEqual(got[k],row[k])

 def test_remaining_queue_is_exactly_1358(self):
  rem=self.fixture['remainingAfterTargetIds']; self.assertEqual(len(rem),1358); self.assertEqual(len(set(rem)),1358); self.assertFalse(set(rem)&self.ids); self.assertEqual(self.fixture['remainingBeforeCount'],1480); self.assertEqual(self.fixture['remainingAfterCount'],1358)

 def test_classifier_counts_all_three_bulk_batches_but_approves_zero(self):
  audit={'summary':{'recordedReviewTargetCount':4961,'heldReviewTargetCount':12},'heldTargets':[], 'remainingUnheldCandidates':[], 'reviewFilesSha256':'x','registrySha256':'y'}
  evidence={'source':True}; original_read=cp._read
  def selective_read(path):
   if Path(path).name=='ignored': return evidence,EVIDENCE_SHA
   return original_read(path)
  with patch.object(holds,'audit',return_value=audit), patch.object(cp,'_read',side_effect=selective_read), patch.object(resolver,'load_reviews',return_value={}), patch.object(classifier.worklist,'validate_ledger',return_value={}): result=classifier.classify(Path('ignored'),review_root=TOOLS)
  self.assertEqual(result['summary']['batch37ExplicitReviewCount'],106); self.assertEqual(result['summary']['batch38ExplicitReviewCount'],111); self.assertEqual(result['summary']['batch39ExplicitReviewCount'],122); self.assertGreaterEqual(result['summary']['explicitBulkReviewCount'],339); self.assertEqual(result['summary']['bindingsApprovedByClassifier'],0)

 def test_named_rice_rules_exclude_generic_and_prepared_rice(self):
  _,compiled=classifier._load_rules()
  for name in ('Rice','Washed basmati rice','Basmati rice, rinsed','Rinsed basmati rice','Sushi rice, rinsed','Sushi rice, well rinsed','Japanese rice (sushi rice), well rinsed'):
   self.assertEqual(classifier._matches(name,compiled),[],name)

 def test_selected_semantic_rice_sources_have_no_hidden_prep_qualifier(self):
  payloads=[]
  for p in semantics._review_paths(TOOLS): payloads.append((p.name,cp._read(p)[0]))
  compiled=semantics.compile_semantic_concepts(payloads); concepts={c['conceptId']:c for c in compiled['concepts']}
  rice_ids={r['reviewTargetId'] for r in self.items if r['bulkFamilyRuleId'] in {'b39-basmati-long-grain-raw','b39-risotto-medium-grain-raw','b39-sushi-short-grain-raw','b39-jasmine-thai-long-grain-raw','b39-brown-rice-raw'} and r['reviewTargetKind']=='semantic-concept'}
  self.assertTrue(rice_ids)
  for tid in rice_ids:
   for m in concepts[tid]['sourceIdentities']: self.assertIsNone(re.search(r'(?i)wash|rins|soak|drain|cooked|boil|steam',m['source']),m['source'])

 def test_ambiguous_high_impact_families_remain_outside_batch39(self):
  for name in ('Rice','Pepper','Potato starch','Starch','Crème fraîche','Curry','Garam masala','Mixed herbs','Washed basmati rice'):
   self.assertNotIn(name,{r['canonicalEnglishName'] for r in self.items})

 def test_generic_fallback_notes_are_explicitly_limited(self):
  tierb=[r for r in self.items if r['bulkFamilyTier']=='B']; self.assertTrue(tierb); self.assertTrue(all(r['confidence']=='medium' for r in tierb)); self.assertTrue(all('not certified' in r['notes'] or 'not a claim' in r['notes'] for r in tierb))

 def test_direct_tier_a_is_narrow(self):
  tiera=[r for r in self.items if r['bulkFamilyTier']=='A']; self.assertTrue(tiera); self.assertTrue(all(r['confidence']=='high' for r in tiera))
  allowed={'b39-meat-nfs','b39-ground-meat-nfs-extension','b39-potato-gnocchi','b39-fish-nfs','b39-crimini-chestnut-mushroom','b39-bicarbonate','b39-drained-sweetcorn','b39-pea-pods-raw'}
  self.assertEqual({r['bulkFamilyRuleId'] for r in tiera},allowed)

 def test_rule_match_without_review_row_stays_unapproved(self):
  _,compiled=classifier._load_rules(); rows=[{'reviewTargetId':'synthetic:basmati','canonicalEnglishName':'Basmati rice','candidates':[{'fdcId':2512381}]}]; matched,b,c=classifier._partition_remaining(rows,compiled); self.assertEqual(len(matched),1); self.assertEqual(b,[]); self.assertEqual(c,[]); self.assertNotIn('synthetic:basmati',self.ids)

 def test_reference_drift_fails_closed(self):
  row=self.items[0]; self.assertEqual(cp.retained_reference_mismatch({**row,'sourceEvidenceCandidateRank':999},self.sources,EVIDENCE_SHA),'retained_reference_candidate_metadata_differs')

 def test_cli_remains_non_approving_and_refuses_overwrite(self):
  result={'schemaVersion':1,'kind':'cook4me-nutrition-review-tier-classification-v60','summary':{'remainingReviewTargetCount':1358},'tierBManual':[],'tierCContext':[]}
  with tempfile.TemporaryDirectory() as tmp, patch.object(classifier,'classify',return_value=result) as mocked:
   out=Path(tmp)/'out'; self.assertEqual(classifier.main(['--evidence','ignored','--output',str(out)]),2); before=(out/'classification.json').read_bytes(); self.assertEqual(classifier.main(['--evidence','ignored','--output',str(out)]),1); self.assertEqual(before,(out/'classification.json').read_bytes()); self.assertEqual(mocked.call_count,1)

if __name__=='__main__': unittest.main()
