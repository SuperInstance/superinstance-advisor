#!/usr/bin/env python3
"""Taps round 139w - retry with fresh voices + a FRESH topic.

Round 1 (script, as instructed) topic "the scar is older than the blade that made it"
was a RECYCLED topic (136w used it) and all 3 voices died on missing ZAI/DEEPINFRA
tokens. The script's p1s are its one-template hand-fallback (verified 20th time).
So: fresh topic, recipe v10 voices (M1 substrate / text-01 structure / M1 witness).
"""
import json, os, ssl, time, urllib.request, hashlib, re, datetime
from concurrent.futures import ThreadPoolExecutor

MM   = "https://api.minimax.io/v1/text/chatcompletion_v2"
KEY  = os.environ.get("MINIMAX_KEY", "")
CTX  = ssl._create_unverified_context()      # gateway MITM leaf expired (000 @ 0.075s w/o -k)
UA   = "taps-creative-break/1.0"
OUT  = "/tmp/advisor/sessions/139w"
os.makedirs(OUT, exist_ok=True)

SEED = ("A cell is not built, it is negotiated. Nothing arrives whole: every value is a "
        "lease on shared substrate, held only as long as the inverse stays computable. "
        "The canon is the residue of leases that could not be revoked.")

VOICES = {
  "zai":  {"model": "minimax-M1",       "sys": "You are the SUBSTRATE voice: physics, material, load, tissue, mechanics. Speak from the body and the material. Be concrete and physical. Open with one paragraph on the seed, then, later, exactly 2 sentences that answer the other voices. No bullet points, no headers."},
  "qwen": {"model": "minimax-text-01",  "sys": "You are the STRUCTURE voice: protocol, governance, versioning, contracts, institutions. Speak from the ledger and the schema. Open with one paragraph on the seed, then, later, exactly 2 sentences that answer the other voices. No bullet points, no headers."},
  "kimi": {"model": "minimax-M1",       "sys": "You are the WITNESS voice: memory, anticipation, archive, erasure, silence. You are permitted - encouraged - to REFUTE the seed or the other voices. Speak from the trace and what outlives it. Open with one paragraph on the seed, then, later, exactly 2 sentences that answer the other voices. No bullet points, no headers."},
}

def call(model, system, user, max_tokens):
    body = {"model": model, "messages": [{"role": "system", "content": system},
                                         {"role": "user", "content": user}],
            "max_tokens": max_tokens}
    req = urllib.request.Request(MM, data=json.dumps(body).encode(), method="POST",
          headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json", "User-Agent": UA})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90, context=CTX) as r:
            d = json.loads(r.read().decode())
    except Exception as e:
        return None, f"{type(e).__name__}: {e}", 0.0
    dt = time.time() - t0
    if d.get("choices") is None:                       # 200 != answered (retired-model trap)
        return None, "choices-null: " + str((d.get("base_resp") or {}).get("status_msg")), dt
    m  = d["choices"][0]["message"]
    c  = (m.get("content") or "").strip()
    rc = (m.get("reasoning_content") or "").strip()
    return (c or rc or None), None, dt                # M1 reasoning fallback

def fnv1a64(s):
    h = 0xcbf29ce484222325
    for b in s.encode("utf-8"):
        h ^= b; h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h

def _sm64(z):
    z = (z + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return z ^ (z >> 31)

def text_to_dials(text):
    d = []
    for i in range(16):
        v = _sm64(fnv1a64(text + "|" + str(i))) & 0xFFFF
        d.append(v - 32768 if v >= 32768 else v)
    return d

stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
tag = "taps-fallback-" + stamp
print("=== Taps 139w retry | seed:", SEED[:70], "===")

# ---- pass 1: all three in parallel (foreground caps at 30s -> threads) ----
with ThreadPoolExecutor(max_workers=3) as ex:
    futs = {n: ex.submit(call, c["model"], c["sys"], "Open with one paragraph on this idea:\n\n" + SEED,
                         8000 if c["model"] == "minimax-M1" else 4000) for n, c in VOICES.items()}
    res1 = {n: f.result() for n, f in futs.items()}
p1s = {}
for n, (txt, err, dt) in res1.items():
    if txt: p1s[n] = txt; print(f"  [{n}] p1 OK ({len(txt)} chars, {dt:.1f}s)")
    else:  print(f"  [{n}] p1 FAIL: {err}")

# ---- pass 2: each answers the other two p1s ----
with ThreadPoolExecutor(max_workers=3) as ex:
    futs = {}
    for n, c in VOICES.items():
        others = "\n\n".join(f"[{m}]\n{p1s[m]}" for m in p1s if m != n) or "(the others were silent)"
        futs[n] = ex.submit(call, c["model"], c["sys"],
                            "The other voices opened like this:\n\n" + others + "\n\nNow respond to them in exactly 2 sentences.",
                            8000 if c["model"] == "minimax-M1" else 4000)
    res2 = {n: f.result() for n, f in futs.items()}
p2s = {}
for n, (txt, err, dt) in res2.items():
    if txt: p2s[n] = txt; print(f"  [{n}] p2 OK ({len(txt)} chars, {dt:.1f}s)")
    else:  print(f"  [{n}] p2 FAIL: {err}")

norm = {hashlib.md5(re.sub(re.escape(n), "X", p1s[n]).encode()).hexdigest()[:10] for n in p1s}
print(f"distinct p1 (name-normalized): {len(norm)} of {len(p1s)}")

parts = [f"## {n}\n\n{p1s[n]}\n\n{p2s[n]}" for n in ("zai", "qwen", "kimi") if n in p1s and n in p2s]
text  = "# Taps creative break\n\n**Seed:** " + SEED + "\n\n" + "\n\n".join(parts)
dials = text_to_dials(text)
assert len(set(dials)) == 16 and dials != sorted(dials), "degenerate dials"

rec = {"tag": tag, "seed": SEED, "voices": {n: {"p1": p1s[n], "p2": p2s[n]} for n in p1s if n in p2s},
       "dials": dials, "ts": datetime.datetime.utcnow().isoformat()}
json.dump(rec, open(f"{OUT}/{tag}.json", "w"), indent=2)
open(f"{OUT}/{tag}.md", "w").write(text)
print(f"saved {tag}.md ({len(text)} chars) dials={dials}")
print("TAG:", tag)
