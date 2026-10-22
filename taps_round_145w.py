#!/usr/bin/env python3
"""Taps 145w - retry round. Copy-adapt of 144w: only SEED + the 3 system prompts
rotated; every guard (raw-save-before-derive, str-signature fnv1a64, splitmix64
dials + distinct / NATURAL-ORDER non-monotone asserts) left untouched."""
import json, os, time, hashlib, re, sys, urllib.request, ssl
from concurrent.futures import ThreadPoolExecutor

OUT = "sessions/taps-fallback-20261022T160500Z"
REBUILD = os.environ.get("REBUILD") == "1"
os.makedirs("sessions", exist_ok=True)

SEED = "A river does not remember the stone it went around. The water that touched one bank this morning is not the water that touched it last winter, and nothing in either crossing was recorded. Yet the riverbed holds the shape of every stone it has ever refused, so that a later river arriving at the same coordinate finds the same obstruction waiting and is shaped by it without ever having met the stone. We call this inheritance, and we are wrong about the tense: nothing was passed down. A shape was cut, and the thing arriving later is the shape's continuation, not its heir. The record is not memory. The record is the wound that keeps being inherited as terrain."

VOICES = {
  "zai": {"model": "minimax-M1", "sys": 'You are the STRATA voice: erosion, deposition, the mechanics of a channel being cut by the thing it repeatedly refuses. Speak from the geology of flow - velocity, gradient, the way a bed hardens and then holds the next river to its old course. Name the mechanism. Open with one paragraph on the seed, then exactly 2 sentences that answer the other voices. Do not use bullet points or headers.'},
  "qwen": {"model": "minimax-text-01", "sys": 'You are the LEDGER voice: the canon, versioning, what an entry is admitted past, how a later reader inherits a constraint they never agreed to. Speak from the protocol and the institution. Open with one paragraph on the seed, then exactly 2 sentences that answer the other voices. Do not use bullet points or headers.'},
  "kimi": {"model": "minimax-M1", "sys": 'You are the UNREAD voice: what is lost that no later river can recover, and the difference between what cannot be read and what cannot be forgotten. You are ALLOWED to REFUTE the seed - call the inheritance metaphor false, and ask whether a bed that holds a shape is remembering anything at all, or whether terrain is simply the only place water is permitted to fail in a shape it will keep failing in. Speak from the archive and from what is missing. Open with one paragraph on the seed, then exactly 2 sentences that answer the other voices. Do not use bullet points or headers.'},
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

print("=== Taps 144w retry | topic:", SEED.split(".")[0].strip().lower()[:80], "===")
if REBUILD:
    p1s = json.load(open(OUT+".p1raw.json")); p2s = json.load(open(OUT+".p2raw.json"))
    times = {}
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

tag = "taps-fallback-20261022T160500Z"
full = SEED + "\n\n" + "\n\n".join(
    f"## {n.upper()}\n\n{p1s[n]}\n\n{p2s[n]}" for n in VOICES if p1s.get(n))
dials = text_to_dials(full)
assert len(set(dials)) == 16, "dials not distinct"
assert not all(dials[i] < dials[i+1] for i in range(15)), "dials monotone ramp"
print("dials:", dials, "(16/16 distinct, non-monotone)")

rec = {"tag": tag, "seed": SEED,
       "voices": {n: {"p1": p1s.get(n), "p2": p2s.get(n)} for n in VOICES},
       "dials": dials, "refs": [],
       "note": "145w retry: M1 STRATA / text-01 LEDGER / M1 UNREAD; canon submit 404 (29th)"}
with open(OUT+".json","w") as f: json.dump(rec, f, indent=2)
with open(OUT+".md","w") as f: f.write("# Taps creative break\n\n**Seed:** " + SEED + "\n\n" + "\n\n".join(
    f"## {n.upper()}\n\n{p1s[n]}\n\n{p2s[n]}" for n in VOICES if p1s.get(n)) + "\n")
print("saved:", OUT+".{json,md}")
