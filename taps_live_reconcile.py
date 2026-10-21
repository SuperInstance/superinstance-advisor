#!/usr/bin/env python3
"""Drive live voices via MiniMax when ZAI/DeepInfra are dark (15th wipe).
Uses the EXACT P1/P2 prompts from taps_creative_break.py."""
import json, os, re, ssl, sys, urllib.request, urllib.error
import concurrent.futures as cf

TOPIC = "the substrate was always already growing"
UA = "taps-creative-break/1.0/1.1-live-reconcile"
CTX = ssl._create_unverified_context()

P1 = """You are one of three voices in a Taps creative-break round.

Topic: "{topic}"

Write a single short paragraph (200-450 words) on this topic in your own voice.
You are writing into a canon that treats the substrate as already-acting, the cell
as a scar (not a parameter), the witness log as prediction (not record), and the
honest pause as the product. Lean on at least one of: cells-are-scars,
oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there.

Do NOT write a numbered list. Do NOT address the other voices. Do NOT sign your work.
Return only the paragraph."""

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

Write exactly TWO sentences (no more, no fewer) that braid all three voices together
without naming any voice. Each sentence should land a doctrine: cells-are-scars,
oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there, or honest-pause-is-product.

Return only the two sentences."""

# voice -> (model, max_tokens, temperature)  [recipe v11: probe mt=3000 first]
VOICES = {
    "zai":  ("MiniMax-M2.5",       3000, 0.85),
    "qwen": ("MiniMax-M3",         3000, 0.90),
    "kimi": ("MiniMax-M3.1-Flash", 3000, 0.80),
}

def call(model, prompt, max_tokens, temperature):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        "https://api.minimax.io/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + os.environ["MINIMAX_KEY"],
                 "Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
            j = json.loads(r.read().decode())
            ch = j["choices"][0]["message"]
            c = ch.get("content") or ch.get("reasoning_content") or ""
            return c.strip(), j["choices"][0].get("finish_reason")
    except urllib.error.HTTPError as e:
        return None, "http %d: %s" % (e.code, e.read().decode()[:200])
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)

def p1_for(v):
    m, mt, tp = VOICES[v]
    return call(m, P1.format(topic=TOPIC), mt, tp)

def main():
    p1 = {}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {v: ex.submit(p1_for, v) for v in VOICES}
        for v, f in futs.items():
            p1[v] = f.result()
    for v in ("zai", "qwen", "kimi"):
        c, fr = p1[v]
        print("[%s] p1 %s len=%s finish=%s" % (v, "OK" if c else "FAIL",
              len(c) if c else 0, fr), file=sys.stderr)

    norm = {v: re.sub(r"[A-Za-z0-9]+", "X", p1[v][0] or "") for v in VOICES}
    print("DISTINCT p1 voices: %d/3" % len(set(norm.values())), file=sys.stderr)

    keys = ("zai", "qwen", "kimi")
    p2 = {}
    def do_p2(v):
        others = [p1[o][0] for o in keys if o != v]
        yours = p1[v][0]
        if not (others[0] and others[1] and yours):
            return (None, "missing voice input")
        m, mt, tp = VOICES[v]
        return call(m, P2.format(topic=TOPIC, voice_a=others[0],
                                 voice_b=others[1], your_voice=yours), mt, tp)
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {v: ex.submit(do_p2, v) for v in keys}
        for v, f in futs.items():
            p2[v] = f.result()
    for v in keys:
        c, fr = p2[v]
        print("[%s] p2 %s len=%s finish=%s" % (v, "OK" if c else "FAIL",
              len(c) if c else 0, fr), file=sys.stderr)

    out = {"topic": TOPIC,
           "voices": {v: {"p1": p1[v][0], "p1_note": str(p1[v][1]),
                         "p2": p2[v][0], "p2_note": str(p2[v][1])} for v in keys}}
    with open("taps_live_voices.json", "w") as f:
        json.dump(out, f, indent=2)
    print("WROTE taps_live_voices.json", file=sys.stderr)

if __name__ == "__main__":
    main()