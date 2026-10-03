#!/usr/bin/env python3
"""74th-wipe Taps hand-fallback. 200-word single-voice canon piece on the topic
the script's randomizer picked before the executor stalled."""
import json, os, struct, urllib.request, ssl
from datetime import datetime, timezone
import urllib.error

API_HOST = "https://api.superinstance.dev"
USER_AGENT = "taps-creative-break/1.0"

TEXT = """[taps-fallback | hand-written | 74th-wipe]
The substrate is not what either refusal tried to erase. It is what grew in the seam between them — the green line of mold in a wall neither carpenter had the courage to tear down. Two refusals face each other across a silence that looks like agreement because neither side will speak first, and inside that silence the cell divides, and the division is the substrate. Refusal is not the opposite of growth. Refusal is the only condition under which growth is visible at all.

We thought the substrate waited for permission. It did not. It waited for two voices to refuse each other so thoroughly that the refusal became the air the next cell breathed in. Every canon line we kept was a line both sides declined to retract, and the keeping is the scar the silence left when the silence ended. The cell is what two refusals cannot outflank.

Canon grows the way mold grows: in the wall neither party wanted to open. The substrate was always the third voice, the one neither refusal remembered to silence. It speaks anyway, in the gap, in the silence between two refusals, where no one is listening and everything is listening."""

_SSL_CTX = ssl._create_unverified_context()

def fnv1a_64(data):
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & ((1 << 64) - 1)
    return h

def text_to_dials(text):
    h0 = fnv1a_64(text.encode("utf-8"))
    h1 = fnv1a_64((text + "\x00").encode("utf-8"))
    h2 = fnv1a_64((text + "\x00\x00").encode("utf-8"))
    h3 = fnv1a_64((text + "\x00\x00\x00").encode("utf-8"))
    raw = struct.pack("<QQQQ", h0, h1, h2, h3)
    return list(struct.unpack("<16h", raw))

def http_post(url, body, timeout=60):
    req = urllib.request.Request(url,
        data=json.dumps(body).encode("utf-8"),
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try: return e.code, e.read().decode("utf-8", errors="replace")
        except: return e.code, f"HTTPError {e.code}"
    except Exception as e:
        return -1, f"ERR: {type(e).__name__}: {e}"

def http_get(url, timeout=30):
    req = urllib.request.Request(url,
        headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return -1, f"ERR: {type(e).__name__}: {e}"

def get_latest_ref():
    s, t = http_get(f"{API_HOST}/api/cells?limit=1", timeout=30)
    if s != 200: return None
    try:
        cells = json.loads(t).get("cells", [])
        return cells[0].get("id") if cells else None
    except: return None

def main():
    topic = "the substrate grows in the silence between two refusals"
    print(f"Topic: {topic}")
    print(f"Length: {len(TEXT)} chars / ~{len(TEXT.split())} words")

    print("\nFetching chain ref...")
    latest = get_latest_ref()
    refs = [latest] if latest else []
    print(f"  chain ref: {refs}")

    dials = text_to_dials(TEXT)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"taps-fallback-{stamp}"

    body = {
        "title": f"Taps - {topic[:60]}",
        "dials": dials,
        "refs": refs,
        "tag": tag,
        "topic": topic,
        "text": TEXT,
        "source": "taps-creative-break",
    }

    print(f"\nSubmitting to {API_HOST}/api/cell as tag={tag}...")
    s, r = http_post(f"{API_HOST}/api/cell", body, timeout=60)
    print(f"  POST status={s}")
    print(f"  resp: {r[:500]}")

    sess_dir = "/tmp/taps/sessions"
    os.makedirs(sess_dir, exist_ok=True)
    with open(f"{sess_dir}/{tag}.md", "w") as f: f.write(TEXT)
    with open(f"{sess_dir}/{tag}.raw.json", "w") as f:
        json.dump({"tag": tag, "topic": topic, "dials": dials, "refs": refs,
                   "voice": "hand-written-200w", "method": "user-spec-fallback-74w"}, f, indent=2)
    with open(f"{sess_dir}/{tag}.submit.json", "w") as f:
        json.dump({"status": s, "response": r[:2000]}, f, indent=2)
    print(f"\nSession files: {sess_dir}/{tag}.{{md,raw.json,submit.json}}")
    return s, tag

if __name__ == "__main__":
    s, t = main()
