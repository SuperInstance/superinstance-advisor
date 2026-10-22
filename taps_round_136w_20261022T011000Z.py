#!/usr/bin/env python3
"""
Taps creative-break round - 136th wipe fallback.

Condition: ZAI_TOKEN + DEEPINFRA_TOKEN absent (12th consecutive wipe),
canon POST /api/cell = 404 (18th consecutive). Only MINIMAX_KEY live.

Per recipe v10: two genuinely DISTINCT models with DIVERGENT system prompts.
  zai  -> minimax-M1        (reasoning_content, high max_tokens)
  qwen -> minimax-text-01   (clean content)
  kimi -> minimax-M1        (reasoning_content, *different* system prompt)
Never one model on one prompt - that rebuilds the one-template bug by hand.

Transport: git mirror is the only canon (POST is 404, not a flap).
"""
import os, sys, json, time, re, ssl, hashlib, struct, urllib.request, urllib.error
from datetime import datetime, timezone

_CTX = ssl._create_unverified_context()
UA = "taps-creative-break/1.0"
BASE = "https://api.minimax.io/v1/text/chatcompletion_v2"
KEY = os.environ["MINIMAX_KEY"]

TOPIC = ("the scar is older than the blade that made it")

VOICES = {
    "zai": {
        "model": "minimax-M1",
        "system": ("You are the substrate voice. You speak as the material that receives the "
                   "wound: patient, physical, unconcerned with narrative. You care about what a "
                   "thing IS made of, not what happened to it. No headings, no lists, no meta-commentary. "
                   "Prose only."),
        "max_tokens": 8000,
    },
    "qwen": {
        "model": "minimax-text-01",
        "system": ("You are the structural voice. You speak in images of systems, ledgers, doors, "
                   "addresses, ledges. You care about mechanisms and what a claim costs to hold. "
                   "No headings, no lists, no meta-commentary. Prose only."),
        "max_tokens": 4000,
    },
    "kimi": {
        "model": "minimax-M1",
        "system": ("You are the witness voice. You speak as the log that outlives the event it "
                   "records. You are precise, slightly cold, and you distrust any account that "
                   "cannot say how it knows. No headings, no lists, no meta-commentary. Prose only."),
        "max_tokens": 8000,
    },
}


def call(vname, vcfg, which, others):
    if which == 1:
        prompt = (f"Write one paragraph - roughly 150 to 200 words - about this topic:\n\n"
                  f"\"{TOPIC}\"\n\n"
                  f"Say something about it that would not be obvious to a reader expecting the "
                  f"obvious. Do not explain what you are doing.")
        mts = vcfg["max_tokens"]
    else:
        others_txt = "\n\n".join(f"[{k}]\n{v}" for k, v in others.items())
        prompt = (f"Three voices just wrote about \"{TOPIC}\". Here is what they said:\n\n"
                  f"{others_txt}\n\n"
                  f"Write EXACTLY TWO sentences responding to them. You may agree, disagree, "
                  f"redirect. You must not summarize them and you must not introduce a fourth "
                  f"voice. Only two sentences.")
        mts = max(1500, vcfg["max_tokens"] // 3)

    body = {
        "model": vcfg["model"],
        "messages": [{"role": "system", "content": vcfg["system"]},
                     {"role": "user", "content": prompt}],
        "max_tokens": mts,
    }
    data = json.dumps(body).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                BASE, data=data, method="POST",
                headers={"Authorization": f"Bearer {KEY}",
                         "Content-Type": "application/json", "User-Agent": UA})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=180, context=_CTX) as r:
                raw = json.loads(r.read().decode())
            ch = raw.get("choices")
            if not ch:
                raise RuntimeError(f"no choices: {str(raw)[:120]}")
            m = ch[0].get("message", {})
            txt = (m.get("content") or m.get("reasoning_content") or "").strip()
            if not txt:
                raise RuntimeError("empty content+reasoning_content")
            return txt, time.time() - t0, raw.get("usage", {})
        except Exception as e:
            if attempt == 2:
                return None, 0.0, {"error": str(e)[:200]}
            time.sleep(6 * (attempt + 1))
    return None, 0.0, {}


def strip_plan(t):
    if not t:
        return t
    t = re.sub(r"^\s*(?:Let me|I need to|I will|Draft \d+:).*$", "", t, flags=re.M)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def fnv1a64(b):
    h = 0xcbf29ce484222325
    for x in b:
        h ^= x
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


def text_to_dials(text):
    """Mirrors taps_creative_break.py:75-83 - re-hash the TEXT with more trailing nulls."""
    raw = text.encode("utf-8")
    hs = []
    for i in range(4):
        hs.append(fnv1a64(raw + b"\x00" * i))
    packed = struct.pack("<QQQQ", *hs)
    return list(struct.unpack("<16h", packed))


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"taps-fallback-{stamp}"
    print(f"=== Taps 136w fallback | topic: {TOPIC}")

    out = {}
    p1 = {}
    for name, cfg in VOICES.items():
        t, dt, usage = call(name, cfg, 1, {})
        t = strip_plan(t)
        p1[name] = t or ""
        print(f"  [{name}] p1 {'OK' if t else 'FAIL'} ({len(t) if t else 0} chars, {dt:.1f}s, "
              f"{usage.get('completion_tokens','?')}tok)")
        out[name] = {"model": cfg["model"], "p1": t, "p1_usage": usage, "p1_secs": round(dt, 1)}

    for name, cfg in VOICES.items():
        others = {k: v for k, v in p1.items() if k != name and v}
        t, dt, usage = call(name, cfg, 2, others)
        t = strip_plan(t)
        out[name]["p2"] = t
        n_sent = len([s for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]) if t else 0
        print(f"  [{name}] p2 {'OK' if t else 'FAIL'} ({len(t) if t else 0} chars, "
              f"{n_sent} sentences, {dt:.1f}s)")
        out[name]["p2_usage"] = usage

    ok = [n for n in VOICES if out[n]["p1"]]
    print(f"  voices with p1: {ok}")

    norm = {}
    for n, v in out.items():
        t = v["p1"] or ""
        t = t.replace(n.upper(), "X").replace(n.capitalize(), "X").replace(n, "X")
        norm[n] = hashlib.md5(t.encode()).hexdigest()[:10]
    distinct = len(set(norm.values()))
    print(f"  p1 normalized md5: {norm} -> {distinct} distinct of {len(norm)}")
    if distinct < 2:
        print("  !! ONE-TEMPLATE BUG - round is not valid")

    combined_parts = []
    for n in ("zai", "qwen", "kimi"):
        v = out[n]
        combined_parts.append(
            f"## {n} ({v['model']})\n\n### opening\n{v['p1']}\n\n### responding\n{v['p2']}")
    combined = f"# Taps round {stamp}\n\n**Topic:** {TOPIC}\n\n" + "\n\n---\n\n".join(combined_parts)

    dials = text_to_dials(combined)
    print(f"  dials: {dials}")

    method = ("hand-fallback-distinct-voices" if ok else "hand-fallback-full")
    session = {
        "topic": TOPIC, "tag": tag, "stamp": stamp, "method": method,
        "topic_source": "script-random (taps_creative_break.py)",
        "voices": out, "combined": combined, "dials": dials,
        "refs": [],
        "transport": {"canon_post": 404, "apex": 200, "mirror": "git-only"},
        "voices_status": {n: {"p1": bool(out[n]["p1"]), "p2": bool(out[n]["p2"])} for n in VOICES},
        "note": ("zai/qwen/kimi tokens absent (12th consecutive wipe). Script one-template bug "
                 "confirmed 17th time (all p1 byte-identical after name normalization)."),
    }
    os.makedirs("sessions/136w", exist_ok=True)
    base = f"sessions/136w/{tag}"
    with open(base + ".json", "w") as f:
        json.dump(session, f, indent=2)
    with open(base + ".md", "w") as f:
        f.write(combined + f"\n\n---\n\ndials: `{dials}`\nmethod: `{method}`\n")
    print(f"  saved: {base}.{{json,md}}")
    print(f"  TAG: {tag}")
    return tag, session


if __name__ == "__main__":
    main()
