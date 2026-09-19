#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("--evidence",required=True,type=Path)
p.add_argument("--decision-output",required=True,type=Path)
p.add_argument("--review-output",required=True,type=Path)
a=p.parse_args()
raw=a.evidence.read_bytes()
e=json.loads(raw.decode("utf-8"))
esha=hashlib.sha256(raw).hexdigest()
rows=e["items"]
byid={r["reviewTargetId"]:r for r in rows}
fdc={}
for i,r in enumerate(rows):
    for c in r["candidates"]:
        cand=(i,int(c["localEvidenceRank"]),r["reviewTargetId"],c)
        old=fdc.get(int(c["fdcId"]))
        if old is None or cand[:2] < old[:2]:
            fdc[int(c["fdcId"])]=cand
plan_path=Path(__file__).with_name("nutrition_accel_plan_current.v1.json")
PLAN=json.loads(plan_path.read_text(encoding="utf-8"))
WHY={
"warm-spice":"a dry mixed-spice profile; retained curry powder preserves a multi-spice dry seasoning form while cuisine-specific proportions can differ",
"mexican-seasoning":"a dry Mexican/Tex-Mex seasoning profile; retained taco seasoning preserves the chili/cumin/garlic/oregano and salt-bearing blend form while brand formulas vary",
"chili-seasoning":"a dry chili-forward seasoning profile; retained chili seasoning preserves the blended dry spice-and-salt form while paprika/chili/herb proportions vary",
"sazon":"a dry Latin/Spanish-style seasoning profile; retained sazon preserves a coriander/annatto salt-bearing seasoning form while paella formulas vary",
"dried-herbs":"a dried leafy-herb blend; retained dried oregano preserves the low-moisture herb form while oregano/basil/thyme/rosemary proportions vary",
"fresh-herbs":"a fresh aromatic-herb bundle; retained fresh thyme preserves the high-moisture leafy-herb form while the particular herb mix varies",
"fresh-parsley":"a fresh leafy-herb mixture with parsley explicitly present; retained fresh parsley preserves the ingredient state while companion herbs can vary",
"fresh-mint":"a fresh mint-containing herb garnish or seasoning; retained fresh spearmint preserves the fresh mint food form while cultivar and companion herbs can vary",
"fresh-basil":"a fresh basil/coriander alternative; retained fresh basil preserves one explicitly allowed fresh herb while the coriander alternative differs",
"pepper":"a peppercorn/pepper seasoning; retained black pepper preserves the dry pepper-spice nutrient form while pink or Sichuan pepper differ botanically",
"cinnamon-spice":"a cinnamon-forward sweet/whole-spice mixture; retained ground cinnamon preserves the dominant dry spice form while ginger, nutmeg, cardamom, bay or clove proportions vary",
"allspice":"an allspice/four-spice style dry blend; retained ground allspice preserves a representative aromatic dry-spice profile while the exact blend differs",
"five-spice":"a Chinese five-spice style dry blend; retained cinnamon is a major component and preserves a dry aromatic-spice profile while star anise, clove, fennel and pepper are not separately represented",
"salt-seasoning":"a salt-and-spice mixture; retained table salt represents the dominant sodium-bearing component while pepper, nutmeg, chili, herbs and other seasonings contribute smaller variable amounts",
"paprika":"a paprika-forward spice mixture; retained paprika preserves the dominant dried pepper-spice form while accompanying herbs or chili heat vary",
"raita":"a yogurt-based sauce; retained plain yogurt preserves the cultured-dairy base while herbs, vegetables, salt and dilution vary",
"cooked-noodles":"a precooked plain noodle product; retained cooked noodles preserve the cooked cereal-noodle form while ramen-specific wheat, alkali and brand formulation vary",
"soy-protein":"a dried soy-meat analogue; retained soy protein concentrate preserves the concentrated soy-protein base while extrusion, seasoning and rehydration differ",
"dried-fruit":"a mixed dried-fruit ingredient; retained dried fruit NFS preserves the dehydrated fruit form while the fruit blend and added sugar vary",
"plant-cream":"a liquid plant-based cream substitute; retained light liquid cream substitute preserves the non-dairy creamy liquid form while plant source, fat and stabilizers vary",
"fresh-cream":"a fresh cream option; retained heavy cream preserves the plain high-fat dairy-cream form while an allowed soft-cheese alternative or chili seasoning can change the final profile",
"tofu-cream":"a tofu-based creamy ingredient; retained silken firm tofu preserves the soy-curd base while blending and added seasonings can change water and fat content",
"fresh-cheese":"a high-moisture fresh dairy cheese; retained cream-cheese spread preserves a fresh creamy-cheese profile while quark can be leaner and higher in protein",
"bisque":"a creamy shellfish-soup form; retained generic bisque preserves the thick soup category while lobster, cream, stock and alcohol proportions vary",
"dry-bouillon":"a dry stock-cube/granule ingredient; retained dry bouillon preserves the concentrated salty stock form while vegetable/meat flavor and sodium vary",
"dry-beef-bouillon":"a dry consomme/bouillon seasoning; retained beef bouillon powder preserves the dry concentrated stock-seasoning form while meat source and sodium vary",
"vegetable-stock":"a liquid vegetable-stock option; retained ready-to-serve vegetable broth preserves the liquid vegetable-stock form while salt concentration varies",
"generic-stock":"a generic liquid stock/broth option; retained generic broth preserves the liquid stock form while species, concentration and any water alternative remain uncertain",
"dry-umami-bouillon":"a dry umami stock powder; retained dry bouillon preserves the concentrated sodium-bearing stock-powder form while dashi uses kelp/bonito rather than beef",
"curry-paste":"a concentrated wet curry seasoning; retained curry sauce preserves the wet spiced-curry family while paste concentration, oil, coconut, salt and regional style vary",
"soy-sauce":"a dark soy sauce; retained shoyu preserves the fermented soy-and-wheat sauce identity while dark soy can contain more caramel and sweetness",
"soy-dipping-sauce":"a concentrated noodle dipping sauce whose dominant seasoning is soy sauce; retained shoyu preserves the salty fermented-soy base while dashi and sweetener vary",
"fermented-soy-paste":"a fermented soybean paste; retained miso sauce preserves the fermented soy seasoning family while cheonggukjang has different organisms, texture and salt content",
"sugar-substitute":"a powdered/granulated low-calorie sugar substitute; retained sugar-substitute NFS preserves the functional sweetener category while erythritol/monk-fruit chemistry and bulking agents vary",
"syrup":"a sweet carbohydrate syrup; retained syrup NFS preserves the liquid concentrated-carbohydrate form while oligosaccharide composition and digestibility differ"
}
items=[]
seen=set()
for tid,fid,conf,kind in PLAN:
    if tid in seen: raise SystemExit(f"duplicate plan target {tid}")
    seen.add(tid)
    if tid not in byid: raise SystemExit(f"missing review target {tid}")
    if fid not in fdc: raise SystemExit(f"missing retained FDC {fid}")
    r=byid[tid]
    _,rank,src,c=fdc[fid]
    name=r["canonicalEnglishName"]
    note=(f"Manual semantic review binds Cook4Me '{name}' to retained USDA '{c['description']}' as a target-specific nutrient-profile proxy because it is {WHY[kind]}. "
          f"Confidence is {conf}; this approval creates no culinary substitution rule and does not authorize automatic reuse for other ingredients.")
    items.append({"approved":True,"reviewTargetId":tid,"reviewTargetKind":r["reviewTargetKind"],"canonicalEnglishName":name,"fdcId":fid,"confidence":conf,"fdcDescription":c["description"],"fdcDataType":c["dataType"],"sourceEvidenceTargetId":src,"sourceEvidenceCandidateRank":rank,"notes":note})
decision={"schemaVersion":1,"kind":"cook4me-fdc-retained-reference-review-decisions-v60","catalogVersion":e["catalogVersion"],"referenceManifestSha256":e["referenceManifestSha256"],"sourceEvidenceSha256":esha,"evidenceBindingScope":"retained-reference-record","policy":{"manualSemanticReviewPerformed":True,"candidateSearchIsIdentityProof":False,"searchResultAutoAccepted":False,"automaticSelectionPerformed":False,"exactFdcBindingRequired":True,"providerIdentityInference":False},"items":items}
a.decision_output.write_text(json.dumps(decision,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
a.review_output.write_text("{}\n",encoding="utf-8")
print(json.dumps({"evidenceSha":esha,"targetCount":len(items),"usageSum":sum(max(0,int(byid[x[0]].get("usageCountSum") or 0)) for x in PLAN),"providerTargets":sum(byid[x[0]]["reviewTargetKind"]=="provider-identity" for x in PLAN)},ensure_ascii=False))
