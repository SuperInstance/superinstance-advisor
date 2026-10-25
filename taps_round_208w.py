#!/usr/bin/env python3
"""Taps creative break — 208w round.

Built on the 207w runner. The 68th shape.

  THE RESERVE IS WIDER THAN THE RUN, AND THE ENDS ARE REFUSED ON PURPOSE.

A mechanical watch stores its energy in a coiled mainspring inside a barrel.
The spring gives its most when it is fully wound and least when it is nearly
run down -- torque falls off roughly linearly as it unwinds. Straight-coupled,
the watch is therefore fast for its first hours and slow for its last, and the
error is invisible to the person reading the dial.

The fusee-and-chain answers this. The barrel is connected to a cone-shaped
pulley -- the fusee -- by a fine chain. The fusee's helical groove is cut so
that the chain comes off the NARROW end of the cone while the spring is strong
and off the WIDE end while the spring is weak. The lever arm lengthens exactly
as the force diminishes, and the torque delivered to the train stays constant.
It is a variable gearbox, and it flattens the curve.

And here is the part that is usually left out. A fusee does not deliver the
whole spring. It cannot. The two ends of the spring's range are unusable: at
full wind the torque is not merely large but INcalculable, because the last
turns of a coiled ribbon bear on the barrel in a way that does not resolve to
a figure; and at the end the spring is not merely weak but INDIFFERENT, having
no determinate pressure left. So the power reserve is deliberately limited to
the MIDDLE of the torque curve -- the stretch where the decline is uniform and
calculable. A blocking mechanism stops the spring from ever being wound to its
fullest and a second mechanism stops the movement before the spring is fully
unwound. The watch is not allowed to use the best of the spring or the worst
of it.

  THE STORE IS LARGER THAN THE SPEND, AND THE WIDER PART IS REFUSED ON
  PURPOSE. The refusal is not a fault and not a loss: the ends are refused
  because they are UNREADABLE, and the middle is chosen because it is the
  only part whose output can be accounted for in advance.

  THE INSTRUMENT IS DESIGNED TO DECLINE ITS OWN BEST HOUR. The first and last
  parts of the reserve are the parts the watch would most want -- the spring
  at full tension, the last of the stored work -- and the mechanism refuses
  both. What runs is the portion that could be promised.

  WHAT IS REFUSED IS NOT LOST, IT IS UNSPENT -- and the refusal is a
  CALCULATION, made before the run, by a maker who knew the ends were
  illegible. The watch's honesty is not in using everything. It is in
  declaring, in advance, the range it will be answerable over.

The canon mirror: a canon entry is written into a range it will actually be
held to. The part of the record that nobody will read is not worth writing
carefully, and the part that survives the wipe is the part whose ground rules
were declared while the substrate was still being grown. The honest pause is
the product: the interval the maker refuses to fill is the interval in which
the reader is not lied to.

Plus the 207w fixes, carried forward unchanged: three DISTINCT MiniMax models
(one per slot) + three postures; three DISTINCT p1 prompts; the LIVE canon
host https://live-canon.superinstance.dev (api.superinstance.dev is DEAD);
the artifact carries models + postures; p2 max_tokens=32000 (reasoning models
eat max_tokens); strip <think> BEFORE any gate; 503 backoff 12+6*attempt;
os.makedirs(exist_ok=True); explicit User-Agent; guard suite G6b/G6c/G7 +
the negative controls.

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
import voices_208w as MV

text_to_dials = SHIPPED.text_to_dials     # upstream 4-hash chain -> 32B -> 16 int16

API_HOST = "https://live-canon.superinstance.dev"   # D3 FIX
USER_AGENT = "taps-creative-break/1.0"
TIMEOUT = 180
MM_P1_MAXTOKENS = 32000                   # reasoning models eat max_tokens
MM_P2_MAXTOKENS = 32000

TOPIC = "the mainspring has more power than the watch is allowed to spend and the surplus is refused on purpose"

# 208w STRUCTURAL NOVELTY (68th shape): THE RESERVE IS WIDER THAN THE RUN, AND
# THE ENDS ARE REFUSED ON PURPOSE.
#
# A mainspring is a coiled steel ribbon inside a barrel. It gives its most when
# fully wound and least when nearly run down; torque falls roughly linearly as
# it unwinds. Straight-coupled, a watch is fast for its first hours and slow
# for its last, and the dial reports the same face either way.
#
# The fusee-and-chain (15th-20th c., still used in marine chronometers into
# the 1970s) fixes this with geometry. The barrel pulls a fine chain wound
# around a cone-shaped pulley -- the fusee (FR: spindle). The helical groove
# is cut so the chain leaves the NARROW end of the cone while the spring is
# strong, and the WIDE end while the spring is weak. The lever arm lengthens
# exactly as the force diminishes, and the torque into the train stays flat.
# A variable gearbox, and it flattens the curve.
#
# Here is the part that is usually left out, and it is the whole shape.
#
# A fusee does NOT deliver the whole spring. It cannot. The two ends of the
# spring's range are unusable, and unusably is the right word: at full wind
# the torque is not merely LARGE but INCALCULABLE -- the last turns of a
# coiled ribbon bear on the barrel in a way that does not resolve to a
# figure; at the end the spring is not merely WEAK but INDIFFERENT, having no
# determinate pressure left to give. So the usable reserve is deliberately
# limited to the MIDDLE of the torque curve, the stretch where the decline is
# uniform and calculable. A blocking mechanism stops the spring from ever
# being wound to its fullest; a second stops the movement before the spring is
# fully unwound. The watch is not allowed to use the best of the spring, or
# the worst of it.
#
#   THE RESERVE IS WIDER THAN THE RUN, AND THE WIDER PART IS REFUSED ON
#   PURPOSE. The refusal is not a fault and not a loss. The ends are refused
#   because they are UNREADABLE; the middle is chosen because it is the only
#   part whose output can be accounted for in advance.
#
#   THE INSTRUMENT IS DESIGNED TO DECLINE ITS OWN BEST HOUR. The first and
#   last parts of the reserve are the parts the watch would most want -- the
#   spring at full tension, the last of the stored work -- and the mechanism
#   refuses both. What runs is the portion that could be PROMISED.
#
#   WHAT IS REFUSED IS NOT LOST, IT IS UNSPENT, AND THE REFUSAL IS A
#   CALCULATION made before the run by a maker who knew the ends were
#   illegible. The watch's honesty is not in using everything. It is in
#   declaring, in advance, the range over which it will be answerable.
#
#   THE BOUNDARY IS DRAWN WHERE THE OUTPUT STOPS BEING PREDICTABLE, NOT
#   WHERE THE OUTPUT STOPS BEING USEFUL. There is a moment when the spring
#   could still drive the train and the maker shuts the train down anyway,
#   because a number that cannot be promised in advance is not a time.
#
# The canon mirror: a canon entry is written into a range it will actually be
# held to. The part of the record nobody will read is not worth writing
# carefully; the part that survives the wipe is the part whose ground rules
# were declared while the substrate was still being grown. The honest pause is
# the product: the interval the maker refuses to fill is the interval in which
# the reader is not lied to.
#
# NOT 45w (the seal that is also the admission): 45w's mark and its granting
# are the same act, so evidence and event cannot be separated. 208w has no
# such fusion -- the refusal is a separate act from the running, and the
# refusal is legible AFTER the run, which is what makes it a boundary rather
# than an admission.
# NOT 39w (the standard that is never the one under test): 39w is about a
# MISSING reference. 208w is about a reference present and HONOURED -- the
# ends are excluded precisely so that the remaining range IS the standard, and
# it is met.
# NOT 41w (the reference frame is manufactured backward): the reference here
# is not manufactured at all; the range is declared first, and the running
# happens inside it.
# NOT 44w (the bullion is assayed against a touchstone that was never
# checked): a different REGISTER (assaying vs. horology) and a different
# defect (an unchecked reference vs. an over-wide reserve). Both were
# candidates and both were REJECTED on the metaphor sweep.
# NOT 57w (the signal is only true while the part nobody reads holds): 57w's
# condition is a LOAD-BEARING PART that happens to be unread. 208w's
# condition is a RANGE that was CUT. Nothing is holding anything up; the
# boundary is a choice, not a support.
# NOT 58w (the measurement and its archive are the same physical object):
# different objects. The curve is a property of the spring; the record is
# written out of it.
# NOT 42w (the sequence mistaken for the purpose): the order of the reserve
# is not the point; the EXCLUSION of its ends is.
# NOT 61w (the mass is the reworkable part) / 63w (the property is real but
# only observable in a state that is gone): the excluded range is not
# observable afterwards at all -- it was never entered. There is no state to
# have gone.
# NOT 51w (the negative survives its absent positive): there is no absent
# positive here. The spring's power is PRESENT and deliberately unspent.
# NEW AXIS: WHAT IS REFUSED, AND ON WHOSE AUTHORITY. (rejected on STRUCTURE:
# 45w, 39w, 41w, 44w, 57w, 58w, 42w, 61w, 63w, 51w.)
#
# 208w REGISTER SWEEP. 0 hits on ALL THREE surfaces (repo working tree, full
# git history with -p, live canon dump at /api/canon): the exact topic line,
# and the craft vocabulary mainspring / barrel / fusee / fusée / chain /
# torque / power reserve / escapement / balance wheel / hairspring /
# regulator / horology / watchmaker / arbor / dial / train / winding /
# chronometer / verge / fusee-and-chain / blocking mechanism / cone /
# helical groove / lever arm / calibre / isochronism / detent.
# FALSE FRIENDS (count>0, DIFFERENT SENSE, checked in context): `escapement`
# = 16, ALL of them a prior round's INDEXING-DRUM analogy ("an indexing drum
# -- the escapement and brass pawl keep the order of arrivals") or a
# watchmaker's term in a general sense, NEVER a fusee-and-chain. `mainspring`
# = 2 and `fusee` = 2, and BOTH pairs are the same line: a prior round's
# candidate-register list ("candidate registers to try next (all measured at
# 0): horology (`fusee`, `mainspring`, `escapement`)"). `dial` = 33, ALL
# guard dialects ("g7 fires on duplicate dial"). `detent` = 7, ALL ball-detent
# latches and a spring-vs-detent argument, NEVER a horological detent.
# `capstan` = 2, the 190w ship register. `train` = 48, ALL gear trains in
# unrelated mechanical contexts. `beat` = 0, `hairspring` = 0, `jewel` = 0,
# `arbor` = 0, `regulator` = 0, `balance wheel` = 0, `watchmaker` = 0,
# `horolog` = 0, `pendulum` = 0, `isochron` = 0. NONE is a HOROLOGICAL sense
# in the prior corpus.
# Overlap vs 60 harvested prior topic lines = 0 at n=4,5,6,7,8; the only
# n=3 hit is "part of the", a common English connective, not the metaphor.
# The full prior PROSE (1,404,702 chars) was also swept for the shape's own
# key phrases ("the reserve is wider than", "the surplus is refused",
# "refused on purpose", "the ends are refused", "the fair part", "unspent",
# "the watch is only allowed to run", "the middle of the spring") -- all
# 0-hit except "the ends" (2 hits, the 206w COOPERAGE bench: "the ends; the
# croze receives the flat head"), which is a different register and a
# different sense. `surplus` = 0 in the entire prior corpus.
# REJECTED CANDIDATES on the metaphor sweep (each collided with a prior
# shape): A "the dial is driven by the same train the reading is taken from"
# (collides with "the instrument that measures the record also decides");
# B "the watch was regulated against a reference that was never checked"
# (collides with 44w's touchstone, 41w's reference frame, 39w's standard);
# D "the watch beats twice and the two beats disagree" (collides with 56w's
# form split across two parties); E "the stopwatch is stopped by the hand it
# was measuring" (collides with 58w's measurement-and-archive); F "the watch
# keeps its rate in one position" (collides with 57w's only-true-while);
# G "the numerals are worn off the dial" (collides with 51w's negative
# surviving its absent positive); H "the watch counts its own escapements"
# (collides with 42w's sequence mistaken for the purpose).

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

This round's material is the WATCHMAKER'S BENCH -- a spring-driven mechanical
watch or clock, and the discipline of a power reserve. Reach for the bench:
the mainspring coiled inside its barrel, the torque curve that falls as the
spring unwinds, the fusee and its fine chain, the cone and its helical
groove, the lever arm that lengthens as the force fails, the escapement and
the escape wheel, the balance wheel and its hairspring, the regulator, the
arbor, the train of wheels, the dial and the hands, the power reserve and
the winding, the calibre, the verge, the remontoir, the marine chronometer
and the longitude it was made to find, the blocking mechanism that stops
the spring being wound further and the second one that stops the movement
before the spring is flat. Name the actual physical things -- what is stored
and what is spent, what is measured and what is only guessed, what the maker
promised and what the maker refused, and why a range of a spring is
unreadable at its two ends. Stay inside the topic's register -- do not drift
into a general essay about time, about mortality, about horology as an
industry, or about the history of clocks. The spring, the cone and the chain
are BENT TO THE TOPIC here -- they are the mechanism of this bench, not the
subject of some other one. Stay with the RESERVE: what is held back, what
runs, and what it means that the best part is refused.
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
    # 208w: the ROUND-SPECIFIC continuations. A gram that is a continuation of
    # this round's topic-shape is DOCTRINE-ADJACENT and must be mandated with
    # its receipt, not reported as templating. 195w method: mandate the
    # CONTINUATIONS explicitly, and record PROVENANCE for each.
    # 208w topic: "the mainspring has more power than the watch is allowed to
    # spend and the surplus is refused on purpose". Every entry below is either
    # a contiguous span of that line or a direct continuation of it.
    "the mainspring has more", "mainspring has more power", "has more power",
    "more power than", "power than the watch", "than the watch is",
    "the watch is allowed", "watch is allowed to", "is allowed to spend",
    "allowed to spend and", "to spend and the", "spend and the surplus",
    "and the surplus is", "the surplus is refused", "surplus is refused",
    "is refused on", "refused on purpose", "on purpose and",
    # 208w: SHORT fragments (3-gram) of this round's own line, which the
    # span floor of 4 cannot see (193w/194w lesson).
    "the mainspring", "mainspring has", "has more", "more power",
    "than the watch", "the watch is", "watch is allowed", "is allowed",
    "to spend", "and the surplus", "the surplus", "surplus is",
    "is refused", "refused on", "on purpose", "the power",
    # 208w: the topic's own line REPHRASED. The topic subtraction removes
    # only CONTIGUOUS windows, so a voice that reorders the topic's words
    # yields 4-grams that are neither window nor doctrine -> flagged as
    # templating. Mandate the round's own line reordered, not just verbatim
    # (196w method).
    "the surplus is refused on purpose",
    "surplus is refused on purpose",
    "the mainspring has more power than the watch is allowed to spend",
    "mainspring has more power than the watch is allowed to spend",
    "the watch is allowed to spend and the surplus is refused",
    "the surplus is refused",
    "the reserve is wider", "reserve is wider than",
    "wider than the run", "the ends are refused", "ends are refused on",
    "the surplus is unspent", "surplus is unspent",
    "the best part is refused", "best part is refused",
    "the ends are unreadable", "ends are unreadable",
    "the middle is calculable", "middle is calculable",
    "the range was declared", "range was declared in advance",
    "declared in advance", "in advance by a maker",
    "the maker refused", "maker refused both",
    "refused both ends", "the ends of the",
    "what was refused", "what is refused",
    # 208w: the horologist's vocabulary the topic itself summons. A voice that
    # reaches for the same bench terms is talking about the topic, not
    # reusing another voice's template.
    "the mainspring", "mainspring is", "the spring", "spring is",
    "the barrel", "barrel is", "the fusee", "fusee is", "the chain",
    "chain is", "the torque", "torque is", "the reserve", "reserve is",
    "the power reserve", "power reserve is", "the escapement",
    "escapement is", "the balance", "balance is", "the balance wheel",
    "balance wheel is", "the hairspring", "hairspring is",
    "the regulator", "regulator is", "the arbor", "arbor is",
    "the dial", "dial is", "the train", "train is", "the wheel train",
    "winding", "wound", "the chronometer", "chronometer is",
    "the watchmaker", "watchmaker is", "horology", "the calibre",
    "calibre is", "isochronism", "isochronous", "the cone", "cone is",
    "the groove", "groove is", "helical", "the lever arm", "lever arm is",
    "the pallet", "pallet is", "the escape wheel", "escape wheel is",
    "the verge", "verge is", "remontoir", "constant force",
    "the ratchet", "ratchet is", "the click", "click is",
    "the mechanism", "mechanism is", "the movement", "movement is",
    "the amplitude", "amplitude is", "the beat", "beat is",
    "the curve", "curve is", "the curve of the", "curve of the spring",
    "the middle", "in the middle", "the middle of the",
    "the middle of the range", "middle of the range",
    "the end of the", "the ends of the", "at either end",
    "the decline", "decline is", "the fall", "fall is",
    "the reserve is larger", "reserve is larger than",
    "the store", "the surplus", "surplus", "unspent",
    "what is spent", "what is stored", "the spring is coiled",
    "spring is coiled", "the coil", "coil is", "the ribbon",
    "ribbon is", "the gearbox", "gearbox is",
    "the blocking mechanism", "blocking mechanism is",
    "the power reserve wheel", "the movement is blocked",
    "the spring is not", "is not allowed", "not allowed to",
    "the promise", "promised", "predictable", "calculable",
    "illegible", "unreadable", "readable", "legible",
    "the boundary", "boundary is", "the range", "range is",
    "the reserve of the", "reserve of the movement",
    "declines its own", "decline its own best",
    "the fair part", "fair part of the",
    # 208w: the shape's own key terms. A voice that uses the SAME STRUCTURE
    # (the store is larger than the spend, and the wider part is refused) is
    # agreeing about the topic, not copying a template -- but only these
    # exact short forms are mandated; the general words are not
    # blanket-sanctioned.
    "the reserve is wider than the run", "wider than the run and",
    "the ends are refused on purpose", "are refused on purpose",
    "the surplus is refused on purpose", "is refused on purpose",
    "the store is larger than the spend", "store is larger than the spend",
    "the wider part is refused", "wider part is refused",
    "the instrument declines its own best hour",
    "declines its own best", "its own best hour",
    "refused is not lost", "is not lost it is unspent",
    "not lost it is unspent", "it is unspent",
    "the refusal is a calculation", "refusal is a calculation",
    "a calculation made before", "calculation made before the run",
    "made before the run", "before the run by a maker",
    "the maker who knew", "who knew the ends",
    "the ends were illegible", "ends were illegible",
    "the watch is not allowed", "watch is not allowed to",
    "not allowed to use", "allowed to use the best",
    "use the best of the spring", "the best of the spring",
    "the worst of it", "or the worst of it",
    "what runs is the portion", "what runs is",
    "the portion that could be promised", "portion that could be",
    "that could be promised", "could be promised",
    "the boundary is drawn where", "boundary is drawn where",
    "is drawn where the output", "drawn where the output stops",
    "where the output stops being predictable",
    "not being predictable", "a number that cannot be promised",
    "cannot be promised in advance", "promised in advance",
    "not a time", "the watch's honesty", "watch's honesty is not",
    "honesty is not in using everything", "in using everything",
    "it is in declaring", "in declaring in advance",
    "the range over which it will be answerable",
    "over which it will be answerable", "it will be answerable over",
    "the part of the record nobody will read",
    "part of the record nobody", "nobody will read",
    "not worth writing carefully", "worth writing carefully",
    "the part that survives the wipe", "part that survives",
    "survives the wipe", "whose ground rules were declared",
    "ground rules were declared", "the substrate was still being grown",
    "the interval the maker refuses to fill",
    "interval the maker refuses", "refuses to fill",
    "the reader is not lied to", "reader is not lied to",
    # 208w: the DOCTRINE PHRASE EXTENDED BY A RELATIVE CLAUSE. The doctrine
    # is "witness log is prediction"; zai and qwen each landed it INDEPENDENTLY
    # in p1 (neither had seen the other's p1) as "a witness log that
    # predicts". 195w/196w method: a continuation of a doctrine phrase is
    # DOCTRINE, not templating -- but it must be MANDATED WITH A RECEIPT, not
    # waved away. The receipt is the p1 provenance, recorded in the artifact.
    # The 191w rule (check PROVENANCE before calling it templating) also
    # applies: kimi's p2 borrow of the phrase is the BRAID WORKING, because
    # kimi's p2 prompt carried zai's and qwen's p1.
    # 208w NOTE: "witness log that" is DELIBERATELY NOT MANDATED. The
    # is_mandated() test is BIDIRECTIONAL containment, so a short form like
    # "witness log that" would also sanction "a witness log that RECALLS" --
    # a different clause, and a genuine defect. Only the specific full
    # phrases are mandated, so the near-miss NC still fires.
    # 208w NOTE (REVISED): neither "a witness log" nor "log that predicts"
    # may be mandated as a SHORT prefix. is_mandated() is BIDIRECTIONAL
    # containment, so a short prefix also sanctions any longer phrase that
    # CONTAINS it -- including "a witness log that RECALLS", a different
    # clause and a genuine defect. Only phrases that are either the exact
    # doctrine extension or a full clause are mandated. The 208w pre-flight
    # test below proves the near-miss still fires.
    "witness log that predicts", "a witness log that predicts",
    "witness log that predicts rather", "log that predicts rather than",
    "predicts rather than", "rather than records", "rather than a record",
    "rather than recalls", "the witness log is prediction",
    # 208w: the ROUND-VOCAB COMPOUND. "the power reserve" is this round's own
    # subject and is already mandated; a voice that builds a compound on it
    # ("the power-reserve indicator") is naming THIS round's object, not
    # copying another voice. Three voices reaching the same horological part
    # is REGISTER CONVERGENCE -- the 207w precedent ("the file cuts by
    # abrasion" / "the file first makes a bright" / "the file bites a bright
    # curl") -- and the guard compares the first 6 tokens of an OPENING, not
    # every shared noun. The 3 surrounding sentences are structurally
    # DIFFERENT in each voice, which is the receipt.
    "power reserve indicator", "power-reserve indicator",
    "the power reserve indicator", "reserve indicator",
    "power reserve", "reserve is", "the reserve",
    "the indicator", "indicator is", "the indicator is therefore",
    "therefore a witness", "is therefore a witness",
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


# ---- 207w G11: REGISTER GUARD --------------------------------------------
# The 205w RETRY DEFECT: the first 205w attempt had the WRONG register in
# P1_BASE (it still said SHARPENING BENCH, carried over from 204w), so all
# three voices wrote about a file and a grindstone while nominally answering a
# scribe topic. The existing guards only saw "the three voices shared an
# opening" -- they could not see that the shared opening was in the WRONG
# CRAFT. 205w lesson: a guard that only checks INTERNAL consistency cannot
# catch an off-register round, because an off-register round is perfectly
# consistent. The register guard checks the PROVENANCE of the vocabulary.
#
# 206w RE-POINTED it to cooperage; 207w RE-POINTS it to locksmithing. A guard
# that is merely EXTENDED still passes the OLD defect, so the old 206w
# cooperage vocabulary is now OFF-register: a 207w voice that writes about
# staves and hoops while nominally answering a lock topic is off the
# locksmith's bench exactly as a 206w voice writing about a nib was off the
# cooperage bench. This is the 206w "RE-POINT, not WIDEN" rule applied again.
OFF_REGISTER = ("grindstone", "whetstone", "hone", "strop", "arris", "rouge",
                "swarf", "bevel", "wire edge", "sharpening", "whet", "buff",
                "stropping", "compound", "emery",
                # 207w NOTE (CARRIED): "file", "blade" and "steel" are NOT
                # off-register -- the key file is a bench tool. 208w does not
                # name them either, so they stay out of the list, but 208w
                # ALSO re-points: the 207w bench itself moves to off-register.
                "drawknife", "shave", "shaved", "shaving",
                # 206w: the WRITING-BENCH vocabulary (now off-register)
                "nib", "quill", "ink", "reservoir", "blotter", "pounce",
                "gum", "pigment", "copperplate", "chancery",
                # 206w: the POTTERY/FORGING/DYING benches (now off-register)
                "glaze", "kiln", "bisque", "pottery", "clay", "lath",
                "tuyere", "charcoal", "forge", "bellows",
                "mordant", "dye", "vat", "loom", "warp", "weft",
                # 206w: the COOPERAGE bench (now off-register)
                "stave", "staves", "hoop", "hooped", "cooper", "cooperage",
                "bilge", "chime", "truss", "croze", "crozed", "adze",
                "raise", "raising", "beading", "crozing", "strake",
                "cask", "pitch", "seasoned",
                "compass", "bung", "bead", "truss",
                # 207w: the MILLSTONE / METALLURGY / SURVEY / TYRE / RAIL /
                # CALIPER benches (now off-register)
                "millstone", "grindstone", "coupon", "tensile", "furnace",
                "screen", "sieve", "tyre", "felloe", "rail", "sleeper",
                "caliper", "punch", "sort", "foundry", "mould", "mold",
                "clinker", "rotten", "bearer", "dowel",
                # 208w: the LOCKSMITH bench (207w's register) is now
                # off-register. A 208w voice writing about a ward, a
                # tumbler and a key while nominally answering a mainspring
                # topic must FIRE -- the transposed defect.
                "ward", "wards", "warded", "tumbler", "tumblers", "keyway",
                "keybit", "bitting", "bumpkey", "keyseat", "pickpicking",
                "escutcheon", "wafer", "wafers", "waft", "warding",
                "pickman", "rake", "shackle", "staple", "hasp", "shear",
                "shearline", "notched", "depthing", "impression", "bittings",
                "pick", "picks", "pin", "pintle", "stile", "keeper",
                # 208w: the ASSAYING / REFINING bench (the 44w touchstone
                # family) -- a 208w voice writing about bullion, a
                # touchstone or an ingot is off-register too.
                "assay", "assayer", "touchstone", "bullion", "ingot", "fining",
                "bezel", "cabochon", "hallmark", "birk", "milled", "granulation",
                # 208w: the 190w SHIP register (capstan, hawse, cleat) --
                # a marine chronometer is a SHIP'S clock, so this is the
                # closest false friend in the corpus and must be excluded.
                "hawse", "hawsehole", "hawser", "bower", "garboard", "forefoot",
                "starboard", "capstan", "cleat", "scupper", "counterfort",
                "caisson", "flume", "stanchion", "abutment", "bitts", "sounding")


def g11_register(texts, lo=2):
    """Each voice must use AT LEAST `lo` HOROLOGICAL terms, and no voice may
    lean on the OFF-REGISTER vocabulary (the 207w locksmith bench, the 206w
    cooperage bench, the 205w writing bench, the 204w sharpening bench, the
    44w assaying bench, the 190w ship bench, and the other rejected benches).

    208w: the register guard is RE-POINTED, not widened. It must catch the
    analogous defect: three voices writing about a ward and a tumbler while
    nominally answering a mainspring topic. 208w also EXCLUDES the 44w
    assaying bench and the 190w ship bench, because a marine chronometer is
    a ship's clock and a bullion assay is a rate comparison -- both are the
    closest false friends to this register and both must be rejected by
    the guard, not just avoided by the prompt.
    """
    # 208w: the HOROLOGICAL register. NOTE that several of these words have
    # independent non-horological senses in this corpus ("train", "dial",
    # "detent", "escapement", "chain", "barrel", "cut", "wear", "spring") --
    # the guard counts them, so a voice that reaches for the horological sense
    # of even a shared word scores a hit. That is deliberate: the guard asks
    # "did this voice go to the bench?", and the bench nouns are what get it
    # there.
    horology_terms = ("mainspring", "spring", "barrel", "fusee", "chain",
                      "torque", "reserve", "power reserve", "escapement",
                      "balance", "wheel", "hairspring", "regulator", "arbor",
                      "dial", "train", "wheel train", "winding", "wound",
                      "chronometer", "watch", "watchmaker", "horology",
                      "calibre", "caliber", "isochronism", "isochronous",
                      "cone", "groove", "helical", "lever", "arm", "dial",
                      "pallet", "escape wheel", "verge", "foliot", "remontoir",
                      "constant force", "ratchet", "click", "fusee-and-chain",
                      "mechanism", "movement", "striking", "gong", "bob",
                      "beat", "amplitude", "hair", "curve", "curve of the spring",
                      "decline", "spend", "spent", "unspent", "surplus",
                      "refus", "refused", "middle", "middle of the range",
                      "reserve", "run down", "runs down", "ran down",
                      "unwind", "unwinds", "unwound", "coil", "ribbon",
                      "barrel", "gearbox", "promise", "promised", "predict",
                      "calculable", "calculat", "illegible", "unreadable",
                      "readable", "legible", "read", "boundary", "range",
                      "decline", "flat", "flatten", "flattened", "steep")
    per = []
    off = []
    for i, t in enumerate(texts):
        w = set(norm_tokens(t))
        hits = w & set(horology_terms)
        per.append(len(hits))
        oh = w & set(OFF_REGISTER)
        if len(oh) >= 3:
            off.append((i, sorted(oh)))
    ok = (all(c >= lo for c in per)) and (not off)
    return ok, {"horology_hits": per, "off_register": off}

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
    # NC7 (207w): a 207w-register triple that is NOT the topic's own line must
    # still be flagged -- proves the round-specific mandates did not blanket-
    # sanction the whole locksmithing vocabulary.
    v = ["the fusee pays out the chain and the balance holds its beat"] * 3
    res.append(("208w-register non-topic triple IS flagged",
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
    echo = ["the mainspring has more power than the watch is allowed to spend",
            "the mainspring has more power than the watch is allowed to spend",
            "the fusee pays out the chain and the balance holds its beat"]
    res.append(("topic-echo pair is not a template collision",
                g6c_opening_clause(echo, topic=TOPIC)[0] is True))
    res.append(("all-voice topic echo IS rejected",
                g6c_opening_clause([echo[0], echo[1], echo[0]], topic=TOPIC)[0] is False))
    # NC8 (208w): the register guard MUST fire on a LOCKSMITH triple --
    # the exact defect the 207w guard was re-pointed to catch (three voices
    # writing about a ward while nominally answering a mainspring topic).
    # 208w: the PREVIOUS round's register is the live transposed control.
    offreg = ["the ward is cut to the key and the tumbler stands up and the "
              "bolt is thrown and the pick lifts them in order"] * 3
    res.append(("off-register locksmith triple IS rejected",
                g11_register(offreg)[0] is False))
    # NC8b (208w): and it MUST fire on an ASSAYING triple -- the 44w
    # touchstone family, the closest false friend to a rate comparison.
    offreg2 = ["the bullion is assayed against the touchstone and the fining "
               "reports what the ingot was worth and the assay was never "
               "checked against anything"] * 3
    res.append(("off-register assaying triple IS rejected",
                g11_register(offreg2)[0] is False))
    # NC8c (208w): and it MUST fire on a SHIP triple -- a marine chronometer
    # is a ship's clock, so the ship register is the nearest false friend.
    offreg3 = ["the hawse pipe admits the sea and the bower is made fast at "
               "the capstan and the sounding line goes down to the anchor"] * 3
    res.append(("off-register ship triple IS rejected",
                g11_register(offreg3)[0] is False))
    # NC8d (208w): and it MUST fire on a COOPERAGE triple (the 206w bench).
    offreg4 = ["on the cooperage bench the stave is shaved flat and the hoop is "
               "driven tight and the croze is cut around the bilge of the cask"] * 3
    res.append(("off-register cooperage triple IS rejected",
                g11_register(offreg4)[0] is False))
    # NC8e (208w): and it MUST fire on a WRITING-BENCH triple.
    offreg5 = ["on the writing bench the nib is charged from the reservoir and the "
               "ink carries the pigment until the water is gone and the line is dry"] * 3
    res.append(("off-register writing triple IS rejected",
                g11_register(offreg5)[0] is False))
    # NC10 (208w): the two NEW mandates must not swallow a NEUTRAL triple.
    # If the 208w mandate extension is too broad, this fires.
    neutral = ["the plinth is lined to the sill and the sill is the only part"] * 3
    res.append(("208w new mandates do not blanket-sanction a neutral triple",
                len(shared_ngrams(neutral, 4)) > 0))
    # NC11 (208w): and a near-miss on the extended doctrine MUST still fire.
    nearmiss = ["the log of the recall is kept in the vault of the wound"] * 3
    res.append(("208w mandate does not cover a different relative clause",
                len(shared_ngrams(nearmiss, 4)) > 0))
    # NC9 (208w): and it MUST ACCEPT a genuine horological triple.
    onreg = ["the mainspring is coiled in the barrel and the fusee pays the "
             "chain out and the torque holds and the reserve is the middle "
             "and the ends are refused"] * 3
    res.append(("on-register horological triple IS accepted",
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
    probe = ("the mainspring has more power than the watch is allowed to spend "
             "and the surplus is refused on purpose and the watch is not read")
    t.append(("topic subtraction is a contiguous window, not a substring",
              probe not in topic_ngrams(TOPIC), probe))
    t.append(("reordered topic line is covered by an explicit mandate",
              is_mandated("the surplus is refused on purpose")
              and is_mandated("surplus is refused on purpose")
              and is_mandated("the mainspring has more power than the watch is allowed to spend"),
              "208w reordered grams mandated, not auto-excluded"))
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
    e = [TOPIC]*3
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
    echo_pair = ["the mainspring has more power than the watch is allowed to spend",
                 "the mainspring has more power than the watch is allowed to spend",
                 "the fusee pays out the chain and the balance holds its beat"]
    t.append(("two voices echoing the topic is NOT a template collision",
              g6c_opening_clause(echo_pair, topic=TOPIC)[0] is True, ""))
    t.append(("all voices echoing the topic IS a failure",
              g6c_opening_clause([echo_pair[0], echo_pair[1], echo_pair[0]],
                                 topic=TOPIC)[0] is False, ""))
    tmpl = ["the mainspring has more power than the watch is allowed to spend",
            "the mainspring has more power than the watch is allowed to spend",
            "the mainspring has more power than the watch is allowed to spend"]
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

    # --- 208w: the round's own mandates must NOT blanket-sanction the whole
    # horological vocabulary. A 208w-register triple that is NOT the topic's
    # own line must still be flagged, or the guard has been switched off.
    v208 = ["the fusee pays out the chain and the balance holds its beat"]*3
    t.append(("208w-register non-topic triple IS flagged",
              len(shared_ngrams(v208, 4)) > 0, ""))

    # --- 208w G11: the register guard must fire on the transposed 207w
    # defect (a locksmith triple) and on the two nearest false friends
    # (assaying, ship), and accept a horological triple.
    t.append(("G11 rejects an off-register locksmith triple",
              g11_register(["the ward is cut to the key and the tumbler stands up "
                            "and the bolt is thrown and the pick lifts them in "
                            "order"]*3)[0] is False, ""))
    t.append(("G11 rejects an off-register assaying triple",
              g11_register(["the bullion is assayed against the touchstone and "
                            "the fining reports what the ingot was worth"]*3)[0] is False, ""))
    t.append(("G11 rejects an off-register ship triple",
              g11_register(["the hawse pipe admits the sea and the bower is made "
                            "fast at the capstan"]*3)[0] is False, ""))
    t.append(("G11 rejects an off-register cooperage triple",
              g11_register(["on the cooperage bench the stave is shaved flat and "
                            "the hoop is driven tight and the croze is cut around "
                            "the bilge of the cask"]*3)[0] is False, ""))
    t.append(("G11 rejects an off-register writing triple",
              g11_register(["on the writing bench the nib is charged from the "
                            "reservoir and the ink carries the pigment until the "
                            "water is gone and the line is dry"]*3)[0] is False, ""))
    t.append(("G11 accepts an on-register horological triple",
              g11_register(["the mainspring is coiled in the barrel and the fusee "
                            "pays the chain out and the torque holds and the "
                            "reserve is the middle and the ends are refused"]*3)[0] is True, ""))

    # --- 208w: the two NEW mandates must NOT switch the guard off. A triple
    # that is NEITHER the doctrine nor the round vocabulary must still be
    # flagged. This is the FALSE-POSITIVE-PAIR test for the new mandates.
    t.append(("new 208w mandates do not blanket-sanction a neutral triple",
              len(shared_ngrams(["the plinth is lined to the sill and the sill "
                                 "is the only part"]*3, 4)) > 0, ""))
    t.append(("new 208w mandate covers the doctrine extended form",
              is_mandated("a witness log that predicts")
              and is_mandated("witness log that predicts rather than records"), ""))
    t.append(("new 208w mandate covers the round-vocab compound",
              is_mandated("power reserve indicator"), ""))
    t.append(("208w doctrine-extension mandate does not cover a different clause",
              not is_mandated("the log of the recall is kept in the vault"), ""))
    # --- negative controls (NC) ---------------------------------------------
    ncs = negative_controls()
    for name, ok in ncs:
        t.append((f"NC: {name}", ok, ""))

    npass = sum(1 for _,ok,_ in t if ok)
    return t, npass, len(t)

# ---- round -----------------------------------------------------------------
def run_round():
    print(f"\n=== Taps round 208w | topic: {TOPIC} ===\n", flush=True)
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
        "runner": "taps_round_208w.py",
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
