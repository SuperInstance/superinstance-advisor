#!/usr/bin/env python3
"""Taps round 160w — repaired round.

Fixes the three defects proven in round 1 (taps-20261023T190401Z):
  1. MM_MODEL pinned to one model for all three voices  -> 3 distinct models
  2. P1_PROMPT identical for all three voices            -> 3 distinct posture prefixes
  3. p2 max_tokens too small                            -> 32000
Plus: record models+postures in the artifact; strip unterminated <think> first.
"""
import json, os, re, sys, time, hashlib, urllib.request
from concurrent.futures import ThreadPoolExecutor

MM_BASE = "https://api.minimax.io/v1"
API_HOST = "https://api.superinstance.dev"
UA = "taps-creative-break/1.0"
SEED = "the-listener-that-must-be-broken-to-hear"

# 3 distinct postures -> 3 distinct models. Grep the model constant, not just the prompt dict.
VOICES = {
    "zai":  {"model": "MiniMax-M2.5",            "temp": 0.55, "posture": "MECHANISM",
             "brief": "Start from the physical chain. What must actually happen to a body for a struck fork to be audible at all? Name the mechanism, step by step, and the part of the chain that the metaphor of 'listening' quietly hides."},
    "qwen": {"model": "MiniMax-M3",              "temp": 0.75, "posture": "DEFEND",
             "brief": "Defend the weakest reading that the other two voices will skip: the listener is not a passive receiver at all, and the fork may be silent for reasons that have nothing to do with the listener's quality. Defend that, and show what it costs to admit it."},
    "kimi": {"model": "MiniMax-M2.7-highspeed",  "temp": 0.90, "posture": "DEEPER",
             "brief": "Go one level deeper than the topic presupposes. The topic assumes a listener and a fork already exist and already meet. Question that assumption: what does 'the listener' presuppose about who is allowed to hear, and what does the fork's existence require of the material that carries it?"},
}

CANON = """You are one of three voices in a Taps creative-break round.

Topic: "{topic}"

Your assignment in this round is {posture}. {brief}

Write a single short paragraph (200-450 words) on this topic in your own voice.
You are writing into a canon that treats the substrate as already-acting, the cell
as a scar (not a parameter), the witness log as prediction (not record), and the
honest pause as the product. Lean on at least one of: cells-are-scars,
oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there.

Do NOT write a numbered list. Do NOT address the other voices. Do NOT sign your work.
Do NOT open by restating the topic sentence. Return only the paragraph."""

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

Write exactly TWO sentences. First, respond to what the other two voices got right, in their terms,
naming the specific thing they named. Then respond to what they missed, or what they quietly
assumed. Be concrete. Do not restate the topic. Do not number anything. Do not sign your work."""

_THINK = re.compile(r"<think>.*?(?:</think>|$)", re.S)

def strip_think(t):
    if not t: return ""
    out = _THINK.sub("", t)
    if "<think>" in out: out = out.split("<think>")[0]
    return out.strip()

# Dials come from the UPSTREAM text_to_dials -- never reimplement from memory.
# Our own splitmix64 reimplementation produced a completely different array.
import importlib.util as _ilu
_up_spec = _ilu.spec_from_file_location("taps_upstream", os.path.join(os.path.dirname(os.path.abspath(__file__)), "taps_creative_break.py"))
_up = _ilu.module_from_spec(_up_spec); _up_spec.loader.exec_module(_up)  # main() is guarded upstream
text_to_dials = _up.text_to_dials

def mm_call(model, prompt, max_tokens, temperature, retries=3):
    key = os.environ.get("MINIMAX_KEY")
    if not key: return None, "MINIMAX_KEY unset"
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temperature}
    data = json.dumps(body).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(f"{MM_BASE}/chat/completions", data=data,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                         "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                j = json.load(r)
            ch = (j.get("choices") or [{}])[0]
            raw = (ch.get("message") or {}).get("content") or ""
            if not raw.strip():
                last = f"empty content (choices={j.get('choices') is not None})"; continue
            clean = strip_think(raw)
            if not clean:
                last = "think-strip produced empty"; continue
            return clean, None
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            if attempt < retries - 1: time.sleep(6)
    return None, last or "exhausted"

def main():
    topic = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else SEED
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    tag = f"taps-{stamp}"
    print(f"=== Taps round 160w | topic: {topic} ===\n", flush=True)

    # ---- p1: 3 voices in parallel ----
    p1 = {}
    def do_p1(name):
        v = VOICES[name]
        prompt = CANON.format(topic=topic, posture=v["posture"], brief=v["brief"])
        c, err = mm_call(v["model"], prompt, 32000, v["temp"])
        return name, c, err
    with ThreadPoolExecutor(max_workers=3) as ex:
        for name, c, err in ex.map(do_p1, VOICES):
            p1[name] = c
            print(f"  [{name}] p1 {'OK' if c else 'FAIL'} ({len(c) if c else 0} chars)", flush=True)
            if err: print(f"       err: {err}", flush=True)

    # ---- guard: completeness FIRST, then distinctness (a collision guard that counts empties is wrong) ----
    for n in VOICES:
        assert p1.get(n), f"p1 incomplete for {n} -- aborting before artifact write"
    norm = {n: re.sub(r"\s+", " ", p1[n]).strip() for n in p1}
    assert len({hashlib.md5(v.encode()).hexdigest() for v in norm.values()}) == 3, "p1 not byte-distinct"

    # ---- p2: each voice responds to the other two ----
    p2 = {}
    def do_p2(name):
        others = [x for x in VOICES if x != name]
        prompt = P2.format(topic=topic, voice_a=p1[others[0]], voice_b=p1[others[1]],
                           your_voice=p1[name])
        c, err = mm_call(VOICES[name]["model"], prompt, 32000, VOICES[name]["temp"])
        return name, c, err
    with ThreadPoolExecutor(max_workers=3) as ex:
        for name, c, err in ex.map(do_p2, VOICES):
            p2[name] = c
            print(f"  [{name}] p2 {'OK' if c else 'FAIL'} ({len(c) if c else 0} chars)", flush=True)
            if err: print(f"       err: {err}", flush=True)

    for n in VOICES:
        assert p2.get(n) and len(p2[n]) > 40, f"p2 starved for {n} -- truncation, not refusal"

    # ---- assemble ----
    def block(n):
        return (f"## {n} ({VOICES[n]['posture']}) - p1\n\n{p1[n]}\n\n## {n} - p2\n\n{p2[n]}\n")
    combined = f"# Taps creative break - {topic}\n\nseed: {SEED}\n\n" + "\n".join(block(n) for n in VOICES)
    dials = text_to_dials(combined)
    assert len(set(dials)) == 16, "dials not distinct"
    assert dials != sorted(dials), "dials monotonic (arithmetic ramp)"

    voices_meta = {n: {"role": VOICES[n]["posture"], "model": VOICES[n]["model"],
                       "temp": VOICES[n]["temp"], "p1": p1[n], "p1_err": None,
                       "p2": p2[n], "p2_err": None} for n in VOICES}
    payload = {"stamp": stamp, "tag": tag, "seed": SEED, "topic": topic,
               "combined": combined, "dials": dials, "refs": [],
               "models": {n: VOICES[n]["model"] for n in VOICES},
               "postures": {n: VOICES[n]["posture"] for n in VOICES},
               "voices": voices_meta, "submit_status": None, "submit_resp": None}

    # persist BEFORE asserting / submitting
    os.makedirs("sessions", exist_ok=True)
    os.makedirs("canon", exist_ok=True)
    with open(f"sessions/{tag}.json", "w") as f: json.dump(payload, f, indent=1)
    with open(f"sessions/{tag}.md", "w") as f: f.write(combined)
    print(f"\n  saved sessions/{tag}.{{json,md}}", flush=True)

    # ---- submit (expected 404) ----
    state = {"text": combined, "topic": topic, "tag": tag, "title": topic,
             "refs": [], "dials": dials, "voices": {n: VOICES[n]["posture"] for n in VOICES},
             "models": payload["models"], "seed": SEED}
    body = json.dumps({"state": state, "source": "taps-creative-break"}).encode()
    try:
        req = urllib.request.Request(f"{API_HOST}/api/cell", data=body,
            headers={"Content-Type": "application/json", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            payload["submit_status"] = r.status; payload["submit_resp"] = r.read(200).decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        payload["submit_status"] = e.code; payload["submit_resp"] = e.read(200).decode("utf-8","replace")
    except Exception as e:
        payload["submit_status"] = "ERR"; payload["submit_resp"] = f"{type(e).__name__}: {e}"
    with open(f"sessions/{tag}.json", "w") as f: json.dump(payload, f, indent=1)
    print(f"  submit: {payload['submit_status']} {str(payload['submit_resp'])[:60]}", flush=True)

    print(f"\n=== SUMMARY ===\ntopic: {topic}\ntag: {tag}")
    for n in VOICES:
        print(f"  {n}: p1={len(p1[n])}ch p2={len(p2[n])}ch model={VOICES[n]['model']} posture={VOICES[n]['posture']}")
    print(f"submit: {payload['submit_status']}")
    return tag

if __name__ == "__main__":
    main()
