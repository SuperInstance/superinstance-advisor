import json, re, hashlib, sys
p = "sessions/taps-20261023T210353Z.json"
j = json.load(open(p))
v = j["voices"]
print("topic:", j["topic"]); print("tag:", j["tag"])
print("has 'models' field:", "models" in j, "| has 'postures':", "postures" in j)
def sents(t):
    t = re.sub(r"<think>.*?</think>","",t or "",flags=re.S)
    t = re.sub(r"\s+"," ",t).strip()
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'“])", t) if x.strip()]
p1s = {k: v[k]["p1"] for k in v}
p2s = {k: v[k]["p2"] for k in v}
print("\n-- p1 lengths:", {k: len(x) for k,x in p1s.items()})
print("-- p2 lengths:", {k: len(x) for k,x in p2s.items()})
print("-- p2 sentence counts:", {k: len(sents(x)) for k,x in p2s.items()})
def norm(t): return re.sub(r"\W+","",t.lower())
print("-- p1 byte-distinct (norm_md5):", len({hashlib.md5(norm(x).encode()).hexdigest() for x in p1s.values()}), "/3")
# opening clause = first 6 content words of first sentence
def clause(t):
    s = sents(t)
    if not s: return ""
    w = [x for x in re.findall(r"[A-Za-z']+", s[0].lower()) if len(x)>2]
    return " ".join(w[:6])
print("\n-- opening clauses:")
cl = {k: clause(x) for k,x in p1s.items()}
for k,vv in cl.items(): print(f"   {k}: {vv!r}")
print("distinct opening clauses:", len(set(cl.values())), "/3")
# sentence skeletons
def skel(t):
    return tuple((len(re.findall(r"[A-Za-z']+",s))//5) for s in sents(t))
sk = {k: skel(x) for k,x in p1s.items()}
for k,vv in sk.items(): print(f"   {k} skeleton: {vv}")
print("distinct skeletons:", len(set(sk.values())), "/3")
# shared n-grams
def grams(t,n):
    w = re.findall(r"[a-z']+", t.lower())
    return {" ".join(w[i:i+n]) for i in range(len(w)-n+1)}
for n in (3,4):
    sets = [grams(x,n) for x in p1s.values()]
    shared = set.intersection(*sets)
    print(f"-- shared {n}-grams across all 3 openings: {len(shared)}")
    if n==3: print("   ", sorted(shared)[:12])
print("\n-- p1 first 90 chars each:")
for k,x in p1s.items(): print(f"   {k}: {x[:110]!r}")
