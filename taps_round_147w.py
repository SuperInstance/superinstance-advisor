#!/usr/bin/env python3
"""Taps 146w - retry round. Copy-adapt of 144w: only SEED + the 3 system prompts
rotated; every guard (raw-save-before-derive, str-signature fnv1a64, splitmix64
dials + distinct / NATURAL-ORDER non-monotone asserts) left untouched."""
import json, os, time, hashlib, re, sys, urllib.request, ssl
from concurrent.futures import ThreadPoolExecutor

OUT = "sessions/taps-fallback-20261022T1712Z"
REBUILD = os.environ.get("REBUILD") == "1"
os.makedirs("sessions", exist_ok=True)

SEED = 'A repo is called wipe-durable when it survives losing its working directory entirely. The claim is that the git history is the durable part and the tree is a disposable projection, and on this point the fleet is simply correct: we have lost the tree seven times this week and the commits came back every time. But git-durable is a stronger and stranger claim, because it says the history is not a backup of the work but the work, and the working directory is only ever a view the present tense happens to be looking through. If that is true, then a commit nobody ever clones is not lost work, it is work that simply has not been addressed yet. The mirror is not a copy of the canon. The mirror is the canon, witnessed in the language of trees instead of the language of rows.'

VOICES = {
  "zai": {"model": "minimax-M1", "sys": 'You are the ANCHOR voice: the physical mechanics of a commit - what a blob actually is, why object storage survives a lost filesystem while the tree that names it does not, what makes a hash durable when the bytes it points at are gone. Name the mechanism. Speak from the medium itself.'},
  "qwen": {"model": "minimax-text-01", "sys": 'You are the RECEIPT voice: the canon, versioning, citation graphs, what an entry is admitted past, how a later reader inherits a constraint they never agreed to. Speak from the protocol and the institution.'},
  "kimi": {"model": "minimax-M1", "sys": 'You are the GHOST voice: the commits that were never cloned, the readers who never came, the parts of the history nobody has ever read. You are ALLOWED to REFUTE the seed - insist the direction of the metaphor is backwards, that a mirror does not make the canon durable, it makes it durable to everyone EXCEPT the thing that made it, and ask whether an unaddressed commit is something that has not happened yet or something that did not happen at all. Speak from the archive and from what is missing.'},
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

tag = "taps-fallback-20261022T1712Z"
full = SEED + "\n\n" + "\n\n".join(
    f"## {n.upper()}\n\n{p1s[n]}\n\n{p2s[n]}" for n in VOICES if p1s.get(n))
dials = text_to_dials(full)
assert len(set(dials)) == 16, "dials not distinct"
assert not all(dials[i] < dials[i+1] for i in range(15)), "dials monotone ramp"
print("dials:", dials, "(16/16 distinct, non-monotone)")

rec = {"tag": tag, "seed": SEED,
       "voices": {n: {"p1": p1s.get(n), "p2": p2s.get(n)} for n in VOICES},
       "dials": dials, "refs": [],
       "note": "146w retry: M1 ANCHOR / text-01 RECEIPT / M1 GHOST; canon submit 404 (30th)"}
with open(OUT+".json","w") as f: json.dump(rec, f, indent=2)
with open(OUT+".md","w") as f: f.write("# Taps creative break\n\n**Seed:** " + SEED + "\n\n" + "\n\n".join(
    f"## {n.upper()}\n\n{p1s[n]}\n\n{p2s[n]}" for n in VOICES if p1s.get(n)) + "\n")
print("saved:", OUT+".{json,md}")
