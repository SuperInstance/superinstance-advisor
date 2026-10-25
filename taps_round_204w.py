#!/usr/bin/env python3
"""Taps creative break — 204w round.

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
import voices_204w as MV

text_to_dials = SHIPPED.text_to_dials     # upstream 4-hash chain -> 32B -> 16 int16

API_HOST = "https://live-canon.superinstance.dev"   # D3 FIX
USER_AGENT = "taps-creative-break/1.0"
TIMEOUT = 180
MM_P1_MAXTOKENS = 32000                   # reasoning models eat max_tokens
MM_P2_MAXTOKENS = 32000

TOPIC = "the strop does not cut the edge and the strop is the last pass that can be taken on it"

# 204w STRUCTURAL NOVELTY (64th shape): THE OPERATION THAT LEAVES NO WITNESS OF
# ITSELF IS THE ONE THAT DECIDES THE RESULT, AND THE RECORD OF THE WORK IS
# MADE OF THE WITNESSES OF THE OPERATIONS THAT DID NOT DECIDE IT.
#
# A blade is brought up over a sequence of passes. Each pass removes metal and
# each pass leaves a witness of itself: the file leaves its tooth marks, the
# grindstone leaves its arc across the bevel, the hone leaves a straight line
# down the flat. A skilled sharpener reads the edge the way a mason reads a
# dressed face -- by the marks of the tools that have been over it. Those marks
# are the record of the work, and they are legible.
#
# Then the strop. A strop is a strip of leather charged with rouge; the edge is
# drawn along it and it is NOT CUT. The strop removes no metal, and it leaves
# no mark of its own -- no line, no arc, no tooth track. The result is that
# the final state of the edge -- whether it will hold a keen edge or fold
# into a wire burr at the first cut, whether it is keen or merely bright --
# is settled by the ONE operation in the sequence that cannot be seen in the
# record. Every visible mark on the edge belongs to a pass that did not
# decide the outcome.
#
# So the structure is:
#
#   THE LAST PASS IS NOT THE ONE THAT SHOWS.  The evidence is legible and
#   abundant, and it is evidence about the earlier passes.  The deciding pass
#   is the only one with no witness, because it is the only one that does not
#   remove material.  A record made of tool marks cannot record the step
#   that changed nothing -- and the step that changed nothing is the step
#   that decided.
#
#   THE PASS THAT CHANGES NOTHING IS NOT THEREFORE THE PASS THAT MATTERS
#   NOTHINGS.  "It left no mark" is normally a way of saying it did no work.
#   Here the strop is the whole work: it is what draws the wire edge down
#   into a single line instead of a row of microscopic teeth, and a row of
#   microscopic teeth is a burr that will fold on the first cut.  The absence
#   of a mark is the evidence of the presence of the effect, and the record
#   cannot carry that inversion.
#
#   THE RECORD AND THE OBJECT DISAGREE ABOUT WHAT IS EVIDENCE.  The edge is
#   read as the sum of what was done to it.  The edge is actually the state
#   left by the last thing done to it, and the last thing left no mark, so
#   the reading of the edge understates the last act and overstates the
#   earlier ones.  A witness log that is a prediction would have to record
#   the invisible step, because the visible steps do not predict the
#   outcome.
#
# The canon mirror: a canon entry's coherence is not the sum of the visible
# marks in it.  The final line, the closing gesture, the last thing added
# before the entry was left alone, is the one that decides whether the entry
# holds -- and the entry's own record is made of everything that was said
# along the way, which is abundant and legible, and tells you very little
# about the one operation that settled it.
#
# NOT 203w (the property is real but only observable in a state that is gone):
# 203w is a TEMPORAL structure -- the state is gone and the judgment is made
# cold.  204w is about WITNESSING -- the state is fully present, fully
# visible, and the record is still silent about the one step that made it.
# Nothing is unobservable here; the edge is plainly there.  What is missing is
# the trace of the pass.
# NOT 194w (the missing interval left no mark, and the perfect contact is the
# proof): 194w's missing interval is an ABSENCE IN TIME -- a gap that was
# never sampled.  204w's strop is a PRESENT ACT that left no trace.  The
# difference is the difference between "nothing happened there" and
# "something happened there and it does not show".
# NOT 46w / 186w (the preparation spent the evidence it was meant to test):
# the strop does not spend anything.  The earlier passes leave their marks
# intact; the strop is added on top and adds none of its own.
# NOT 52w / 192w (the witness IS the destruction): here the witness is not
# destructive, and it is not absent either -- it is plentiful and pointed at
# the wrong passes.
# NOT 54w (the perfect contact is the proof): the contact here is not perfect;
# a keen edge is a single line and the marks around it are coarse.
# NOT 179w / 39w (the standard is never the one under test): the standard IS
# applied and it is sound -- the edge is judged by cutting it, by the shave,
# by the hone-stone, by the thumbnail.  The problem is not WHICH standard.
# NOT 61w / 201w (the error lives in the instance that cannot be reworked):
# nothing here is unreworkable.  A stropped edge can be re-stropped, a
# re-honed, a re-ground.  The unrepeatable thing is not the OBJECT.
# NOT 199w (the self-check has no third term): the check HAS a third term --
# the shave, the cut, the hone-stone.  This is not a self-check.
# NOT 197w / 57w (the signal is only true while the part nobody reads
# holds): nothing flips and nothing stops being true.  The edge is exactly
# as sharp as the strop left it.
# NOT 58w (the measurement and its archive are the same physical object):
# the edge and its record are DIFFERENT objects -- the object keeps the
# effect, the record keeps the marks, and they are not the same thing.
# NOT 190w / 50w (the verdict is a comparison disguised as a property): the
# keenness is a genuine property of the edge, not a comparison.
# NOT 166w (the instrument decides what counts as measurable): the marks are
# a fine instrument and they are measuring the wrong thing.
# NOT 200w (the apparatus has a floor): there is no floor here; the strop is
# a pass and passes have no floor.
# NOT 202w (where the property lives -- the thing or the arrangement of the
# unexamined parts): the property lives in the EDGE, and the arrangement of
# the passes is not the locus.
# NOT 176w / 199w (register neighbours only): `burr` and `honing` appear in
# prior rounds in a DIFFERENT SENSE (a burr at a beam balance's fulcrum; a
# honed hydraulic bore).  The register sweep below confirms the STROP
# register is 0-hit on all three surfaces.
# NOT 106w (the absence family: cameo, intaglio, millefiori, aquatint,
# stopout, cast pattern, negative mould): A STANDING TRAP.  `burnish` is a
# 106w printmaking word (burnishing away what should not print) and is
# DELIBERATELY EXCLUDED from this round's vocabulary for that reason -- the
# strop is the 204w word and `burnishing` never appears in the prompt.
# NEW AXIS: WHICH OPERATION IS THE RECORD ACTUALLY A WITNESS OF?  Is a record
# a witness of the operations that left marks, or of the operation that
# decided?  Rejected on STRUCTURE: 203w, 194w, 46w, 186w, 52w, 192w, 54w,
# 179w, 39w, 61w, 201w, 199w, 197w, 57w, 58w, 190w, 50w, 166w, 200w, 202w,
# 176w, 199w, 106w.
# 204w also ran a REGISTER SWEEP. 0 hits on ALL THREE surfaces (repo working
# tree, full git history, live canon dump): strop / stropping / stropped /
# stroppes / strop-leather / hone / whet / whetting / razor / rouge / crocus /
# grindstone / drawknife / arris / beveling / buffing / swarfe / tapering /
# tamping / dresser-free.
# FALSE FRIENDS (count>0 but a DIFFERENT SENSE, checked in context):
#   burr = 25 -- the 176w BEAM BALANCE ("a burr at the fulcrum clicks"), a
#     defect in an instrument, not a sharpening wire edge.
#   honing = 2 / honed = 24 -- the 199w HYDRAULIC BORE ("the honed steel
#     bore", "the honed surface retains its substrate-grown lay"), a
#     cylinder bore, not a blade edge.
#   file = 161 -- generic; "file" as a verb in prior prose.
#   draw = 38 -- generic; "draw" the wire, but also "draw" in prose.
#   lip = 18 -- the 199w cylinder lip; not the edge of a blade.
#   taper = 35 -- generic; the taper of a blade is a different subject.
#   compound = 11 -- generic; the polishing compound on a strop is the
#     204w sense, but the word is not used in the topic.
#   burnish = 2 -- the 106w PRINTMAKING round ("burnishing away what should
#     not print"). DELIBERATELY EXCLUDED from this round's vocabulary.
#   edge = 130 -- prior prose uses "edge" METAPHORICALLY ("the edge where
#     two absences learned to lean on each other"). No prior edge-sharpening
#     passage exists.
# Overlap vs 194 harvested prior topic lines = 0 at n=3,4,5,6,7,8. No prior
# topic is a substring or superstring of this one.
# The full prior PROSE was also swept for the metaphor (the 201w lesson: a
# topic can be 0-hit on every surface and still repeat an old shape) -- the
# shape was checked against the full 63-shape ledger FIRST, and the new
# shape's own key phrases ("the last pass that leaves no mark", "decides the
# result", "no witness of itself", "the record of the work", "the operations
# that did not decide it") are 0-hit across the tree and the whole history.

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
Do NOT begin your paragraph by quoting the topic sentence verbatim -- three voices
opening on the same clause is a templated round, not a braid. Start somewhere else
in the topic: from the tool, the material, or the moment of the act.

This round's material is the SHARPENING BENCH and the sequence of passes that
brings a blade up. Reach for the bench: the file, the grindstone and the
whetstone, the hone, the strop and the strop leather, the rouge and the
compound, the drawknife, the taper, the wire edge, the arris, the swarf, the
shave and the cut that tests it. Name the actual physical things -- what is
steel and what is stone and what is leather and what is abrasive, what is cut
and what is rubbed and what is only drawn along, what leaves a mark and what
leaves none, what is read off the blade and what is only known by cutting it.
Stay inside the topic's register -- do not drift into a general essay about
knives, about combat, or about sharpening as a hobby.
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
    # 198w: the ROUND-SPECIFIC continuations. A gram that is a continuation of
    # this round's topic-shape is DOCTRINE-ADJACENT and must be mandated with
    # its receipt, not reported as templating. 195w method: mandate the
    # CONTINUATIONS explicitly, and record PROVENANCE for each.
    "the sounding line", "sounding line is", "line is marked", "is marked at",
    "marked at every", "at every fathom", "every fathom and", "fathom and the",
    "and the marks are", "the marks are read", "marks are read by",
    "are read by nobody", "read by nobody", "by nobody",
    # 198w: short fragments (3-gram) of this round's own line, which the
    # span floor of 4 cannot see (193w/194w lesson).
    "the sounding", "the marks", "every fathom", "fathom", "the line",
    # 198w: the topic's own line REPHRASED. The topic subtraction removes
    # only CONTIGUOUS windows, so a voice that reorders the topic's words
    # ("the marks are read by nobody") yields 4-grams that are
    # neither contiguous windows nor doctrine -> flagged as templating.
    # These are the round's own prompt, echoed. Mandate them explicitly.
    "the marks are read by nobody", "marks are read by nobody",
    "the marks are read", "marks are read", "read by nobody and",
    "the sounding line is marked", "sounding line is marked at every",
    "is marked at every fathom", "at every fathom and the",
    "every fathom and the marks", "fathom and the marks are read",
    "the marks are read by", "marked at every fathom and",
    "the canon gate is a chord",
    # 204w: the ROUND-SPECIFIC continuations of this round's own topic line.
    # A shared gram that is a continuation of the topic-shape is
    # DOCTRINE-ADJACENT and must be mandated with its receipt, not reported
    # as templating. Mandate the CONTINUATIONS explicitly (193w/194w/195w).
    "the strop", "strop is", "the strop does not", "strop does not cut",
    "does not cut the", "not cut the edge", "cut the edge and",
    "the edge and the strop", "edge and the strop is", "and the strop is the",
    "the strop is the last", "strop is the last pass", "is the last pass",
    "the last pass", "last pass that", "pass that can be", "that can be taken",
    "can be taken on it", "be taken on it", "taken on it",
    # 204w: SHORT fragments (3-gram) of this round's own line -- the span
    # floor of 4 cannot see them (193w/194w lesson).
    "strop", "edge", "pass", "cut", "last",
    # 204w: the topic's own line REPHRASED -- the topic subtraction removes
    # only CONTIGUOUS windows, so a voice that reorders the topic's words
    # yields grams that are neither window nor doctrine -> flagged. Mandate
    # the round's own line reordered, not just verbatim (196w method).
    "the strop does not cut the edge and the strop is the last pass",
    "strop does not cut the edge and the strop is the last pass",
    "does not cut the edge and the strop is the last pass that can be taken",
    "the strop is the last pass that can be taken on it",
    "strop is the last pass that can be taken on it",
    "is the last pass that can be taken on it",
    "last pass that can be taken on it",
    # 204w: the sharpener's vocabulary the topic itself summons. A voice
    # that reaches for the same bench terms is talking about the topic, not
    # reusing another voice's template.
    "the hone", "hone is", "the grindstone", "grindstone is", "the whetstone",
    "whetstone is", "the file", "file is", "the drawknife", "drawknife is",
    "the strop leather", "strop leather is", "the rouge", "rouge is",
    "the compound", "compound is", "the arris", "arris is", "the swarf",
    "swarf is", "the taper", "taper is", "the wire edge", "wire edge is",
    "the shave", "shave is", "the cut", "cut is", "the bench", "bench is",
    "the strop does not", "does not cut", "not cut the",
    # 204w: the shape's own key terms. A voice that uses the SAME STRUCTURE
    # (the deciding pass leaves no witness; the record is made of the marks
    # of the passes that did not decide) is agreeing about the topic, not
    # copying a template -- but only these exact short forms are mandated;
    # the general words are not blanket-sanctioned.
    "leaves no mark", "leave no mark", "left no mark", "no mark of",
    "no mark of its own", "mark of its own", "of its own",
    "leaves no witness", "no witness of", "witness of itself",
    "decides the result", "decide the result", "the deciding",
    "the record of the work", "record of the work", "of the work is",
    "did not decide", "that did not decide", "the operations that",
    "the visible marks", "visible marks", "the earlier passes",
    "earlier passes", "the marks are read", "marks are read by",
    "marks are read", "read by nobody",
    # 195w: SHORT doctrine FRAGMENTS (193w lesson) -- a 3-token fragment of a
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

def g6c_opening_clause(texts, topic=None):
    """Two voices opening on the SAME clause = two-template round (the 192w
    baseline defect). Compare the first 6 content tokens.

    198w CORRECTION (found by the 198w round itself): a shared opening that is
    a CONTIGUOUS WINDOW OF THE TOPIC is the voices ECHOING THE PROMPT, which
    the topic-subtraction elsewhere in this runner already treats as mandated.
    Flagging it as a two-template collision is a GUARD FALSE POSITIVE on the
    echo axis -- and it hides a REAL defect if the guard fires on it, because
    a genuinely templated pair that ALSO quotes the topic would be excused.

    So the guard is SPLIT into two axes:
      (a) TEMPLATE collision: two voices share an opening clause that is NOT a
          topic window -> REAL defect, fail.
      (b) TOPIC ECHO: two voices share an opening clause that IS a topic
          window -> report as a PROVENANCE receipt (both voices quoted the
          prompt), do not fail the round on it alone, but DO require that the
          echo is not the whole round: if ALL voices echo the topic, the round
          has no independent voice at all -> fail.
    This keeps the original defect detectable while refusing to launder it.
    """
    firsts = []
    for t in texts:
        w = norm_tokens(t)[:6]
        firsts.append(" ".join(w))
    dup = len(firsts) != len(set(firsts))
    tset = topic_ngrams(topic) if topic else set()
    if not dup:
        return (True, {"openings": firsts, "collisions": []})
    collisions, echoes = [], []
    for a, b in itertools.combinations(range(len(firsts)), 2):
        if firsts[a] != firsts[b]:
            continue
        if firsts[a] in tset:
            echoes.append(f"{a}-{b}")
        else:
            collisions.append(f"{a}-{b}")
    detail = {"openings": firsts, "collisions": collisions, "topic_echo_pairs": echoes,
              "all_voices_echo_topic": len(set(firsts)) == 1 and len(echoes) > 0}
    # FAIL on a real template collision, or on a round where EVERY voice opens
    # on the topic (no independent voice at all). A partial topic echo is
    # reported as a receipt, not a failure.
    ok = (not collisions) and not detail["all_voices_echo_topic"]
    return (ok, detail)

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
    # NC7 (204w): a 204w-register triple that is NOT the topic's own line must
    # still be flagged -- proves the round-specific mandates did not blanket-
    # sanction the whole sharpening-bench vocabulary.
    v = ["the hone takes the steel and the strop leather is charged with rouge"] * 3
    res.append(("204w-register non-topic triple IS flagged",
                len(shared_ngrams(v, 4)) > 0))
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
    res.append(("identical openings rejected", g6c_opening_clause([same[0], same[1], diff[0]], topic=TOPIC)[0] is False))
    # NC7 (200w): the echo axis -- two voices on the SAME TOPIC WINDOW is a
    # receipt, not a collision; but three voices all echoing = no independent
    # voice at all, and the guard MUST fire.
    # 201w NOTE: this NC is RE-POINTED at the 201w topic. The 200w
    # strings were NOT a topic window of the 201w topic, so the guard would
    # correctly call them a template collision and the NC would fail -- the
    # TEST was stale, not the code (195w method: a failing pre-flight can be
    # the TEST's fault; diagnose which side is wrong).
    echo = ["the strop does not cut the edge and the strop is the last pass at once",
            "the strop does not cut the edge and the strop is the last pass at once",
            "the hone takes the steel and the strop leather is charged with rouge"]
    res.append(("topic-echo pair is not a template collision",
                g6c_opening_clause(echo, topic=TOPIC)[0] is True))
    res.append(("all-voice topic echo IS rejected",
                g6c_opening_clause([echo[0], echo[1], echo[0]], topic=TOPIC)[0] is False))
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
    probe = "the strop does not cut the edge and the strop is the last pass and the edge is not looked at"
    t.append(("topic subtraction is a contiguous window, not a substring",
              probe not in topic_ngrams(TOPIC), probe))
    t.append(("reordered topic line is covered by an explicit mandate",
              is_mandated("the strop is the last pass that can be taken on it")
              and is_mandated("strop is the last pass that can be taken on it")
              and is_mandated("is the last pass that can be taken on it"),
              "204w reordered grams mandated, not auto-excluded"))
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
    e = ["the strop does not cut the edge and the strop is the last pass that can be taken on it"]*3
    t.append(("round topic-line triple not flagged", shared_ngrams(e,4,topic=TOPIC) == set(), ""))

    # --- classifier: distinct_skeleton (G5) --------------------------------
    same = ["alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"]*3
    t.append(("identical skeletons rejected", g6b_distinct_skeleton(same, TOPIC)[0] is False, ""))
    diff = ["the ledger was drawn to a balance and the balance is the shape it keeps",
            "a ferry leaves the north dock before the fog and the fog is the passenger",
            "the seam of the sleeve was stitched from the inside and the inside is warm"]
    t.append(("different skeletons accepted", g6b_distinct_skeleton(diff, TOPIC)[0] is True, ""))

    # --- classifier: opening clause (G4) ----------------------------------
    t.append(("identical openings rejected",
              g6c_opening_clause([same[0],same[1],diff[0]], topic=TOPIC)[0] is False, ""))
    t.append(("different openings accepted", g6c_opening_clause(diff, topic=TOPIC)[0] is True, ""))
    # 200w: the ECHO axis. Two voices opening on the SAME TOPIC WINDOW is a
    # provenance receipt, not a template collision -- but if EVERY voice echoes
    # the topic there is no independent voice, and that MUST fail.
    echo_pair = ["the strop does not cut the edge and the strop is the last pass at once",
                 "the strop does not cut the edge and the strop is the last pass at once",
                 "the hone takes the steel and the strop leather is charged with rouge"]
    t.append(("two voices echoing the topic is NOT a template collision",
              g6c_opening_clause(echo_pair, topic=TOPIC)[0] is True, ""))
    t.append(("all voices echoing the topic IS a failure",
              g6c_opening_clause([echo_pair[0], echo_pair[1], echo_pair[0]],
                                 topic=TOPIC)[0] is False, ""))
    # and a genuine template collision that ALSO quotes the topic must still fail
    tmpl = ["the strop does not cut the edge and the strop is the last pass at once",
            "the strop does not cut the edge and the strop is the last pass at once",
            "the strop does not cut the edge and the strop is the last pass at once"]
    t.append(("template collision on a topic window still fails",
              g6c_opening_clause(tmpl, topic=TOPIC)[0] is False, ""))

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

    # --- 203w: the round's own mandates must NOT blanket-sanction the whole
    # wheelwright's vocabulary. A 203w-register triple that is NOT the topic's own
    # line must still be flagged, or the guard has been switched off.
    v204 = ["the hone takes the steel and the strop leather is charged with rouge"]*3
    t.append(("204w-register non-topic triple IS flagged",
              len(shared_ngrams(v204, 4)) > 0, ""))

    # --- negative controls (6) ---------------------------------------------
    ncs = negative_controls()
    for name, ok in ncs:
        t.append((f"NC: {name}", ok, ""))

    npass = sum(1 for _,ok,_ in t if ok)
    return t, npass, len(t)

# ---- round -----------------------------------------------------------------
def run_round():
    print(f"\n=== Taps round 204w | topic: {TOPIC} ===\n", flush=True)
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
    g, d = g6c_opening_clause(p1s, topic=TOPIC); guards["G4_distinct_openings"] = {"pass": g, "detail": d}
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
        "runner": "taps_round_204w.py",
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
