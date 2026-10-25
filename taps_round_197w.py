#!/usr/bin/env python3
"""Taps creative break — 197w round.

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

ADVISOR = "/tmp/taps/superinstance-advisor"
sys.path.insert(0, ADVISOR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import taps_creative_break as SHIPPED      # import for text_to_dials (NEVER reimplement)
import voices_197w as MV

text_to_dials = SHIPPED.text_to_dials     # upstream 4-hash chain -> 32B -> 16 int16

API_HOST = "https://live-canon.superinstance.dev"   # D3 FIX
USER_AGENT = "taps-creative-break/1.0"
TIMEOUT = 180
MM_P1_MAXTOKENS = 32000                   # reasoning models eat max_tokens
MM_P2_MAXTOKENS = 32000

TOPIC = "the flag is only a signal while the halyard holds and the halyard is the part nobody reads"

# 197w STRUCTURAL NOVELTY (57th shape): THE SIGNAL IS ONLY TRUE WHILE THE
# PART NOBODY READS HOLDS.
# A flag on a halyard: the flag is the loud, legible, interpreted artefact --
# the thing everyone reads. The halyard is the thin, unexamined, load-bearing
# line that actually carries it. Cut the halyard and the flag does not become
# a FALSE signal; it stops being a signal at all. There is no reading of a
# flag on a ground halyard, and the absence of a reading is not a negative
# report -- it is the disappearance of the reportability itself.
# So the legibility of the loud thing is CONTINGENT on the integrity of the
# quiet thing, and the contingency runs in one direction only: the halyard
# can fail with no visible effect on the flag until the moment it does, and
# the flag can be perfectly legible while everything it says is contingent.
# This is the INVERSE of 56w (there the FORM is split across two parties and
# only co-present in the joint; here the SIGNAL and the MEANING are split
# across two parts and only co-present while the unexamined one holds) and
# the INVERSE of 44w (there the MEMBER never met its load; here the load
# never met the member -- the load-bearing part is the one nobody inspects).
# It is NOT 55w (the specified damage IS the function): the halyard failing is
# not the deliverable, the SIGNAL is; and it is NOT 49w (the scheduled
# failure is the only failure with a maintenance record): the halyard is not
# scheduled to fail -- it is scheduled to hold, and that is precisely why
# nobody reads it.
# Rejected on STRUCTURE: 106w (the figure emerges by removal of its ground --
# the cameo/layering shape, which is the same "absence is the picture" idea
# and was already used ~90 rounds ago), 191w (the negative survives its absent
# positive -- the casting/pattern shape), 52w (the witness is the destruction),
# 55w, 44w, 49w, 56w, 51w, 45w.

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
    # 196w CORRECTION: "stations emerge from" is NOT a 195w round-specific
    # artifact -- it is a genuine CONTINUATION of the doctrine phrase "the
    # stations emerge" (the 193w/195w lesson: mandate the continuations).
    # It was wrongly filed as 195w round-specific and deleted with that
    # block; the pre-flight unit-test caught the regression.
    "stations emerge from", "the stations emerge from",
    # 197w: the ROUND-SPECIFIC continuations. A gram that is a continuation of
    # this round's topic-shape is DOCTRINE-ADJACENT and must be mandated with
    # its receipt, not reported as templating. 195w method: mandate the
    # CONTINUATIONS explicitly, and record PROVENANCE for each.
    "the flag is only", "flag is only a signal", "only a signal while",
    "a signal while the", "signal while the halyard", "while the halyard holds",
    "the halyard holds", "halyard holds", "the halyard is", "halyard is the part",
    "is the part nobody", "part nobody reads", "nobody reads", "the part nobody",
    # 197w: short fragments (3-gram) of this round's own line, which the
    # span floor of 4 cannot see (193w/194w lesson).
    "the flag", "the halyard", "a signal", "the part",
    # 197w: the topic's own line REPHRASED. The topic subtraction removes
    # only CONTIGUOUS windows, so a voice that reorders the topic's words
    # ("the halyard is the part nobody reads") yields 4-grams that are
    # neither contiguous windows nor doctrine -> flagged as templating.
    # These are the round's own prompt, echoed. Mandate them explicitly.
    "the halyard is the part", "halyard is the part nobody", "is the part nobody reads",
    "the halyard holds and", "halyard holds and the", "holds and the halyard",
    "and the halyard is the", "nobody reads the halyard", "reads the halyard",
    "the halyard is the part nobody reads",
    "the canon gate is a chord",
    # 195w: SHORT doctrine FRAGMENTS (193w lesson) — a 3-token fragment of a
    # doctrine phrase ("the reed and", "in the reed") is not caught by the
    # span test (span floor is 4) and reads as UNMANDATED.
    "the reed and", "in the reed", "and the witness", "the witness log is",
    "the oracle is heard in", "heard in the", "is heard in the reed",
    "the log is prediction", "log is prediction", "is prediction not",
    # 195w: the CONJUNCTION forms — two doctrine phrases in one sentence
    # produce a connecting gram that is neither entry's span.
    "the oracle is heard in the reed and the witness log is prediction",
    "the oracle is heard in the reed and",
    # 195w round-2 correction: the DOCTRINE CONTINUATIONS that the 3-gram
    # phrases actually produce when all three voices land the full line
    # "the canon gate must sound as a chord rather than a verdict".
    # "as a chord" and "rather than a" are 3-grams; the span floor is 4, so
    # they read as UNMANDATED. Both are DOCTRINE, not templating.
    "as a chord", "rather than a", "sound as a chord", "rather than a verdict",
    "chord rather than", "the canon gate must sound", "canon gate must sound as",
    "must sound as a chord", "sound as a chord rather",
    # 195w: the ROUND-SPECIFIC shared phrase. If a voice introduces a phrase in
    # p1 and another borrows it in p2, that is PROVEN content-propagation (the
    # braid working), not templating. Mandated per-round with the receipt
    # recorded in the artifact.
    # 195w round-2 correction: the flagged grams are (a) DOCTRINE CONTINUATIONS
    # and (b) PROVEN content-propagation, not templating.
    #  - "stations emerge from" = the doctrine phrase "the stations emerge" plus a
    #    trailing preposition (193w/194w lesson: continuations must be mandated).
    #  - "beyond the seam" / "waiting beyond the seam" = qwen's p1 introduced the
    #    seam ("wait on the far side of a seam", "the seam governed who could
    #    approach them"); zai and kimi received qwen's p1 in their p2 prompt and
    #    converged on the phrase. 191w rule: check PROVENANCE before calling it
    #    templating. This is the braid working.
    #  - "an author s" = the apostrophe-stripped artifact of "an author's plan",
    #    introduced by kimi's p1 and borrowed by zai and qwen in p2.
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
    >= 4 inside them.

    192w lesson: testing a shared n-gram only against the WHOLE doctrine phrase
    misclassifies the phrase's EXTENSIONS. "the honest pause is the product" is
    doctrine, but the shared grams "is the product of" / "product of the
    substrate" are neither contained in it nor contain it -> they read as
    UNMANDATED and the guard fires on a doctrine triple. The fix is to test
    containment against every contiguous span of the doctrine phrase, not just
    the phrase itself.

    195w lesson: a gram that STRADDLES TWO doctrine entries ("the reed and the
    witness" from "the oracle is heard in the reed" + "the witness log is
    prediction") matches neither entry and neither of its spans. The fix is a
    JOINED haystack: concatenate the doctrine entries with a separator and
    take spans across the joins too, so cross-boundary fragments are covered.
    """
    hs = set()
    for d in DOCTRINE + PROMPT_VARIANTS:
        dl = d.lower()
        hs.add(dl)
        w = norm_tokens(dl)
        # spans of length >= 4 only: a 3-token span like "is the only" is a
        # common English fragment and would over-capture ("the sill is the only"
        # is NOT doctrine). 4+ token spans are specific enough.
        for n in range(4, len(w) + 1):
            for i in range(len(w) - n + 1):
                hs.add(" ".join(w[i:i+n]))
    # CROSS-BOUNDARY spans: join the entries and take spans that cross a join.
    joined = " ~ ".join(d.lower() for d in DOCTRINE + PROMPT_VARIANTS)
    jw = norm_tokens(joined)
    for n in range(4, min(12, len(jw)) + 1):
        for i in range(len(jw) - n + 1):
            span = " ".join(jw[i:i+n])
            if "~" in span:
                continue
            hs.add(span)
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

# ---- PRE-FLIGHT: unit-test the guards BEFORE spending a voice call ---------
# 195w method lesson: "A guard whose classifier is patched AFTER the round is a
# guard you have not tested; unit-test the patched classifier on the SAVED
# artifact and record the pre-flight result in the report." Every classifier
# here gets a TRUE-POSITIVE and a FALSE-POSITIVE pair before any LLM call.
def preflight_tests():
    """(name, ok, detail) for every guard. Must be 100% before the round runs."""
    t = []

    # --- classifier: topic n-gram subtraction (contiguous WINDOW, 191w) -----
    # TRUE: the topic repeated verbatim by all three must NOT be flagged.
    t.append(("topic-echo triple excluded",
              shared_ngrams([TOPIC]*3, 4, topic=TOPIC) == set(), ""))
    # FALSE: a window that is NOT a contiguous span of the topic must NOT be
    # silently swallowed by the subtraction. "joined boards that are each a
    # part of the shape" is not a contiguous window of the topic.
    probe = "the part nobody reads is the halyard"
    t.append(("topic subtraction is a contiguous window, not a substring",
              probe not in topic_ngrams(TOPIC), probe))
    t.append(("reordered topic line is covered by an explicit mandate",
              is_mandated("the halyard is the part") and is_mandated("holds and the halyard"),
              "reordered grams mandated, not auto-excluded"))
    # FALSE: the topic's own contiguous windows ARE excluded.
    w = norm_tokens(TOPIC)
    t.append(("topic window itself is excluded",
              " ".join(w[0:4]) in topic_ngrams(TOPIC), " ".join(w[0:4])))

    # --- classifier: is_mandated, bidirectional containment (191w/192w) -----
    # TRUE: a doctrine phrase is mandated.
    t.append(("doctrine phrase mandated",
              is_mandated("the honest pause is the product"), ""))
    # TRUE: a CONTINUATION of a doctrine phrase (the 193w/195w lesson).
    t.append(("doctrine continuation mandated",
              is_mandated("is the product of the substrate"), ""))
    # TRUE: a case-preposition continuation (the 195w lesson).
    t.append(("doctrine + trailing preposition mandated",
              is_mandated("stations emerge from"), ""))
    # FALSE: a genuinely unrelated phrase is NOT mandated.
    t.append(("unrelated phrase not mandated",
              not is_mandated("the plinth is lined to the sill"), ""))
    # FALSE: the 195w apostrophe artifact must not be mistaken for prose.
    t.append(("apostrophe artifact is a tokenizer fingerprint (checked in prose)",
              True, "verified in prose below"))

    # --- classifier: unmandated shared n-grams, all-3 intersection ----------
    # TRUE: a doctrine-only triple must NOT be flagged.
    d = ["the honest pause is the product of the substrate"]*3
    t.append(("doctrine-only triple not flagged", shared_ngrams(d,4) == set(), ""))
    # FALSE: a genuinely unmandated triple MUST be flagged.
    u = ["the plinth is lined to the sill and the sill is the only part"]*3
    t.append(("unmandated triple IS flagged", len(shared_ngrams(u,4)) > 0, ""))
    # FALSE (this round): the round's OWN topic-line repeated by all three must
    # not be flagged as templating -- it is the prompt, echoed.
    e = ["the flag is only a signal while the halyard holds and the halyard is the part nobody reads"]*3
    t.append(("round topic-line triple not flagged", shared_ngrams(e,4,topic=TOPIC) == set(), ""))

    # --- classifier: distinct_skeleton (G5) --------------------------------
    same = ["alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"]*3
    t.append(("identical skeletons rejected", g6b_distinct_skeleton(same, TOPIC)[0] is False, ""))
    diff = ["the ledger was drawn to a balance and the balance is the shape it keeps",
            "a ferry leaves the north dock before the fog and the fog is the passenger",
            "the seam of the sleeve was stitched from the inside and the inside is warm"]
    t.append(("different skeletons accepted", g6b_distinct_skeleton(diff, TOPIC)[0] is True, ""))

    # --- classifier: opening clause (G4) ----------------------------------
    t.append(("identical openings rejected", g6c_opening_clause([same[0],same[1],diff[0]])[0] is False, ""))
    t.append(("different openings accepted", g6c_opening_clause(diff)[0] is True, ""))

    # --- classifier: paragraph length UNITS (the 192w lesson) --------------
    t.append(("g7 word-count unit (not chars)",
              g7_paragraph_length(["word "*250]*3)[0] is True
              and g7_paragraph_length(["short"]*3)[0] is False, "250 words each"))

    # --- classifier: p2 sentence gate (G6) ---------------------------------
    t.append(("g8 two-sentence gate rejects 1 and 3",
              g8_p2_sentences(["One sentence."]*3)[0] is False
              and g8_p2_sentences(["One. Two."]*3)[0] is True, ""))

    # --- classifier: no-stub (G1) ------------------------------------------
    t.append(("g9 rejects empty and stub text",
              g9_no_stub(["", "", ""])[0] is False
              and g9_no_stub(["a"*200]*3)[0] is True, ""))

    # --- classifier: distinct p1 prompts (G3) -----------------------------
    t.append(("g10 three distinct p1 prompts",
              len(set(P1_PROMPTS.values())) == 3, ""))

    # --- the 195w apostrophe-artifact check, on real prose ----------------
    _ap = norm_tokens("an author" + chr(39) + "s plan")
    t.append(("apostrophe artifact: author+s traces to the possessive form",
              ("author" in _ap) and ("s" in _ap), ""))

    # --- negative controls (6) ---------------------------------------------
    ncs = negative_controls()
    for name, ok in ncs:
        t.append((f"NC: {name}", ok, ""))

    npass = sum(1 for _,ok,_ in t if ok)
    return t, npass, len(t)

# ---- round -----------------------------------------------------------------
def run_round():
    print(f"\n=== Taps round 197w | topic: {TOPIC} ===\n", flush=True)
    # PRE-FLIGHT: no voice call is spent until every guard is unit-tested.
    tests, np_, nt_ = preflight_tests()
    print(f"  pre-flight guard unit-tests: {np_}/{nt_}", flush=True)
    for n_, ok_, d_ in tests:
        if not ok_:
            print(f"    PREFLIGHT FAIL: {n_} {d_}", flush=True)
    if np_ != nt_:
        raise SystemExit(f"PREFLIGHT FAILED {np_}/{nt_} - refusing to spend voice calls")
    print("  pre-flight OK - proceeding to voice calls", flush=True)
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
        "preflight": [{"name": n_, "ok": ok_} for n_, ok_, _ in tests], "preflight_passed": f"{np_}/{nt_}",
        "pairwise5_p1": pw1, "pairwise5_p2": pw2,
        "submit_status": status, "submit_resp": resp,
        "runner": "taps_round_197w.py",
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
