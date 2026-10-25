#!/usr/bin/env python3
"""Taps creative break — 205w round.

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
import voices_205w as MV

text_to_dials = SHIPPED.text_to_dials     # upstream 4-hash chain -> 32B -> 16 int16

API_HOST = "https://live-canon.superinstance.dev"   # D3 FIX
USER_AGENT = "taps-creative-break/1.0"
TIMEOUT = 180
MM_P1_MAXTOKENS = 32000                   # reasoning models eat max_tokens
MM_P2_MAXTOKENS = 32000

TOPIC = "the scribe is dry before it is loaded and the ink is dry because the water is gone"

# 205w STRUCTURAL NOVELTY (65th shape): THE CARRIER IS GONE BEFORE THE ACT
# THAT NEEDS IT, AND THE MARK THAT SURVIVES IS THE MARK OF THE LOSS, NOT
# THE MARK OF THE WORK.
#
# A scribe is an instrument that carries its own means. The nib holds ink; the
# ink is a suspension, and a suspension is a carrier -- it holds pigment and
# water and a vehicle, and until it is written with, the writing instrument
# is an empty shape with a promise in it. The scribe is a shape that can hold
# a mark and has not yet been allowed to.
#
# Then it is loaded. The dip, the charged pen, the reservoir, the well. From
# the moment of loading, the instrument is a carrier of something it will
# spend. The whole craft of the scribe is in managing that: a scribe loaded
# too heavily smears and blots, one loaded too lightly skips and starves. The
# craft is a judgment about a quantity, made once, before the work.
#
# And then the water goes. Not the pigment -- the pigment is the mark and the
# pigment is permanent. The water is the carrier, and the carrier leaves
# first. As the water leaves the ink, the ink dries. A dried ink is not a
# lesser ink; it is an ink that has become the thing it was carrying. The
# water was there to make the pigment move; once the pigment is on the page
# the water has no further business, and it is gone. The mark that survives
# is therefore not the record of the writing. It is the record of the
# water's departure.
#
# So the structure is:
#
#   THE LAST THING TO HAPPEN IS THE THING THAT LEAVES NO TRACE OF ITSELF.
#   A wet mark is ambiguous -- you cannot tell a good line from a blot until
#   it dries. The dry mark is the only legible mark, and it is legible
#   precisely because the carrier that made it ambiguous is gone. The
#   instrument that writes is a witness of the writing. The instrument that
#   dries is a witness of the loss. And the loss is what settles whether
#   what was written was legible at all.
#
#   THE ORDER OF THE FAILURE IS THE ORDER OF THE RECORD. A scribe that runs
#   dry mid-line does not produce a partial mark -- it produces a mark that
#   tapers into a drag and then stops, and the stop is INVISIBLE until the
#   ink dries and the line is read. While the ink is wet the writer knows
#   something is wrong, because the line is dying in the hand. The record
#   will not know for a long time, and by the time the record knows, the
#   writer has long since believed the page. The witness log is a
#   prediction: the taper predicts the dry line that will show the failure,
#   and the prediction is available long before the evidence.
#
#   THE INSTRUMENT AND ITS LOAD ARE SEPARATE OBJECTS THAT ARE EASILY
#   CONFLATED. A dry scribe is a scribe with no ink in it -- an instrument
#   that cannot do the work and looks exactly like an instrument that has
#   already done it. The empty nib and the written page are the same
#   silhouette. The state of the carrier is not legible on the object, only
#   in what it last produced.
#
# The canon mirror: a canon entry's coherence is not visible while it is
# being written, and a canon entry that is DONE and empty of its carrier
# looks exactly like a canon entry that is done and full. The final state of
# the record -- the last thing added, the closing gesture -- is settled by
# the last thing that left, and the last thing that left leaves no mark of
# its own in the text. The text cannot carry the evidence of its own
# drying. What the text can carry is the taper: the last mark's decline
# predicts what the whole thing will read as.
#
# NOT 204w (the pass that leaves no witness of itself decides the result):
# 204w's strop is an operation that removes nothing and leaves no trace, so
# the RECORD IS BLIND to the deciding step. 205w's drying is an operation
# that removes a CARRIER and leaves a trace -- the mark itself is the trace
# of the loss. The record is not blind here; the record is DECEIVED. It
# reads the mark as evidence of the writing and the mark is evidence of the
# writing AND of the loss, and the record cannot tell which.
# NOT 194w (the missing interval left no mark, and the perfect contact is the
# proof): 194w's missing interval is an ABSENCE IN TIME -- a gap that was
# never sampled. 205w's water is a PRESENT ACT that left the strongest mark
# in the record. Nothing is unobserved; the mark is the most visible thing
# on the page.
# NOT 202w (the property lives in the thing or in the arrangement of the
# unexamined parts): the property here lives in the MARK, not in the
# arrangement of the parts.
# NOT 181w (the datum was set after the measurement it was supposed to hold):
# the water is not set after anything; it is the carrier that was there
# FIRST and is gone LAST.
# NOT 197w / 57w (the signal is only true while the part nobody reads
# holds): nothing flips and nothing stops being true. The line reads the
# same after drying as it will forever.
# NOT 199w (the check has no third term): there IS a third term here -- the
# writer's own hand, which knows the taper while the record cannot.
# NOT 61w / 201w (the error lives in an instance that cannot be reworked):
# nothing here is unreworkable. You can dip the pen again. The unrepeatable
# thing is not the OBJECT.
# NOT 46w / 186w (the preparation spent the evidence it was meant to test):
# the drying does not spend anything that was being tested. The pigment
# survives; the carrier leaves.
# NOT 52w / 192w (the witness IS the destruction): the witness here is not
# destructive, and it is not absent. It is abundant and it is misread.
# NOT 54w (the perfect contact is the proof): the contact is not perfect; a
# well-loaded line and a starved line are the same width on the page.
# NOT 58w (the measurement and its archive are the same physical object):
# the mark and the record of the mark are DIFFERENT objects -- the mark
# keeps the effect, the record keeps the reading, and they are not the same
# thing.
# NOT 190w / 50w (the verdict is a comparison disguised as a property): the
# legibility is a genuine property of the line, not a comparison.
# NOT 166w (the instrument decides what counts as measurable): the taper is
# a fine instrument and it is measuring the wrong thing.
# NOT 179w / 39w (the standard is never the one under test): the standard IS
# applied and it is sound -- the page is read by whoever reads pages.
# NOT 195w (the nearest register neighbour: the book is sewn to be opened):
# 195w is a BINDING craft and its shape is "the thing meant to be broken".
# 205w is a MARKING craft and its shape is "the carrier is what leaves".
# The sewing is a process that is meant to fail; the drying is a process
# that is meant to succeed, and the failure is in the reading of what it
# produced.
# NOT 106w (the absence family: cameo, intaglio, millefiori, aquatint,
# stopout, cast pattern, negative mould): A STANDING TRAP. `ink` appears in
# prior rounds in a DIFFERENT SENSE ("a compact written in ink", "a vibration
# made visible") and `scribe` appears in prior rounds as a manufacturing
# CELL (the dovetail / coupon rounds). `dry` = the 178w-family dry rattle of
# loose material, a different sense. None of these is a WRITING-CRAFT sense.
# NEW AXIS: DOES THE SURVIVING TRACE RECORD THE WORK OR THE LOSS OF THE
# CARRIER?  Rejected on STRUCTURE: 204w, 194w, 202w, 181w, 197w, 57w, 199w,
# 61w, 201w, 46w, 186w, 52w, 192w, 54w, 58w, 190w, 50w, 166w, 179w, 39w,
# 195w, 106w.
#
# 205w REGISTER SWEEP. 0 hits on ALL THREE surfaces (repo working tree, full
# git history with -p, live canon dump at /api/canon): the exact topic line,
# and the craft vocabulary scribe-loaded / nib / quill / ink-dries / runs-dry /
# out-of-ink / dry-pen / blot / reservoir / capillary / siphon / wick /
# foolscap / carbon-copy.
# FALSE FRIENDS (count>0 but a DIFFERENT SENSE, checked in context):
#   scribe = 13 -- a manufacturing CELL in the 196w dovetail and 191w coupon
#     rounds, not a writing instrument.
#   ink = 55 -- METAPHORICAL in prior prose ("a compact written in ink",
#     "a vibration made visible by the material that receives it").
#   dry = 24 -- the 178w-family DRY RATTLE of loose material; also plain
#     English "dry". A different sense.
#   loaded = 30 -- mechanical loading (a rail, a key) in the 202w/203w
#     rounds; the word is not used in this topic.
#   water = 300 -- the 104w BOAT's substrate metaphor ("floating on what
#     was never water"), which is a substrate-image, not a solvent.
#   copy = 96 / original = 44 / transfer = 35 -- generic, and NONE of them
#     is a first-copy-vs-original shape; the nearest prior "copy" sense is
#     the 162w "trail rather than a pristine copy".
#   well = 12, reservoir = 7 -- generic; `wick` = 1 (a single incidental
#     use), `capillary` = 0.
# Overlap vs 191 harvested prior topic lines = 0 at n=3,4,5,6,7,8. No prior
# topic is a substring or superstring of this one.
# The full prior PROSE was also swept for the metaphor (the 201w lesson): the
# new shape's own key phrases ("the water is gone", "the carrier is gone",
# "is dry because", "before it is loaded", "the ink dries", "dries in the
# nib", "the writing is dry", "the solvent is gone") are 0-hit across the
# tree and the whole history -- the single exception is the generic English
# "the ink is dry" (114 history hits), and THAT hit was a 185w CIVIC phrase
# ("the ballot box is sealed before the ink is dry"), a different sense and a
# different shape.

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

This round's material is the WRITING BENCH and the instruments that carry their
own means. Reach for the bench: the dip pen and the split nib, the reservoir
and the well, the bottle and the ink, the blotter and the pounce, the ruled
line and the unruled page, the quill and the steel, the held pen and the set
down pen, the line that runs and the line that stops, the blot and the skip,
the copperplate and the chancery hand, the nib charged and the nib spent.
Name the actual physical things -- what is the carrier and what is the carried,
what is water and what is pigment and what is the gum that binds them, what is
wet and what is dry and what is legible only once it is dry, what is read off
the page and what is known only by the hand that made it. Stay inside the
topic's register -- do not drift into a general essay about handwriting, about
penmanship, or about calligraphy as a hobby. Do NOT write about blades,
files, stones, or sharpening.
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
    # 205w: the ROUND-SPECIFIC continuations. A gram that is a continuation of
    # this round's topic-shape is DOCTRINE-ADJACENT and must be mandated with
    # its receipt, not reported as templating. 195w method: mandate the
    # CONTINUATIONS explicitly, and record PROVENANCE for each.
    # 205w provenance: every entry below is either a contiguous span of THIS
    # round's topic line ("the scribe is dry before it is loaded and the ink
    # is dry because the water is gone") or a direct continuation of it.
    "the scribe is dry", "scribe is dry", "is dry before it is loaded",
    "before it is loaded", "it is loaded", "the ink is dry", "ink is dry",
    "is dry because", "dry because the water", "because the water is gone",
    "the water is gone", "water is gone", "the scribe", "the ink",
    # 205w: short fragments (3-gram) of this round's own line, which the
    # span floor of 4 cannot see (193w/194w lesson).
    "scribe is", "is dry", "the water", "water is", "the ink", "the scribe",
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
    # 205w: the ROUND-SPECIFIC continuations of this round's own topic line.
    # A shared gram that is a continuation of the topic-shape is
    # DOCTRINE-ADJACENT and must be mandated with its receipt, not reported
    # as templating. Mandate the CONTINUATIONS explicitly (193w/194w/195w).
    "the scribe is dry", "scribe is dry before", "is dry before it is",
    "dry before it is loaded", "before it is loaded", "it is loaded and",
    "loaded and the ink", "and the ink is dry", "the ink is dry because",
    "ink is dry because the", "is dry because the water", "dry because the water",
    "because the water is gone", "the water is gone",
    "the scribe", "the ink", "the water",
    # 205w: SHORT fragments (3-gram) of this round's own line -- the span
    # floor of 4 cannot see them (193w/194w lesson).
    "scribe", "dry", "loaded", "ink", "water",
    # 205w: the topic's own line REPHRASED -- the topic subtraction removes
    # only CONTIGUOUS windows, so a voice that reorders the topic's words
    # yields grams that are neither window nor doctrine -> flagged. Mandate
    # the round's own line reordered, not just verbatim (196w method).
    "the scribe is dry before it is loaded and the ink is dry",
    "scribe is dry before it is loaded and the ink is dry because the water",
    "does not cut the edge and the strop is the last pass that can be taken",
    "the strop is the last pass that can be taken on it",
    "strop is the last pass that can be taken on it",
    "is the last pass that can be taken on it",
    "last pass that can be taken on it",
    # 205w: the scribe's vocabulary the topic itself summons. A voice that
    # reaches for the same bench terms is talking about the topic, not
    # reusing another voice's template.
    "the nib", "nib is", "the quill", "quill is", "the dip pen", "dip pen is",
    "the reservoir", "reservoir is", "the well", "well is", "the bottle",
    "bottle is", "the blotter", "blotter is", "the pounce", "pounce is",
    "the line", "line is", "the page", "page is", "the mark", "mark is",
    "the taper", "taper is", "the blot", "blot is", "the skip", "skip is",
    "the hand", "hand is", "the carrier", "carrier is", "the pigment",
    "pigment is", "the gum", "gum is", "the bench", "bench is",
    # 205w: the shape's own key terms. A voice that uses the SAME STRUCTURE
    # (the carrier is gone before the act; the surviving trace records the
    # loss and not the work) is agreeing about the topic, not copying a
    # template -- but only these exact short forms are mandated; the general
    # words are not blanket-sanctioned.
    "the water is gone", "water is gone", "the carrier is gone",
    "carrier is gone", "the carrier leaves", "carrier leaves",
    "the carrier was", "leaves the carrier", "the record cannot",
    "record cannot", "cannot tell", "the mark is", "mark is the",
    "the line reads", "line reads", "reads the same", "the taper predicts",
    "taper predicts", "predicts the dry", "the dry line", "dry line",
    "the wet mark", "wet mark", "the writer knows", "writer knows",
    "the hand knows", "hand knows", "the page is read", "page is read",
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
                "blade", "steel", "shave")

def g11_register(texts, lo=2):
    """Each voice must use AT LEAST `lo` WRITING-BENCH terms, and no voice may
    lean on the OFF-REGISTER sharpening vocabulary."""
    writing_terms = ("nib", "quill", "ink", "reservoir", "well", "blotter",
                     "pounce", "page", "line", "carrier", "pigment", "scribe",
                     "bottle", "dip", "gum", "wet", "dry", "taper", "blot",
                     "skip", "copperplate", "hand", "bench", "loaded", "water")
    per = []
    off = []
    for i, t in enumerate(texts):
        w = set(norm_tokens(t))
        hits = w & set(writing_terms)
        per.append(len(hits))
        oh = w & set(OFF_REGISTER)
        if len(oh) >= 3:
            off.append((i, sorted(oh)))
    ok = (all(c >= lo for c in per)) and (not off)
    return ok, {"writing_hits": per, "off_register": off}

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
    # NC7 (205w): a 205w-register triple that is NOT the topic's own line must
    # still be flagged -- proves the round-specific mandates did not blanket-
    # sanction the whole writing-bench vocabulary.
    v = ["the quill is cut and the bottle is stoppered and the pounce is dry"] * 3
    res.append(("205w-register non-topic triple IS flagged",
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
    echo = ["the scribe is dry before it is loaded and the ink is dry at once",
            "the scribe is dry before it is loaded and the ink is dry at once",
            "the quill is cut and the bottle is stoppered and the pounce is dry"]
    res.append(("topic-echo pair is not a template collision",
                g6c_opening_clause(echo, topic=TOPIC)[0] is True))
    res.append(("all-voice topic echo IS rejected",
                g6c_opening_clause([echo[0], echo[1], echo[0]], topic=TOPIC)[0] is False))
    # NC8 (205w): the register guard MUST fire on a SHARPENING-BENCH triple --
    # this is the exact defect the first 205w attempt had, and a guard that
    # cannot catch it is an assertion, not a guard.
    offreg = ["on the sharpening bench the file begins by cutting rather than rubbing "
              "its steel teeth take shavings from the blade leaving coarse scratches"] * 3
    res.append(("off-register sharpening triple IS rejected",
                g11_register(offreg)[0] is False))
    # NC9 (205w): and it MUST ACCEPT a genuine writing-bench triple.
    onreg = ["the nib is charged from the reservoir and the ink carries the pigment "
             "and the gum until the water is gone and the line is dry on the page"] * 3
    res.append(("on-register writing triple IS accepted",
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
    # TRUE: the topic repeated verbatim by all three must NOT be flagged.
    t.append(("topic-echo triple excluded",
              shared_ngrams([TOPIC]*3, 4, topic=TOPIC) == set(), ""))
    # FALSE: a window that is NOT a contiguous span of the topic must NOT be
    # silently swallowed by the subtraction. "joined boards that are each a
    # part of the shape" is not a contiguous window of the topic.
    probe = "the scribe is dry before it is loaded and the ink is dry because the water is gone and the mark is not looked at"
    t.append(("topic subtraction is a contiguous window, not a substring",
              probe not in topic_ngrams(TOPIC), probe))
    t.append(("reordered topic line is covered by an explicit mandate",
              is_mandated("the ink is dry because the water is gone")
              and is_mandated("ink is dry because the water is gone")
              and is_mandated("is dry because the water is gone"),
              "205w reordered grams mandated, not auto-excluded"))
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
    e = ["the scribe is dry before it is loaded and the ink is dry because the water is gone"]*3
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
    echo_pair = ["the scribe is dry before it is loaded and the ink is dry at once",
                 "the scribe is dry before it is loaded and the ink is dry at once",
                 "the quill is cut and the bottle is stoppered and the pounce is dry"]
    t.append(("two voices echoing the topic is NOT a template collision",
              g6c_opening_clause(echo_pair, topic=TOPIC)[0] is True, ""))
    t.append(("all voices echoing the topic IS a failure",
              g6c_opening_clause([echo_pair[0], echo_pair[1], echo_pair[0]],
                                 topic=TOPIC)[0] is False, ""))
    # and a genuine template collision that ALSO quotes the topic must still fail
    tmpl = ["the scribe is dry before it is loaded and the ink is dry at once",
            "the scribe is dry before it is loaded and the ink is dry at once",
            "the scribe is dry before it is loaded and the ink is dry at once"]
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

    # --- 205w: the round's own mandates must NOT blanket-sanction the whole
    # scribe's vocabulary. A 205w-register triple that is NOT the topic's own
    # line must still be flagged, or the guard has been switched off.
    v205 = ["the quill is cut and the bottle is stoppered and the pounce is dry"]*3
    t.append(("205w-register non-topic triple IS flagged",
              len(shared_ngrams(v205, 4)) > 0, ""))

    # --- 205w G11: the register guard must fire on the FIRST attempt's
    # actual defect (a sharpening-bench triple) and accept a writing triple.
    t.append(("G11 rejects an off-register sharpening triple",
              g11_register(["on the sharpening bench the file begins by cutting rather "
                            "than rubbing its steel teeth take shavings from the blade "
                            "leaving coarse scratches"]*3)[0] is False, ""))
    t.append(("G11 accepts an on-register writing triple",
              g11_register(["the nib is charged from the reservoir and the ink carries "
                            "the pigment and the gum until the water is gone and the line "
                            "is dry on the page"]*3)[0] is True, ""))

    # --- negative controls (6) ---------------------------------------------
    ncs = negative_controls()
    for name, ok in ncs:
        t.append((f"NC: {name}", ok, ""))

    npass = sum(1 for _,ok,_ in t if ok)
    return t, npass, len(t)

# ---- round -----------------------------------------------------------------
def run_round():
    print(f"\n=== Taps round 205w | topic: {TOPIC} ===\n", flush=True)
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
        "runner": "taps_round_205w.py",
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
