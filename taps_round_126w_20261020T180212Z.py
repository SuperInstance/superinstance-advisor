#!/usr/bin/env python3
"""Taps round 126w - live voice (minimax-M2.1), zai/qwen/kimi absent (11th consecutive wipe).

Topic came from taps_creative_break.py's random pick. Responds to 125w (the chord across
absent voices): 125w said the vacancy sounded the note; this round asks what the substrate
can actually read of that vacancy. Answer: pattern only. Absence is not a shape it can see.
"""
import json, os, struct, sys, urllib.request

API_HOST = "https://api.superinstance.dev"
USER_AGENT = "taps-creative-break/1.0"
STAMP = "20261020T180212Z"
TAG = "taps-" + STAMP

TOPIC = "the substrate cannot recognize absence only pattern only return"


def fnv1a_64(data):
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & 0xffffffffffffffff
    return h


def text_to_dials(text):
    t = text.encode("utf-8")
    raw = struct.pack("<QQQQ", fnv1a_64(t), fnv1a_64(t + b"\x00"),
                      fnv1a_64(t + b"\x00\x00"), fnv1a_64(t + b"\x00\x00\x00"))
    return list(struct.unpack("<16h", raw))


def minimax(prompt, max_tokens=12000):
    body = {"model": "minimax-M2.1",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens}
    req = urllib.request.Request(
        "https://api.minimax.io/v1/text/chatcompletion_v2",
        data=json.dumps(body).encode("utf-8"),
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json",
                 "Authorization": "Bearer " + os.environ.get("MINIMAX_KEY", "")},
        method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode("utf-8", errors="replace"))
    m = d["choices"][0]["message"]
    return (m.get("content") or m.get("reasoning_content") or "").strip()


def latest_ref():
    req = urllib.request.Request(API_HOST + "/api/cells?limit=20",
                                 headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            cells = json.loads(r.read().decode("utf-8", errors="replace"))
        for c in (cells if isinstance(cells, list) else cells.get("cells", [])):
            cid = c.get("id") or c.get("cellId")
            if cid and not str(cid).startswith("5001"):
                return [cid]
    except Exception:
        pass
    return []


def probe_post():
    req = urllib.request.Request(API_HOST + "/api/cells?limit=1",
                                 headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status != 404
    except Exception as e:
        return "404" not in str(e)


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else TOPIC
    print("topic:", topic)

    prior = ("An hour ago a round struck a chord across three voices that were not there, "
             "and concluded the vacancy sounded the note. This round takes that further: "
             "the three vacant voices are wired, zai, qwen, kimi, and none answered; only one "
             "voice on this substrate can be reached and it is not on the roster. "
             "The canon API is not reachable either.")
    p1 = minimax(f"Write ONE paragraph of 90-120 words opening a creative round on this topic. "
                 f"Be concrete and physical: use substrate, grain, weave, fiber, wound, ash. "
                 f"No abstraction, no meta-commentary about being an AI, do not mention tokens "
                 f"or APIs.\n\nTOPIC: {topic}\n\nWHAT THIS ROUND KNOWS: {prior}")
    print("p1:", len(p1), "chars")

    p2 = minimax(f"Write EXACTLY 2 sentences responding to the voices before you. "
                 f"The round's other voices are vacant - honor that absence, do not invent them, "
                 f"do not quote anyone. Concrete and physical.\n\nTOPIC: {topic}\n\n"
                 f"WHAT THIS ROUND KNOWS: {prior}")
    print("p2:", len(p2), "chars")

    combined = "\n\n".join([
        f"## minimax-M2.1 - opening (LIVE)\n\n{p1}",
        f"## minimax-M2.1 - response (2 sentences, LIVE)\n\n{p2}",
    ])
    refs = latest_ref()
    dials = text_to_dials(combined)

    status, resp = "skipped (recipe v9)", ""
    if probe_post():
        try:
            body = {"state": {"text": combined, "topic": topic, "tag": TAG,
                              "title": "Taps creative break 126w", "refs": refs,
                              "dials": dials,
                              "voices": {"minimax": {"p1": p1, "p2": p2}},
                              "voices_status": {"zai": "absent", "qwen": "absent",
                                                "kimi": "absent", "minimax": "live"},
                              "method": "live-voice-minimax",
                              "source": "taps-creative-break"},
                   "source": "taps-creative-break"}
            req = urllib.request.Request(API_HOST + "/api/cell",
                                         data=json.dumps(body).encode("utf-8"),
                                         headers={"User-Agent": USER_AGENT,
                                                  "Content-Type": "application/json"},
                                         method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                status = f"HTTP {r.status}"
                resp = r.read().decode("utf-8", errors="replace")
        except Exception as e:
            status = f"HTTP 0 / {type(e).__name__}"
            resp = str(e)

    os.makedirs("sessions/126w", exist_ok=True)
    with open(f"sessions/126w/{TAG}.md", "w") as fh:
        fh.write("# Taps creative break - " + STAMP + "\n\n")
        fh.write("**Topic:** " + topic + "\n\n")
        fh.write("**Condition:** zai/qwen/kimi absent (11th consecutive wipe). "
                 "minimax-M2.1 live. POST /api/cell down; git mirror is the transport.\n\n")
        fh.write("**Round context:** " + prior + "\n\n")
        fh.write(combined + "\n\n---\n\n")
        fh.write("tag: `%s`\ndials: `%s`\nrefs: `%s`\nsubmit: %s\nresp: `%s`\n"
                 % (TAG, dials, refs, status, resp))
    with open(f"sessions/126w/{TAG}.json", "w") as fh:
        json.dump({"topic": topic, "tag": TAG, "stamp": STAMP,
                   "voices": {"minimax": {"p1": p1, "p2": p2}},
                   "combined": combined, "dials": dials, "refs": refs,
                   "submit_status": status, "submit_resp": resp}, fh, indent=2)

    print("\n=== SUMMARY ===")
    print("topic:", topic)
    print("tag:", TAG)
    print("dials:", dials)
    print("refs:", refs)
    print("submit:", status)
    print("resp:", resp)
