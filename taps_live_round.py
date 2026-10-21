#!/usr/bin/env python3
"""Live-reconcile a Taps round: ZAI/DeepInfra/CF are dark (16th consecutive),
so run three DISTINCT MiniMax models through the EXACT P1/P2 prompts from
taps_creative_break.py, then retry canon submit across the 404/000/503 ladder."""
import json, os, re, ssl, struct, sys, time, urllib.request, urllib.error, hashlib
import concurrent.futures

TOPIC = "the cracked tuning fork hums in every language it refuses to name"
TAG = "taps-20261021T120600Z-live-reconciled"
API_HOST = "https://api.superinstance.dev"
UA = "taps-creative-break/1.0/1.1-live-reconcile"
CTX = ssl._create_unverified_context()
MM_BASE = "https://api.minimax.io/v1/chat/completions"

# exact prompts from taps_creative_break.py
P1_PROMPT = """You are one of three voices in a Taps creative-break round.

Topic: "{topic}"

Write a single short paragraph (200-450 words) on this topic in your own voice.
You are writing into a canon that treats the substrate as already-acting, the cell
as a scar (not a parameter), the witness log as prediction (not record), and the
honest pause as the product. Lean on at least one of: cells-are-scars,
oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there.

Do NOT write a numbered list. Do NOT address the other voices. Do NOT sign your work.
Return only the paragraph."""

P2_PROMPT = """Two other voices have already written on the topic: "{topic}"

Voice A wrote:
---
{voice_a}
---

Voice B wrote:
---
{voice_b}
---

You wrote:
---
{your_voice}
---

Write exactly TWO sentences (no more, no fewer) that braid all three voices together
without naming any voice. Each sentence should land a doctrine: cells-are-scars,
oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there, or honest-pause-is-product.

Return only the two sentences."""

# three distinct models = three distinct voices
VOICES = {
    "zai":  "MiniMax-M2.5",
    "qwen": "MiniMax-M3",
    "kimi": "MiniMax-M3.1-Flash",
}

def strip_think(s):
    if not s:
        return s
    out = re.sub(r"<think>.*?</think>", "", s, flags=re.S)
    out = re.sub(r"^\s*<think>.*$", "", out, flags=re.S)
    out = out.strip()
    return out if len(out) > 40 else (s or "").strip()

def http_post(url, headers, body, timeout=180):
    merged = {**headers, "User-Agent": UA, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers=merged, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        try: return e.code, e.read().decode("utf-8")
        except Exception: return e.code, ""
    except Exception as e:
        return 0, str(e)

def mm_call(prompt, model, max_tokens=3000, temp=0.85):
    key = os.environ["MINIMAX_KEY"]
    body = {"model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temp}
    status, text = http_post(MM_BASE, {"Authorization": f"Bearer {key}"}, body)
    if status != 200:
        return None, None, f"http {status}: {text[:200]}"
    try:
        j = json.loads(text)
        ch = j["choices"][0]
        raw = ch["message"].get("content") or ""
        return strip_think(raw), ch.get("finish_reason"), None
    except Exception as e:
        return None, None, f"parse: {e}"

def run(name, model, p1):
    txt, fr, err = mm_call(p1, model)
    return name, txt, fr, err

def fnv1a_64(data: bytes) -> int:
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & ((1 << 64) - 1)
    return h

def text_to_dials(text: str):
    h0 = fnv1a_64(text.encode())
    h1 = fnv1a_64((text + "\x00").encode())
    h2 = fnv1a_64((text + "\x00\x00").encode())
    h3 = fnv1a_64((text + "\x00\x00\x00").encode())
    return list(struct.unpack("<16h", struct.pack("<QQQQ", h0, h1, h2, h3)))

def get_latest_ref():
    req = urllib.request.Request(f"{API_HOST}/api/cells?limit=1",
                                 headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            cells = json.loads(r.read().decode()).get("cells", [])
            return cells[0].get("id") if cells else None
    except Exception:
        return None

print(f"TOPIC: {TOPIC}")
print(f"TAG: {TAG}\n--- p1 ---")

p1 = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    futs = {ex.submit(run, n, m, P1_PROMPT.format(topic=TOPIC)): n for n, m in VOICES.items()}
    for f in concurrent.futures.as_completed(futs):
        n, txt, fr, err = f.result()
        p1[n] = txt
        print(f"  {n} ({VOICES[n]}): {'OK' if txt else 'FAIL'} "
              f"{len(txt.split()) if txt else 0}w finish={fr} {err or ''}")

# provenance check: are the three p1 distinct?
norm = [re.sub(r"\[taps-fallback\].*?\n", "", p1.get(n) or "") for n in VOICES]
distinct_p1 = len(set(norm))
print(f"  distinct p1: {distinct_p1}/3")

live = {n: p1[n] for n in p1 if p1[n]}
print(f"--- p2 ({len(live)} live) ---")

p2 = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    futs = {}
    for n in live:
        others = [live[o] for o in live if o != n]
        if len(others) < 2:
            p2[n] = ""
            continue
        futs[ex.submit(run, n, VOICES[n],
                        P2_PROMPT.format(topic=TOPIC, voice_a=others[0],
                                         voice_b=others[1], your_voice=live[n]))] = n
    for f in concurrent.futures.as_completed(futs):
        n, txt, fr, err = f.result()
        p2[n] = txt or ""
        print(f"  {n}: p2 {'OK' if txt else 'FAIL'} "
              f"{len(txt.split()) if txt else 0}w finish={fr} {err or ''}")

# ---- chain ref ----
prev_ref = get_latest_ref()
print(f"  chain ref: {prev_ref or 'NONE (no-chain-ref case)'}")

# ---- entry ----
blend = "\n\n".join(f"[{n}]\n{live[n]}\n\n[{n} -> others]\n{p2.get(n,'')}" for n in live)
dials = text_to_dials(blend)

entry = {
    "tag": TAG,
    "topic": TOPIC,
    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "voices": {n: {"model": VOICES[n], "p1": live[n], "p2": p2.get(n, "")} for n in live},
    "refs": [TAG] + ([prev_ref] if prev_ref else []),
    "dials": dials,
    "provenance": {
        "script": "taps_live_round.py",
        "script_md5": hashlib.md5(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "live_voices": list(live),
        "providers_dark": ["zai", "qwen", "kimi"],
        "note": "zai/qwen/kimi keys absent; reconciled via 3 distinct MiniMax models",
        "distinct_p1": f"{distinct_p1}/3",
    },
}

out = f"sessions/{TAG}.json"
os.makedirs("sessions", exist_ok=True)
json.dump(entry, open(out, "w"), indent=2)
print(f"STAGED: {out}")

# ---- submit: full ladder, 404 + 000 + 503 all retryable ----
body = {"tag": TAG, "topic": TOPIC, "content": blend, "dials": dials,
        "refs": entry["refs"]}
last = None
for attempt in range(5):
    status, text = http_post(f"{API_HOST}/api/cell",
                             {"Authorization": "Bearer " + os.environ.get("TYPESAFE_AI_TOKEN", "")},
                             body, timeout=60)
    last = (status, text[:120])
    print(f"  submit try {attempt+1}: HTTP {status} {text[:80]}")
    if status == 200:
        break
    time.sleep(4)

print(f"\nSUBMIT: {last[0]} {last[1]}")
print(f"LIVE: {list(live)}  distinct_p1={distinct_p1}/3")
print("\n===== CONTENT =====")
for n in live:
    print(f"\n--- {n} ({VOICES[n]}) p1 ---\n{live[n]}")
    print(f"\n--- {n} p2 ---\n{p2.get(n,'')}")