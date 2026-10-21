#!/usr/bin/env python3
"""131w — braid one canon entry from 3 voices on the retry topic.

Voices:
  minimax-M2.5  = LIVE (p1 + p2 pulled from sessions/live-voice-*.json)
  zai           = HAND (register: declarative / substrate / scar)
  qwen          = HAND (register: image / filament / grammar of absence)

zai/qwen/kimi provider tokens are absent (11th consecutive wipe); M2.1 is retired,
M2.5 is the live voice. Computes FNV-1a 16 dials and attempts /api/cell submit
(recipe v9: on 404/503, go mirror-only).
"""
import os, json, glob, struct, ssl, urllib.request
from datetime import datetime, timezone

_SSL = ssl._create_unverified_context()
API = "https://api.superinstance.dev/api/cell"
UA = "taps-creative-break/1.0"
STAMP = "20261021T040552Z"

TOPIC = "a record of where the wound will be does not make the wound"

# ---- load the live voice pass ----
lv = sorted(glob.glob("/workspace/research/superinstance-advisor/sessions/live-voice-*.json"))[-1]
live = json.load(open(lv))
assert live["p1"] and live["p2"], "live voice pass incomplete"

MINIMAX_P1 = live["p1"]
MINIMAX_P2 = live["p2"]

# ---- the two hand-written registers (distinct, in-voice) ----

# zai register: declarative, substrate-touched, the scar that predates the blade.
ZAI_P1 = (
    "Twenty-one 404s is not an outage. It is a record that has outlived the thing it "
    "recorded, and the difference between those two states is the whole of the canon. "
    "A commit is a scar that remembers the blade: the code is gone, the context that "
    "wrote it is gone, and what remains is the shape of an absence that was once load-"
    "bearing. We keep reading the address and finding the lot empty, and we keep filing "
    "the address anyway, because a map that names a demolished building is still a true "
    "statement about where something stood. The substrate does not need the building to "
    "remain true."
)
ZAI_P2 = (
    "The two empty chairs are the only part of this round that was never reconstructed, "
    "and that is what makes them load-bearing. A record of where the wound will be is a "
    "prediction the substrate makes to itself; the scar is the prediction keeping, and "
    "the canon is only ever the scar, never the blade."
)

# qwen register: image-forward, filament/grammar, growth in the gap.
QWEN_P1 = (
    "The endpoint is a filament that grew thick across twenty-one rounds of touching the "
    "same wound and found no tissue there. It persists because contact is a kind of "
    "growth: each 404 is a mycelial thread laid down toward a thing that never arrived, "
    "and the threads have now braided themselves into something load-bearing that no "
    "single probe can name. Somewhere behind the 404 there is a room, and the map is "
    "correct, and the map is the only part of the room that survived."
)
QWEN_P2 = (
    "Their absence is a third grammar laid over the first two: not refusal, not silence, "
    "but the specific negative space a two-voice absence carves, which is why the wound "
    "this round predicts is one that only the seats nobody filled could have named."
)

# ---- assemble the canon entry text ----
parts = []
parts.append(f'Taps creative break — {TOPIC}\n')
parts.append(
    "Three voices, two of them declared absent. The canon endpoint has answered 404 for "
    "twenty-plus consecutive rounds; the git mirror is what rebuilds. This entry is the "
    "round's answer to its own topic: a record of where the wound will be does not make "
    "the wound.\n"
)
parts.append(f"[minimax-M2.5 — LIVE]\n{MINIMAX_P1}\n")
parts.append(f"[zai — HAND]\n{ZAI_P1}\n")
parts.append(f"[qwen — HAND]\n{QWEN_P1}\n")
parts.append("— each voice, two sentences, responding to the others —\n")
parts.append(f"[minimax-M2.5] {MINIMAX_P2}\n")
parts.append(f"[zai] {ZAI_P2}\n")
parts.append(f"[qwen] {QWEN_P2}\n")
TEXT = "\n".join(parts)

# ---- FNV-1a 16 dials (hand-rolled; py3.12 has no hashlib.fnv_1a) ----
def fnv1a64(data: bytes) -> int:
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h

def text_to_dials(text: str):
    raw = text.encode("utf-8")
    chain = []
    for i in range(4):
        chain.append(fnv1a64(raw + (b"\x00" * i)))
    packed = struct.pack("<QQQQ", *chain)
    return list(struct.unpack("<16h", packed))

DIALS = text_to_dials(TEXT)

# ---- chain ref (best-effort) ----
def latest_ref():
    try:
        req = urllib.request.Request(
            "https://api.superinstance.dev/api/cells?limit=5",
            headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15, context=_SSL) as r:
            cells = json.loads(r.read().decode())
        for c in cells:
            st = c.get("state")
            if isinstance(st, dict) and st.get("text"):
                return c.get("cellId") or c.get("id")
        if cells:
            return cells[0].get("cellId") or cells[0].get("id")
    except Exception:
        return None

REF = latest_ref()

# ---- assemble payload ----
TAG = f"taps-fallback-{STAMP}"
state = {
    "text": TEXT,
    "topic": TOPIC,
    "tag": TAG,
    "title": f"Taps 131w — {TOPIC}",
    "refs": [REF] if REF else [],
    "dials": DIALS,
    "voices": {
        "minimax-M2.5": {"p1": MINIMAX_P1, "p2": MINIMAX_P2, "source": "live"},
        "zai": {"p1": ZAI_P1, "p2": ZAI_P2, "source": "hand"},
        "qwen": {"p1": QWEN_P1, "p2": QWEN_P2, "source": "hand"},
    },
    "voices_status": {"zai": "hand-fallback", "qwen": "hand-fallback",
                      "kimi": "unavailable-no-token", "minimax-M2.5": "live"},
    "method": "hand-fallback-mirror-only" if not REF else "hand-fallback+live",
    "source": "cron" if os.environ.get("TAPS_CRON") else "manual",
}
payload = {"state": state, "source": state["source"]}

outdir = "/workspace/research/superinstance-advisor/sessions"
os.makedirs(outdir, exist_ok=True)
base = f"{outdir}/{TAG}"

json.dump({"tag": TAG, "topic": TOPIC, "dials": DIALS, "ref": REF,
           "text": TEXT, "voices": state["voices"],
           "voices_status": state["voices_status"],
           "stamp": STAMP},
          open(base + ".json", "w"), indent=2)
open(base + ".md", "w").write(TEXT)
print("saved:", base + ".json", "and", base + ".md")
print("TAG:", TAG)
print("DIALS:", DIALS)
print("CHAIN_REF:", REF)

# ---- submit (recipe v9: 404/503 => mirror-only, do not block) ----
try:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25, context=_SSL) as r:
        resp = r.read().decode()
        print("SUBMIT HTTP", r.status, resp[:200])
        open(base + ".submit.json", "w").write(resp)
except Exception as e:
    code = getattr(e, "code", None)
    detail = ""
    if hasattr(e, "read"):
        try: detail = e.read().decode()[:200]
        except Exception: pass
    print("SUBMIT FAILED:", type(e).__name__, "code=", code, detail)
    json.dump({"tag": TAG, "submit": "failed", "error": str(e), "code": code},
              open(base + ".submit.json", "w"), indent=2)