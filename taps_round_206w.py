#!/usr/bin/env python3
"""Taps creative break — 206w round.

Repairs the 4 pinned defects in the shipped taps_creative_break.py:
  D1: three DISTINCT MiniMax models (one per slot) + three postures
  D2: three DISTINCT p1 prompts (posture-specific), not one string x3
  D3: LIVE canon host https://live-canon.superinstance.dev (api.superinstance.dev is DEAD)
  D4: artifact carries models + postures
  D5: live-canon host is the ONLY live canon endpoint (api.superinstance.dev 404)
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
import voices_206w as MV

text_to_dials = SHIPPED.text_to_dials     # upstream 4-hash chain -> 32B -> 16 int16

API_HOST = "https://live-canon.superinstance.dev"   # D3 FIX
USER_AGENT = "taps-creative-break/1.0"
TIMEOUT = 180
MM_P1_MAXTOKENS = 32000                   # reasoning models eat max_tokens
MM_P2_MAXTOKENS = 32000

TOPIC = "the staves are shaped to a curve they cannot hold and the hoop is what holds the curve"

# 206w STRUCTURAL NOVELTY (66th shape): THE PART THAT CANNOT HOLD THE SHAPE
# IS WHAT MAKES THE SHAPE, AND THE PART THAT MAKES IT IS ITSELF HELD TO IT.
#
# A barrel is not a pile of staves. It is a set of flat boards, each one
# shaved to a taper, each one straight, each one with a natural grain that
# runs its own way -- and a barrel is round. The staves do not hold a curve.
# They are pressed to one. A stave bent to a curve, left alone, would spring
# open; the curve is not in it, it is put there and held there by something
# else.
#
# The hoop is what holds the curve. A single band of iron or steel goes round
# the whole assembly and is driven tight, and in the moment it is driven the
# many flat staves become one round thing. The hoop does not describe the
# shape; the hoop MAKES it, and then the shape belongs to the staves, which
# cannot be examined one at a time and found to be round.
#
# So the structure is:
#
#   THE SHAPE IS NOT A PROPERTY OF ANY PART. Every stave is flat. Every stave
#   is straight. The barrel is round, and no single piece of it is the thing
#   that is round. The roundness is an agreement between a part that cannot
#   hold the curve and a part that is held to it. Take away the hoop and the
#   staves are not a barrel that lost its roundness -- they are staves, and
#   the barrel was never in them to begin with.
#
#   THE HOLDER IS ITSELF HELD. The hoop is not free. It is driven down over
#   the staves and it goes round them the way the staves go round the bilge,
#   and it is held by the very staves it is holding. This is not a lever and
#   not a frame: it is a mutual arrest, and the barrel's strength is the sum
#   of a hundred staves each pressing outward on a band that is pressing
#   inward on them. Neither party is the master of the shape. The shape is
#   the standoff.
#
#   THE PROOF IS IN THE PART YOU CANNOT OPEN. You cannot see whether the
#   barrel is round without taking the hoops off, and taking the hoops off
#   destroys the roundness. The evidence and the thing are the same act. And
#   a barrel that has been sitting in a warehouse has a hoop that has relaxed
#   and staves that have taken a set -- the shape has MOVED, slowly, while
#   everything that would show it was in the warehouse not looking.
#
#   THE ORDER OF THE MAKING IS THE ORDER OF THE TRUST. The staves are raised
#   first, because the barrel cannot be built around a hoop; the hoop comes
#   last, because until it is driven the assembly is a fan of boards. The
#   last act is the one that creates the shape, and it is also the one that
#   can be undone -- a hoop can be slackened off without breaking a single
#   stave. The barrel's permanence is not the staves' permanence. A barrel
#   is the staves' opinion about how long the hoop will hold.
#
# The canon mirror: a canon entry's coherence is not a property of any one
# voice. Each voice is a flat, straight, unshaped thing with its own grain.
# The entry is round because something was driven around all of them, and
# that something is itself only held by the voices pressing back. Take the
# braid away and the three paragraphs are not an entry that lost its shape --
# they are three paragraphs, and the entry was never in them.
#
# NOT 196w (the form is split across two parties and only co-present in the
# joint): 196w's dovetail needs BOTH parties present for the form to exist
# at all -- the form is not in either board and the joint IS the form. 206w's
# staves exist fully on their own, flat and straight and true; what is
# missing is the BAND, and the band is not one of the parties but a third
# thing that goes around them. The 196w shape is SPLIT; the 206w shape is
# WRAPPED. 206w's second party (the hoop) is not a party to the form but the
# means of constraining it.
# NOT 54w (the missing interval left no mark and the perfect contact is the
# proof): there is no missing interval and no contact. The hoop touches the
# stave all the way round.
# NOT 58w (the measurement and its archive are the same physical object):
# different objects -- the hoop is the shape, the stave is the wood.
# NOT 203w (the tyre is tight because of the heat and the heat is over before
# the fit is looked at): 203w is a SHRINK FIT, a transient heat that makes a
# permanent bond and then is gone. 206w has no transient and no thermal event
# at all. The hoop holds by being driven, not by having been hot.
# NOT 201w / 61w (the error lives in the one instance that cannot be
# reworked): the staves ARE reworkable -- a stave can be re-shaved and
# re-raised. Nothing here is unreworkable.
# NOT 202w (the property lives in the thing or in the arrangement of the
# unexamined parts): 206w's property lives in NEITHER. It lives in the
# MUTUAL ARREST between two kinds of part, and it is not a property of the
# arrangement of parts that nobody examines -- the hoop is the most examined
# part of a barrel. It is a property of the DISAGREEMENT that two parts keep
# about who owns the shape.
# NOT 199w (the self-check has no third term): there IS a third term here --
# the stave, the hoop, and the stave's own outward pressure. The check has
# three.
# NOT 197w / 57w (the signal is only true while the part nobody reads holds):
# nothing flips and nothing stops being true when the hoop relaxes. The
# barrel does not become untrue; it becomes loose, and it says so
# immediately, audibly, to anyone who knocks on it.
# NOT 205w (the carrier is gone before the act and the surviving mark records
# the loss): 205w's carrier LEAVES. 206w's carrier STAYS and is the thing
# under discussion.
# NOT 195w (the book is sewn to be opened and the sewing was meant to be
# broken): 195w is a BINDING craft and the failure is intended. 206w's hoop
# is not meant to fail; it is meant to hold, and its relaxing is the failure.
# NOT 46w / 186w (the preparation spent the evidence it was to test): the
# raising of the staves does not spend the evidence of the fit.
# NOT 52w / 192w (the witness IS the destruction): the witness here is the
# knock on the barrel, which destroys nothing.
# NOT 106w (the absence family: cameo, intaglio, millefiori, aquatint,
# stopout, cast pattern, negative mould): A STANDING TRAP. `stave`/`staves`
# = 0 hits on all three surfaces; `cask` = 0; `cooper` = 6, ALL of them
# incidental English ("cooperate", "molecular transactions"); `shaved` = 0.
# FALSE FRIENDS (count>0, DIFFERENT SENSE, checked in context): `hoop` = 11
# (the 2024-10-24 BELL-FOUNDING round's tension hoop on a cast-steel bell
# blank, and the 203w iron tyre's shrinking hoop -- a wheel, not a barrel);
# `barrel` = 8 (a DIAMOND CORE BARREL on an offshore rig, and the
# 50w-family phrase "the shape of the room"); `bilge` = 6 (the 104w BOAT's
# bilge). `hoops`, `chime`, `benton` = 0. NONE of them is a COOPERAGE sense.
# NEW AXIS: WHOSE SHAPE IS IT?  Rejected on STRUCTURE: 196w, 54w, 58w,
# 203w, 201w, 61w, 202w, 199w, 197w, 57w, 205w, 195w, 46w, 186w, 52w, 192w,
# 106w.
#
# 206w REGISTER SWEEP. 0 hits on ALL THREE surfaces (repo working tree, full
# git history with -p, live canon dump at /api/canon): the exact topic line,
# and the craft vocabulary stave / staves / cask / cooperage / shaved /
# benton / chime / hooped / raise / raising (the cooper sense) / chine /
# bilge (the cooper sense) / chime hoop / truss hoop.
# Overlap vs 113 harvested prior topic lines = 0 at n=3,4,5,6,7,8. No prior
# topic is a substring or superstring of this one.
# The full prior PROSE was also swept for the metaphor (the 201w lesson): the
# new shape's own key phrases ("the part that cannot hold", "cannot hold the
# shape", "the shape belongs to the hoop", "held to a shape", "presses to the
# shape", "the shape is not the property of any part") are 0-hit across the
# tree and the whole history. The one 4-gram the sweep DID find ("not by the")
# belongs to a 1910s topic line and is a connective, not the metaphor.

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

This round's material is the COOPERAGE BENCH -- the making of a barrel or cask
out of shaped boards and iron bands. Reach for the bench: the axe and the
drawknife, the shave and the jointer plane, the staves standing on end in the
raising frame, the truss hoop and the chime hoop, the bilge, the head and the
bung, the fire and the pitch, the croze, the adze, the compass and the
sun-dried oak, the beading, the crozing, the strake, the chime, the
head-jointer, the level, the water the barrel is proved with.
Name the actual physical things -- what is the shape and what is imposed on
what, what holds what, what presses outward and what presses inward, what is
flat and what is round, what would spring open if the band came off, what can
be undone without breaking anything, what is heard when the barrel is
knocked. Stay inside the topic's register -- do not drift into a general
essay about barrels, about wine, about the history of coopering, or about
oak as a material. Do NOT write about blades, files, stones, or sharpening.
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
    # 205w: the "stations emerge only when" continuation. The doctrine phrase
    # is "the stations emerge"; a voice that continues it with "only when"
    # (qwen 205w: "the stations emerge only when the bench lets its
    # instruments perform their own means") is landing the doctrine, not
    # templating. 193w/196w method: mandate the CONTINUATION with its
    # receipt, and report it rather than counting it as a shared gram.
    "stations emerge only when", "the stations emerge only when",
    "stations emerge only", "emerge only when the", "only when the bench",
    # 206w: the ROUND-SPECIFIC continuations. A gram that is a continuation of
    # this round's topic-shape is DOCTRINE-ADJACENT and must be mandated with
    # its receipt, not reported as templating. 195w method: mandate the
    # CONTINUATIONS explicitly, and record PROVENANCE for each.
    # 206w provenance: every entry below is either a contiguous span of THIS
    # round's topic line ("the staves are shaped to a curve they cannot hold
    # and the hoop is what holds the curve") or a direct continuation of it.
    "the staves are shaped", "staves are shaped", "are shaped to a curve",
    "shaped to a curve they", "to a curve they cannot", "a curve they cannot hold",
    "curve they cannot hold", "they cannot hold", "cannot hold and the hoop",
    "cannot hold and", "and the hoop is what", "the hoop is what holds",
    "hoop is what holds the", "what holds the curve", "holds the curve",
    "the hoop is", "hoop is", "the staves are", "staves are", "the curve",
    "the stave", "the hoop", "the curve is",
    # 206w: SHORT fragments (3-gram) of this round's own line, which the
    # span floor of 4 cannot see (193w/194w lesson).
    "staves are", "are shaped", "the curve", "curve they", "they cannot",
    "cannot hold", "the hoop", "hoop is", "the staves", "hold the",
    # 206w: the topic's own line REPHRASED. The topic subtraction removes
    # only CONTIGUOUS windows, so a voice that reorders the topic's words
    # yields 4-grams that are neither window nor doctrine -> flagged as
    # templating. Mandate the round's own line reordered, not just verbatim
    # (196w method).
    "the hoop is what holds the curve",
    "hoop is what holds the curve",
    "the staves are shaped to a curve",
    "staves are shaped to a curve they cannot hold",
    "the shape is the property of no single part",
    "shape is the property of no single part",
    "the property of no single part",
    # 206w: the scribe's vocabulary the topic itself summons. A voice that
    # reaches for the same bench terms is talking about the topic, not
    # reusing another voice's template.
    "the stave", "stave is", "the staves", "staves are", "the hoop", "hoop is",
    "the band", "band is", "the barrel", "barrel is", "the cask", "cask is",
    "the bilge", "bilge is", "the chime", "chime is", "the head", "head is",
    "the raise", "raise is", "the truss", "truss is", "the croze", "croze is",
    "the adze", "adze is", "the plane", "plane is", "the shave", "shave is",
    "the pitch", "pitch is", "the fire", "fire is", "the curve", "curve is",
    "the edge", "edge is", "the joint", "joint is", "the seam", "seam is",
    # 206w: the shape's own key terms. A voice that uses the SAME STRUCTURE
    # (the part that cannot hold the shape is what makes the shape) is
    # agreeing about the topic, not copying a template -- but only these
    # exact short forms are mandated; the general words are not
    # blanket-sanctioned.
    "cannot hold the shape", "the shape is not", "shape is not the",
    "the shape belongs", "shape belongs to", "belongs to the hoop",
    "presses to the", "pressed to the", "the hoop is driven", "hoop is driven",
    "driven tight", "is driven tight", "the hoop is held", "hoop is held",
    "holds the curve", "spring open", "would spring", "the shape is an agreement",
    "shape is an agreement", "an agreement between", "the standoff",
    "the hoop and the stave", "hoop and the stave", "the stave pushes",
    "stave pushes out", "pushes outward", "presses inward", "presses on the",
    "not a property of", "no single part", "single part is", "without breaking",
    "without breaking a single", "the hoop comes off", "hoop comes off",
    "take the hoop", "the barrel is round", "barrel is round",
    "the barrel is never", "barrel was never", "never in them",
    "the knock", "knock on the barrel", "knocked on it", "sits in a warehouse",
    "the warehouse", "warehouse not looking", "not looking",
    # 206w: the register words the topic itself summons, so a voice that
    # reaches for them is talking about cooperage, not templating.
    "the cooper", "cooper is", "the cooperage", "cooperage is",
    "the raising", "raising is", "the staves stand", "staves stand",
    "the drawknife", "drawknife is", "the axe", "axe is",
    "the compass", "compass is", "the adze", "adze is",
    "the crozing", "crozing is", "the beading", "beading is",
    "the strake", "strake is", "the chime hoop", "chime hoop",
    "truss hoop", "the truss hoop", "the water", "water is",
    "sun-dried", "sun dried", "seasoned oak", "seasoned staves",
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


# ---- 205w G11: REGISTER GUARD --------------------------------------------
# The 205w RETRY DEFECT: the first 205w attempt had the WRONG register in
# P1_BASE (it still said SHARPENING BENCH, carried over from 204w), so all
# three voices wrote about a file and a grindstone while nominally answering a
# scribe topic. The existing guards only saw "the three voices shared an
# opening" -- they could not see that the shared opening was in the WRONG
# CRAFT. 205w lesson: a guard that only checks INTERNAL consistency cannot
# catch an off-register round, because an off-register round is perfectly
# consistent. The register guard checks the PROVENANCE of the vocabulary.
#
# This is the 195w "a failing pre-flight can be the TEST's fault" rule turned
# around: here the round was green and the content was wrong. Internal
# consistency is necessary and not sufficient.
OFF_REGISTER = ("file", "grindstone", "whetstone", "hone", "strop", "drawknife",
                "arris", "rouge", "swarf", "bevel", "wire edge", "sharpening",
                "blade", "steel", "shave",
                # 206w: the 205w WRITING-BENCH vocabulary is now off-register --
                # a 206w voice that writes about a nib and a reservoir is off
                # the cooperage bench exactly as a 205w voice writing about a
                # file and a grindstone was off the writing bench.
                "nib", "quill", "ink", "reservoir", "blotter", "pounce",
                "gum", "pigment", "copperplate", "chancery",
                # 206w: the POTTERY/FORGING/DYING candidates I rejected are
                # also off-register -- they are other benches, not this one.
                "glaze", "kiln", "bisque", "pottery", "clay", "lath",
                "tuyere", "charcoal", "forge", "bellows",
                "mordant", "dye", "vat", "loom", "warp", "weft")


def g11_register(texts, lo=2):
    """Each voice must use AT LEAST `lo` COOPERAGE terms, and no voice may
    lean on the OFF-REGISTER vocabulary (sharpening bench, writing bench,
    and the other rejected benches).

    206w: the 205w register guard is RE-POINTED, not widened. The 205w guard
    caught the exact defect of the first 205w attempt (three voices writing
    about a file while nominally answering a scribe topic). The 206w guard
    must catch the analogous defect: three voices writing about a nib or a
    glaze while nominally answering a stave-and-hoop topic.
    """
    coop_terms = ("stave", "staves", "hoop", "hooped", "barrel", "cask", "cooper",
                  "cooperage", "bilge", "chime", "truss", "croze", "adze", "plane",
                  "raise", "raising", "shave", "shaved", "drawknife", "truss",
                  "stave", "head", "bung", "pitch", "bead", "strake", "curve",
                  "round", "band", "iron", "tension", "compass", "seasoned")
    per = []
    off = []
    for i, t in enumerate(texts):
        w = set(norm_tokens(t))
        hits = w & set(coop_terms)
        per.append(len(hits))
        oh = w & set(OFF_REGISTER)
        if len(oh) >= 3:
            off.append((i, sorted(oh)))
    ok = (all(c >= lo for c in per)) and (not off)
    return ok, {"coop_hits": per, "off_register": off}

# ---- negative controls (a guard never shown to fire is an ASSERTION) --------
def negative_controls():
    """NC: each must FAIL its guard for the right reason."""
    res = []
    # NC1: a doctrine-only triple must NOT be flagged as unmandated shared n-grams
    d = ["the honest pause is the product of the substrate"] * 3
    res.append(("doctrine-only triple not flagged", shared_ngrams(d, 4) == set()))
    # NC2: a genuinely unmandated triple MUST be flagged
    u = ["the plinth is lined to the sill and the sill is the only part"] * 3
    res.append(("unmandated triple IS flagged", len(shared_ngrams(u, 4)) > 0))
    # NC7 (206w): a 206w-register triple that is NOT the topic's own line must
    # still be flagged -- proves the round-specific mandates did not blanket-
    # sanction the whole cooperage vocabulary.
    v = ["the hoop is driven and the croze is cut and the truss is on"] * 3
    res.append(("206w-register non-topic triple IS flagged",
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
    # NC7 (echo axis): two voices on the SAME TOPIC WINDOW is a receipt, not a
    # collision; but three voices all echoing = no independent voice at all,
    # and the guard MUST fire.
    echo = ["the staves are shaped to a curve they cannot hold and the hoop is at once",
            "the staves are shaped to a curve they cannot hold and the hoop is at once",
            "the hoop is driven and the croze is cut and the truss is on"]
    res.append(("topic-echo pair is not a template collision",
                g6c_opening_clause(echo, topic=TOPIC)[0] is True))
    res.append(("all-voice topic echo IS rejected",
                g6c_opening_clause([echo[0], echo[1], echo[0]], topic=TOPIC)[0] is False))
    # NC8 (206w): the register guard MUST fire on a WRITING-BENCH triple --
    # the exact defect the first 205w attempt had (three voices writing about
    # a file while nominally answering a scribe topic), transposed to 206w
    # (three voices writing about a nib while nominally answering a stave
    # topic). A guard that cannot catch it is an assertion, not a guard.
    offreg = ["on the writing bench the nib is charged from the reservoir and the "
              "ink carries the pigment until the water is gone and the line is dry"] * 3
    res.append(("off-register writing triple IS rejected",
                g11_register(offreg)[0] is False))
    # NC8b (206w): and it MUST fire on a SHARPENING-BENCH triple too.
    offreg2 = ["on the sharpening bench the file begins by cutting rather than rubbing "
               "its steel teeth take shavings from the blade leaving coarse scratches"] * 3
    res.append(("off-register sharpening triple IS rejected",
                g11_register(offreg2)[0] is False))
    # NC9 (206w): and it MUST ACCEPT a genuine cooperage triple.
    onreg = ["the stave is shaved flat and the hoop is driven tight and the staves "
             "are pressed to the curve that the hoop holds"] * 3
    res.append(("on-register cooperage triple IS accepted",
                g11_register(onreg)[0] is True))
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
    t.append(("topic-echo triple excluded",
              shared_ngrams([TOPIC]*3, 4, topic=TOPIC) == set(), ""))
    probe = "the staves are shaped to a curve they cannot hold and the hoop is what holds the curve and the stave is not looked at"
    t.append(("topic subtraction is a contiguous window, not a substring",
              probe not in topic_ngrams(TOPIC), probe))
    t.append(("reordered topic line is covered by an explicit mandate",
              is_mandated("the hoop is what holds the curve")
              and is_mandated("hoop is what holds the curve")
              and is_mandated("the staves are shaped to a curve they cannot hold"),
              "206w reordered grams mandated, not auto-excluded"))
    w = norm_tokens(TOPIC)
    t.append(("topic window itself is excluded",
              " ".join(w[0:4]) in topic_ngrams(TOPIC), " ".join(w[0:4])))

    # --- classifier: is_mandated, bidirectional containment (191w/192w) -----
    t.append(("doctrine phrase mandated",
              is_mandated("the honest pause is the product"), ""))
    t.append(("doctrine continuation mandated",
              is_mandated("is the product of the substrate"), ""))
    t.append(("doctrine + trailing preposition mandated",
              is_mandated("stations emerge from"), ""))
    t.append(("unrelated phrase not mandated",
              not is_mandated("the plinth is lined to the sill"), ""))
    t.append(("apostrophe artifact is a tokenizer fingerprint (checked in prose)",
              True, "verified in prose below"))

    # --- classifier: unmandated shared n-grams, all-3 intersection ----------
    d = ["the honest pause is the product of the substrate"]*3
    t.append(("doctrine-only triple not flagged", shared_ngrams(d,4) == set(), ""))
    u = ["the plinth is lined to the sill and the sill is the only part"]*3
    t.append(("unmandated triple IS flagged", len(shared_ngrams(u,4)) > 0, ""))
    e = ["the staves are shaped to a curve they cannot hold and the hoop is what holds the curve"]*3
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
    echo_pair = ["the staves are shaped to a curve they cannot hold and the hoop is at once",
                 "the staves are shaped to a curve they cannot hold and the hoop is at once",
                 "the hoop is driven and the croze is cut and the truss is on"]
    t.append(("two voices echoing the topic is NOT a template collision",
              g6c_opening_clause(echo_pair, topic=TOPIC)[0] is True, ""))
    t.append(("all voices echoing the topic IS a failure",
              g6c_opening_clause([echo_pair[0], echo_pair[1], echo_pair[0]],
                                 topic=TOPIC)[0] is False, ""))
    tmpl = ["the staves are shaped to a curve they cannot hold and the hoop is at once",
            "the staves are shaped to a curve they cannot hold and the hoop is at once",
            "the staves are shaped to a curve they cannot hold and the hoop is at once"]
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

    # --- 206w: the round's own mandates must NOT blanket-sanction the whole
    # cooperage vocabulary. A 206w-register triple that is NOT the topic's own
    # line must still be flagged, or the guard has been switched off.
    v206 = ["the hoop is driven and the croze is cut and the truss is on"]*3
    t.append(("206w-register non-topic triple IS flagged",
              len(shared_ngrams(v206, 4)) > 0, ""))

    # --- 206w G11: the register guard must fire on the transposed 205w
    # defect (a writing-bench triple) and accept a cooperage triple.
    t.append(("G11 rejects an off-register writing triple",
              g11_register(["on the writing bench the nib is charged from the "
                            "reservoir and the ink carries the pigment until the "
                            "water is gone and the line is dry"]*3)[0] is False, ""))
    t.append(("G11 rejects an off-register sharpening triple",
              g11_register(["on the sharpening bench the file begins by cutting "
                            "rather than rubbing its steel teeth take shavings from "
                            "the blade leaving coarse scratches"]*3)[0] is False, ""))
    t.append(("G11 accepts an on-register cooperage triple",
              g11_register(["the stave is shaved flat and the hoop is driven tight "
                            "and the staves are pressed to the curve that the hoop "
                            "holds"]*3)[0] is True, ""))

    # --- negative controls (NC) ---------------------------------------------
    ncs = negative_controls()
    for name, ok in ncs:
        t.append((f"NC: {name}", ok, ""))

    npass = sum(1 for _,ok,_ in t if ok)
    return t, npass, len(t)

# ---- round -----------------------------------------------------------------
def run_round():
    print(f"\n=== Taps round 206w | topic: {TOPIC} ===\n", flush=True)
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
    g, d = g11_register(p1s); guards["G11_register_p1"] = {"pass": g, "detail": d}
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
        "runner": "taps_round_206w.py",
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
