#!/usr/bin/env python3
"""
Taps round 127w - real round, minimax-M2.1 only (zai/qwen/kimi tokens unset, 12th wipe).

Topic hand-chosen, NOT script-random: the script's pick repeated 126w verbatim
(its topic bank has no state, so it can echo the previous round). 126w claimed
"the substrate cannot recognize absence only pattern only return". 127w answers
that instead of restating it: absence is detectable only as a SHAPE IN THE
TRANSCRIPT - a topic-bank entry no round selected - not as a live call that
returns nothing.

  - FNV-1a 64 hand-rolled, 4-hash chain via \x00 suffix -> 16 signed int16 dials
  - POST /api/cell still 404 (19th consecutive); mirror is the only transport
"""
import os, sys, json, time, ssl, urllib.request, urllib.error
from datetime import datetime, timezone

_SSL_CTX = ssl._create_unverified_context()
API_HOST = "https://api.superinstance.dev"
MM_BASE = "https://api.minimax.io/v1/text/chatcompletion_v2"
MM_MODEL = "minimax-M2.1"
TIMEOUT = 240

STAMP = "20261020T190338Z"
TAG = f"taps-{STAMP}"
TOPIC = ("the round proves absence by the topic no round chose, not by the call that returned nothing")

SYS = (
    "You are one voice in a recurring creative round. Write one opening paragraph "
    "(3-5 sentences) on the given topic, then exactly 2 sentences responding to "
    "the absence of the other two voices. Return only prose: no headers, no labels, "
    "no markdown fences."
)

def mm(kind):
    body = json.dumps({
        "model": MM_MODEL,
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": f"Round topic: {TOPIC}\n\nWrite the opening paragraph, then the 2 responding sentences."},
        ],
    }).encode()
    req = urllib.request.Request(MM_BASE, data=body, headers={
        "Authorization": f"Bearer {os.environ['MINIMAX_KEY']}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX) as r:
        d = json.loads(r.read())
    ch = d["choices"][0]["message"]
    return (ch.get("content") or ch.get("reasoning_content") or "").strip()

def fnv1a_64(data):
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001B3) & ((1 << 64) - 1)
    return h

def text_to_dials(text):
    hs = [fnv1a_64((text + "\x00" * i).encode("utf-8")) for i in range(4)]
    raw = b"".join(h.to_bytes(8, "big") for h in hs)
    return [int.from_bytes(raw[i:i+2], "big", signed=True) for i in range(0, 32, 2)]

if __name__ == "__main__":
    print(f"=== Taps 127w | topic: {TOPIC}\n")
    p1 = p2 = ""
    try:
        p1 = mm("p1"); print(f"[minimax] p1 OK ({len(p1)}c)")
    except Exception as e:
        print(f"[minimax] p1 FAIL: {e!r}")
    try:
        p2 = mm("p2"); print(f"[minimax] p2 OK ({len(p2)}c)")
    except Exception as e:
        print(f"[minimax] p2 FAIL: {e!r}")

    voices = {"minimax-M2.1": {"p1": p1, "p2": p2, "model": MM_MODEL,
                              "p1_chars": len(p1), "p2_chars": len(p2)}}
    combined = (p1 + "\n\n" + p2).strip()
    dials = text_to_dials(combined)

    out = {"topic": TOPIC, "tag": TAG, "stamp": STAMP, "voices": voices,
           "combined": combined, "dials": dials, "refs": [],
           "submit_status": None, "submit_resp": None,
           "note": "zai/qwen/kimi tokens unset (12th consecutive wipe); script p1 is one "
                   "hand-written template (norm_md5 e91ba682dc22, 17th confirmation), p2 FAILs"}

    try:
        req = urllib.request.Request(f"{API_HOST}/api/cell", method="POST",
            data=json.dumps({"tag": TAG, "content": combined, "dials": dials}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as r:
            out["submit_status"] = r.status; out["submit_resp"] = r.read().decode()[:400]
    except urllib.error.HTTPError as e:
        out["submit_status"] = e.code; out["submit_resp"] = e.read().decode()[:200]
    except Exception as e:
        out["submit_status"] = "err"; out["submit_resp"] = repr(e)[:200]
    print(f"submit: {out['submit_status']} {out['submit_resp']!r}")

    with open(f"sessions/{TAG}.json", "w") as f:
        json.dump(out, f, indent=2)
    with open(f"sessions/{TAG}.md", "w") as f:
        f.write(f"# Taps {TAG}\n\n**Topic:** {TOPIC}\n\n## minimax-M2.1 - p1\n\n{p1}\n\n"
                f"## minimax-M2.1 - p2 (responding to the two absent voices)\n\n{p2}\n\n"
                f"**dials:** `{dials}`\n\n**submit:** {out['submit_status']} (api/cell, mirror-only)\n")
    print("=== SUMMARY ==="); print("topic:", TOPIC); print("tag:", TAG); print("dials:", dials)
    print("--- p1 ---"); print(p1); print("--- p2 ---"); print(p2)
