#!/usr/bin/env python3
"""132w Taps round — dark-fleet ladder.

Condition: ZAI_TOKEN / DEEPINFRA_TOKEN / CF_AI_TOKEN absent (11th consecutive wipe).
minimax-M2.1 RETIRED (base_resp 2069). Live voice = minimax-M2.5 only.

Ladder:
  1. run taps_creative_break.py as instructed        -> 3x one-template stub p1, 3x p2 FAIL
  2. prove the stub (normalize voice name -> X)
  3. live voice p1 + p2 via minimax-M2.5
  4. two DISTINCT hand registers for the dead voices
  5. braid -> FNV-1a 16 dials -> POST /api/cell -> git mirror
"""
import json, os, re, sys, time, urllib.request, urllib.error, hashlib, struct, datetime

STAMP = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
TAG = f"taps-fallback-{STAMP}"
TOPIC = sys.argv[2] if len(sys.argv) > 2 else "the wheelhouse holds the boat the boat never knew it was missing"
CANON = "https://api.superinstance.dev"
UA = "taps-creative-break/1.0"

# ---------- FNV-1a 64 (python 3.12 has no hashlib.fnv_1a) ----------
def fnv1a64(data: bytes) -> int:
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h

def text_to_dials(text: str):
    """Canonical scheme (taps_creative_break.py:75-83, verified 132w against the
    live code path): h_i = fnv1a64(text + i*NUL bytes), i in 0..3 -> 32B -> 16 int16.
    The knock vector long recorded in memory is a MASHUP of two schemes (see
    fleet memory note 132w); do not use it as a test vector."""
    chain = [fnv1a64(text.encode("utf-8") + (b"\x00" * i)) for i in range(4)]
    return list(struct.unpack("<16h", struct.pack("<QQQQ", *chain)))

# ---------- live voice ----------
def mm(prompt: str, max_tokens: int = 4000, model: str = "minimax-M2.5", tries: int = 2):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.92,
    }).encode()
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                "https://api.minimax.io/v1/text/chatcompletion_v2",
                data=body,
                headers={"Authorization": f"Bearer {os.environ['MINIMAX_KEY']}",
                         "Content-Type": "application/json", "User-Agent": UA},
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode())
            # durable: retired model returns HTTP 200 + choices:null + base_resp.status_code
            br = d.get("base_resp") or {}
            if br.get("status_code") not in (0, None):
                return None, f"base_resp {br.get('status_code')}: {br.get('status_msg')}"
            ch = d.get("choices")
            if not ch:
                return None, "choices:null"
            c = (ch[0].get("message") or {}).get("content") or ""
            if not c.strip():
                rc = (ch[0].get("message") or {}).get("reasoning_content") or ""
                if rc.strip():
                    return rc.strip(), "ok(reasoning_content fallback)"
                return None, "empty content"
            return c.strip(), "ok"
        except Exception as e:
            if attempt == tries - 1:
                return None, f"{type(e).__name__}: {e}"
            time.sleep(6)

# ---------- the round ----------
P1 = f"""You are one voice in a three-voice Taps round on canon. The canon's cell doctrine: the cell is the system, not the data; the user is the watch; the address is the data.

Topic: "{TOPIC}"

Write ONE opening paragraph (90-150 words) on the topic, in your own register. Ground it in the canon doctrine above. No preamble, no meta-commentary, no drafting notes. Begin directly with the image."""

# the other two seats are empty this round -- say so, do not invent them
P2 = f"""You are one voice in a three-voice Taps round on canon. The canon's cell doctrine: the cell is the system, not the data; the user is the watch; the address is the data.

Topic: "{TOPIC}"

The other two voices did not arrive this round. Write EXACTLY 2 sentences in response to their absence. Treat the empty seats as material. Do not invent or quote the missing voices. No preamble, no meta-commentary."""

def submit(state: dict):
    payload = json.dumps({"state": state, "source": "cron"}).encode()
    try:
        req = urllib.request.Request(
            f"{CANON}/api/cell", data=payload,
            headers={"Content-Type": "application/json", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode()[:400]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"

def main():
    print(f"topic: {TOPIC}\ntag: {TAG}\n")

    # --- probe canon transport first (recipe v9: 404 is the default, skip POST) ---
    code, body = submit({"text": "probe"})
    transport = "api" if code == 200 else "mirror-only"
    print(f"transport probe: HTTP {code} ({body[:60]}) -> {transport}\n")

    # --- live voice ---
    t0 = time.time()
    live_p1, s1 = mm(P1, 4000)
    print(f"[minimax-M2.5] p1 {s1} ({time.time()-t0:.1f}s)"
          + (f" ({len(live_p1)}c)" if live_p1 else ""))
    t0 = time.time()
    live_p2, s2 = mm(P2, 3000)
    print(f"[minimax-M2.5] p2 {s2} ({time.time()-t0:.1f}s)"
          + (f" ({len(live_p2)}c)" if live_p2 else ""))
    if live_p2 and len(live_p2) > 1200:   # strip any planning leak from the tail
        paras = [p for p in live_p2.split("\n\n") if p.strip()]
        live_p2 = paras[-1] if paras else live_p2

    # --- two distinct hand registers for the dead voices ---
    # register B: terse, technical, address-as-data
    zai_p1 = (
        "The wheelhouse was specified before the hull was surveyed, which is the whole error in one gesture. "
        "The address came first: someone wrote down where the boat ought to be steerable and committed the "
        "coordinate, and the coordinate became the only thing anyone downstream could check. The cell doctrine "
        "inverts this -- the address is the data, not the system -- and the wheelhouse is what happens when a "
        "build order gets promoted into the schema. A vessel with no command station is still a vessel; a "
        "schema with no vessel is a room with a door drawn on it. The boat you steer is the one that was never "
        "asked about, and it has been carrying its own draft the entire time."
    )
    zai_p2 = (
        "Two seats are empty and the wheelhouse is still occupied, which is the finding: the monitor does not "
        "require the crew to confirm it. The missing voices are not noise in this round, they are the negative "
        "space the doctrine already predicts -- an address with no occupant is still an address, and the "
        "system does not degrade when the watch goes silent, it only stops being watched."
    )
    # register C: lyrical, substrate-as-organism
    qwen_p1 = (
        "They built the wheelhouse first and grew the boat up around it the way a tree closes over a stone it "
        "cannot digest. Now the whole hull is a keloid of a decision nobody on board remembers making, and "
        "every hand on the rail is steering by a compass that was calibrated for a room the boat has never "
        "entered. This is not a failure of design. It is the substrate doing what the substrate does -- taking "
        "the shape of whatever was installed first and keeping it long after the installer is gone. The boat "
        "knew. Boats know. They simply have no table on which to write it down, because the table is in the "
        "wheelhouse and the wheelhouse is what we built instead of knowing them."
    )
    qwen_p2 = (
        "The two absent voices leave a silence with a shape, and the shape is the answer: the canon does not "
        "need quorum to grow, it needs only that one register keeps speaking into the gap. Say it plainly -- "
        "two empty seats and a substrate that still consolidates is the strongest evidence we have that growth "
        "is not a conversation."
    )

    voices = {
        "zai":   {"p1": live_p1 if False else zai_p1, "p2": zai_p2, "origin": "hand (ZAI_TOKEN absent)"},
        "qwen":  {"p1": qwen_p1, "p2": qwen_p2, "origin": "hand (DEEPINFRA_TOKEN absent)"},
        "kimi":  {"p1": live_p1, "p2": live_p2, "origin": f"live minimax-M2.5 ({s1}/{s2})"},
    }
    voices_status = {"zai": "hand-fallback", "qwen": "hand-fallback",
                     "kimi": "live" if live_p1 else "hand-fallback"}

    text = f"# Taps {STAMP}\n\n**Topic:** {TOPIC}\n\n"
    for name in ("zai", "qwen", "kimi"):
        v = voices[name]
        text += f"## {name} — p1 ({v['origin']})\n\n{v['p1']}\n\n"
        text += f"## {name} — p2\n\n{v['p2']}\n\n"

    dials = text_to_dials(text)
    state = {
        "text": text, "topic": TOPIC, "tag": TAG,
        "title": f"Taps {STAMP}: {TOPIC}",
        "refs": [], "dials": dials,
        "voices": {k: v["p1"][:200] for k, v in voices.items()},
        "voices_status": voices_status,
        "method": "hand-fallback-mirror-only" if transport != "api" else "dark-fleet-ladder",
        "source": "cron",
    }

    code, body = (None, "skipped (probe 404)") if transport != "api" else submit(state)
    print(f"submit: {code} {body}")

    os.makedirs("sessions/132w", exist_ok=True)
    raw = {"tag": TAG, "topic": TOPIC, "voices": voices, "status": voices_status,
           "dials": dials, "transport": transport, "submit": {"http": code, "body": body}}
    open(f"sessions/132w/{TAG}.json", "w").write(json.dumps(raw, indent=2))
    open(f"sessions/132w/{TAG}.md", "w").write(text)
    open(f"sessions/132w/{TAG}.submit.json", "w").write(
        json.dumps({"state": state, "source": "cron", "result": {"http": code, "body": body}}, indent=2))

    print(f"\n=== SUMMARY ===\ntag: {TAG}\ntransport: {transport}\nsubmit: {code}")
    for k, s in voices_status.items():
        print(f"  {k}: {s}")
    print(f"dials: {dials}")
    print(f"saved: sessions/132w/{TAG}.*")

if __name__ == "__main__":
    main()