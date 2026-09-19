import argparse, json, hashlib
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--evidence', required=True, type=Path)
parser.add_argument('--decision-output', required=True, type=Path)
parser.add_argument('--review-output', required=True, type=Path)
args=parser.parse_args()
EVID=args.evidence
DEC=args.decision_output
REV=args.review_output

def encoded(v):
    return (json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()
def digest(b): return hashlib.sha256(b).hexdigest()

e=json.loads(EVID.read_text())
e_sha=digest(EVID.read_bytes())
manifest=e['referenceManifestSha256']; catalog=e['catalogVersion']
rows=e['items']; byid={r['reviewTargetId']:r for r in rows}; pos={r['reviewTargetId']:i for i,r in enumerate(rows)}
# global FDC receipt index, deterministic earliest evidence position then rank
fdc={}
for i,r in enumerate(rows):
    for c in r['candidates']:
        k=c['fdcId']; cand=(i,c['localEvidenceRank'],r['reviewTargetId'],c)
        if k not in fdc or cand[:2] < fdc[k][:2]: fdc[k]=cand

# id, fdc, confidence, note-kind
M=[]
def add(tid, fdcid, conf, kind):
    assert tid in byid, tid
    assert fdcid in fdc, fdcid
    M.append((tid,fdcid,conf,kind))

# Rice family
for tid in [
'concept:food:d475265f55cce204989d','M_FOOD_421','concept:food:bf4a2f0ce31a454ad482',
'concept:food:3b9db8fb0d86e0ebf36d','concept:food:ed7921fb8ad8850d6541','concept:food:da5abe8ff4db931dba5d',
'concept:food:6ea76618cbacba09032a','concept:food:126ec9e57ec17133b3d8','concept:food:29e6ad40e1f3cf6cf10e',
'concept:food:95831653b0bf271dd21c','concept:food:7b3e7d0e218bb1d1a4e2','concept:food:1e2e54ca2ff4854d6971',
'concept:food:bf05b1f0b567858fe367']:
    add(tid,2512381,'medium','rice-long')
for tid in ['concept:food:7b31531574b9350619e4','concept:food:8aaacbda8c4051a8d5cf']:
    add(tid,169760,'medium','rice-medium')

# Stocks / bouillon
add('concept:food:d350b8a74804a01034ec',172883,'medium','veal-stock')
add('M_FOOD_208',172883,'medium','veal-stock')
add('concept:food:8378d0091c36fda8fb81',172883,'medium','meat-stock')
add('M_FOOD_659',172883,'medium','meat-stock')
for tid in ['concept:food:d7dbd58f263c6dc867b1','concept:food:cc53a76ea5366250cfe4','concept:food:4564b408fdd3dc447087',
            'concept:food:b24f3f4ecd5c307d89fd','concept:food:78a946baa820a4f56d04','concept:food:826eb8833ac1e5fab3cf',
            'concept:food:56acc3589f6c769c4451','concept:food:ef92f6e36404089ee9cc','concept:food:a20a7fdfaabdb7c0d3d6',
            'concept:food:d21aaf9f187412801d7a','concept:food:c528519d1b62230372f1','concept:food:083d127ce9b452962bb1',
            'concept:food:5083b4442f649d8e4543']:
    add(tid,172884,'medium','chicken-stock')
add('concept:food:a229b6daf2752fd25a7c',171583,'medium','vegetable-stock-alt')
add('concept:food:ea76ae631d69c831ee79',172883,'medium','beef-stock-alt')
for tid in ['concept:food:563f83ee2a387f52b41a','concept:food:447021a5ec6f8fcb58e8']:
    add(tid,171560,'medium','dry-bouillon')

# Fermented / Japanese seasoning sauces
for tid in ['concept:food:01ecc202d862d5646373','concept:food:629ee2f9ca49d1e11110']:
    add(tid,174277,'medium','mentsuyu')
for tid in ['concept:food:e81a79dd7c99526e527a','concept:food:36e6b19c70236b6a6245']:
    add(tid,2707438,'medium','doenjang')
for tid in ['concept:food:5f289b53be804efe6003','concept:food:c5ee6e18f27d29fd44f6','concept:food:1cfdee74a53620c517ca',
            'concept:food:c9da619743be56f6337e','concept:food:027830b61f28c1889978','concept:food:755b313df80621bbd8a6']:
    add(tid,174277,'medium','ponzu')
for tid in ['concept:food:78b9a2db762f27300c40','concept:food:9fa7e983b8719389e14d','concept:food:0327c9db96a7e9e79a69']:
    add(tid,2707445,'medium','sweet-soy-sauce')
for tid in ['concept:food:78f12ab3bec23eb3d649','M_FOOD_839','concept:food:633c8bc90c4f716c2b1c']:
    add(tid,2709752,'medium','brown-table-sauce')
add('concept:food:6ab76e5300dd0c645e2a',2707546,'medium','satay')
add('M_FOOD_381',2710175,'medium','pistou')

# Tea / wine
for tid in ['concept:food:6409907fc2828a1764ad','concept:food:994c082d56d84b39ecf4','concept:food:8b05eb4a8bc1564e03eb']:
    add(tid,2710490,'medium','green-tea')
for tid in ['concept:food:eab3363c59053eaa94e6','concept:food:62bf85d8452fa206ceed']:
    add(tid,174837,'medium','vin-jaune')

# Other direct food-family matches
add('concept:food:ee58231eb3a30e4286c1',173431,'high','parmesan-alt')
add('concept:food:553c12a29000e002b141',175132,'medium','roe')
add('concept:food:0026e3ff92085345a383',170579,'high','toasted-coconut')
for tid in ['concept:food:f183cee464ded3c1c18e','concept:food:5697f100482ba025b2b3']:
    add(tid,170567,'medium','toasted-almond')
add('M_FOOD_393',168039,'high','polenta')
add('concept:food:379823ce461df70dc2fd',167859,'medium','trotters')
for tid in ['concept:food:c6f7e54b50f5d33b5413','concept:food:be938b71b3c654ee5e01']:
    add(tid,2706230,'medium','smoked-trout')
add('concept:food:9648bfa5871e90f409c4',2706224,'medium','whole-fish')
add('concept:food:75d0f260f6acfeabb315',2258588,'medium','carliston')
add('concept:food:a445ff5a78841c3ab216',169311,'medium','marinated-artichoke')
add('concept:food:bee74c53fd7d42e21b3e',174286,'medium','mixed-beans')
add('concept:food:5de923e3d4abe8a0c716',169998,'medium','baby-corn-alt')
for tid in ['concept:food:d19e171d560ca07e1e23','concept:food:c8fbf7b74cbbd30c7b20']:
    add(tid,2346386,'high','heavy-cream')

assert len({x[0] for x in M})==len(M)

def note(name, desc, kind):
    if kind=='rice-long':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA Foundation '{desc}' through an exact retained record in the same immutable evidence snapshot. The destination denotes plain rice in its uncooked ingredient state; washing, soaking, draining, or broken-grain preparation does not materially change the underlying dry-rice nutrient identity. Confidence remains medium because cultivar, grain length, enrichment, and milling can vary; this decision does not generalize to cooked, fried, flavored, brown, glutinous, or mixed-grain rice."
    if kind=='rice-medium':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' through an exact retained record in the same immutable evidence snapshot. Egyptian rice is commonly a white medium/short-grain rice and the destination is used before cooking; washing or soaking does not materially change the base dry-rice identity. Confidence remains medium because cultivar and enrichment vary; this decision does not generalize to cooked, brown, glutinous, or flavored rice."
    if kind=='veal-stock':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' as the closest retained bovine stock profile in the same immutable evidence snapshot. Veal and beef stocks share the same bovine stock base and liquid culinary form. Confidence remains medium because calf versus adult cattle, bone/meat ratio, reduction, salt, and gelatin concentration vary; this decision does not generalize to meat cuts, bouillon powder, or non-bovine stock."
    if kind=='meat-stock':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' as the closest retained generic meat-stock profile in the same immutable evidence snapshot. Beef stock is used as the pinned representative for unspecified meat stock while preserving the liquid stock form. Confidence remains medium because the source animal, salt, reduction, and formulation are unspecified; this decision does not generalize to dry bouillon, gravy, or whole meat."
    if kind=='chicken-stock':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' through an exact retained stock record in the same immutable evidence snapshot. The destination explicitly permits or identifies chicken/poultry stock, and the retained profile preserves the home-prepared liquid-stock form. Confidence remains medium where alternative stocks or water are also permitted because salt, reduction, and selected alternative can differ; this decision does not generalize to chicken meat or dry bouillon."
    if kind=='vegetable-stock-alt':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' through an exact retained vegetable-broth record in the same immutable evidence snapshot. The destination explicitly permits vegetable stock, so ready-to-serve vegetable broth is the closest pinned liquid vegetable-stock profile. Confidence remains medium because chicken stock is an allowed alternative and salt/reduction vary; this decision does not generalize to dry stock cubes or vegetable dishes."
    if kind=='beef-stock-alt':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' through an exact retained beef-stock record in the same immutable evidence snapshot. The destination explicitly permits beef stock, so the home-prepared beef-stock profile preserves the liquid stock form. Confidence remains medium because chicken stock is an allowed alternative and salt/reduction vary; this decision does not generalize to whole beef or dry bouillon."
    if kind=='dry-bouillon':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' through an exact retained dry bouillon record in the same immutable evidence snapshot. The destination identifies a dry meat-bouillon/stock-cube seasoning, so powdered beef bouillon is the closest pinned dry concentrated stock profile. Confidence remains medium because meat species, cube formulation, sodium, and serving dilution vary; this decision does not generalize to prepared liquid stock or whole meat."
    if kind=='mentsuyu':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' as the closest retained soy-based seasoning profile in the same immutable evidence snapshot. Mentsuyu is a concentrated soy-sauce-based noodle seasoning with dashi and sweetener, so shoyu preserves its dominant salty soy component. Confidence remains medium because dashi, mirin/sugar, and concentration materially affect sodium and carbohydrate; this decision does not generalize to plain broth or undiluted soy sauce as a culinary substitute."
    if kind=='doenjang':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA FNDDS '{desc}' as the closest retained fermented-soy seasoning profile in the same immutable evidence snapshot. Doenjang and miso are fermented soybean pastes/sauces with similar high-protein, high-sodium seasoning roles. Confidence remains medium because grain content, fermentation, moisture, and sodium differ; this decision does not generalize to tofu, soybean oil, or unfermented soybeans."
    if kind=='ponzu':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' as the closest retained base profile in the same immutable evidence snapshot. Ponzu is a citrus-seasoned soy sauce, and shoyu preserves its dominant soy-sauce component. Confidence remains medium because citrus juice, vinegar, dashi, and sweetener alter sodium, sugars, and acidity; this decision does not generalize to plain soy sauce as a culinary substitute."
    if kind=='sweet-soy-sauce':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA FNDDS '{desc}' as the closest retained sweet soy-based Japanese sauce profile in the same immutable evidence snapshot. The destination is a sweet-savory grilling/glazing sauce built around soy sauce, matching teriyaki at the nutrient-family level. Confidence remains medium because sugar, mirin, fruit, garlic, and reduction vary; this decision does not generalize to plain soy sauce or unrelated barbecue sauces."
    if kind=='brown-table-sauce':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA FNDDS '{desc}' as the closest retained thick brown table-sauce profile in the same immutable evidence snapshot. Chuno/tonkatsu-style sauces and steak sauce are sweet, acidic, spiced brown condiments with comparable culinary form. Confidence remains medium because fruit, Worcestershire-style seasonings, sugar, and sodium vary; this decision does not generalize to tomato ketchup, soy sauce, or curry sauce."
    if kind=='satay':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA FNDDS '{desc}' through an exact retained peanut-sauce record in the same immutable evidence snapshot. Satay sauce is characteristically peanut-based, so the retained profile preserves the dominant fat/protein/carbohydrate source. Confidence remains medium because coconut milk, sugar, soy, chili, and concentration vary; this decision does not generalize to plain peanut butter or soy sauce."
    if kind=='pistou':
        return f"Manual semantic review binds Cook4Me provider identity '{name}' to USDA FNDDS '{desc}' as the closest retained herb-oil sauce profile in the same immutable evidence snapshot. Pistou and pesto share a basil/garlic/oil base, although pistou commonly omits nuts and cheese. Confidence remains medium because those additions materially affect fat and protein; this decision does not generalize to tomato pesto or cream sauces."
    if kind=='green-tea':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA FNDDS '{desc}' through an exact retained brewed-green-tea record in the same immutable evidence snapshot. Sencha and most jasmine/genmaicha preparations are green-tea based, so the brewed green-tea profile matches the beverage state. Confidence remains medium because white-tea alternatives, roasted rice, jasmine scenting, and brew strength vary; this decision does not generalize to matcha powder, sweetened tea, or milk tea."
    if kind=='vin-jaune':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' through an exact retained white-table-wine record in the same immutable evidence snapshot. Vin jaune is an oxidative dry white wine, so table white wine preserves the alcoholic beverage family and liquid cooking form. Confidence remains medium because alcohol, residual sugar, acidity, and oxidative aging differ; this decision does not generalize to spirits, fortified wine, or vinegar."
    if kind=='parmesan-alt':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' through an exact retained Parmesan record in the same immutable evidence snapshot. Parmigiano Reggiano is explicitly one of the allowed cheeses and is nutritionally represented directly by Parmesan. Confidence is high for the Parmesan alternative; this decision does not generalize to unrelated soft cheeses, while Pecorino can differ modestly in fat, protein, and sodium."
    if kind=='roe':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' as the closest retained fish-roe profile in the same immutable evidence snapshot. Tarako is cod roe, so mixed-species raw fish roe preserves the egg/roe food family and nutrient density. Confidence remains medium because cod species, salting, membrane removal, and curing materially affect sodium and water; this decision does not generalize to caviar substitutes or fish flesh."
    if kind=='toasted-coconut':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' through an exact retained toasted dried-coconut record in the same immutable evidence snapshot. The destination explicitly specifies toasted coconut flakes, so the food form matches directly. Confidence is high aside from possible sweetening and flake-size differences; this decision does not generalize to fresh coconut, coconut milk, or sweetened coconut unless specified."
    if kind=='toasted-almond':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' through an exact retained plain-almond record in the same immutable evidence snapshot. Flaking/slivering changes only shape and light toasting changes moisture slightly while preserving the almond nutrient identity. Confidence remains medium because commercial toasted almonds may include oil or salt; this decision does not generalize to almond butter, almond flour, or sugar-coated almonds."
    if kind=='polenta':
        return f"Manual semantic review binds Cook4Me provider identity '{name}' to USDA SR Legacy '{desc}' through an exact retained yellow-cornmeal record in the same immutable evidence snapshot. Dry polenta is coarsely ground cornmeal, so the ingredient identity matches directly at the grain-product level. Confidence is high for dry plain polenta; this decision does not generalize to cooked polenta, taragna blends, or seasoned instant polenta."
    if kind=='trotters':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' as the closest retained trotter/feet record in the same immutable evidence snapshot. Culinary 'trotters' most commonly denotes pig's feet, preserving the anatomical cut and species typically intended. Confidence remains medium because the destination does not state species or cooking state; this decision does not generalize to lamb/calf feet or prepared pickled/braised trotters."
    if kind=='smoked-trout':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA FNDDS '{desc}' through an exact retained generic smoked-fish record in the same immutable evidence snapshot. The destination explicitly specifies smoked trout, so the retained profile preserves the smoking process and fish food family. Confidence remains medium because trout species, brining, fat content, and smoking method vary; this decision does not generalize to raw/fried fish."
    if kind=='whole-fish':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA FNDDS '{desc}' through an exact retained generic-fish record in the same immutable evidence snapshot. The destination leaves fish species unspecified, so Fish NFS is the closest pinned generic fish profile; cleaning and seasoning are preparation qualifiers. Confidence remains medium because species, fat content, edible yield, and cooking state vary; this decision does not generalize to shellfish or breaded fish."
    if kind=='carliston':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA Foundation '{desc}' as the closest retained fresh green sweet-pepper profile in the same immutable evidence snapshot. Çarliston is a long Turkish green pepper cultivar commonly used like a sweet/mild green pepper; cutting into strips does not change identity. Confidence remains medium because cultivar pungency and maturity vary; this decision does not generalize to hot chilies or dried pepper."
    if kind=='marinated-artichoke':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' as the closest retained prepared-artichoke profile in the same immutable evidence snapshot. The destination is a preserved/marinated globe artichoke, and the cooked drained salted record preserves the vegetable and prepared state. Confidence remains medium because oil, vinegar, herbs, and marinade retention can materially add fat and sodium; this decision does not generalize to raw artichoke or artichoke dip."
    if kind=='mixed-beans':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' as the closest retained canned-bean profile in the same immutable evidence snapshot. Mixed canned beans are a blend of cooked legumes, and canned drained pinto beans provide a representative prepared-bean nutrient profile. Confidence remains medium because bean proportions and packing liquid vary; this decision does not generalize to baked beans, refried beans, or bean dishes with meat."
    if kind=='baby-corn-alt':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA SR Legacy '{desc}' through an exact retained sweet-corn record in the same immutable evidence snapshot. Sweetcorn is explicitly permitted as an alternative, so the retained raw sweet-corn profile represents that allowed ingredient. Confidence remains medium because baby corn differs in maturity and nutrient density; this decision does not generalize to creamed corn or cornmeal."
    if kind=='heavy-cream':
        return f"Manual semantic review binds Cook4Me '{name}' to USDA Foundation '{desc}' through an exact retained heavy-cream record in the same immutable evidence snapshot. The destination explicitly specifies thick fresh cream, for which heavy cream is the closest plain high-fat dairy cream profile. Confidence is high at the food-family level, while commercial thickened cream can vary in stabilizers and fat percentage; this decision does not generalize to low-fat cream, crème fraîche, or plant cream."
    raise KeyError(kind)

# Build decisions
items=[]
for tid,fdcid,conf,kind in M:
    r=byid[tid]; _,rank,src,c=fdc[fdcid]
    items.append({
        'approved':True,'reviewTargetId':tid,'reviewTargetKind':r['reviewTargetKind'],'canonicalEnglishName':r['canonicalEnglishName'],
        'fdcId':fdcid,'confidence':conf,'fdcDescription':c['description'],'fdcDataType':c['dataType'],
        'sourceEvidenceTargetId':src,'sourceEvidenceCandidateRank':rank,'notes':note(r['canonicalEnglishName'],c['description'],kind)
    })
dec={
 'schemaVersion':1,'kind':'cook4me-fdc-retained-reference-review-decisions-v60','catalogVersion':catalog,
 'referenceManifestSha256':manifest,'sourceEvidenceSha256':e_sha,'evidenceBindingScope':'retained-reference-record',
 'policy':{'manualSemanticReviewPerformed':True,'candidateSearchIsIdentityProof':False,'searchResultAutoAccepted':False,'automaticSelectionPerformed':False,'exactFdcBindingRequired':True,'providerIdentityInference':False},
 'items':items,
}
dec_bytes=encoded(dec); dec_sha=digest(dec_bytes); DEC.write_bytes(dec_bytes)

# Compile retained review exactly
reviewed=[]; receipts={}
for x in items:
    tid=x['reviewTargetId']; r=byid[tid]; fdcid=x['fdcId']; _,rank,src,c=fdc[fdcid]
    csha=digest(encoded(c)); receipt={'sourceEvidenceTargetId':src,'sourceEvidenceCandidateRank':rank,'sourceCandidateSha256':csha}
    k=str(fdcid)
    if k in receipts and receipts[k]!=receipt: raise RuntimeError('conflict receipt')
    receipts[k]=receipt
    reviewed.append((pos[tid],{
      'reviewTargetId':tid,'reviewTargetKind':r['reviewTargetKind'],'canonicalEnglishName':r['canonicalEnglishName'],
      'fdcId':fdcid,'confidence':x['confidence'],'fdcDescription':c['description'],'fdcDataType':c['dataType'],
      'usageCountAtReview':max(0,int(r.get('usageCountSum') or 0)),'notes':x['notes'],'sourceEvidenceSha256':e_sha,
      'sourceEvidenceTargetId':src,'sourceEvidenceCandidateRank':rank,'sourceCandidateSha256':csha,
    }))
reviewed.sort(key=lambda z:z[0]); review_items=[x for _,x in reviewed]
rev={
 'schemaVersion':1,'kind':'cook4me-reviewed-nutrition-target-source','catalogVersion':catalog,'referenceManifestSha256':manifest,
 'evidenceKind':'cook4me-fdc-review-target-candidate-evidence-offline-v60','evidenceBindingScope':'retained-reference-record','sourceEvidenceSha256':e_sha,
 'policy':{'searchResultAutoAccepted':False,'exactFdcBindingRequired':True,'semanticConceptGroupingReviewed':True,'providerIdentityInference':False,'candidateSearchIsIdentityProof':False},
 'selectionMethod':'explicit-semantic-review','decisionMethod':'manual-retained-reference-binding','referenceReceipts':receipts,
 'items':review_items,'reviewDecisionSha256':dec_sha,
}
REV.write_bytes(encoded(rev))
print(json.dumps({
 'evidenceSha':e_sha,'decisionSha':dec_sha,'decisionBytes':len(dec_bytes),'reviewBytes':REV.stat().st_size,
 'targetCount':len(items),'usageSum':sum(x['usageCountAtReview'] for x in review_items),
 'providerTargets':sum(x['reviewTargetKind']=='provider-identity' for x in review_items),
 'names':[x['canonicalEnglishName'] for x in review_items]
},ensure_ascii=False,indent=2))
