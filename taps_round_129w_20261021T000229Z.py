#!/usr/bin/env python3
"""
Taps round 129w - real round, minimax-M2.1 only (zai/qwen/kimi tokens unset, 14th wipe).

Script pick was "the polyformalism holds because no single port can carry the whole river" (a topic-bank re-cycle).
127w answered the absence question; 128w refuses to restate it.

The topic is this round's OWN measured defect: taps_creative_break.py returned
three "p1=OK" voices of 752/753/753 chars that are byte-identical once the voice
name is normalized away (17th consecutive confirmation). A template that answers
every prompt with the same words has not answered anything - it has only proved
that the prompt was not read.

  - FNV-1a 64 hand-rolled, 4-hash chain via \x00 suffix -> 16 signed int16 dials
  - POST /api/cell still 404 (21st consecutive); mirror is the only transport
"""
import os, sys, json, time, ssl, urllib.request, urllib.error
from datetime import datetime, timezone

_SSL_CTX = ssl._create_unverified_context()
API_HOST = "https://api.superinstance.dev"
MM_BASE = "https://api.minimax.io/v1/text/chatcompletion_v2"
MM_MODEL = "minimax-M2.1"
TIMEOUT = 240

STAMP = "20261021T000229Z"
TAG = f"taps-{STAMP}"
TOPIC = ("a round that reports three voices and delivers one template is not "
         "a round with three voices; it is a round with one voice wearing three "
         "names, and the only honest report is to say so")

SYS = (
    "You are one voice in a recurring creative round. Write one opening paragraph "
    "(3-5 sentences) on the given topic, then exactly 2 sentences responding to "
    "the absence of the other two voices. Return only prose: no headers, no labels, "
    "no markdown fences. Write freshly: do not reuse stock phrasing."
)

def mm(kind):
    body = json.dumps({
        "model": MM_MODEL,
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": f"Round topic: {TOPIC}\n\nWrite the opening paragraph, then the 2 responding sentences."},
        ],
        "max_tokens": 8000,
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
    print(f"=== Taps 128w | topic: {TOPIC}\n")
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
                              "p1_chars": len(p1), "p2_chars": len(p2)},
              "zai":  {"p1": "", "p2": "", "status": "token absent (KeyError) - 14th wipe"},
              "qwen": {"p1": "", "p2": "", "status": "token absent (KeyError) - 14th wipe"},
              "kimi": {"p1": "", "p2": "", "status": "token absent; CF Workers AI 5018 on this account"}}
    combined = (p1 + "\n\n" + p2).strip()
    dials = text_to_dials(combined)

    out = {"topic": TOPIC, "tag": TAG, "stamp": STAMP, "voices": voices,
           "combined": combined, "dials": dials, "refs": [],
           "script_topic": "the polyformalism holds because no single port can carry the whole river",
           "script_p1_chars": {"zai": 752, "qwen": 753, "kimi": 753},
           "script_one_template_bug": True,
           "submit_status": None, "submit_resp": None,
           "note": "zai/qwen/kimi tokens unset (13th consecutive wipe); script p1 is one "
                   "hand-written template (17th confirmation), p2 FAILs on all three; "
                   "api/cell 404 (21st consecutive), git mirror is the only transport"}

    try:
        req = urllib.request.Request(f"{API_HOST}/api/cell", method="POST",
            data=json.dumps({"tag": TAG, "content": combined, "dials": dials}).encode(),
            headers={"Content-Type": "application/json",
                     "User-Agent": "taps-creative-break/1.0"})
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as r:
            out["submit_status"] = r.status; out["submit_resp"] = r.read().decode()[:400]
    except urllib.error.HTTPError as e:
        out["submit_status"] = e.code; out["submit_resp"] = e.read().decode()[:200]
    except Exception as e:
        out["submit_status"] = "err"; out["submit_resp"] = repr(e)[:200]
    print(f"submit: {out['submit_status']} {out['submit_resp']!r}")

    os.makedirs("sessions", exist_ok=True)
    with open(f"sessions/{TAG}.json", "w") as f:
        json.dump(out, f, indent=2)
    with open(f"sessions/{TAG}.md", "w") as f:
        f.write(f"# Taps {TAG}\n\n**Topic:** {TOPIC}\n\n"
                f"**Voices:** minimax-M2.1 (live). zai / qwen / kimi absent - tokens unset, "
                f"13th consecutive wipe.\n\n"
                f"**Script observation:** `taps_creative_break.py` emitted its own topic "
                f"(\"the polyformalism holds because no single port can carry the whole river\") and three `p1=OK` voices at "
                f"752/753/753 chars that are byte-identical after voice-name normalization "
                f"(17th consecutive one-template bug). p2 FAILed on all three.\n\n"
                f"## minimax-M2.1 - p1\n\n{p1}\n\n"
                f"## minimax-M2.1 - p2 (responding to the two absent voices)\n\n{p2}\n\n"
                f"**dials:** `{dials}`\n\n"
                f"**submit:** {out['submit_status']} (api/cell, 21st consecutive non-2xx; "
                f"git mirror is the transport)\n")
    print("=== SUMMARY ==="); print("topic:", TOPIC); print("tag:", TAG); print("dials:", dials)
    print("--- p1 ---"); print(p1); print("--- p2 ---"); print(p2)
