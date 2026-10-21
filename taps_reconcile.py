#!/usr/bin/env python3
"""Live-reconcile a Taps round when ZAI/DeepInfra are dark, via MiniMax.

Uses the EXACT P1_PROMPT / P2_PROMPT templates imported from taps_creative_break.py
so the reconciled content is the same shape the stock script would have produced.
"""
import json, os, ssl, sys, urllib.request, urllib.error, re, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/workspace")
import taps_creative_break as T

API = "https://api.minimax.io/v1"
KEY = os.environ["MINIMAX_KEY"]
# three distinct models = three distinct voices
VOICES = {"zai": "MiniMax-M2.5", "qwen": "MiniMax-M3", "kimi": "MiniMax-M3.1-Flash"}
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def call(model, prompt, max_tokens, temp):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temp}
    req = urllib.request.Request(
        f"{API}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180, context=_CTX) as r:
            j = json.loads(r.read().decode())
    except Exception as e:
        return None, f"http: {e}"
    ch = j["choices"][0]
    content = ch["message"].get("content") or ""
    return content.strip() or None, ch.get("finish_reason")


def strip_think(t):
    """Closed <think> blocks, then unterminated tail."""
    if not t:
        return t
    s = re.sub(r"<think>.*?</think>", "", t, flags=re.S)
    if "<think>" in s:  # unterminated -> cut at the tag
        s = s.split("<think>")[0]
    return s.strip()


def clean(t):
    s = strip_think(t)
    # drop preamble lines like "Here's a paragraph:" / markdown fences
    s = re.sub(r"^```[a-z]*\n|\n```$", "", s.strip())
    s = re.sub(r"^(Here'?s?|Sure[,!.]?|Certainly[,!.]?)\s*(is\s*)?(a\s*)?(the\s*)?"
               r"(paragraph|draft|reflection)?[^:\n]{0,40}:\s*", "", s, flags=re.I)
    return s.strip()


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "the substrate cannot recognize absence only pattern only return"
    tag = sys.argv[2] if len(sys.argv) > 2 else T.gen_tag() if hasattr(T, "gen_tag") else None

    # ---- p1: three voices in parallel
    def do_p1(v):
        m = VOICES[v]
        txt, fr = call(m, T.P1_PROMPT.format(topic=topic), 3000, 0.88)
        return v, clean(txt), fr
    with ThreadPoolExecutor(max_workers=3) as ex:
        p1 = {v: (txt, fr) for v, txt, fr in ex.map(do_p1, VOICES)}

    ok = {}
    for v, (txt, fr) in p1.items():
        w = len((txt or "").split())
        print(f"  [{v}] {VOICES[v]}  finish={fr}  {w}w", file=sys.stderr)
        if txt and w > 120 and fr in ("stop", "end_turn"):
            ok[v] = txt
        else:
            print(f"  [{v}] REJECT (short/stub or finish={fr})", file=sys.stderr)
    if len(ok) < 3:
        print(f"FATAL: only {len(ok)}/3 usable p1", file=sys.stderr)
        sys.exit(2)

    bodies = list(ok.values())
    print("  p1 distinct:", len(set(bodies)) == 3, file=sys.stderr)

    # ---- p2: each braids the other two
    def do_p2(v):
        m = VOICES[v]
        others = [bodies[i] for i in range(3) if i != list(ok).index(v)]
        pr = T.P2_PROMPT.format(topic=topic, voice_a=others[0], voice_b=others[1],
                                your_voice=ok[v])
        txt, fr = call(m, pr, 3000, 0.85)
        return v, clean(txt), fr
    with ThreadPoolExecutor(max_workers=3) as ex:
        p2 = {v: (txt, fr) for v, txt, fr in ex.map(do_p2, list(ok))}

    for v, (txt, fr) in p2.items():
        w = len((txt or "").split())
        print(f"  [{v}] p2 finish={fr} {w}w", file=sys.stderr)
        if fr in ("length",):
            # unterminated reasoning ate the budget -> take last draft from tail
            print(f"  [{v}] p2 TRUNCATED by finish=length", file=sys.stderr)

    out = {"topic": topic, "voices": {
        v: {"p1": ok[v], "p2": (p2[v][0] or "")} for v in ok}}
    dest = sys.argv[3] if len(sys.argv) > 3 else "/workspace/taps_reconciled.json"
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"topic": topic, "tag": tag,
                      "ok_voices": list(ok),
                      "p1_chars": {v: len(ok[v]) for v in ok},
                      "p2_words": {v: len((p2[v][0] or "").split()) for v in ok}}))


if __name__ == "__main__":
    main()