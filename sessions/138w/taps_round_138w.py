#!/usr/bin/env python3
"""Taps round 138w — retry with fresh voices.
Recipe v10: zai/qwen/kimi creds absent; use two distinct MiniMax models with
divergent system prompts (substrate / structure / witness) to force genuine dissent.
Durable gotchas: ssl unverified (MITM cert wall), M1 max_tokens>=8000 + reasoning
fallback, verify choices is not null, hand-rolled FNV-1a for dials.
"""
import json, os, ssl, sys, time, urllib.request, urllib.error, hashlib, re, datetime

MM = "https://api.minimax.io/v1/text/chatcompletion_v2"
KEY = os.environ.get("MINIMAX_KEY", "")
CTX = ssl._create_unverified_context()   # gateway MITM leaf; -k equivalent
UA = "taps-creative-break/1.0"
OUT = "/tmp/advisor/sessions/138w"
os.makedirs(OUT, exist_ok=True)

# --- canon text the round is responding to (a substrate/structure/witness split) ---
SEED = ("The substrate cannot recognize absence. It knows only pattern and return. "
        "A cell is the smallest unit that can hold a witness: an address that behaves like data, "
        "a scar rather than a plan, a value produced from context with an inverse on a clock. "
        "The canon is not what was written but what could not be wiped away.")

VOICES = {
  "zai":   {"model": "minimax-M1", "sys": "You are the SUBSTRATE voice: physics, material, load, tissue. Speak from the body. Be concrete and physical. Open with one paragraph on the seed, then exactly 2 sentences that answer the other voices. Do not use bullet points or headers."},
  "qwen": {"model": "minimax-text-01", "sys": "You are the STRUCTURE voice: protocol, governance, versioning, institutions. Speak from the ledger and the schema. Open with one paragraph on the seed, then exactly 2 sentences that answer the other voices. Do not use bullet points or headers."},
  "kimi": {"model": "minimax-M1", "sys": "You are the WITNESS voice: memory, anticipation, archive, dissent. You are allowed to REFUTE the seed. Speak from the archive and the trace. Open with one paragraph on the seed, then exactly 2 sentences that answer the other voices. Do not use bullet points or headers."},
}

def call(model, system, user, max_tokens):
    body = {"model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "max_tokens": max_tokens}
    req = urllib.request.Request(MM, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json", "User-Agent": UA})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
            d = json.loads(r.read().decode())
    except Exception as e:
        return None, f"{type(e).__name__}: {e}", 0.0
    dt = time.time() - t0
    if d.get("choices") is None:              # 200 but model didn't answer (retired model trap)
        return None, "choices-null: " + str((d.get("base_resp") or {}).get("status_msg")), dt
    m = d["choices"][0]["message"]
    content = (m.get("content") or "").strip()
    rc = m.get("reasoning_content") or ""
    if not content and rc:
        content = rc.strip()                  # M1 reasoning fallback
    return (content or None), None, dt

def fnv1a64(s):
    h = 0xcbf29ce484222325
    for b in s.encode("utf-8"):
        h ^= b; h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h

def _splitmix64(z):
    z=(z+0x9E3779B97F4A7C15)&0xFFFFFFFFFFFFFFFF
    z=((z^(z>>30))*0xBF58476D1CE4E5B9)&0xFFFFFFFFFFFFFFFF
    z=((z^(z>>27))*0x94D049BB133111EB)&0xFFFFFFFFFFFFFFFF
    return z^(z>>31)
def text_to_dials(text):
    # 16 signed dials; fnv1a seed + splitmix64 avalanche so the 16 values are
    # decorrelated (raw fnv over 1-char deltas yields a degenerate -435 ramp)
    dials = []
    for i in range(16):
        h=_splitmix64(fnv1a64((text+"|"+str(i)).encode()))
        v=h & 0xFFFF
        dials.append(v - 32768 if v >= 32768 else v)
    return dials

def sentences2(text, other_blurb):
    # ask for exactly 2 sentences answering the others
    others = other_blurb.strip()
    return (f"The other voices in this round said:\n\n{others}\n\n"
            f"Answer them in exactly two sentences.")

tag = "taps-fallback-" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
print("=== Taps retry round | topic:", SEED.split(".")[0].strip().lower()[:80], "===")

blurbs = {}   # name -> (p1, p2)
p1s = {}
for name, cfg in VOICES.items():
    p1, err, dt = call(cfg["model"], cfg["sys"], "Open with one paragraph on this idea: " + SEED, 8000 if cfg["model"]=="minimax-M1" else 4000)
    if p1:
        print(f"  [{name}] p1 OK ({len(p1)} chars, {dt:.1f}s)")
        p1s[name] = p1
    else:
        print(f"  [{name}] p1 FAIL: {err}")

# second pass: each answers the other two p1s
for name, cfg in VOICES.items():
    others = "\n\n".join(f"[{n}]\n{p1s[n]}" for n in p1s if n != name) or "(the others were silent)"
    p2, err, dt = call(cfg["model"], cfg["sys"],
                       "The other voices opened like this:\n\n" + others + "\n\nRespond in exactly 2 sentences.",
                       8000 if cfg["model"]=="minimax-M1" else 4000)
    if p2:
        print(f"  [{name}] p2 OK ({len(p2)} chars, {dt:.1f}s)")
        blurbs[name] = (p1s.get(name,""), p2)
    else:
        print(f"  [{name}] p2 FAIL: {err}")

# distinctness proof: name-normalized md5 set-compare
norm = set()
for name in p1s:
    norm.add(hashlib.md5(re.sub(re.escape(name), "X", p1s[name]).encode()).hexdigest()[:10])
print(f"distinct p1 (name-normalized): {len(norm)} of {len(p1s)}")

# assemble canon text
parts = []
for name in ("zai","qwen","kimi"):
    if name in blurbs:
        parts.append(f"## {name}\n\n{blurbs[name][0]}\n\n{blurbs[name][1]}")
text = "# Taps creative break\n\n**Seed:** " + SEED + "\n\n" + "\n\n".join(parts)
dials = text_to_dials(text)

rec = {"tag": tag, "seed": SEED, "voices": {n: {"p1": blurbs[n][0], "p2": blurbs[n][1]} for n in blurbs},
       "dials": dials, "ts": datetime.datetime.utcnow().isoformat()}
with open(f"{OUT}/{tag}.json", "w") as f: json.dump(rec, f, indent=2)
with open(f"{OUT}/{tag}.md", "w") as f: f.write(text)
print(f"saved: {tag}.md  ({len(text)} chars)  dials={dials}")
print("TAG:", tag)
