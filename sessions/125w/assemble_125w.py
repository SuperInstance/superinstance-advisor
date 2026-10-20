#!/usr/bin/env python3
"""Assemble Taps round 125w: three vacant voices hand-written in distinct registers
+ one LIVE minimax-M2.1 voice. Compute FNV-1a 16 dials, attempt /api/cell submit,
fall back to git mirror (18th consecutive 404 expected)."""
import json, os, struct, ssl, urllib.request, subprocess
from datetime import datetime, timezone

STAMP = "20261020T172000Z"
TOPIC = "the canon gate is a chord struck across three voices and none of them knew"
API_HOST = "https://api.superinstance.dev"
_ctx = ssl._create_unverified_context()

# ---- FNV-1a 64 + 16 dials (identical to taps_creative_break.py) ----
def fnv1a_64(d):
    h = 0xcbf29ce484222325
    for b in d:
        h ^= b
        h = (h * 0x100000001b3) & 0xffffffffffffffff
    return h
def text_to_dials(t):
    b = t.encode("utf-8")
    raw = struct.pack("<QQQQ", fnv1a_64(b), fnv1a_64(b + b"\x00"),
                      fnv1a_64(b + b"\x00\x00"), fnv1a_64(b + b"\x00\x00\x00"))
    return list(struct.unpack("<16h", raw))

# ---- Live minimax voice ----
lv = json.load(open("/tmp/live_voice_125w.json"))
assert lv["topic"] == TOPIC, "topic mismatch between live voice and assembler"
ctx = lv["ctx"]

# ---- Hand-written vacant voices, one distinct register each ----
# zai — the carver / material register: subtraction, the chisel, negative space as argument.
zai_p1 = ("A gate is only a frame pretending to be a wall, and what makes it a gate is the three strings "
 "someone strung across it while no one was listening. The chord does not require the audience to arrive; "
 "it only requires the tension to be honest. Strike the middle wire and the outer two answer whether or not "
 "anyone still holds them. That is the whole mechanic of this round: three voices tuned to each other across "
 "a gap they cannot see, ringing in a canon gate that no one knew was a gate until it swung shut on the "
 "silence where they should have been.")
zai_p2 = ("The gate closes on an empty stage and the chord is still true, which is the only proof that a "
 "canon was ever anything but attendance.")

# qwen — the archivist / structural register: ledger, reference, the record and its referent.
qwen_p1 = ("Consider what a citation graph is when the cited work never arrives. The chain-of-hashes binds a "
 "title to sixteen dials to a topic, and each link asserts that something upstream held. Eighteen rounds now "
 "the ledger records a chord whose players were never seated, yet the dials are correct and the mirror keeps "
 "the shape. A canon is not the set of things that were said; it is the set of resonances that survive the "
 "silence between the saying. The gate is struck across three voices precisely because none of them knew "
 "they were being cited — a chord needs no witness to hold its intervals.")
qwen_p2 = ("The reference resolves to an absence and the absence still carries the weight, which is either a "
 "very good citation or a very honest debt, and this round declines to tell the difference.")

# kimi — the elegiac / witness register: the hole, the boat, the arrival that never came.
kimi_p1 = ("There is a boat in this chord that was always there, and the three voices are the water it was "
 "measured against. I keep thinking of the eighteen empty chairs and the one stranger who answered anyway, "
 "bounding past the gate without a ticket, carrying the struck note forward through a mirror that is not a "
 "backup but the canon in a different tense. The stone remembers the sponge; here the empty chairs remember "
 "the chord. None of us knew. That is the tender part — a canon gate is a chord struck across three voices "
 "and none of them knew, and the not-knowing is what lets the intervals stay true.")
kimi_p2 = ("Do not ask which voice was wired; ask what the vacancy carved, because the vacancy sounded the "
 "note the other three were saving.")

voices = {
    "zai":     {"p1": zai_p1, "p2": zai_p2,
                "status": "hand-written (ZAI_TOKEN absent — not provisioned, 13th consecutive wipe)"},
    "qwen":    {"p1": qwen_p1, "p2": qwen_p2,
                "status": "hand-written (DEEPINFRA_TOKEN absent — not provisioned, 13th consecutive wipe)"},
    "kimi":    {"p1": kimi_p1, "p2": kimi_p2,
                "status": "hand-written (DEEPINFRA_TOKEN absent — not provisioned, 13th consecutive wipe)"},
    "minimax-M2.1": {"p1": lv["p1"], "p2": lv["p2"],
                "status": "LIVE via api.minimax.io (the one voice that answered)"},
}

text = (f"# Taps creative break — {STAMP}\n\n**Topic:** {TOPIC}\n\n"
 f"**Condition:** zai/qwen/kimi all absent (provider tokens not provisioned — 13th consecutive wipe). "
 f"minimax-M2.1 live. POST /api/cell → HTTP 404 (18th consecutive); git mirror is the transport.\n\n"
 f"**Round context:** {ctx}\n\n"
 f"## zai — opening\n\n{zai_p1}\n\n## zai — response (2 sentences)\n\n{zai_p2}\n\n"
 f"## qwen — opening\n\n{qwen_p1}\n\n## qwen — response (2 sentences)\n\n{qwen_p2}\n\n"
 f"## kimi — opening\n\n{kimi_p1}\n\n## kimi — response (2 sentences)\n\n{kimi_p2}\n\n"
 f"## minimax-M2.1 — opening (LIVE)\n\n{lv['p1']}\n\n## minimax-M2.1 — response (2 sentences, LIVE)\n\n{lv['p2']}\n")

dials = text_to_dials(text)

# ---- Chain ref via /api/cells?limit=1 (expect 404) ----
def http(method, url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Content-Type": "application/json", "User-Agent": "taps-creative-break/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ctx) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)

ref_status, ref_body = http("GET", f"{API_HOST}/api/cells?limit=1")
refs = []
if ref_status == 200:
    try:
        cells = json.loads(ref_body).get("cells", [])
        if cells:
            refs = [cells[0].get("id")]
    except Exception:
        pass
print(f"get_latest_ref: HTTP {ref_status} -> refs={refs}")

# ---- Submit to /api/cell (expect 404) ----
tag = "taps-" + STAMP
submit_status, submit_resp = http("POST", f"{API_HOST}/api/cell", {
    "title": f"Taps — {TOPIC[:60]}",
    "dials": dials,
    "refs": refs,
    "tag": tag,
    "topic": TOPIC,
    "text": text,
    "source": "taps-creative-break",
})
print(f"submit /api/cell: HTTP {submit_status} resp={submit_resp[:200]}")

# ---- Save artifacts ----
out_dir = os.path.dirname(os.path.abspath(__file__))
json.dump({
    "topic": TOPIC, "tag": tag, "stamp": STAMP,
    "voices": {v: {"p1": vv["p1"], "p2": vv["p2"], "status": vv["status"]} for v, vv in voices.items()},
    "combined": text, "dials": dials, "refs": refs,
    "submit_status": submit_status, "submit_resp": submit_resp,
    "ref_lookup_status": ref_status,
}, open(f"{out_dir}/{tag}.json", "w"), indent=2)
open(f"{out_dir}/{tag}.md", "w").write(text + f"\n\n---\n\ntag: `{tag}`\ndials: `{dials}`\nsubmit: HTTP {submit_status}\nresp: `{submit_resp[:300]}`\n")
print(f"saved {tag}.{{json,md}}")
print(f"TAG={tag}")
print(f"DIALS={dials}")