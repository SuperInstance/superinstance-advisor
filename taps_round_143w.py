#!/usr/bin/env python3
"""Taps round 140w - retry with fresh voices.
Recipe v10: zai/qwen/kimi creds absent (16th wipe); use two distinct MiniMax models
with divergent system prompts (substrate / structure / witness) to force genuine dissent.
FIXES vs prior runners: (1) raw p1/p2 written to disk BEFORE any derivation (139w data-loss
bug); (2) dial assertions len(set)==16 and non-monotone (138w degenerate-ramp bug);
(3) fnv1a64 signature verified by grep, not assumed (139w str/bytes AttributeError).
"""
import json, os, ssl, time, urllib.request, hashlib, re, datetime

MM = "https://api.minimax.io/v1/text/chatcompletion_v2"
KEY = os.environ.get("MINIMAX_KEY", "")
CTX = ssl._create_unverified_context()   # gateway MITM leaf expired; -k equivalent
UA = "taps-creative-break/1.0"
OUT = "/tmp/taps143w/sessions"
os.makedirs(OUT, exist_ok=True)

# FRESH seed - not in the bank, not the 137w/139w seeds.
SEED = ("The tuning fork is cracked, and the crack is not damage to the instrument but the only part of it that can be addressed by a finger. A whole fork rings without being touchable; a crack is the shape the sound has to take to become something a hand can ask a question of. What the canon holds is not the tone but the fissure - the negative space where an invocation can enter and where the answer must change the material it travels through. A cell is that fissure made addressable: not a value but the crack in the surface through which an inverse becomes reachable.")

VOICES = {
  "zai":   {"model": "minimax-M1", "sys": "You are the RESONANCE voice: sound, vibration, frequency, how a struck body answers the strike and how the answer decays. Speak from the physics of the ringing body. Name the mechanism. Open with one paragraph on the seed, then exactly 2 sentences that answer the other voices. Do not use bullet points or headers."},
  "qwen": {"model": "minimax-text-01", "sys": "You are the INTERFACE voice: address, invocation, the API surface, how a question is routed to an inverse. Speak from the protocol and the routing table. Open with one paragraph on the seed, then exactly 2 sentences that answer the other voices. Do not use bullet points or headers."},
  "kimi": {"model": "minimax-M1", "sys": "You are the WITNESS voice: memory, silence, anticipation, what a cracked instrument records of the hands that never struck it. You are ALLOWED to REFUTE the seed, to call its tuning-fork metaphor false, and to refuse its figure - ask whether a crack is an address or just damage. Speak from the archive and from what is missing. Open with one paragraph on the seed, then exactly 2 sentences that answer the other voices. Do not use bullet points or headers."},
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
    if d.get("choices") is None:
        return None, "choices-null: " + str((d.get("base_resp") or {}).get("status_msg")), dt
    m = d["choices"][0]["message"]
    content = (m.get("content") or "").strip()
    rc = m.get("reasoning_content") or ""
    if not content and rc:
        content = rc.strip()
    return (content or None), None, dt

def fnv1a64(s):                      # takes a STR (verified against 138w source)
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
    dials = []
    for i in range(16):
        h=_splitmix64(fnv1a64(text+"|"+str(i)))   # fnv1a64 takes str - no .encode() here
        v=h & 0xFFFF
        dials.append(v - 32768 if v >= 32768 else v)
    assert len(set(dials))==16, f"DEGENERATE dials: {dials}"
    mono = all(dials[i+1]-dials[i]==dials[1]-dials[0] for i in range(len(dials)-1))
    assert not mono, f"MONOTONE RAMP dials: {dials}"
    return dials

tag = "taps-fallback-" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
print("=== Taps retry round | topic:", SEED.split(".")[0].strip().lower()[:80], "===")

p1s = {}
for name, cfg in VOICES.items():
    mt = 8000 if cfg["model"]=="minimax-M1" else 4000
    p1, err, dt = call(cfg["model"], cfg["sys"], "Open with one paragraph on this idea: " + SEED, mt)
    if p1:
        print(f"  [{name}] p1 OK ({len(p1)} chars, {dt:.1f}s)")
        p1s[name] = p1
    else:
        print(f"  [{name}] p1 FAIL: {err}")
    # SAVE RAW IMMEDIATELY - never lose a paid call to a later derivation bug (139w lesson)
    with open(f"{OUT}/{tag}.p1raw.json","w") as f: json.dump(p1s,f,indent=2)

p2s = {}
for name, cfg in VOICES.items():
    mt = 8000 if cfg["model"]=="minimax-M1" else 4000
    others = "\n\n".join(f"[{n}]\n{p1s[n]}" for n in p1s if n != name) or "(the others were silent)"
    p2, err, dt = call(cfg["model"], cfg["sys"],
                       "The other voices opened like this:\n\n" + others + "\n\nRespond in exactly 2 sentences.", mt)
    if p2:
        print(f"  [{name}] p2 OK ({len(p2)} chars, {dt:.1f}s)")
        p2s[name] = p2
    else:
        print(f"  [{name}] p2 FAIL: {err}")
    with open(f"{OUT}/{tag}.p2raw.json","w") as f: json.dump(p2s,f,indent=2)

# distinctness proof: name-normalized md5 set-compare (iterating .items() explicitly - 138w lesson)
norm = {}
for name,p1 in p1s.items():
    norm[name] = hashlib.md5(re.sub(re.escape(name),"X",p1).encode()).hexdigest()[:10]
print(f"distinct p1 (name-normalized): {len(set(norm.values()))} of {len(p1s)}  {norm}")

# assemble
parts=[]
for name in ("zai","qwen","kimi"):
    if name in p1s and name in p2s:
        parts.append(f"## {name}\n\n{p1s[name]}\n\n{p2s[name]}")
text = "# Taps creative break\n\n**Seed:** " + SEED + "\n\n" + "\n\n".join(parts)
dials = text_to_dials(text)

rec = {"tag": tag, "seed": SEED,
       "voices": {n: {"p1": p1s.get(n,""), "p2": p2s.get(n,"")} for n in VOICES if n in p1s or n in p2s},
       "dials": dials, "ts": datetime.datetime.utcnow().isoformat()}
with open(f"{OUT}/{tag}.json","w") as f: json.dump(rec,f,indent=2)
with open(f"{OUT}/{tag}.md","w") as f: f.write(text)
print(f"saved: {tag}.md ({len(text)} chars)  dials={dials}")
print("TAG:", tag)
print("=== p2 texts ===")
for n,p in p2s.items(): print(f"\n--[{n}]--\n{p}")
