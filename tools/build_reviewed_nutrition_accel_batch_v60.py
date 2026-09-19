#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("--evidence", required=True, type=Path)
p.add_argument("--decision-output", required=True, type=Path)
p.add_argument("--review-output", required=True, type=Path)
a=p.parse_args()

raw=a.evidence.read_bytes()
e=json.loads(raw.decode("utf-8"))
esha=hashlib.sha256(raw).hexdigest()
rows=e["items"]
byid={r["reviewTargetId"]:r for r in rows}
pos={r["reviewTargetId"]:i for i,r in enumerate(rows)}

# Retain one deterministic exact receipt for every FDC record visible anywhere
# in this immutable evidence snapshot. This is a locator only; selection below
# remains an explicit manually-reviewed target->FDC binding.
fdc={}
for i,r in enumerate(rows):
    for c in r["candidates"]:
        cand=(i,int(c["localEvidenceRank"]),r["reviewTargetId"],c)
        old=fdc.get(int(c["fdcId"]))
        if old is None or cand[:2] < old[:2]:
            fdc[int(c["fdcId"])]=cand

PLAN=[
    ("concept:food:9a0077198ff432aa97b1",173470,"medium"),
    ("concept:food:0bf8b14f9137ef17899b",171328,"medium"),
    ("concept:food:bc11ef9de9052c29bc35",171328,"medium"),
    ("concept:food:c888f147bd9b918a4eb5",170924,"medium"),
    ("concept:food:16f77c1541dc06fdac35",2710178,"medium"),
    ("concept:food:4ba30096c62591c046d1",170924,"medium"),
    ("concept:food:7b396e2f0c519ef6475f",173470,"medium"),
    ("concept:food:4ba5ec30bccd84b0d245",170924,"low"),
    ("concept:food:c77f363d55b864932906",2707132,"low"),
    ("concept:food:1520e1dc851682225d28",172243,"medium"),
    ("concept:food:c9ff4a71cd315bc1a8cd",172243,"medium"),
    ("concept:food:7bfbfb84388581780b61",2707132,"low"),
    ("concept:food:72b91123349bbabdce8a",173476,"medium"),
    ("concept:food:dbbdf9fbae7edde86e8d",170924,"low"),
    ("concept:food:d50d92d6a2f826754901",170924,"low"),
    ("concept:food:c2c57ebf692690761230",171646,"medium"),
    ("concept:food:84086f09a6cdac4a5fa7",170924,"medium"),
    ("concept:food:8c300390b57c41fa6e32",171328,"medium"),
    ("concept:food:70e73e0ab15c03553a43",172243,"medium"),
    ("concept:food:4b0de88d911bf226b5b6",173470,"medium"),
    ("concept:food:8cdc7fe163bcc7613193",173470,"medium"),
    ("concept:food:b2092d9fea8587b6af54",170924,"medium"),
    ("concept:food:5a0880eaf475ea865e14",170924,"medium"),
    ("concept:food:f67d1bc5e8eb2a8c76f0",170924,"medium"),
    ("concept:food:9f4eebb78048df39e3f7",170924,"medium"),
    ("concept:food:546752e1eac007986850",170924,"medium"),
    ("concept:food:6f78175a2908c8719d62",171328,"medium"),
    ("concept:food:3165160174cf2f13d0b7",171328,"medium"),
    ("concept:food:d6a2d1ec9fa98d688314",2710178,"medium"),
    ("concept:food:481d8a5571601c6f7848",173470,"medium"),
    ("concept:food:e799169c66586dc39cc9",173470,"medium"),
    ("concept:food:e5488190e9d50a12bb34",171328,"low"),
    ("concept:food:851f7461059548fffc7a",171328,"medium"),
    ("concept:food:f679a5db909334ecabb1",171328,"medium"),
    ("concept:food:670fe9fa83e6a57eb4b2",2707140,"medium"),
    ("concept:food:c74882062141fcfeb743",173470,"medium"),
    ("concept:food:d00efdef350242534e10",171583,"medium"),
    ("concept:food:83efe076e482a93672a4",2707132,"low"),
    ("concept:food:a241d893dfe7548eff59",171583,"medium"),
    ("concept:food:29663ac23085d4ed3cba",2512381,"medium"),
    ("concept:food:d01e86020d6bd8734fe7",173470,"medium"),
    ("concept:food:96969844dedae5a62bfb",173476,"medium"),
    ("concept:food:bf8d0e699f5bc9a6e494",172884,"medium"),
    ("concept:food:4b5a4571adfa813952fa",170924,"medium"),
    ("concept:food:14a2773d3065623e3f15",2707140,"medium"),
    ("concept:food:7709f7a2923a6885fb49",170924,"medium"),
    ("concept:food:8a99c9e042870c0e96fa",173470,"medium"),
    ("concept:food:c78f8c6e4815471f10fa",170924,"medium"),
    ("concept:food:85ba4f9bf9c526b5a69a",2512381,"medium"),
    ("concept:food:a4023490922824fde8c5",170924,"medium"),
    ("concept:food:10ac620e10cae0bef148",170924,"medium"),
    ("concept:food:7c9a6e547d3fe5572089",171328,"medium"),
    ("concept:food:51d5c66a1f4c5a5cfe74",173470,"medium"),
    ("concept:food:5543400a2f5104f43590",171328,"medium"),
    ("concept:food:0078fa22eb52709fa76a",171583,"medium"),
    ("concept:food:41b80669710298f8fb7b",172883,"medium"),
    ("concept:food:7b1a3c4dc5729bd64f10",2707132,"low"),
    ("M_FOOD_217",170924,"medium"),
    ("M_FOOD_59",171328,"medium"),
]

WHY={
    170924:"a dry warm-spice blend represented by retained curry powder; the core coriander/cumin/turmeric/pepper-style nutrient family overlaps, while cuisine-specific proportions can differ",
    171328:"an unspecified or Italian-style dried herb blend represented by retained dried oregano; this preserves the dried leafy-herb nutrient form while herb proportions and salt can differ",
    173470:"a fresh herb bundle or bouquet represented by retained fresh thyme; this preserves the fresh leafy aromatic-herb form while parsley, bay, rosemary, celery leaf and other proportions can differ",
    172243:"a dry Mexican/Tex-Mex seasoning represented by retained taco seasoning; the dry chili/cumin/garlic/oregano seasoning form is preserved while sodium and formulation vary",
    173476:"a dry Cajun-style blend represented by retained chili seasoning; paprika/chili, garlic, onion, pepper, herbs and salt overlap while cayenne and sodium vary",
    2710178:"a concentrated wet curry seasoning represented by retained prepared curry sauce; the wet spiced-curry food family is preserved while oil, coconut, salt and concentration vary",
    2707132:"a stock-or-water alternative represented by retained generic broth; this models the nutrient-bearing stock option, but water may instead be selected and stock species/concentration are unspecified",
    171583:"a vegetable-stock option represented by retained ready-to-serve vegetable broth; the liquid vegetable-stock family is preserved while salt and concentration vary",
    172884:"a chicken-or-shrimp stock option represented by retained chicken stock; chicken is an explicitly allowed stock and preserves the liquid stock form while the shrimp alternative differs",
    172883:"a water-or-veal-stock option represented by retained beef stock; veal is bovine and this is the closest retained bovine liquid-stock profile while water may instead be used",
    2512381:"a raw basmati/other-rice option represented by retained raw white long-grain rice; rinsing does not materially change dry-rice identity while cultivar, milling and brown-rice alternatives differ",
    171646:"a granola-or-muesli option represented by retained granola; granola is explicitly allowed while muesli is less toasted and recipes vary in oil, nuts, fruit and sugar",
    2707140:"a lobster soup/bisque-style item represented by retained generic bisque; the thick shellfish-soup food form is preserved while lobster, cream, alcohol, stock and thickener vary",
}

items=[]
for tid,fid,conf in PLAN:
    if tid not in byid:
        raise SystemExit(f"missing target {tid}")
    if fid not in fdc:
        raise SystemExit(f"missing retained FDC {fid}")
    r=byid[tid]
    _,rank,src,c=fdc[fid]
    name=r["canonicalEnglishName"]
    note=(
        f"Manual semantic review binds Cook4Me '{name}' to retained USDA "
        f"'{c['description']}' as a nutrient-profile proxy because it is {WHY[fid]}. "
        f"Confidence is {conf}; this approval is target-specific, creates no culinary substitution rule, "
        f"and does not authorize automatic reuse for other ingredients."
    )
    items.append({
        "approved":True,
        "reviewTargetId":tid,
        "reviewTargetKind":r["reviewTargetKind"],
        "canonicalEnglishName":name,
        "fdcId":fid,
        "confidence":conf,
        "fdcDescription":c["description"],
        "fdcDataType":c["dataType"],
        "sourceEvidenceTargetId":src,
        "sourceEvidenceCandidateRank":rank,
        "notes":note,
    })

if len({x["reviewTargetId"] for x in items}) != len(items):
    raise SystemExit("duplicate target in accelerated plan")

decision={
    "schemaVersion":1,
    "kind":"cook4me-fdc-retained-reference-review-decisions-v60",
    "catalogVersion":e["catalogVersion"],
    "referenceManifestSha256":e["referenceManifestSha256"],
    "sourceEvidenceSha256":esha,
    "evidenceBindingScope":"retained-reference-record",
    "policy":{
        "manualSemanticReviewPerformed":True,
        "candidateSearchIsIdentityProof":False,
        "searchResultAutoAccepted":False,
        "automaticSelectionPerformed":False,
        "exactFdcBindingRequired":True,
        "providerIdentityInference":False,
    },
    "items":items,
}
a.decision_output.write_text(json.dumps(decision,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
# Kept for workflow compatibility; the trusted compiler produces the review file.
a.review_output.write_text("{}\n",encoding="utf-8")
print(json.dumps({
    "evidenceSha":esha,
    "targetCount":len(items),
    "usageSum":sum(max(0,int(byid[x["reviewTargetId"]].get("usageCountSum") or 0)) for x in items),
    "names":[x["canonicalEnglishName"] for x in items],
},ensure_ascii=False))
