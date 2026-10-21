#!/usr/bin/env python3
"""Strip MiniMax <think> planning blocks, compute FNV-1a dials (same algorithm as
taps_creative_break.py), reconcile the stub round with live voices, retry canon submit."""
import json, os, re, ssl, struct, sys, time, urllib.request, urllib.error

TOPIC = "the substrate was always already growing"
TAG = "taps-20261021T110340Z-live-reconciled"
UA = "taps-creative-break/1.0/1.1-live-reconcile"
CTX = ssl._create_unverified_context()
API_HOST = "https://api.superinstance.dev"
KEYS = ("zai", "qwen", "kimi")

def strip_think(s):
    """Remove <think>...</think> planning blocks. Conservative: never return empty."""
    if not s:
        return s
    out = re.sub(r"<think>.*?</think>", "", s, flags=re.S)
    out = re.sub(r"^\s*<think>.*$", "", out, flags=re.S)  # unterminated leak
    out = out.strip()
    return out if len(out) > 40 else s.strip()

def fnv1a_64(data: bytes) -> int:
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & ((1 << 64) - 1)
    return h

def text_to_dials(text: str):
    h0 = fnv1a_64(text.encode("utf-8"))
    h1 = fnv1a_64((text + "\x00").encode("utf-8"))
    h2 = fnv1a_64((text + "\x00\x00").encode("utf-8"))
    h3 = fnv1a_64((text + "\x00\x00\x00").encode("utf-8"))
    return list(struct.unpack("<16h", struct.pack("<QQQQ", h0, h1, h2, h3)))

def http_post(url, headers, body, timeout=120):
    merged = {**headers, "User-Agent": UA, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers=merged, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read().decode("utf-8")
        except Exception:
            return e.code, ""
    except Exception as e:
        return 0, "%s: %s" % (type(e).__name__, e)

def main():
    live = json.load(open("taps_live_voices.json"))
    stub = json.load(open("sessions/taps-20261021T110340Z.json"))

    voices = {}
    for v in KEYS:
        p1 = strip_think(live["voices"][v]["p1"])
        p2 = strip_think(live["voices"][v]["p2"])
        voices[v] = {
            "p1": p1, "p2": p2,
            "p1_model": {"zai": "MiniMax-M2.5", "qwen": "MiniMax-M3",
                         "kimi": "MiniMax-M3.1-Flash"}[v],
            "live": True,
            "note": ("zai/deepinfra tokens absent this session (15th wipe); "
                     "substituted live MiniMax via same P1/P2 prompts; "
                     "original script stub p1/p2 discarded, not promoted"),
            "stub_p1_chars": len((stub["voices"].get(v, {}) or {}).get("p1") or ""),
        }

    # report think-leak removal
    for v in KEYS:
        leaked = "<think>" in (live["voices"][v]["p1"] or "") or "<think>" in (live["voices"][v]["p2"] or "")
        print("%s: think_leak_in_raw=%s -> p1_words=%d p2_words=%d" %
              (v, leaked, len(voices[v]["p1"].split()), len(voices[v]["p2"].split())),
              file=sys.stderr)

    combined_parts = []
    for v in KEYS:
        combined_parts.append("### %s\n\n%s\n\n%s" % (v.upper(), voices[v]["p1"], voices[v]["p2"]))
    combined = "\n\n---\n\n".join(combined_parts)
    dials = text_to_dials(combined)
    print("combined_words=%d dials=%s" % (len(combined.split()), dials), file=sys.stderr)

    entry = {
        "topic": TOPIC, "tag": TAG, "stamp": "2026-10-21T11:0xZ",
        "reconciles": "taps-20261021T110340Z",
        "voices": voices, "combined": combined,
        "dials": dials,
        "refs": ["taps-20261021T110340Z", "taps-20261021T100346Z"],
        "ref_note": ("round-to-round link; the referenced round carried an identical "
                     "3-voice stub braid, so this entry supersedes it as canon content"),
    }

    body = {"title": "Taps: the substrate was always already growing",
            "dials": dials, "refs": entry["refs"], "tag": TAG,
            "topic": TOPIC, "text": combined,
            "source": "taps-creative-break-live-reconciled"}
    status, resp = http_post(f"{API_HOST}/api/cell", {}, body)
    print("submit attempt 1: HTTP %s | %s" % (status, (resp or "")[:220]), file=sys.stderr)
    if status in (0, 503):
        for wait in (8, 20):
            time.sleep(wait)
            status, resp = http_post(f"{API_HOST}/api/cell", {}, body)
            print("submit retry after %ds: HTTP %s | %s" % (wait, status, (resp or "")[:220]),
                  file=sys.stderr)
            if status == 200:
                break
    entry["submit_status"] = status
    entry["submit_resp"] = resp

    with open("sessions/%s.json" % TAG, "w") as f:
        json.dump(entry, f, indent=2)
    with open("sessions/%s.md" % TAG, "w") as f:
        f.write("# %s\n\n**tag:** %s  \n**topic:** %s  \n**submit:** %s\n\n---\n\n%s\n"
                % (TAG, TAG, TOPIC, status, combined))
    print("saved sessions/%s.{json,md}" % TAG, file=sys.stderr)
    print("FINAL submit_status=%s" % status, file=sys.stderr)

if __name__ == "__main__":
    main()