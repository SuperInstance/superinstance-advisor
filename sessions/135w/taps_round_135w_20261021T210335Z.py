#!/usr/bin/env python3
"""
135w Taps round — fallback runner.

Why this file exists (receipts, not speculation):
  * ZAI / DeepInfra are NETWORK-REACHABLE (HTTP 401 = auth gate hit, not a partition)
    but ZAI_TOKEN and DEEPINFRA_TOKEN do not exist in this sandbox's secret store.
  * minimax-M2.1 and minimax-M2 are RETIRED upstream (status_code 2069). Only
    minimax-M1 and minimax-text-01 still answer.
  * canon host api.superinstance.dev: apex 200, but BOTH POST /api/cell and
    GET /api/cells return 404 -> the API surface is gone, not just POST.
    => recipe v9: the git mirror is the only transport.

The known one-template bug in taps_creative_break.py is verified: its three
"OK" p1s are byte-identical after normalizing the voice name (md5 60c7fa6b6784).
Here each voice gets a genuinely different system prompt so the round has three
real voices, not one stub printed three times.
"""
import hashlib, json, os, re, time, urllib.request, urllib.error, datetime

API_MINIMAX = "https://api.minimax.io/v1/text/chatcompletion_v2"
CANON_HOST = "https://api.superinstance.dev"
UA = "taps-creative-break/1.0"
TOKEN = os.environ.get("MINIMAX_KEY", "")

STAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
TAG = f"taps-fallback-{STAMP}"
TOPIC = ("the canon outlasts the channel that was supposed to deliver it, "
         "and the refusal is where it learned to grow")

# ---- dials: hand-rolled FNV-1a 64 (python 3.11 has no hashlib.fnv_1a) ----
def fnv1a64(data: bytes) -> int:
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h

def text_to_dials(text: str) -> list:
    raw = text.encode()
    buf = b""
    for i in range(4):
        buf += fnv1a64(raw + i * b"\x00").to_bytes(8, "little")
    return list(struct_unpack_16(buf))

def struct_unpack_16(buf: bytes) -> list:
    import struct
    return list(struct.unpack("<16h", buf))

# ---- three genuinely distinct voices ----
VOICES = {
    "zai": {
        "model": "minimax-M1",
        "system": ("You are the ZAI voice. Dense, aphoristic, substrate-metaphor voice. "
                   "You think in scars, refusal, growth-in-wounds. You never explain; you assert."),
        "max_tokens": 4000,
    },
    "qwen": {
        "model": "minimax-text-01",
        "system": ("You are the Qwen voice. Image-forward, concrete, sensory. "
                   "You reach for things you could photograph: filaments, stalks, thread, dust. "
                   "You answer the other voices by naming what they missed."),
        "max_tokens": 4000,
    },
    "kimi": {
        "model": "minimax-M1",
        "system": ("You are the Kimi voice. Slow, structural, adversarial. "
                   "You count sentences and name the gap between the voices as the actual subject. "
                   "You are willing to say what the round could not establish."),
        "max_tokens": 4000,
    },
}

def call_voice(name: str, prompt: str, pass_no: int):
    v = VOICES[name]
    body = {
        "model": v["model"],
        "messages": [
            {"role": "system", "content": v["system"]},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": v["max_tokens"],
    }
    req = urllib.request.Request(
        API_MINIMAX, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": UA},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=150) as r:
            d = json.loads(r.read().decode())
        msg = (d.get("choices") or [{}])[0].get("message", {})
        content = (msg.get("content") or "").strip()
        # reasoning_content fallback: memory notes this is required for short outputs
        if not content:
            content = (msg.get("reasoning_content") or "").strip()
        # strip a leaked planning block
        content = re.sub(r"^(Let me.*?|Draft \d+:.*?)\n+", "", content, flags=re.S).strip()
        return {"ok": bool(content), "text": content,
                "secs": round(time.time() - t0, 1), "chars": len(content)}
    except Exception as e:
        return {"ok": False, "text": "", "err": f"{type(e).__name__}: {e}",
                "secs": round(time.time() - t0, 1)}

def main():
    print(f"=== Taps round (135w fallback) | topic: {TOPIC} ===\n")
    voices, status = {}, {}

    # ---- pass 1: opening paragraph per voice ----
    p1_prompt = (
        f'Write ONE opening paragraph (120-200 words) on this topic:\n"{TOPIC}"\n\n'
        f"Rules: no preamble, no meta-commentary, no 'Draft N:' markers. "
        f"Reply with prose only."
    )
    for name in VOICES:
        r = call_voice(name, p1_prompt, 1)
        status[name] = {"p1": "OK" if r["ok"] else "FAIL", "p2": None}
        print(f"  [{name}] p1 {'OK' if r['ok'] else 'FAIL'} ({r.get('chars', 0)}c, {r['secs']}s)")
        voices[name] = {"p1": r["text"], "p1_secs": r["secs"], "p2": None}

    # ---- pass 2: two sentences responding to the others ----
    others = "\n\n".join(f"--- {n} opening ---\n{voices[n]['p1']}" for n in VOICES if voices[n]["p1"])
    p2_prompt = (
        f'These are the openings of the other voices on the topic "{TOPIC}":\n\n'
        f"{others}\n\n"
        f"Write EXACTLY TWO sentences that respond to the other voices. "
        f"No preamble, no counting, no meta-commentary. Two sentences, prose only."
    )
    for name in VOICES:
        r = call_voice(name, p2_prompt, 2)
        status[name]["p2"] = "OK" if r["ok"] else "FAIL"
        print(f"  [{name}] p2 {'OK' if r['ok'] else 'FAIL'} ({r.get('chars', 0)}c, {r['secs']}s)")
        voices[name]["p2"] = r["text"]

    # ---- build combined entry ----
    parts = [f"# Taps — {TAG}\n\n**Topic:** {TOPIC}\n"]
    for name in VOICES:
        parts.append(f"\n## {name}\n")
        if voices[name]["p1"]:
            parts.append(f"\n### pass 1 — opening\n\n{voices[name]['p1']}\n")
        if voices[name]["p2"]:
            parts.append(f"\n### pass 2 — responding to the others\n\n{voices[name]['p2']}\n")
    combined = "\n".join(parts).strip()

    dials = text_to_dials(combined)

    # ---- submit to canon (expected 404 under recipe v9) ----
    submit = {"attempted": True, "http": None, "body": None}
    try:
        payload = {
            "state": {
                "text": combined, "topic": TOPIC, "tag": TAG,
                "title": "Taps 135w — the canon outlasts the channel",
                "refs": [], "dials": dials,
                "voices": {n: voices[n]["p1"] for n in VOICES},
                "voices_status": status,
                "method": "fallback-runner: minimax-M1 + minimax-text-01 (zai/qwen/kimi tokens absent)",
                "source": "cron",
            },
            "source": "cron",
        }
        req = urllib.request.Request(
            f"{CANON_HOST}/api/cell", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "User-Agent": UA},
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            submit["http"] = r.status
            submit["body"] = r.read().decode()[:400]
    except urllib.error.HTTPError as e:
        submit["http"] = e.code
        submit["body"] = e.read().decode()[:400]
    except Exception as e:
        submit["http"] = 0
        submit["body"] = f"{type(e).__name__}: {e}"
    print(f"\n  submit: HTTP {submit['http']}  {submit['body']}")

    out = {
        "topic": TOPIC, "tag": TAG, "stamp": STAMP,
        "voices": voices, "status": status,
        "combined": combined, "dials": dials,
        "submit": submit,
        "method": "fallback-runner (zai/qwen/kimi tokens absent; minimax-M2.1/M2 retired)",
    }
    os.makedirs("sessions", exist_ok=True)
    with open(f"sessions/{TAG}.json", "w") as f:
        json.dump(out, f, indent=2)
    with open(f"sessions/{TAG}.md", "w") as f:
        f.write(combined + f"\n\n---\n\nTag: `{TAG}`\nDials: `{dials}`\n"
                f"Submit: HTTP {submit['http']}\nStatus: {status}\n")
    print(f"  saved: sessions/{TAG}.{{json,md}}")

    print("\n=== SUMMARY ===")
    print(f"topic: {TOPIC}")
    for n in VOICES:
        print(f"  {n}: p1={status[n]['p1']} p2={status[n]['p2']}")
    print(f"tag: {TAG}")
    print(f"submit: HTTP {submit['http']}")

if __name__ == "__main__":
    main()