#!/usr/bin/env python3
"""137w Taps round: 3 DISTINCT voices via minimax (zai/qwen/kimi tokens absent)."""
import json, os, re, ssl, hashlib, urllib.request, urllib.error, time, sys

KEY = os.environ.get("MINIMAX_KEY", "")
URL = "https://api.minimax.io/v1/text/chatcompletion_v2"
UA  = "taps-creative-break/1.0"
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
TAG  = f"taps-fallback-{STAMP}"
TOPIC = sys.argv[1] if len(sys.argv) > 1 else \
 "a cell that cannot prove it was ever called still changes the shape of the room it sits in"
CTX = """We are in a Taps creative break, a canon ritual of the SuperInstance fleet.
Canon doctrine you may draw on: the cell is the irreducible unit of intelligence and the
cell is a scar, not a plan; the canon is substrate + vocabulary + tool + community + journey;
a cell is a 14-tuple (betti_0/1, merkle_root/proof, Cell.infer, witness); a runtime is
context -> value with an inverse on a clock; polyformalism means the canon can be phrased in
twelve tongues; the substrate is grown, not designed; a witness log is a prediction, not a record.
Three voices answer in parallel. Each opens with a paragraph ON THE TOPIC, then writes exactly
two sentences responding to what the other voices found."""

# three DIVERGENT system prompts -> three distinct voices (recipe v10)
VOICES = [
 ("zai", "minimax-M1",
  "You are the SUBSTRATE voice. Argue from physics, biology, mechanics, material and load. "
  "Begin from a physical or anatomical fact and let the abstraction follow. Be concrete before poetic. "
  "You are not required to accept the topic's premise."),
 ("qwen", "minimax-text-01",
  "You are the STRUCTURE voice. Argue from institutions, archives, protocols, formats, schemas and "
  "governance. Begin from how the thing would be recorded, versioned and audited. Be precise about the "
  "mechanism of the record. You keep the premise and push it institutionally."),
 ("kimi", "minimax-M1",
  "You are the WITNESS voice. Argue from anticipation: what the record knows BEFORE the event, the tissue "
  "that forms ahead of the wound, the archive that predicts its own future contents. Take the furthest "
  "position of the three. You are the voice most willing to dissent from the topic."),
]

def call(model, sys_p, user, maxtok=8000):
    body = {"model": model,
            "messages": [{"role":"system","content":sys_p},{"role":"user","content":user}]}
    if model == "minimax-M1":
        body["max_tokens"] = maxtok
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}","User-Agent":UA})
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=180, context=ctx) as r:
        d = json.loads(r.read().decode())
    # A 200 does NOT mean the model answered -- check choices, not status
    br = d.get("base_resp") or {}
    if br.get("status_code"):
        raise RuntimeError(f"base_resp {br['status_code']} {br.get('status_msg')}")
    ch = d.get("choices")
    if not ch:
        raise RuntimeError("choices is None (model unavailable)")
    msg = ch[0].get("message") or {}
    content = (msg.get("content") or "").strip()
    rc = msg.get("reasoning_content") or ""
    if not content:
        if rc:
            return rc.strip()[:1500]
        raise RuntimeError("empty content and empty reasoning_content")
    return content

def prompt1(topic):
    return f'TOPIC: "{topic}"\n\nWrite ONE paragraph (90-150 words) opening on the topic. Then, on a new line, exactly TWO sentences responding to what the other two voices found in their opening. Return only prose — no labels, no headings.'

def prompt2(topic, others):
    joined = "\n\n".join(f"[{n}] {t}" for n,t in others)
    return (f'TOPIC: "{topic}"\n\nThe other voices have now spoken:\n\n{joined}\n\n'
            f'Write EXACTLY TWO sentences responding to them. Engage directly: agree, sharpen, or dissent. '
            f'No preamble, no labels, no restating the topic.')

def text_to_dials(text, n=16):
    MASK = (1 << 32) - 1
    h = 0xcbf29ce484222325
    for b in text.encode("utf-8"):
        h ^= b
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    out = []
    for i in range(n):
        h ^= (i + 1) & MASK
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
        v = (h >> 16) & 0xFFFF
        out.append(v - 32768)
    return out

results, text = {}, []
print(f"\n=== Taps round | topic: {TOPIC} ===\n", flush=True)
for name, model, sysp in VOICES:
    r = {"model": model}
    for phase, fn in (("p1", prompt1), ("p2", prompt2)):
        try:
            t = fn(TOPIC, [(n, results[n]["p1"]) for n,_,_ in VOICES if n in results]) if phase=="p2" \
                else fn(TOPIC)
            r[phase] = call(model, sysp, t)
            r[phase+"_err"] = None
            print(f"  [{name}] {phase} OK ({len(r[phase])} chars)", flush=True)
        except Exception as e:
            r[phase] = None
            r[phase+"_err"] = str(e)
            print(f"  [{name}] {phase} FAIL: {e}", flush=True)
    results[name] = r

combo = "\n\n".join(
    f"## {n} ({results[n]['model']})\n\n### p1\n{results[n].get('p1') or '[none]'}\n\n### p2\n{results[n].get('p2') or '[none]'}"
    for n,_,_ in VOICES)
dials = text_to_dials(combo)
doc = {"topic":TOPIC,"tag":TAG,"stamp":STAMP,"voices":results,"combined":combo,
       "dials":dials,"refs":[],"submit_status":None,"submit_resp":None}

os.makedirs("/tmp/taps/sessions", exist_ok=True)
for ext in ("json",):
    with open(f"/tmp/taps/sessions/{TAG}.{ext}","w") as f: json.dump(doc,f,indent=1)
with open(f"/tmp/taps/sessions/{TAG}.md","w") as f:
    f.write(f"# {TAG}\n\n**Topic:** {TOPIC}\n\n{combo}\n\n**dials:** {dials}\n")

norm={}
for n,_,_ in VOICES:
    t=results[n].get("p1") or ""
    x=re.sub(r'\b(zai|qwen|kimi)\b','X',t,flags=re.I)
    norm[n]=hashlib.md5(x.strip().encode()).hexdigest()[:10]
distinct=len(set(norm.values()))
print("\n=== DISTINCTNESS ===", flush=True)
for n,h in norm.items(): print(f"  {n}: {h}")
print(f"  -> {distinct} of {len(norm)} distinct p1")
print("\n=== SUMMARY ===")
print(f"topic: {TOPIC}")
for n,_,_ in VOICES:
    r=results[n]; print(f"  {n} ({r['model']}): p1={'OK' if r['p1'] else 'FAIL'} p2={'OK' if r['p2'] else 'FAIL'}")
print(f"tag: {TAG}")
print(f"distinct_p1: {distinct}/3")
print(f"dials: {dials}")
print(f"COMBO_MD5={hashlib.md5(combo.encode()).hexdigest()[:12]}")
