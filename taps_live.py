#!/usr/bin/env python3
"""Taps live reconcile: 3 real voices via MiniMax (zai=M2.5, qwen=M3, kimi=M3.1-Flash).

Reuses taps_creative_break's prompts, hashing, and submit path so the entry is
byte-compatible with what the stock script would have produced.
"""
import os, sys, json, time, hashlib, urllib.request
import concurrent.futures as cf
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taps_creative_break as T

API = "https://api.minimax.io/v1/text/chatcompletion_v2"
MM = {"zai": "MiniMax-M2.5", "qwen": "MiniMax-M3", "kimi": "MiniMax-M3.1-Flash"}

def strip_think(s):
    a, b = s.find("<think>"), s.find("</think>")
    if a != -1 and b != -1 and b > a:
        out = s[:a] + s[b + 8:]
        return out if len(out.strip()) >= 40 else s
    return s

def call(voice, prompt, max_tokens, temp=0.85, retries=2):
    key = os.environ["MINIMAX_KEY"]
    payload = {"model": MM[voice],
               "messages": [{"role": "user", "content": prompt}],
               "max_tokens": max_tokens, "temperature": temp, "stream": False}
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                API, data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json",
                         "User-Agent": "taps-live-reconcile/1.0"})
            with urllib.request.urlopen(req, timeout=180, context=T._SSL_CTX) as r:
                d = json.loads(r.read().decode())
            ch = (d.get("choices") or [{}])[0]
            raw = ch.get("message", {}).get("content") or ""
            fr = ch.get("finish_reason", "?")
            txt = strip_think(raw).strip()
            # unterminated <think> + length truncation: salvage the last "Sentence N:" draft
            if fr == "length" and "<think>" in raw and "</think>" not in raw:
                tail = raw.rsplit("Sentence", 1)
                if len(tail) == 2:
                    txt = ("Sentence" + tail[1]).strip()
            return txt, f"finish_reason:{fr}", fr
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(4 + 4 * attempt)
    return None, last, "error"

def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else __import__('random').choice(T.TOPIC_BANK)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"taps-{stamp}-live-reconciled"
    print(f"\n=== Taps live reconcile | topic: {topic} ===\n", flush=True)

    p1 = {}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {v: ex.submit(call, v, T.P1_PROMPT.format(topic=topic), 3000) for v in MM}
        for v, f in futs.items():
            txt, err, fr = f.result(); p1[v] = txt
            print(f"  [{v}] p1 {fr} {len(txt.split()) if txt else 0}w :: {err}", flush=True)

    good = [v for v in MM if p1.get(v)]
    if len(good) < 2:
        print(f"only {len(good)} voice(s) alive; aborting"); return 1

    p2 = {}
    p2futs = {}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        for v in good:
            others = [u for u in good if u != v] or [v]
            while len(others) < 2:
                others.append(others[0])
            p2p = T.P2_PROMPT.format(topic=topic, voice_a=p1[others[0]],
                                     voice_b=p1[others[1]], your_voice=p1[v])
            p2futs[v] = ex.submit(call, v, p2p, 3000)
        for v, f in p2futs.items():
            txt, err, fr = f.result(); p2[v] = txt
            print(f"  [{v}] p2 {fr} {len(txt.split()) if txt else 0}w :: {err}", flush=True)

    voices = {v: {"p1": p1[v], "p1_err": None, "p2": p2.get(v),
                  "p2_err": None if p2.get(v) else "empty"} for v in good if p1[v]}
    if not voices:
        print("no voice completed"); return 1

    parts = [f"# Taps creative break — {topic}\n"]
    for v in voices:
        parts.append(f"\n## {v} (p1)\n\n{voices[v]['p1']}\n")
        if voices[v]["p2"]:
            parts.append(f"\n## {v} (p2)\n\n{voices[v]['p2']}\n")
    combined = "".join(parts)

    latest_ref = T.get_latest_ref()
    refs = [latest_ref] if latest_ref else []
    print(f"  chain ref: {refs or '(none)'}", flush=True)

    dials = T.text_to_dials(combined)
    print(f"\n  submitting to /api/cell as tag={tag}...", flush=True)
    status, text_resp = T.submit_to_canon(
        title=f"Taps — {topic[:60]}", dials=dials, refs=refs,
        tag=tag, topic=topic, text=combined, source="taps-live-reconcile")
    print(f"  submit: HTTP {status}\n  resp: {str(text_resp)[:300]}\n", flush=True)

    sess = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
    os.makedirs(sess, exist_ok=True)
    art = {"topic": topic, "tag": tag, "stamp": stamp, "voices": voices,
           "combined": combined, "dials": dials, "refs": refs,
           "submit_status": status, "submit_resp": text_resp}
    with open(os.path.join(sess, f"{tag}.json"), "w") as f:
        json.dump(art, f, indent=2)
    with open(os.path.join(sess, f"{tag}.md"), "w") as f:
        f.write(combined + f"\n\n---\n\ntag: `{tag}`\nsubmit: HTTP {status}\n"
                f"resp: `{str(text_resp)[:300]}`\n")

    print(f"=== SUMMARY ===\ntopic: {topic}")
    for v in MM:
        if v in voices:
            print(f"  {v}: p1={len(p1[v].split())}w p2={len(p2[v].split()) if p2.get(v) else 0}w")
        else:
            print(f"  {v}: FAILED")
    print(f"tag: {tag}\nsubmit: HTTP {status}")
    return 0

if __name__ == "__main__":
    sys.exit(main())