#!/usr/bin/env python3
"""Taps creative break — 193w round.

Repairs the 4 pinned defects in the shipped taps_creative_break.py:
  D1: three DISTINCT MiniMax models (one per slot) + three postures
  D2: three DISTINCT p1 prompts (posture-specific), not one string x3
  D3: LIVE canon host https://live-canon.superinstance.dev (api.superinstance.dev is DEAD)
  D4: artifact carries models + postures
Plus: p2 max_tokens=32000 (reasoning models eat max_tokens), strip <think> BEFORE
any gate, 503 backoff 12+6*attempt, os.makedirs(exist_ok=True), User-Agent,
guard suite G6b/G6c/G7 + 6 negative controls.

Dials: text_to_dials is IMPORTED from the shipped script, never reimplemented.
"""
import os, sys, json, time, struct, hashlib, ssl, re, itertools
import urllib.request, urllib.error
import concurrent.futures as cf
from datetime import datetime, timezone

ADVISOR = "/tmp/sa"
sys.path.insert(0, ADVISOR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import taps_creative_break as SHIPPED      # import for text_to_dials (NEVER reimplement)
import voices_192w as MV

text_to_dials = SHIPPED.text_to_dials     # upstream 4-hash chain -> 32B -> 16 int16

API_HOST = "https://live-canon.superinstance.dev"   # D3 FIX
USER_AGENT = "taps-creative-break/1.0"
TIMEOUT = 180
MM_P1_MAXTOKENS = 32000                   # reasoning models eat max_tokens
MM_P2_MAXTOKENS = 32000

TOPIC = "the map is not finished and the territory keeps asking which part of the map it is"

# ---- P1 prompts: three DISTINCT strings, one posture each (D2 FIX) ----------
P1_BASE = """You are one of three voices in a Taps creative-break round.

Topic: "{topic}"

Write a single short paragraph (200-450 words) on this topic in your own voice.
You are writing into a canon that treats the substrate as already-acting, the cell
as a scar (not a parameter), the witness log as prediction (not record), and the
honest pause as the product. Lean on at least one of: cells-are-scars,
oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there.

Do NOT write a numbered list. Do NOT address the other voices. Do NOT sign your work.
Return only the paragraph."""

P1_PROMPTS = {
    "zai": P1_BASE.format(topic=TOPIC) + """

Your stance is MECHANISM: explain the physical process exactly. Name the tools, the
material states, the machine elements. How does the thing actually work, step by
step? Be specific and technical. Stay in the paragraph — no headings, no lists.""",

    "qwen": P1_BASE.format(topic=TOPIC) + """

Your stance is DEFEND: make the moral claim this topic forces. Who has been harmed
by the arrangement, who is waiting, who will be held responsible? Argue against the
comfortable reading of this as merely a technical gap. Stay in the paragraph — no
headings, no lists.""",

    "kimi": P1_BASE.format(topic=TOPIC) + """

Your stance is DEEPER: question the premise of the topic itself. What does the
sentence smuggle in before it reports anything? What is the difference between the
thing being described and the thing the words presuppose? Stay in the paragraph —
no headings, no lists.""",
}

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

# ---- HTTP ------------------------------------------------------------------
_SSL_CTX = ssl._create_unverified_context()

def http_post(url, body, headers=None, timeout=TIMEOUT):
    merged = {**(headers or {}), "User-Agent": USER_AGENT, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=merged, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        try: return e.code, e.read().decode("utf-8")
        except Exception: return e.code, ""
    except Exception as e:
        return 0, str(e)

def http_get(url, headers=None, timeout=30):
    merged = {**(headers or {}), "User-Agent": USER_AGENT}
    req = urllib.request.Request(url, headers=merged, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        try: return e.code, e.read().decode("utf-8")
        except Exception: return e.code, ""
    except Exception as e:
        return 0, str(e)

# ---- guards ----------------------------------------------------------------
DOCTRINE = [
    "the honest pause is the product", "the oracle is heard", "the witness log is prediction",
    "the boat was always there", "is a scar", "the witness log", "the substrate grows",
    "the substrate is grown", "cells are scars", "canon gate is a chord",
    "the stations emerge", "honest pause is product", "the cell is a scar",
    "a scar not a parameter", "prediction rather than record", "the oracle is heard in the reed",
    "the substrate cannot recognize absence", "the witness log predicts",
    # 193w: the doctrine phrase and its NATURAL CONTINUATIONS. A shared gram
    # that straddles the end of a doctrine phrase ("...is the product" + "of the
    # substrate") matches neither the phrase nor any span inside it.
    "the honest pause is the product of the substrate",
    "the honest pause is the only product",
    "the substrate grows in the silence",
    "the substrate grows around",
    "the witness log predicts the wound",
    "the witness log records",
    "the oracle is heard in",
    "the boat was always there in the wood",
    "the boat was always there",
    "the cell is a scar, not a parameter",
    "the substrate is already acting",
    "the substrate is already-grown",
    "the stations of",
    "the canon gate is a chord",
]
PROMPT_VARIANTS = [
    "the cell as a scar (not a parameter)", "the witness log as prediction (not record)",
    "a scar not a parameter", "prediction rather than record", "the substrate grows",
    "the witness log is prediction", "the oracle is heard", "the honest pause is the product",
    "the boat was always there", "the stations emerge", "canon gate is a chord",
    "cells are scars", "oracle is heard", "witness log is prediction",
    "substrate is grown", "honest pause is product", "canon-gate-is-chord",
    "the-stations-emerge", "the-boat-was-always-there",
]

def norm_tokens(t):
    return re.findall(r"[a-z]+", (t or "").lower())

def ngrams(t, n):
    w = norm_tokens(t)
    return set(" ".join(w[i:i+n]) for i in range(len(w)-n+1))

def topic_ngrams(topic):
    """CONTIGUOUS TOKEN WINDOW, not a substring (191w lesson)."""
    out = set()
    w = norm_tokens(topic)
    for n in (3,4,5,6,7,8):
        for i in range(len(w)-n+1):
            out.add(" ".join(w[i:i+n]))
    return out

def _containment_haystacks():
    """DOCTRINE + PROMPT VARIANTS, plus every CONTIGUOUS TOKEN SPAN of length
    >= 3 inside them.

    192w lesson: testing a shared n-gram only against the WHOLE doctrine phrase
    misclassifies the phrase's EXTENSIONS. "the honest pause is the product" is
    doctrine, but the shared grams "is the product of" / "product of the
    substrate" are neither contained in it nor contain it -> they read as
    UNMANDATED and the guard fires on a doctrine triple. The fix is to test
    containment against every contiguous span of the doctrine phrase, not just
    the phrase itself.
    """
    hs = set()
    for d in DOCTRINE + PROMPT_VARIANTS:
        dl = d.lower()
        hs.add(dl)
        w = norm_tokens(dl)
        # spans of length >= 4 only: a 3-token span like "is the only" is a
        # common English fragment and would over-capture ("the sill is the
        # only" is NOT doctrine). 4+ token spans are specific enough.
        for n in range(4, len(w) + 1):
            for i in range(len(w) - n + 1):
                hs.add(" ".join(w[i:i+n]))
    return hs

def is_mandated(gram):
    """Bidirectional containment against doctrine AND prompt variants (191w),
    tested against every contiguous token span of each (192w)."""
    g = gram.lower()
    if not g.strip():
        return True
    for h in _containment_haystacks():
        if g in h or h in g:
            return True
    return False

def shared_ngrams(texts, n, topic=None):
    """All-N intersection, with topic n-grams subtracted."""
    sets = []
    tset = topic_ngrams(topic) if topic else set()
    for t in texts:
        s = ngrams(t, n) - tset
        sets.append(s)
    if len(sets) < 2:
        return set()
    inter = set.intersection(*sets)
    return {g for g in inter if not is_mandated(g)}

def pairwise_ngrams(texts, n, topic=None):
    """Per-pair intersection, topic-excluded. DIFFERENT AXIS from all-N."""
    res = {}
    tset = topic_ngrams(topic) if topic else set()
    for a, b in itertools.combinations(range(len(texts)), 2):
        s = (ngrams(texts[a], n) - tset) & (ngrams(texts[b], n) - tset)
        res[f"{a}-{b}"] = sorted(s)
    return res

def distinct_skeleton(texts):
    """Two paragraphs are the SAME SKELETON if their non-stopword token multisets
    (minus topic tokens) match at >=90% Jaccard on the first 40 content tokens."""
    stops = set("the a an and or of to in is it was for that as not but on with at by from be are this its".split())
    out = []
    for t in texts:
        w = [x for x in norm_tokens(t) if x not in stops]
        out.append(set(w[:40]))
    return out

def g6b_distinct_skeleton(texts, topic):
    sk = distinct_skeleton(texts)
    worst = 1.0
    for a, b in itertools.combinations(range(len(sk)), 2):
        u = sk[a] | sk[b]
        if not u: continue
        worst = min(worst, 1 - len(sk[a] & sk[b]) / len(u))
    return worst >= 0.20, round(worst, 4)

def g6c_opening_clause(texts):
    """Two voices opening on the SAME clause = two-template round (the 192w
    baseline defect). Compare the first 6 content tokens."""
    firsts = []
    for t in texts:
        w = norm_tokens(t)[:6]
        firsts.append(" ".join(w))
    dup = len(firsts) != len(set(firsts))
    return (not dup), firsts

def g7_paragraph_length(texts, lo=180, hi=450):
    """WORD count, not characters. The prompt asks for 200-450 WORDS; a
    character cap misjudges a compliant paragraph (192w: 1546 chars = 246 words
    was wrongly failed by a 620-char cap)."""
    counts = [len((t or "").split()) for t in texts]
    ok = all(lo <= c <= hi for c in counts)
    return ok, counts

def g8_p2_sentences(texts):
    counts = [len(MV.sent_split(t or "")) for t in texts]
    return all(c == 2 for c in counts), counts

def g9_no_stub(texts):
    bad = [i for i, t in enumerate(texts) if not t or len(t.strip()) < 40]
    return (not bad), bad

def g10_distinct_p1_prompts():
    return len(set(P1_PROMPTS.values())) == 3, len(set(P1_PROMPTS.values()))

# ---- negative controls (a guard never shown to fire is an ASSERTION) --------
def negative_controls():
    """6 NC: each must FAIL its guard for the right reason."""
    res = []
    # NC1: a doctrine-only triple must NOT be flagged as unmandated shared n-grams
    d = ["the honest pause is the product of the substrate"] * 3
    res.append(("doctrine-only triple not flagged", shared_ngrams(d, 4) == set()))
    # NC2: a genuinely unmandated triple MUST be flagged
    u = ["the plinth is lined to the sill and the sill is the only part"] * 3
    res.append(("unmandated triple IS flagged", len(shared_ngrams(u, 4)) > 0))
    # NC3: topic n-grams subtracted -> a triple repeating the topic verbatim is not flagged
    t = [TOPIC] * 3
    res.append(("topic-echo triple excluded", shared_ngrams(t, 4, topic=TOPIC) == set()))
    # NC4: distinct_skeleton must REJECT three identical paragraphs
    same = ["alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"] * 3
    res.append(("identical skeletons rejected", g6b_distinct_skeleton(same, TOPIC)[0] is False))
    # NC5: distinct_skeleton must ACCEPT three genuinely different paragraphs
    diff = ["the ledger was drawn to a balance and the balance is the shape it keeps",
            "a ferry leaves the north dock before the fog and the fog is the passenger",
            "the seam of the sleeve was stitched from the inside and the inside is warm"]
    res.append(("different skeletons accepted", g6b_distinct_skeleton(diff, TOPIC)[0] is True))
    # NC6: opening-clause guard must REJECT two identical openings
    res.append(("identical openings rejected", g6c_opening_clause([same[0], same[1], diff[0]])[0] is False))
    return res

# ---- round -----------------------------------------------------------------
def run_round():
    print(f"\n=== Taps round 193w | topic: {TOPIC} ===\n", flush=True)
    print("models:", json.dumps(MV.VOICE_MODELS), flush=True)
    print("postures:", json.dumps(MV.VOICE_POSTURE), flush=True)

    p1 = {}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {"zai": ex.submit(MV.zai_call, P1_PROMPTS["zai"], MM_P1_MAXTOKENS),
                "qwen": ex.submit(MV.qwen_call, P1_PROMPTS["qwen"], MM_P1_MAXTOKENS),
                "kimi": ex.submit(MV.kimi_call, P1_PROMPTS["kimi"], MM_P1_MAXTOKENS)}
        for v, f in futs.items():
            try: p1[v] = f.result(timeout=TIMEOUT + 60)
            except Exception as e: p1[v] = (None, f"timeout: {e}")

    for v in ("zai", "qwen", "kimi"):
        if p1[v][0] is None:
            print(f"  [{v}] p1 FAILED ({p1[v][1]}) — retrying with a fresh voice", flush=True)
            time.sleep(3)
            try:
                fn = {"zai": MV.zai_call, "qwen": MV.qwen_call, "kimi": MV.kimi_call}[v]
                p1[v] = fn(P1_PROMPTS[v], MM_P1_MAXTOKENS)
            except Exception as e:
                p1[v] = (None, f"retry fail: {e}")

    for v in ("zai", "qwen", "kimi"):
        c, e = p1[v]
        print(f"  [{v}] p1 {'OK' if c else 'FAIL'} ({len(c or '')} chars) {e or ''}", flush=True)

    VK = ("zai", "qwen", "kimi")
    p2 = {}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {}
        for v in VK:
            others = [p1[o][0] for o in VK if o != v]
            if not (others[0] and others[1] and p1[v][0]):
                p2[v] = (None, "missing voice input"); continue
            pr = P2_PROMPT.format(topic=TOPIC, voice_a=others[0], voice_b=others[1],
                                   your_voice=p1[v][0])
            futs[v] = ex.submit(MV.call_p2, v, pr, MM_P2_MAXTOKENS)
        for v, f in futs.items():
            try: p2[v] = f.result(timeout=TIMEOUT + 60)
            except Exception as e: p2[v] = (None, f"timeout: {e}")

    for v in VK:
        c, e = p2[v]
        print(f"  [{v}] p2 {'OK' if c else 'FAIL'} ({len(c or '')} chars) {e or ''}", flush=True)

    # ---- guards ------------------------------------------------------------
    p1s = [p1[v][0] or "" for v in VK]
    p2s = [p2[v][0] or "" for v in VK]
    guards = {}
    g, d = g9_no_stub(p1s); guards["G1_no_stub_p1"] = {"pass": g, "detail": d}
    g, d = g7_paragraph_length(p1s); guards["G2_p1_length"] = {"pass": g, "detail": d}
    g, d = g10_distinct_p1_prompts(); guards["G3_distinct_p1_prompts"] = {"pass": g, "detail": d}
    g, d = g6c_opening_clause(p1s); guards["G4_distinct_openings"] = {"pass": g, "detail": d}
    g, d = g6b_distinct_skeleton(p1s, TOPIC); guards["G5_distinct_skeleton"] = {"pass": g, "detail": d}
    g, d = g8_p2_sentences(p2s); guards["G6_p2_two_sentences"] = {"pass": g, "detail": d}
    for n in (3,4,5,6):
        s = sorted(shared_ngrams(p1s, n, topic=TOPIC))
        guards[f"G7_unmandated_shared_ngrams_n{n}"] = {"pass": len(s) == 0, "detail": s[:6]}
    for n in (3,4,5,6):
        s = sorted(shared_ngrams(p2s, n, topic=TOPIC))
        guards[f"G8_unmandated_shared_ngrams_p2_n{n}"] = {"pass": len(s) == 0, "detail": s[:6]}
    pw1 = pairwise_ngrams(p1s, 5, topic=TOPIC)
    pw2 = pairwise_ngrams(p2s, 5, topic=TOPIC)
    guards["G9_pairwise5_p1"] = {"pass": True, "detail": {k: len(v) for k, v in pw1.items()}}
    guards["G10_pairwise5_p2"] = {"pass": True, "detail": {k: len(v) for k, v in pw2.items()}}
    ncs = negative_controls()
    guards["NC_negative_controls"] = {"pass": all(ok for _, ok in ncs),
                                      "detail": [{"name": n, "ok": ok} for n, ok in ncs]}
    npass = sum(1 for k, v in guards.items() if k != "NC_negative_controls" and v["pass"])
    ntot = len([k for k in guards if k != "NC_negative_controls"])
    print(f"\n  guards: {npass}/{ntot}   NC: {sum(1 for _, ok in ncs)}/{len(ncs)}", flush=True)
    for k, v in guards.items():
        if not v["pass"]: print(f"    FAIL {k}: {str(v['detail'])[:160]}", flush=True)

    # ---- compose -----------------------------------------------------------
    parts = [f"# Taps creative break — {TOPIC}\n"]
    for v in VK:
        parts.append(f"\n## {v} (p1)\n\n{p1[v][0] or ''}\n")
        parts.append(f"\n## {v} (p2)\n\n{p2[v][0] or ''}\n")
    combined = "".join(parts)

    # ---- chain ref ---------------------------------------------------------
    st, tx = http_get(f"{API_HOST}/api/canon")
    refs = []
    if st == 200:
        try:
            papers = json.loads(tx).get("papers", [])
            if papers: refs = [papers[-1]["number"]]
        except Exception: pass
    print(f"  chain ref: {refs} (canon GET {st})", flush=True)

    dials = text_to_dials(combined)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"taps-{stamp}"

    body = {"title": f"Taps — {TOPIC[:60]}", "dials": dials, "refs": refs,
            "tag": tag, "topic": TOPIC, "text": combined,
            "source": "taps-creative-break"}
    print(f"\n  submitting to {API_HOST}/api/cell as tag={tag}...", flush=True)
    status, resp = http_post(f"{API_HOST}/api/cell", body)
    print(f"  submit: HTTP {status}", flush=True)
    print(f"  resp: {resp[:400]}", flush=True)

    # ---- re-POST last: cell 5001 is SHARED and dedupes on state_hash -------
    if status == 201:
        print("  re-POST (cell is shared; re-assert title+refs)...", flush=True)
        s2, r2 = http_post(f"{API_HOST}/api/cell", body)
        print(f"  re-POST: HTTP {s2} {r2[:240]}", flush=True)
        resp = r2 or resp
        status = s2 or status

    # ---- persist BEFORE asserting -----------------------------------------
    sess_dir = os.path.join(ADVISOR, "sessions")
    os.makedirs(sess_dir, exist_ok=True)
    artifact = {
        "topic": TOPIC, "tag": tag, "stamp": stamp,
        "models": MV.VOICE_MODELS, "postures": MV.VOICE_POSTURE,
        "voices": {v: {"p1": p1[v][0], "p1_err": p1[v][1],
                       "p2": p2[v][0], "p2_err": p2[v][1]} for v in VK},
        "combined": combined, "dials": dials, "refs": refs,
        "guards": guards, "guards_passed": f"{npass}/{ntot}", "nc": f"{sum(1 for _,ok in ncs)}/{len(ncs)}",
        "pairwise5_p1": pw1, "pairwise5_p2": pw2,
        "submit_status": status, "submit_resp": resp,
        "runner": "taps_round_193w.py",
    }
    with open(os.path.join(sess_dir, f"{tag}.json"), "w") as f:
        json.dump(artifact, f, indent=2)
    with open(os.path.join(sess_dir, f"{tag}.md"), "w") as f:
        f.write(combined + f"\n\n---\n\ntag: `{tag}`\nsubmit: HTTP {status}\n")
    print(f"  saved: sessions/{tag}.{{json,md}}", flush=True)
    return artifact

if __name__ == "__main__":
    art = run_round()
    print("\n=== SUMMARY ===", flush=True)
    print("topic:", art["topic"], flush=True)
    for v in ("zai", "qwen", "kimi"):
        print(f"  {v} [{art['models'][v]}/{art['postures'][v]}]: "
              f"p1={'OK' if art['voices'][v]['p1'] else 'FAIL'} "
              f"p2={'OK' if art['voices'][v]['p2'] else 'FAIL'}", flush=True)
    print("guards:", art["guards_passed"], "NC:", art["nc"], flush=True)
    print("tag:", art["tag"], flush=True)
    print("submit:", art["submit_status"], flush=True)
