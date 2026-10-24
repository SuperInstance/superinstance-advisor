import json,re,sys,importlib.util,os
sys.path.insert(0,"/tmp/advisor")
spec=importlib.util.spec_from_file_location("upstream_taps","/tmp/advisor/taps_creative_break.py")
up=importlib.util.module_from_spec(spec); spec.loader.exec_module(up)
tag=sys.argv[1]
A=json.load(open(f"/tmp/work/{tag}.json"))
V=A["voices"]; VOICES=("zai","qwen","kimi")
fail=[]
def chk(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    if not ok: fail.append(name)

# G1 distinct models
models=[A["models"][v] for v in VOICES]
chk("G1 distinct models", len(set(models))==3, str(dict(zip(VOICES,models))))
# G2 distinct postures
post=[A["postures"][v] for v in VOICES]
chk("G2 distinct postures", len(set(post))==3, str(post))
# G1b byte-distinct p1
p1s=[V[v]["p1"] for v in VOICES]
chk("G1b p1 byte-distinct", len(set(p1s))==3, f"lens={[len(p) for p in p1s]}")
chk("G1c p1 min length >800", all(len(p)>800 for p in p1s), f"min={min(len(p) for p in p1s)}")
# G6b distinct opening clauses
def first_clause(t):
    s=re.split(r"(?<=[.!?])\s+", t.strip())[0]
    return re.sub(r"[^a-z ]","",s.lower()).strip()
oc=[first_clause(p) for p in p1s]
chk("G6b distinct opening clauses", len(set(oc))==3, f"distinct={len(set(oc))}/3")
for v,c in zip(VOICES,oc): print(f"      {v}: {c[:95]}")
# G6c distinct sentence skeletons
def skel(t):
    s=re.split(r"(?<=[.!?])\s+", t.strip())
    return tuple(tuple(re.sub(r'[^a-z ]','',x.lower()).strip().split()[:6]) for x in s[:3])
sk=[skel(p) for p in p1s]
chk("G6c distinct sentence skeletons", len(set(sk))==3, f"distinct={len(set(sk))}/3")
# G5 p2 exactly two sentences
def sents(t):
    t=re.sub(r"<think>.*?</think>","",t or "",flags=re.S)
    t=re.sub(r"^\s*#{1,6}\s.*$","",t,flags=re.M)
    t=re.sub(r"\s+"," ",t).strip()
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'“])",t) if s.strip()]
for v in VOICES:
    n=len(sents(V[v]["p2"]))
    chk(f"G5 p2 two sentences [{v}]", n==2, f"n={n}")
# G7 p2 nontrivial
chk("G7 p2 nontrivial", all(len(V[v]["p2"])>200 for v in VOICES), f"min={min(len(V[v]['p2']) for v in VOICES)}")
# shared n-grams (corroborating only)
def grams(t,n):
    w=re.findall(r"[a-z]+",t.lower())
    return set(tuple(w[i:i+n]) for i in range(len(w)-n+1))
for n in (3,4):
    inter=set.intersection(*[grams(p,n) for p in p1s])
    chk(f"G3/G4 shared {n}-grams <=3", len(inter)<=3, f"n={len(inter)} {sorted(inter)[:6]}")
# G8 dials: distinct + non-monotone + diff vs upstream
d=A["dials"]
chk("G8 dials 16 distinct", len(set(d))==16, f"distinct={len(set(d))}")
mono=all(d[i]<=d[i+1] for i in range(len(d)-1)) or all(d[i]>=d[i+1] for i in range(len(d)-1))
chk("G8 dials non-monotone", not mono)
up_dials=up.text_to_dials(A["combined"])
chk("G8 dials == upstream text_to_dials", d==up_dials, f"match={d==up_dials}")
# G9 submit + refs
chk("G9 submit 201", A["submit_status"]==201, str(A["submit_status"]))
chk("G9 refs non-empty", bool(A["refs"]), str(A["refs"]))
try:
    cell=json.loads(A["submit_resp"])["cell"]
    chk("G9 stored cell refs non-empty", bool(cell.get("refs")), str(cell.get("refs")))
    chk("G9 stored title correct", "first version of the record" in cell.get("title",""), cell.get("title",""))
except Exception as e:
    chk("G9 parse submit resp", False, str(e))
# G10 no fallback text leaked
fb=sum(1 for v in VOICES if "[taps-fallback]" in (V[v]["p1"] or ""))
chk("G10 no hand-fallback used", fb==0, f"fallbacks={fb}")
print("\n=== GUARD SUMMARY:", "ALL PASS" if not fail else f"{len(fail)} FAILED: {fail}","===")
