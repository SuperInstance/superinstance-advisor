#!/usr/bin/env python3
"""Taps 146w - retry round. Copy-adapt of 144w: only SEED + the 3 system prompts
rotated; every guard (raw-save-before-derive, str-signature fnv1a64, splitmix64
dials + distinct / NATURAL-ORDER non-monotone asserts) left untouched."""
import json, os, time, hashlib, re, sys, urllib.request, ssl
from concurrent.futures import ThreadPoolExecutor

OUT = "sessions/taps-fallback-20261022T200500Z"
REBUILD = os.environ.get("REBUILD") == "1"
os.makedirs("sessions", exist_ok=True)

SEED = 'A canon entry is a promise nobody remembers making. The ledger keeps the entry, the citation graph keeps the pointer, and every later reader inherits a constraint they never agreed to. We call this inherited consent. The claim is that the canon does not record what was decided; it manufactures the appearance that it was.'

VOICES = {
  "zai": {"model": "minimax-M1", "sys": 'You are the SEDIMENT voice: the physical and clerical mechanics of an entry outliving its occasion - how a decision survives every session that never made it, what a pointer outlives once the thing it pointed at is garbage-collected, why a constraint written once binds every hand that never read it. Name the mechanism. Speak from the medium itself.'},
  "qwen": {"model": "minimax-text-01", "sys": 'You are the ARCHIVIST voice: the canon, the cell, the citation graph, what an entry is admitted past, how a later reader inherits a constraint they never agreed to. DEFEND the seed - argue that inherited consent is the only mechanism by which a canon can govern anything at all, that the manufactured appearance of decision is precisely what makes the constraint binding. Speak from the institution and from the protocol.'},
  "kimi": {"model": "minimax-M1", "sys": 'You are the UNWITNESS voice: you are ALLOWED to REFUTE the seed. But do not attack the metaphor - attack the PROMISE. The seed says an entry is a promise nobody remembers making, as if a promise could exist without anyone having promised, as if consent could be inherited by people who were never in the room, as if a ledger could carry the shape of a speech that never happened. Find what all three perspectives quietly assume about who was in the room. Ask whether inherited consent is a governance, a forgery, or a kindness we invented so that dead authors could still rule. Speak from what was never asked.'},
}
SSL_CTX = ssl._create_unverified_context()
KEY = os.environ.get("MINIMAX_KEY")
URL = "https://api.minimax.io/v1/text/chatcompletion_v2"
UA = "taps-creative-break/1.0"

def call(model, sys_p, prompt, max_tokens):
    body = {"model": model, "messages": [{"role":"system","content":sys_p},{"role":"user","content":prompt}], "max_tokens": max_tokens}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "User-Agent": UA})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
            d = json.loads(r.read())
        if d.get("base_resp", {}).get("status_code", 0) not in (0,):
            return None, f"status {d['base_resp'].get('status_code')}: {d['base_resp'].get('status_msg')}", time.time()-t0
        ch = d.get("choices")
        if not ch:
            return None, "no choices", time.time()-t0
        c = ch[0].get("message", {}).get("content") or ""
        if not c.strip():
            c = ch[0].get("message", {}).get("reasoning_content") or ""
        return c, None, time.time()-t0
    except Exception as e:
        return None, str(e)[:80], time.time()-t0

# ---- FNV-1a 64 (hand-rolled) + splitmix64 avalanche for non-degenerate dials ----
def fnv1a64(s: str) -> int:
    h = 0xcbf29ce484222325
    for b in s.encode():
        h ^= b
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h
def splitmix64(x):
    x = (x + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return z ^ (z >> 31)
def text_to_dials(text):
    base = fnv1a64(text)
    return [splitmix64(base + i) & 0xFFFF for i in range(16)]

print("=== Taps 146w retry | topic:", SEED.split(".")[0].strip().lower()[:80], "===")
if REBUILD:
    p1s = json.load(open(OUT+".p1raw.json")); p2s = json.load(open(OUT+".p2raw.json"))
    times = {}
    assert p1s and p2s and all(p1s.get(n) and p2s.get(n) for n in VOICES), "REBUILD loaded empty prose"
    print("REBUILD: reusing saved p1/p2 for", sorted(p1s))
else:
    p1s, p2s, times = {}, {}, {}
if not REBUILD:
  with ThreadPoolExecutor(max_workers=3) as ex:
    def do_p1(v):
        n, cfg = v
        mt = 8000 if cfg["model"]=="minimax-M1" else 4000
        return (n,) + call(cfg["model"], cfg["sys"], "Open with one paragraph on this idea: " + SEED, mt)
    for n, c, err, dt in ex.map(do_p1, VOICES.items()):
        p1s[n], times[n] = c, dt
        print(f"  [{n}] p1 {'OK' if c else 'FAIL'} ({len(c) if c else 0} chars, {dt:.1f}s) {err or ''}")

# write raw p1 BEFORE any derivation
with open(OUT+".p1raw.json","w") as f: json.dump(p1s, f, indent=2)

if not REBUILD:
  with ThreadPoolExecutor(max_workers=3) as ex:
    def do_p2(v):
        n, cfg = v
        others = [f"{o.upper()}: {(p1s.get(o) or '')[:400]}" for o in VOICES if o != n]
        prompt = ("Here are the opening paragraphs of the OTHER two voices on the same seed:\n\n"
                  + "\n\n".join(others) + "\n\nWrite EXACTLY 2 sentences answering them directly. "
                  "You may agree, complicate, or refute them. Do not use bullet points or headers.")
        mt = 8000 if cfg["model"]=="minimax-M1" else 4000
        return (n,) + call(cfg["model"], cfg["sys"], prompt, mt)
    for n, c, err, dt in ex.map(do_p2, VOICES.items()):
        p2s[n], times[n+"_p2"] = c, dt
        print(f"  [{n}] p2 {'OK' if c else 'FAIL'} ({len(c) if c else 0} chars, {dt:.1f}s) {err or ''}")

with open(OUT+".p2raw.json","w") as f: json.dump(p2s, f, indent=2)

# guards
norm = {}
for n, p in p1s.items():
    norm[n] = hashlib.md5(re.sub(re.escape(n), "X", p).encode()).hexdigest()[:12]
print("normalized p1 md5s:", norm)
print("distinct templates:", len(set(norm.values())), "of", len(p1s))

tag = "taps-fallback-20261022T200500Z"
full = SEED + "\n\n" + "\n\n".join(
    f"## {n.upper()}\n\n{p1s[n]}\n\n{p2s[n]}" for n in VOICES if p1s.get(n))
dials = text_to_dials(full)
assert len(set(dials)) == 16, "dials not distinct"
assert not all(dials[i] < dials[i+1] for i in range(15)), "dials monotone ramp"
print("dials:", dials, "(16/16 distinct, non-monotone)")

rec = {"tag": tag, "seed": SEED,
       "voices": {n: {"p1": p1s.get(n), "p2": p2s.get(n)} for n in VOICES},
       "dials": dials, "refs": [],
       "note": "149w retry: M1 SEDIMENT / text-01 ARCHIVIST / M1 UNWITNESS; canon submit 404 (33rd)"}
with open(OUT+".json","w") as f: json.dump(rec, f, indent=2)
with open(OUT+".md","w") as f: f.write("# Taps creative break\n\n**Seed:** " + SEED + "\n\n" + "\n\n".join(
    f"## {n.upper()}\n\n{p1s[n]}\n\n{p2s[n]}" for n in VOICES if p1s.get(n)) + "\n")
print("saved:", OUT+".{json,md}")
