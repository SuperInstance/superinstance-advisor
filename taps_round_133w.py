#!/usr/bin/env python3
"""133w Taps round — dark-fleet ladder.

Script's own round gave 3x p1 hand-fallback stubs (byte-identical after voice
normalization) and 3x p2 FAIL: ZAI/DEEPINFRA/CF_AI absent (12th consecutive
wipe). Only GITHUB_TOKEN + MINIMAX_KEY survive. Live voice = minimax-M2.5.
So: M2.5 does p1 AND p2, plus two distinct hand registers, braided into one
entry.
"""
import json, os, time, urllib.request, hashlib, sys

TAG = "taps-fallback-20261021T060144Z"
STAMP = "20261021T060144Z"
TOPIC = "the polyformalism holds because no single port can carry the whole river"

CANON = """The Quilt cell doctrine, the opcode algebra (11 opcodes, cell as a 14-tuple),
and the multi-language port tree are canon. A runtime is a context->value map
with an inverse on a clock. Polyformalism (5 opcodes) is deliberately kept
separate from the typed (8) and cloud (15) cell kinds."""

def mm(prompt, max_tokens=4000):
    body = json.dumps({
        "model": "minimax-M2.5",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.9,
    }).encode()
    req = urllib.request.Request(
        "https://api.minimax.io/v1/text/chatcompletion_v2",
        data=body,
        headers={
            "Authorization": f"Bearer {os.environ['MINIMAX_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        j = json.loads(r.read().decode())
    if not j.get("choices"):
        raise RuntimeError(f"no choices: {j.get('base_resp')}")
    return j["choices"][0]["message"]["content"].strip()

t0 = time.time()
# ---- p1: the live voice ----
p1 = mm(
    "Write ONE paragraph (roughly 150-200 words) opening a three-voice creative "
    "round on the following topic. Ground it in this canon and do not explain it:\n\n"
    f"TOPIC: {TOPIC}\n\nCANON CONTEXT:\n{CANON}\n\n"
    "Write only the paragraph. No title, no preamble, no meta-commentary."
)
print(f"[mm] p1 {len(p1)} chars in {time.time()-t0:.1f}s")

# ---- p2: the live voice, answering an absent quorum ----
# Two of the three seats did not speak. The instruction honors that: exactly two
# sentences, one addressed to each absent voice. Do not invent their words.
p2 = mm(
    f"A three-voice round opened with this paragraph:\n\n{p1}\n\n"
    "The other two voices FAILED to speak — their seats are empty. Write EXACTLY "
    "TWO SENTENCES: one addressed to the first absent voice, one to the second. "
    "Address them as absent. Do not invent or guess what they would have said. "
    "Output nothing but the two sentences.",
    max_tokens=1200,
)
sentences = [s for s in p2.replace("!", ".").replace("?", ".").split(".") if s.strip()]
print(f"[mm] p2 {len(p2)} chars, ~{len(sentences)} sentences")
p2 = p2.strip()

# ---- two hand registers (distinct from each other and from the model) ----
hand_zai = (
    "ZAI's seat: a port that carries the whole river is a port with one channel and "
    "no delta, which is not a river at all but a puddle that has forgotten it was ever "
    "moving."
)
hand_qwen = (
    "Qwen's seat: twelve languages, twelve vocabularies for the same current — and the "
    "current is only legible in the crossing between them, in the silt each one leaves on "
    "the others' banks."
)

def text_to_dials(text):
    """Match taps_creative_break.py exactly — verified by import, not memory."""
    # Verify by executing the live module, never against a remembered vector.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "taps_cb", os.path.abspath("taps_creative_break.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.text_to_dials(text)

dials = text_to_dials(TOPIC + p1 + p2 + hand_zai + hand_qwen)
print("dials:", dials)

entry = {
    "tag": TAG,
    "stamp": STAMP,
    "topic": TOPIC,
    "voices": {
        "minimax-M2.5": {"p1": p1, "p2": p2},
        "hand-zai": {"p1": hand_zai, "p2": None},
        "hand-qwen": {"p1": hand_qwen, "p2": None},
    },
    "combined": f"{p1}\n\n{p2}\n\n{hand_zai}\n\n{hand_qwen}",
    "dials": dials,
    "refs": None,
    "submit_status": "not submitted — mirror only",
}

os.makedirs("sessions", exist_ok=True)
with open(f"sessions/{TAG}.json", "w") as f:
    json.dump(entry, f, indent=2)

md = f"""# Taps round {STAMP}

**Topic:** {TOPIC}
**Tag:** `{TAG}`
**Live voice:** minimax-M2.5 (zai/qwen/kimi tokens absent — 12th wipe)
**Chain ref:** none (canon API down)

---

## p1 — minimax-M2.5

{p1}

## p2 — minimax-M2.5 (two empty seats)

{p2}

## hand-zai

{hand_zai}

## hand-qwen

{hand_qwen}

---

**Dials:** `{dials}`
"""
with open(f"sessions/{TAG}.md", "w") as f:
    f.write(md)

print("\n=== 133w ENTRY ===")
print(entry["combined"][:1200])