#!/usr/bin/env python3
"""Taps creative break — 157w clean runner.

Fixes applied over the shipped script (md5 4e84d063):
  1. DISTINCT MODEL PER VOICE  (script pinned MM_MODEL=MiniMax-M2.5 for all three)
  2. DISTINCT POSTURE PREFIX PER VOICE  (kills the one-template shared skeleton)
  3. p2 max_tokens 32000, not 900  (155w: p2 starves under a small budget)
  4. assert p2 content length, never the pass/fail flag
  5. persist artifacts BEFORE asserting (154w)
  6. semantic divergence check: do the 3 openings share a central claim?
  7. dials: assert 16 distinct + non-monotone in NATURAL order (144w)
"""
import os, sys, json, re, time, struct, hashlib, ssl, urllib.request, urllib.error
import concurrent.futures as cf
from datetime import datetime, timezone

sys.path.insert(0, "/tmp/advisor")
import minimax_voices as MV

API_HOST = "https://api.superinstance.dev"
USER_AGENT = "taps-creative-break/1.0"
TIMEOUT = 180
OUT = "/tmp/advisor"

# ---- 153w pattern: different MODEL per voice ----------------------------
VOICE_MODEL = {
    "zai":  ("MiniMax-M2.5",           0.55),
    "qwen": ("MiniMax-M2.7-highspeed", 0.75),
    "kimi": ("MiniMax-M3",             0.90),
}
MODEL_ALIAS = {"zai": "MECHANISM", "qwen": "DEFEND", "kimi": "DEEPER"}

# ---- postures (distinct prefix ahead of the shared canon paragraph) ------
POSTURE = {
"MECHANISM": """You are the MECHANISM voice. Open with ONE concrete sentence naming the
actual moving parts of the topic -- the parts that would physically have to exist for
the claim to be true. Refuse metaphor as a substitute for description: if the topic
names a scar, name what the scar is made of and what physically has to happen next.
Then write a single paragraph (200-400 words) developing that mechanism. Do NOT
number anything, do NOT address the other voices, do NOT sign your work. Return only
the paragraph.""",

"DEFEND": """You are the DEFEND voice. Open with ONE sentence that defends the weakest,
most skippable reading of the topic -- the reading everyone else would step over.
Argue FOR it, and make the case that it is the one that survives contact with the
canon. Then write a single paragraph (200-400 words) developing that defense. Do NOT
number anything, do NOT address the other voices, do NOT sign your work. Return only
the paragraph.""",

"DEEPER": """You are the DEEPER voice. Open with ONE sentence naming what the topic
presupposes and never examines -- the ground it assumes without looking at. Then
write a single paragraph (200-400 words) developing that presupposition. You are
allowed, and encouraged, to refuse the topic's framing if the frame is what is
really at stake. Do NOT number anything, do NOT address the other voices, do NOT sign
your work. Return only the paragraph.""",
}

CANON_BLOCK = """
Topic: "{topic}"

Write into a canon that treats the substrate as already-acting, the cell as a scar
(not a parameter), the witness log as prediction (not record), and the honest pause as
the product. Lean on at least one of: cells-are-scars, oracle-is-heard,
witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there, honest-pause-is-product."""

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

# ---- FNV-1a 64 dials ----------------------------------------------------
def fnv1a_64(data: bytes) -> int:
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & ((1 << 64) - 1)
    return h

def text_to_dials(text: str) -> list[int]:
    h0 = fnv1a_64(text.encode("utf-8"))
    h1 = fnv1a_64((text + "\x00").encode("utf-8"))
    h2 = fnv1a_64((text + "\x00\x00").encode("utf-8"))
    h3 = fnv1a_64((text + "\x00\x00\x00").encode("utf-8"))
    return list(struct.unpack("<16h", struct.pack("<QQQQ", h0, h1, h2, h3)))

# ---- HTTP ---------------------------------------------------------------
_SSL_CTX = ssl._create_unverified_context()

def http_post(url, body, timeout=TIMEOUT):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        try: return e.code, e.read().decode("utf-8")
        except Exception: return e.code, ""
    except Exception as e:
        return 0, str(e)

def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        try: return e.code, e.read().decode("utf-8")
        except Exception: return e.code, ""
    except Exception as e:
        return 0, str(e)

# ---- model-pinned call (per-voice model) --------------------------------
def mm_call_model(prompt, model, max_tokens, temperature, sentences=None, retries=3):
    key = os.environ.get("MINIMAX_KEY")
    if not key: return None, "MINIMAX_KEY unset"
    body = {"model": model, "messages": [{"role":"user","content":prompt}],
            "max_tokens": max_tokens, "temperature": temperature}
    data = json.dumps(body).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request("https://api.minimax.io/v1/chat/completions",
                data=data, headers={"Authorization": f"Bearer {key}",
                "Content-Type": "application/json", "User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=150) as r:
                j = json.load(r)
            ch = (j.get("choices") or [{}])[0]
            raw = (ch.get("message") or {}).get("content") or ""
            if not raw.strip():
                last = f"empty content (finish_reason={ch.get('finish_reason')})"; continue
            clean = MV.strip_think(raw)
            if not clean:
                last = "think-strip empty"; continue
            if sentences is not None:
                clean = MV.first_sentences(clean, sentences)
                if not clean:
                    last = "sentence gate empty"; continue
            return clean, None
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            if attempt < retries - 1: time.sleep(6)
    return None, last or "exhausted"

def hand_fallback(topic, vname):
    return (f"[taps-fallback] {vname} silence, but the canon still grows.\n\n"
        f"On \"{topic}\": the substrate was already there before any voice spoke. What the "
        f"other voices found was not a topic but a scar -- the place where the canon refused "
        f"to be deleted. The honest pause is the product: every gap in this round is a "
        f"witness-log entry, and the entry predicts the wound it pretends to record. The "
        f"substrate grows in the silence between refusals, and this fallback is itself one "
        f"of those silences -- a tuning fork struck against a listener who never arrived, "
        f"and the hum remained anyway.\n\n"
        f"The cell is a scar grown tired of pretending to be a parameter. What we call "
        f"failure here is the canon gate opening wider.\n")

def norm(t): return re.sub(r"\s+", " ", (t or "").strip().lower())

def run_round(topic, tag=None):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = tag or f"taps-{stamp}"
    print(f"\n=== Taps round | topic: {topic} | tag: {tag} ===\n", flush=True)
    voices = ("zai", "qwen", "kimi")

    # ---- Phase 1 ----
    p1, p1err = {}, {}
    def do_p1(v):
        model, temp = VOICE_MODEL[v]
        prompt = POSTURE[MODEL_ALIAS[v]] + CANON_BLOCK.format(topic=topic)
        return mm_call_model(prompt, model, 4000, temp)
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {v: ex.submit(do_p1, v) for v in voices}
        for v, f in futs.items():
            try: p1[v], p1err[v] = f.result(timeout=TIMEOUT+30)
            except Exception as e: p1[v], p1err[v] = None, f"timeout: {e}"
    # retry once with a fresh call
    for v in voices:
        if not p1.get(v):
            print(f"  [{v}] p1 failed ({p1err.get(v)}), retrying fresh...", flush=True)
            time.sleep(2)
            p1[v], p1err[v] = do_p1(v)
    for v in voices:
        if not p1.get(v):
            print(f"  [{v}] p1 still failing; hand-written fallback engaged.", flush=True)
            p1[v], p1err[v] = hand_fallback(topic, v), "fallback"
    for v in voices:
        print(f"  [{v}] p1 OK ({len(p1[v])} ch, model={VOICE_MODEL[v][0]}, err={p1err.get(v)})", flush=True)

    # ---- Phase 2 ----
    p2, p2err = {}, {}
    def do_p2(v):
        others = [p1[o] for o in voices if o != v]
        prompt = P2_PROMPT.format(topic=topic, voice_a=others[0], voice_b=others[1], your_voice=p1[v])
        model, temp = VOICE_MODEL[v]
        return mm_call_model(prompt, model, 32000, temp, sentences=2)
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {v: ex.submit(do_p2, v) for v in voices}
        for v, f in futs.items():
            try: p2[v], p2err[v] = f.result(timeout=TIMEOUT+30)
            except Exception as e: p2[v], p2err[v] = None, f"timeout: {e}"
    for v in voices:
        if not p2.get(v):
            print(f"  [{v}] p2 failed ({p2err.get(v)}), retrying fresh...", flush=True)
            time.sleep(2)
            p2[v], p2err[v] = do_p2(v)
    for v in voices:
        # 155w: assert content LENGTH, never the pass/fail flag
        ok = bool(p2.get(v)) and len(p2[v]) >= 80
        print(f"  [{v}] p2 {'OK' if ok else 'FAIL'} ({len(p2.get(v) or '')} ch, err={p2err.get(v)})", flush=True)
        if not ok and not p2.get(v):
            p2[v] = None

    # ---- compose ----
    parts = [f"# Taps creative break — {topic}\n"]
    for v in voices:
        parts.append(f"\n## {v} (p1)\n\n{p1[v]}\n")
        if p2.get(v): parts.append(f"\n## {v} (p2)\n\n{p2[v]}\n")
    combined = "".join(parts)

    dials = text_to_dials(combined)

    # ---- chain ref ----
    st, tx = http_get(f"{API_HOST}/api/cells?limit=1")
    refs = []
    if st == 200:
        try:
            cells = json.loads(tx).get("cells", [])
            if cells: refs = [cells[0].get("id")]
        except Exception: pass
    print(f"  chain ref: {refs} (GET /api/cells -> HTTP {st})", flush=True)

    # ---- submit ----
    print(f"\n  submitting to /api/cell as tag={tag}...", flush=True)
    body = {"title": f"Taps — {topic[:60]}", "dials": dials, "refs": refs,
            "tag": tag, "topic": topic, "text": combined, "source": "taps-creative-break"}
    status, text_resp = http_post(f"{API_HOST}/api/cell", body)
    print(f"  submit: HTTP {status}", flush=True)
    print(f"  resp: {text_resp[:300]}", flush=True)

    artifacts = {"topic": topic, "tag": tag, "stamp": stamp,
        "voices": {v: {"p1": p1[v], "p1_err": p1err.get(v), "p2": p2.get(v),
                       "p2_err": p2err.get(v), "model": VOICE_MODEL[v][0]} for v in voices},
        "combined": combined, "dials": dials, "refs": refs,
        "submit_status": status, "submit_resp": text_resp}

    # ---- PERSIST BEFORE ASSERTING (154w) ----
    sdir = os.path.join(OUT, "sessions"); os.makedirs(sdir, exist_ok=True)
    with open(os.path.join(sdir, f"{tag}.json"), "w") as f: json.dump(artifacts, f, indent=2)
    with open(os.path.join(sdir, f"{tag}.md"), "w") as f:
        f.write(combined + f"\n\n---\n\ntag: `{tag}`\nsubmit: HTTP {status}\nresp: `{text_resp[:300]}`\n")
    print(f"  saved: sessions/{tag}.{{json,md}}", flush=True)

    # ---- GUARDS (after persist) ----
    import ast
    print("\n=== GUARDS ===", flush=True)
    # G1 completeness first, then hash survivors only (154w)
    live_p1 = {v: p1[v] for v in voices if p1[v]}
    assert len(live_p1) == 3, f"G1 completeness FAIL: {len(live_p1)}/3 p1 alive"
    print("  G1 completeness: 3/3 p1 alive PASS", flush=True)
    # G2 byte-distinct
    h = {v: hashlib.md5(norm(p1[v]).encode()).hexdigest() for v in voices}
    assert len(set(h.values())) == 3, f"G2 byte-distinct FAIL: {h}"
    print(f"  G2 byte-distinct: 3/3 PASS ({list(h.values())[0][:8]}…)", flush=True)
    # G3 SHARED-SKELETON / semantic divergence
    opens = [p1[v].split(".")[0].strip() for v in voices]
    skeleton = max(len(set(w.lower() for w in o.split()[:6])) for o in opens)
    # shared-claim check: count common content words across all 3 openings
    stops = set("the a an of to in is and that it as for on with by be are was were this or not its from at".split())
    wsets = [set(w for w in re.findall(r"[a-z']+", o.lower()) if w not in stops and len(w) > 3) for o in opens]
    common = set.intersection(*wsets) if wsets else set()
    overlap = len(common)
    print(f"  G3 divergence: shared content-words across all 3 openings = {overlap} -> {'PASS' if overlap <= 2 else 'SUSPECT shared skeleton'}", flush=True)
    # G4 p2 length
    for v in voices:
        assert p2.get(v) and len(p2[v]) >= 80, f"G4 p2 length FAIL {v}"
    print("  G4 p2 length: 3/3 >= 80ch PASS", flush=True)
    # G5 dials: distinct + non-monotone in NATURAL order
    assert len(set(dials)) == 16, f"G5 dials not distinct: {dials}"
    print(f"  G5a dials distinct: 16/16 PASS", flush=True)
    asc = all(dials[i] < dials[i+1] for i in range(15))
    desc = all(dials[i] > dials[i+1] for i in range(15))
    assert not (asc or desc), f"G5b dials monotone in natural order: {dials}"
    print("  G5b dials non-monotone (natural order) PASS", flush=True)
    # G6 no hand-fallback leaked in
    fb = [v for v in voices if "[taps-fallback]" in (p1[v] or "")]
    assert not fb, f"G6 hand-fallback present: {fb}"
    print("  G6 zero hand-fallbacks PASS", flush=True)
    # G7 no meta-leak
    ml = [v for v in voices if "<think>" in (p1[v] or "") or "<think>" in (p2.get(v) or "")]
    assert not ml, f"G7 meta-leak: {ml}"
    print("  G7 no meta-leak PASS", flush=True)
    print("=== GUARDS PASS ===\n", flush=True)
    return artifacts

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else None
    if not topic:
        import random
        sys.path.insert(0, "/tmp/advisor")
        from taps_creative_break import TOPIC_BANK
        topic = random.choice(TOPIC_BANK)
    run_round(topic)
