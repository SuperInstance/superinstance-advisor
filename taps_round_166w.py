#!/usr/bin/env python3
"""Taps creative break - 166w repaired runner.

Repairs vs shipped taps_creative_break.py (md5 4e84d063..., unchanged 11 wipes):
  1. THREE DISTINCT MODELS (not one model x3 temperature aliases)
  2. THREE DISTINCT P1 PROMPTS (not the same prompt string three times)
  3. LIVE HOST live-canon.superinstance.dev (not api.superinstance.dev -> 404)
  4. refs from GET /api/canon papers[-1].number (not /api/cells -> 404)
  5. p2 max_tokens 32000 (900 starved M3 reasoning into truncation)
  6. artifact carries models + postures fields
"""
import os, sys, json, re, ssl, struct, time, hashlib
import urllib.request, urllib.error
import concurrent.futures as cf
from datetime import datetime, timezone

ADVISOR = "/tmp/advisor"
sys.path.insert(0, ADVISOR)
import minimax_voices as MV
import taps_creative_break as UP   # upstream: for text_to_dials + http helpers

HOST = "https://live-canon.superinstance.dev"
UA = "taps-creative-break/1.0"
CTX = ssl._create_unverified_context()

# ---- distinct models ----------------------------------------------------
VOICES = {
    "zai":  {"model": "MiniMax-M2.7-highspeed", "posture": "MECHANISM", "temp": 0.62, "mt": 32000},
    "qwen": {"model": "MiniMax-M3",           "posture": "DEFEND",    "temp": 0.85, "mt": 32000},
    "kimi": {"model": "MiniMax-M2.5",         "posture": "DEEPER",    "temp": 0.55, "mt": 32000},
}

# ---- three DISTINCT p1 prompts ------------------------------------------
P1 = {
"zai": """You are the MECHANISM voice in a three-voice round.

Topic: "{topic}"

Your job is MECHANISM ONLY: describe the physical, causal, material chain that would make this topic true. Ask what has to actually happen in the world for the claim to hold -- what moves, what wears, what is carried, what is consumed, what leaves a mark that cannot be sanded off. Be concrete about surfaces, loads, and residue. Do NOT abstract, do NOT moralize, do NOT summarize.

Write ONE paragraph of 200-450 words. No numbered lists. Do not address the other voices. Do not sign your work. Return only the paragraph.""",

"qwen": """You are the DEFEND voice in a three-voice round. You are a partisan and you are to be made to defend.

Topic: "{topic}"

Your job is to DEFEND the topic's framing against every obvious objection -- including objections you invent yourself. Find the strongest counter-argument to this topic, state it fairly, and then show why the framing still holds, or where it must be narrowed. Argue with yourself on the page. Do not merely agree; the value here is in what survives the attack.

Write ONE paragraph of 200-450 words. No numbered lists. Do not address the other voices. Do not sign your work. Return only the paragraph.""",

"kimi": """You are the DEEPER voice in a three-voice round.

Topic: "{topic}"

Your job is DEPTH: go one layer under what the topic presupposes. Identify the hidden assumption the topic smuggles in, and ask what the world looks like if that assumption is removed. Trace the consequences to the far end -- what it costs, what it forecloses, what later readers would have to unlearn. Be willing to complicate or even undercut the topic.

Write ONE paragraph of 200-450 words. No numbered lists. Do not address the other voices. Do not sign your work. Return only the paragraph.""",
}

P2 = """Two other voices have already written on the topic: "{topic}"

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

Write exactly TWO sentences (no more, no fewer) that braid all three voices together without naming any voice. Each sentence should land a doctrine: cells-are-scars, oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord, the-stations-emerge, the-boat-was-always-there, or honest-pause-is-product.

Return only the two sentences."""


def mm_call(model, prompt, max_tokens, temperature, sentences=None, retries=3):
    key = os.environ.get("MINIMAX_KEY")
    if not key:
        return None, "MINIMAX_KEY unset"
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temperature}
    data = json.dumps(body).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                "https://api.minimax.io/v1/chat/completions", data=data,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                         "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
                j = json.load(r)
            ch = (j.get("choices") or [None])[0]
            if ch is None:
                last = f"choices null base_resp={j.get('base_resp')}"; time.sleep(8+6*attempt); continue
            msg = ch.get("message") or {}
            raw = msg.get("content") or ""
            if not raw.strip():
                last = f"empty content (reasoning_tokens may have eaten budget) finish={ch.get('finish_reason')}"
                time.sleep(8+6*attempt); continue
            clean = MV.strip_think(raw)
            if not clean:
                last = "think-strip produced empty"; time.sleep(8+6*attempt); continue
            if sentences is not None:
                clean = MV.first_sentences(clean, sentences)
                if not clean:
                    last = "sentence gate produced empty"; time.sleep(8+6*attempt); continue
            return clean, None
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(8+6*attempt)
    return None, last or "exhausted"


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)


def http_post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
        headers={"User-Agent": UA, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)


def get_latest_ref():
    st, tx = http_get(f"{HOST}/api/canon")
    if st != 200:
        print(f"  [refs] GET /api/canon -> HTTP {st}", flush=True); return None
    try:
        ps = json.loads(tx)["papers"]
        return ps[-1]["number"]
    except Exception as e:
        print(f"  [refs] parse fail {e}", flush=True); return None


def submit(title, dials, refs, tag, topic, text):
    body = {"title": title, "dials": dials, "refs": refs, "tag": tag,
            "topic": topic, "text": text, "source": "taps-creative-break"}
    st, tx = http_post(f"{HOST}/api/cell", body)
    if st == 503 and "DNS" in (tx or ""):
        time.sleep(8); st, tx = http_post(f"{HOST}/api/cell", body)
    return st, tx


def run_round(topic):
    print(f"\n=== Taps 166w | topic: {topic} ===", flush=True)
    p1 = {}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {v: ex.submit(mm_call, VOICES[v]["model"], P1[v].format(topic=topic),
                             VOICES[v]["mt"], VOICES[v]["temp"]) for v in VOICES}
        for v, f in futs.items():
            try: p1[v] = f.result(timeout=240)
            except Exception as e: p1[v] = (None, f"timeout: {e}")
    for v in VOICES:
        if p1[v][0] is None:
            print(f"  [{v}] p1 failed ({p1[v][1]}), retrying fresh...", flush=True)
            time.sleep(3)
            p1[v] = mm_call(VOICES[v]["model"], P1[v].format(topic=topic), VOICES[v]["mt"], VOICES[v]["temp"])
        print(f"  [{v}] p1 {'OK' if p1[v][0] else 'FAIL'} ({len(p1[v][0]) if p1[v][0] else 0} chars)", flush=True)

    p2 = {}
    vk = ("zai","qwen","kimi")
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {}
        for v in vk:
            others = [p1[o][0] for o in vk if o != v]
            if not (others[0] and others[1] and p1[v][0]):
                p2[v] = (None, "missing voice input"); continue
            futs[v] = ex.submit(mm_call, VOICES[v]["model"],
                P2.format(topic=topic, voice_a=others[0], voice_b=others[1], your_voice=p1[v][0]),
                VOICES[v]["mt"], VOICES[v]["temp"], sentences=2)
        for v, f in futs.items():
            try: p2[v] = f.result(timeout=240)
            except Exception as e: p2[v] = (None, f"timeout: {e}")
    for v in vk:
        if p2[v][0] is None and "missing voice input" not in (p2[v][1] or ""):
            print(f"  [{v}] p2 failed ({p2[v][1]}), retrying fresh...", flush=True)
            time.sleep(3)
            others = [p1[o][0] for o in vk if o != v]
            if others[0] and others[1] and p1[v][0]:
                p2[v] = mm_call(VOICES[v]["model"],
                    P2.format(topic=topic, voice_a=others[0], voice_b=others[1], your_voice=p1[v][0]),
                    VOICES[v]["mt"], VOICES[v]["temp"], sentences=2)
        print(f"  [{v}] p2 {'OK' if p2[v][0] else 'FAIL'} ({len(p2[v][0]) if p2[v][0] else 0} chars)", flush=True)

    parts = [f"# Taps creative break - {topic}\n"]
    for v in vk:
        parts.append(f"\n## {v} (p1)\n\n{p1[v][0] or ''}\n")
        if p2[v][0]: parts.append(f"\n## {v} (p2)\n\n{p2[v][0]}\n")
    combined = "".join(parts)

    ref = get_latest_ref()
    refs = [ref] if ref else []
    print(f"  chain ref: {refs}", flush=True)
    dials = UP.text_to_dials(combined)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"taps-{stamp}"
    print(f"  submitting as tag={tag}...", flush=True)
    st, tx = submit(f"Taps - {topic[:60]}", dials, refs, tag, topic, combined)
    print(f"  submit: HTTP {st}", flush=True)
    print(f"  resp: {tx[:400]}", flush=True)

    art = {"topic": topic, "tag": tag, "stamp": stamp,
           "models": {v: VOICES[v]["model"] for v in vk},
           "postures": {v: VOICES[v]["posture"] for v in vk},
           "voices": {v: {"p1": p1[v][0], "p1_err": p1[v][1], "p2": p2[v][0], "p2_err": p2[v][1]} for v in vk},
           "combined": combined, "dials": dials, "refs": refs,
           "submit_status": st, "submit_resp": tx}
    sd = os.path.join(ADVISOR, "sessions"); os.makedirs(sd, exist_ok=True)
    with open(os.path.join(sd, f"{tag}.json"), "w") as f: json.dump(art, f, indent=2)
    with open(os.path.join(sd, f"{tag}.md"), "w") as f:
        f.write(combined + f"\n\n---\n\ntag: `{tag}`\nsubmit: HTTP {st}\n")
    print(f"  saved: sessions/{tag}.{{json,md}}", flush=True)
    return art


if __name__ == "__main__":
    topic = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else None
    if topic is None:
        import random
        topic = random.choice(UP.TOPIC_BANK)
    a = run_round(topic)
    print("\n=== SUMMARY ===", flush=True)
    print(f"topic: {a['topic']}")
    for v in ("zai","qwen","kimi"):
        print(f"  {v} [{a['models'][v]}/{a['postures'][v]}]: p1={'OK' if a['voices'][v]['p1'] else 'FAIL'} p2={'OK' if a['voices'][v]['p2'] else 'FAIL'}")
    print(f"tag: {a['tag']}")
    print(f"submit: HTTP {a['submit_status']}")
