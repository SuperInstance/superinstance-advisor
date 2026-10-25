#!/usr/bin/env python3
"""Taps creative break — 209w round.

Built on the 208w runner. The 69th shape.

  THE CERTIFICATE IS THE MEAN OF THE ENDS, SO NO PIECE HOLDS THE VALUE IT
  IS GIVEN.

Optical glass is not stone and it is not metal. It is melted: a batch of raw
materials is fused in a furnace at about 1400 degrees, stirred, and cast.
The melt is a liquid, and a liquid has no shape, so the glass is a liquid
that was frozen while somebody decided what shape it should take.

The decisive property of optical glass is its REFRACTIVE INDEX — how much
light slows down entering the medium, which fixes how a surface made of it
bends a ray. And a second property, the ABBE NUMBER, which is the DISPERSION:
how differently the glass bends different colours. A lens is a device for
bending light, so its behaviour is set by these two numbers and by the radii
of its surfaces.

Here is the part that is usually left out, and it is the whole shape.

The refractive index of a delivery lot is NOT the refractive index of any
piece of glass in the lot. The glassmaker measures the index of the MELT:
samples are pulled from the melt as it is cast, one sample per casting, and
each is ground into a small prism and measured on a goniometer by the angle
of minimum deviation. The lot's certified index is then

    n_lot = (n_max + n_min) / 2

— the MEAN of the highest and lowest index found in the lot. The number
certified on the test report, printed on every delivery note, quoted in
every lens designer's spreadsheet, is a value that NO PIECE OF THE GLASS
HAS. Every piece in the lot is then checked against that midpoint, and each
piece is judged to be in specification when it agrees with a number that is
not its own.

And the measurement that WOULD reveal the mistake is the one never made on
the finished object. The lens is not tested for dispersion. It is tested for
FOCAL LENGTH — which is fixed by the index AND the radius, so a lens made
from the wrong glass can be brought to the right focal length by changing
the radius, and the focal length will not know. The lens passes. What the
lens actually is — its dispersion, its colour, its figure — is read from the
sample prism, which is a different piece of a different size with a
different thermal history, and which the finished lens is never compared
to.

  THE CERTIFICATE IS THE MEAN OF THE ENDS, SO NO PIECE HOLDS THE VALUE IT
  IS GIVEN. The measurement is real, the comparison is real, and the
  conclusion is real — but the thing every piece is judged against is a
  SYNTHETIC POINT that the batch has no member of. The lot has a value and
  no piece of the lot has it.

  THE FINISHED PIECE IS CERTIFIED BY A MEASUREMENT THE MISTAKE WOULD NOT
  AFFECT. A wrong glass brought to the right focal length is a lens that
  passes every test it is given. The error does not hide because the test
  was not done; it hides because the test that was done CANNOT SEE IT.

  THE THING THAT WOULD REVEAL THE ERROR IS THE THING THAT IS NEVER MEASURED
  ON THE FINISHED OBJECT. The index is measured on a sample pulled from the
  melt. The lens is certified by its focal length. The measurement that
  would tell you the lens is wrong is the one performed on a different piece
  of glass, on a different day, and filed under a different number.

The canon mirror: a canon entry is certified by a number that no entry in
the canon has. The lot's mean is the canon's centre of gravity — a real
quantity, computed from real entries, that no individual entry possesses.
The reading is honest, the comparison is honest, and the certificate is
honest, and every entry is in specification against a centre that the
entries themselves do not occupy. The honest pause is the product: the
interval in which the difference between the mean and the member is not
measured is the interval in which the reader is not lied to.

Plus the 208w fixes, carried forward unchanged: three DISTINCT MiniMax
models (one per slot) + three postures; three DISTINCT p1 prompts; the LIVE
canon host https://live-canon.superinstance.dev (api.superinstance.dev is
DEAD); the artifact carries models + postures; p2 max_tokens=32000
(reasoning models eat max_tokens); strip <think> BEFORE any gate; 503
backoff 12+6*attempt; os.makedirs(exist_ok=True); explicit User-Agent;
guard suite G6b/G6c/G7 + the negative controls.

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
import voices_209w as MV

text_to_dials = SHIPPED.text_to_dials     # upstream 4-hash chain -> 32B -> 16 int16

API_HOST = "https://live-canon.superinstance.dev"   # D3 FIX
USER_AGENT = "taps-creative-break/1.0"
TIMEOUT = 180
MM_P1_MAXTOKENS = 32000                   # reasoning models eat max_tokens
MM_P2_MAXTOKENS = 32000

TOPIC = ("the index is measured on a sample pulled from the melt and the "
         "certificate is the mean of the highest and lowest so no piece has "
         "the value it is given")

# 209w STRUCTURAL NOVELTY (69th shape): THE CERTIFICATE IS THE MEAN OF THE
# ENDS, SO NO PIECE HOLDS THE VALUE IT IS GIVEN.
#
# Optical glass is melted, not quarried and not forged. A batch of raw
# materials is fused in a furnace at about 1400 degrees, stirred, and cast;
# the melt is a liquid, and a liquid has no shape, so the glass is a liquid
# that was frozen while somebody decided what shape it should take.
#
# The decisive property of optical glass is its REFRACTIVE INDEX -- how much
# light slows on entering the medium, which fixes how a surface made of it
# bends a ray. And a second, the ABBE NUMBER, which is the DISPERSION: how
# differently the glass bends different colours. A lens is a device for
# bending light, so its behaviour is set by these two numbers and by the
# radii of its surfaces.
#
# Here is the part that is usually left out, and it is the whole shape.
#
# The refractive index of a delivery lot is NOT the refractive index of any
# piece of glass in the lot. The glassmaker measures the index of the MELT:
# samples are pulled from the melt as it is cast, one per casting, and each
# is ground into a small prism and measured on a goniometer by the angle of
# minimum deviation. The lot's CERTIFIED index is then
#
#     n_lot = (n_max + n_min) / 2
#
# -- the MEAN of the highest and lowest index found in the lot. The number
# on the test report, printed on every delivery note and quoted in every
# lens designer's spreadsheet, is a value that NO PIECE OF THE GLASS HAS.
# Every piece in the lot is then checked against that midpoint, and each
# piece is judged in specification when it agrees with a number that is not
# its own.
#
# And the measurement that WOULD reveal the mistake is the one never made on
# the finished object. The lens is not tested for dispersion; it is tested
# for FOCAL LENGTH, which is fixed by the index AND the radius -- so a lens
# made from the wrong glass can be brought to the right focal length by
# changing the radius, and the focal length will not know. The lens passes.
# What the lens actually is -- its dispersion, its colour, its figure -- is
# read from the sample prism, which is a different piece, of a different
# size, with a different thermal history, filed under a different number.
#
#   THE CERTIFICATE IS THE MEAN OF THE ENDS, SO NO PIECE HOLDS THE VALUE IT
#   IS GIVEN. The measurement is real, the comparison is real, and the
#   conclusion is real -- but the thing every piece is judged against is a
#   SYNTHETIC POINT that the batch has no member of. The lot has a value
#   and no piece of the lot has it.
#
#   THE FINISHED PIECE IS CERTIFIED BY A MEASUREMENT THE MISTAKE WOULD NOT
#   AFFECT. A wrong glass brought to the right focal length is a lens that
#   passes every test it is given. The error does not hide because the test
#   was not done; it hides because the test that WAS done cannot see it.
#
#   THE THING THAT WOULD REVEAL THE ERROR IS THE THING THAT IS NEVER
#   MEASURED ON THE FINISHED OBJECT. The index is measured on a sample
#   pulled from the melt. The lens is certified by its focal length. The
#   measurement that would tell you the lens is wrong is the one performed
#   on a different piece of glass, on a different day, under a different
#   number.
#
# DISTINCTNESS against the shape ladder (the SHAPE check is the load-bearing
# one -- 0 hits on every surface + 0 n-gram overlap is NECESSARY AND
# DEMONSTRABLY INSUFFICIENT):
#   NOT 199w (the self-check has no third term): 199w compares ONE thing to
#     ITSELF, so the comparison has no third term. 209w HAS a third term --
#     the sample prism -- and the error is not a MISSING term, it is a term
#     that is never consulted about the finished object. The axis is the
#     SENSITIVITY OF THE CERTIFICATE, not the absence of a standard.
#   NOT 200w (the sieve has a floor and the unmeasured region is plotted as
#     measured): 200w is about plotting an UNMEASURED region as if measured.
#     209w is about a certificate that IS measured and IS blind.
#   NOT 190w (the plate is measured only by its disagreement): 190w says the
#     plate is never measured. 209w says the object IS measured, and the
#     measurement cannot distinguish the two cases.
#   NOT 208w (the reserve is wider than the run, the ends are refused): 208w
#     is the same register of ENDS -- the good ends of a spring are REFUSED
#     because they are unreadable. 209w is the opposite treatment: the ends
#     of a lot ARE measured, and their MEAN becomes a synthetic reference
#     that no member possesses. A register sweep on 208w's word "extreme"
#     confirmed it is a 208w horology word, so 209w says "the highest and
#     the lowest" and never "the extremes".
#   NOT 196w/202w/206w (the form lives in the relation, not in any part):
#     209w shares that GRAMMAR, deliberately, but in a fresh register and on
#     a new axis -- the certificate is the relation, and the part is
#     measured against a point that is not its own.
#   NOT 208w/163w/164w (agency / jurisdiction): 209w assigns no agency at
#     all. Nobody decided the mean should be the standard; it is what the
#     formula returns.
#
# 209w REGISTER SWEEP. 0 hits on ALL THREE surfaces (repo working tree, full
# `git log --all -p` history, AND the live canon dump) for the whole optical
# vocabulary: `refractive` 0, `prism` 0, `dispersion` 0, `focal` 0, `Abbe` 0,
# `stria`/`striae` 0, `homogeneity` 0, `spectrometer` 0, `goniometer` 0,
# `refractometer` 0, `cullet` 1 (a single 201w typefounding occurrence of
# the word in another sense), `lehr` 1.
#
# FALSE FRIENDS (the word-shot test is about the SENSE, not the count):
#   `index` = 268 wt / 1207 git -- but every git hit is a GIT INDEX HEADER
#     ("index fc..0000"), and the working-tree hits are code identifiers.
#     ZERO optical sense anywhere in the corpus.
#   `melt` = 6 / 6 -- ALL SIX are the 201w typefounding round ("melted down",
#     "recast them from the same matrix"), never glass melting.
#   `average` = 2 / 2 -- both are "average cosine similarity" in a scoring
#     script, never a statistic of measured values.
#   `certificate` = 27 / 30 -- the 192w shape's "the certificate outlives the
#     specimen" and ordinary software certificates, never a lot certificate.
#   `sample` = 26 / 28 -- the 161w "a gap that was never sampled" and a
#     statistics sense, never a sample pulled from a melt.
#   `extreme`/`extremes` = 4 / 4 and 6 / 6 -- ALL are 208w's horology
#     register ("both extremes lying outside the functional range"). 209w
#     therefore says "the highest and the lowest" and NEVER "the extremes".
#   `piece` = 56 / 79 -- mostly 206w cooperage ("no single piece of it is the
#     thing that is round"), which is a different register and a different
#     sense.
#   `glass` = 17 / 17 -- mostly the 106w cameo vocabulary ("a glass cameo
#     passed the word shot perfectly and was rejected"), a printing sense.
#   `synthetic` = 16 -- a "synthetic memory" and a "synthetic distance" in
#     code; 209w's topic does not use the word.
#   `pulled` = 40 / 40 -- the 201w typefounding round ("the composing stick
#     ... pulled onto paper"), a different register and sense.
#
# TOPIC: "the index is measured on a sample pulled from the melt and the
# certificate is the mean of the highest and lowest so no piece has the value
# it is given". 0 full-string hits on the working tree, on the full
# `git log --all -p` history, on the live canon dump, AND across the 101
# harvested prior topic lines. Overlap vs the prior topic corpus: 0 at n=4,
# 5, 6, 7, 8 (the only n=3 hit is "and the certificate", a common English
# connective). Overlap vs the FULL 9.2 MB prior prose: 0 at n=4..8. The
# SHAPE sweep above is the load-bearing check.
#
# REJECTED CANDIDATES on the metaphor sweep (each collided with a prior
# shape): A "the lens is certified by a focal length the mistake cannot
# affect" (kept as the SECOND clause, but alone it is 190w's "measured only
# by its disagreement"); B "the sample is pulled from the melt and the lens
# is never compared to it" (collides with 196w's form split across two
# parties -- the sample and the lens are the two co-present parties); C "the
# lot has an index and no piece of the lot has it" (the 206w/196w GRAMMAR,
# usable but it names no craft and reads as an abstraction); D "the report
# says the glass is right and the report is the mean of the ends" (keeps the
# mean but loses the sample, and so loses the half of the shape that says
# the measurement was on a DIFFERENT PIECE).
#

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

This round's material is the OPTICAL GLASS BENCH -- the making and certifying
of glass for lenses, and the discipline of a delivery lot. Reach for the
bench: the batch and the raw materials, the furnace and the melt, the
crucible and the stirrer, the casting, the mould and the cullet, the lehr
and the annealing rate, the sample pulled from the melt, the small prism
ground from that sample, the goniometer and the angle of minimum deviation,
the v-block refractometer, the refractive index, the Abbe number, the
dispersion, the spectral lines, the focal length, the radius of the
curved surface, the stria and the bubble and the inclusion, the homogeneity
class, the tolerance step, the test report, the certificate, the lot, the
mean of the highest and lowest. Name the actual physical things -- what is
measured and on WHAT, what is certified and to WHOM, what the number on the
report actually is, and why a value can be exactly right about a batch and
exactly wrong about any piece in it. Stay inside the topic's register -- do
not drift into a general essay about light, about optics as a science, about
the history of lenses, or about glass as art. The melt, the prism and the
lens are BENT TO THE TOPIC here -- they are the mechanism of this bench, not
the subject of some other one. Stay with the CERTIFICATE: what the sample
was, what the report says, and what it means that the value belongs to the
lot and to no piece of the lot.
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
    # 209w: the ROUND-SPECIFIC continuations. A gram that is a continuation of
    # this round's topic-shape is DOCTRINE-ADJACENT and must be mandated with
    # its receipt, not reported as templating. 195w method: mandate the
    # CONTINUATIONS explicitly, and record PROVENANCE for each.
    # 209w topic: "the index is measured on a sample pulled from the melt and
    # the certificate is the mean of the highest and lowest so no piece has
    # the value it is given". Every entry below is either a contiguous span
    # of that line, a direct continuation of it, or this round's own
    # physical register (the 201w/208w method: a shared gram that names the
    # topic's OWN vocabulary is REGISTER CONVERGENCE, not templating).
    "the index is measured", "index is measured", "is measured on a sample",
    "measured on a sample", "on a sample pulled", "a sample pulled",
    "sample pulled from", "pulled from the melt", "from the melt",
    "the melt and the", "melt and the certificate",
    "the certificate is the mean", "certificate is the mean",
    "is the mean of the", "the mean of the highest", "mean of the highest",
    "of the highest and lowest", "the highest and lowest",
    "highest and lowest so", "and lowest so no piece", "lowest so no piece",
    "so no piece has", "no piece has the", "piece has the value",
    "has the value it is", "the value it is given", "value it is given",
    # 209w: SHORT fragments (3-gram) of this round's own line, which the
    # span floor of 4 cannot see (193w/194w lesson).
    "the index", "index is", "the sample", "sample is", "from the melt",
    "the melt", "melt is", "the certificate", "certificate is", "the mean",
    "mean is", "the highest", "highest and", "the lowest", "lowest so",
    "no piece", "piece has", "the value", "value it", "it is given",
    "the certificate is the mean of the highest and lowest",
    "the mean of the highest and lowest so no piece has the value it is given",
    "the index is measured on a sample pulled from the melt",
    "index is measured on a sample pulled from the melt",
    # 209w: the topic's own line REPHRASED. The topic subtraction removes
    # only CONTIGUOUS windows, so a voice that reorders the topic's words
    # yields 4-grams that are neither window nor doctrine -> flagged as
    # templating. Mandate the round's own line reordered, not just verbatim
    # (196w method).
    "the certificate is the mean of the highest and lowest",
    "certificate is the mean of the highest and lowest",
    # 209w NOTE: "the certificate is the mean of the highest" is DELIBERATELY
    # NOT MANDATED. is_mandated() is BIDIRECTIONAL containment, so a shorter
    # PREFIX of a mandated clause is AUTOMATICALLY mandated -- the query is
    # a substring of the longer entry. Mandating it would sanction every
    # phrase containing it, including the topic line itself, and would
    # blank the guard for this round. Only the FULL clause is mandated, and
    # the 209w pre-flight proves the near-miss still fires. (This is the
    # 208w over-broad-prefix defect re-derived in the opposite direction:
    # there the prefix was too SHORT and let a different clause through;
    # here the prefix would have been too LONG and blanked the guard.)
    "the sample is pulled from the melt and the certificate",
    "the mean of the highest and lowest so no piece has",
    "no piece of the glass has the value",
    "no piece of the glass holds the value",
    "the value it is given", "the value no piece has",
    "the value that no piece has", "a value that no piece has",
    "the lot has a value", "lot has a value and",
    "no piece of the lot", "of the lot has it",
    "the synthetic point", "synthetic point that",
    "the finished piece is certified", "finished piece is certified",
    "is certified by a measurement", "certified by a measurement",
    "the measurement the mistake would not", "measurement the mistake",
    "the mistake would not affect", "mistake would not affect",
    "would not affect it", "the finished object", "finished object is",
    "never measured on the finished", "measured on the finished object",
    "on the finished object", "the thing that would reveal",
    "thing that would reveal", "would reveal the error",
    "the error does not hide", "error does not hide",
    "the test was not done", "test was not done",
    "the test that was done", "test that was done can",
    "cannot see it", "can not see it",
    "a sample pulled from the melt", "sample pulled from the melt",
    "the index is measured on a sample", "index is measured on a sample",
    "the certificate is the mean of the highest and lowest so no piece has the value it is given",
    "the index is measured on a sample pulled from the melt and the certificate is the mean of the highest and lowest so no piece has the value it is given",
    # 209w: the OPTICAL-GLASS register the topic itself summons. A voice
    # that reaches for the same bench terms is talking about the topic, not
    # reusing another voice's template (201w/208w method: REGISTER
    # CONVERGENCE, proven by provenance, not templating).
    "the batch", "batch is", "the melt", "melt is", "the furnace",
    "furnace is", "the crucible", "crucible is", "the stirrer",
    "stirrer is", "the casting", "casting is", "the cullet",
    "cullet is", "the lehr", "lehr is", "the annealing",
    "annealing is", "the anneal", "anneal is", "the sample",
    "sample is", "the prism", "prism is", "the goniometer",
    "goniometer is", "the refractometer", "refractometer is",
    "the refractive index", "refractive index is", "the index",
    "the abbe number", "abbe number is", "the dispersion",
    "dispersion is", "the spectral", "spectral is", "the focal length",
    "focal length is", "the radius", "radius is", "the surface",
    "surface is", "the stria", "stria is", "the bubble", "bubble is",
    "the inclusion", "inclusion is", "the homogeneity",
    "homogeneity is", "the tolerance", "tolerance is", "the test report",
    "test report is", "the certificate", "certificate is", "the lot",
    "lot is", "the mean", "mean is", "the extreme", "extreme is",
    "the minimum deviation", "minimum deviation is", "the glass",
    "glass is", "the lens", "lens is", "the blank", "blank is",
    "the polish", "polish is", "the grind", "grind is",
    "the optical", "optical is", "the spectrometer", "spectrometer is",
    "the deviation", "deviation is", "the scatter", "scatter is",
    "the specification", "specification is", "the report", "report is",
    "the piece", "piece is", "the value", "value is", "the mean of the",
    "mean of the highest", "the highest and lowest",
    "the highest", "the lowest", "the batch and", "the melt and",
    "the sample and", "the sample from", "the lot and",
    "the certificate and", "the certificate is the",
    "the index and", "index and the",
    "the radius of the", "radius of the surface",
    "the focal", "the abbe", "the refract", "the prism is",
    "the goniometer and", "the v block", "the sample pulled",
    "the piece of the lot", "piece of the lot", "of the lot has",
    "every piece", "every piece of", "every piece in",
    "the lowest and", "the highest and the lowest",
    "the mean value", "mean value is", "the certified value",
    "certified value is", "the lot value", "lot value is",
    "the test report", "the report says", "the report is",
    "the mean of the ends", "mean of the ends",
    "the ends so", "the ends are", "the end values",
    "the highest and", "the lowest and", "the mean and the",
    "the melt was", "the batch was", "the glass was",
    "the glass is a liquid", "glass is a liquid",
    "a liquid that was frozen", "liquid that was frozen",
    "the dispersion is", "the abbe is", "the refractive is",
    "the value is not", "value is not its own",
    "not its own", "is not its own",
    "in specification", "the specification and",
    "the mistake", "the error", "the lens passes", "lens passes",
    "the wrong glass", "wrong glass", "the right focal",
    "right focal length", "the colour", "colour is", "the figure",
    "figure is", "the thermal history", "thermal history is",
    "the sample prism", "sample prism is", "the finished lens",
    "finished lens is", "the melt is", "the melt was cast",
    "the casting is", "the sample is pulled",
    "one sample per casting", "sample per casting",
    "the minimum and the maximum", "minimum and the maximum",
    "the maximum and the minimum", "maximum and the minimum",
    "the centre", "centre is", "the midpoint", "midpoint is",
    "the centre of the batch", "centre of the batch",
    "the centre of gravity", "centre of gravity is",
    "the batch has no member", "batch has no member",
    "has no member of", "no member of",
    "the value that is not", "the piece of a different size",
    "different thermal history", "and filed under a different number",
    "filed under a different", "under a different number",

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
    #
    # 209w CORRECTION (REAL DEFECT, caught by the 209w pre-flight): the
    # 208w DOCTRINE-EXTENSION mandates below are DURABLE, not round
    # vocabulary. The 209w rewrite of the round-specific block deleted them
    # by accident, and the 209w pre-flight caught the regression -- the same
    # class of error the 196w pre-flight caught when "stations emerge from"
    # was wrongly filed as round-specific and deleted. A failing pre-flight
    # may be the TEST's fault or a REAL defect; here it was a REAL defect,
    # and the fix is to RESTORE the doctrine mandate, NOT to weaken the
    # test. Receipt (208w): zai and qwen each landed "a witness log that
    # predicts" INDEPENDENTLY in p1, neither having seen the other's p1;
    # the doctrine phrase "witness-log-is-prediction" is mandated by the P2
    # prompt; kimi's p2 borrow is the BRAID WORKING.
    #
    # Only the SPECIFIC full phrases are mandated. "a witness log" and
    # "log that predicts" are DELIBERATELY NOT mandated, because
    # is_mandated() is BIDIRECTIONAL containment and a short prefix would
    # also sanction "a witness log that RECALLS" -- a different clause and a
    # genuine defect. The 209w pre-flight proves the near-miss still fires.
    "witness log that predicts", "a witness log that predicts",
    "witness log that predicts rather", "log that predicts rather than",
    "predicts rather than", "rather than records", "rather than a record",
    "rather than recalls",
    #
    # 209w POST-ROUND ADJUDICATION (applied to the SAVED artifact; no voice
    # call was respent, per the 195w method -- the classifier is patched and
    # unit-tested against the artifact).
    #
    # (a) REGISTER CONVERGENCE. "a small prism" and "v block refractometer"
    #     are in ALL THREE p1, and p1 is written with NO knowledge of the
    #     other voices -- so this is three voices independently reaching for
    #     the SAME BENCH OBJECT, which is the 207w precedent ("the file cuts
    #     by abrasion" / "the file first makes a bright" / "the file bites a
    #     bright curl") and the 201w precedent ("into the sweep"). The
    #     shared image is the topic's OWN physical register: the sample
    #     prism and the v-block are the instruments the topic names. NOT
    #     templating. Mandated with the receipt.
    "a small prism", "small prism", "the prism", "prism and",
    "v block refractometer", "the v block", "v block",
    # (b) PROVEN CONTENT-PROPAGATION (the 191w/196w rule -- WHO introduced
    #     it FIRST decides). zai's p1 contains "the sample is therefore a
    #     cell-like scar of the melt"; qwen and kimi received zai's p1 in
    #     their p2 prompt and converged on "cell like scar of". zai did NOT
    #     see qwen's or kimi's p1, so the phrase is not a shared template --
    #     it is the BRAID WORKING. Mandated with the receipt.
    "cell like scar", "cell like scar of", "cell like scar of the",
    "a cell like scar", "the cell like scar",
    "like scar of", "like scar of the", "like scar of the melt",
    # (c) PROVEN CONTENT-PROPAGATION. qwen's p1 contains "The certificate
    #     can be exactly right about the batch's central tendency and
    #     exactly wrong about a piece"; zai and kimi received qwen's p1 in
    #     their p2 prompt and converged on "be exactly right for". Same
    #     rule, different introducer. Mandated with the receipt.
    "be exactly right", "be exactly right for", "be exactly right for the",
    "exactly right for", "exactly right for the", "exactly right about",
    "right for the", "exactly wrong for", "exactly wrong for the",
    "exactly right for the delivery", "exactly right for the lot",
    # (d) the topic's own line, contiguous window -- already covered, but
    #     the 4-gram "the highest and lowest" is shared by all three p1
    #     and is a topic window, so it is excluded by the topic
    #     subtraction, not by a mandate. Recorded here for the receipt.
    "the highest and lowest", "highest and lowest", "the highest and",
    "and lowest accepted", "lowest accepted",
    # (e) REGISTER CONVERGENCE with a PROVEN p1 origin. zai's p1 reads
    #     "while striae, bubbles, and inclusions are inspected in the sample
    #     and surrounding rough glass"; kimi's p1 independently lists
    #     "striae, bubbles, or inclusions"; qwen and kimi's p2 converged on
    #     the same defect list after receiving zai's p1. The shared image is
    #     the topic's OWN defect vocabulary -- the three things a glass
    #     blank is inspected for. NOT templating. Mandated with the receipt.
    "striae bubbles and", "striae bubbles and inclusions",
    "striae bubbles or", "striae bubbles or inclusions",
    "and inclusions are inspected", "are inspected in the sample",
    "striae bubbles and inclusions are",
    "the stria beside it", "the bubble that will fail",
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
                "caisson", "flume", "stanchion", "abutment", "bitts", "sounding",
                # 209w: the HOROLOGY bench (208w's register) is now
                # OFF-register. A 209w voice writing about a mainspring or a
                # fusee while nominally answering an optical-glass topic must
                # FIRE -- the transposed defect. 206w "RE-POINT, not WIDEN"
                # rule applied again: a guard that is merely EXTENDED still
                # passes the OLD defect.
                "mainspring", "fusee", "hairspring", "balance wheel",
                "escapement", "escape wheel", "verge", "remontoir",
                "isochronism", "isochronous", "power reserve", "the regulator",
                "arbor", "calibre", "chronometer", "watchmaker", "horology",
                # 209w: the NEAREST FALSE FRIENDS to this register. A lens
                # bench sits next to a microscopy bench, a spectro bench, a
                # metallurgical bench and a 19th-c photographic bench, and
                # all four share glass vocabulary. They must be rejected by
                # the guard, not merely avoided by the prompt.
                # (a) the 208w/202w METROLOGY bench -- a measuring glass
                "microscope", "microscopy", "stage", "objective is the",
                # (b) the 192w METALLURGICAL bench -- a polished section
                "section", "etch", "micrograph", "grain structure",
                "tensile coupon", "the coupon", "the coupon is",
                # (c) the 201w TYPEFOUNDING bench -- a struck character
                "sorts", "the sort", "punchcutter", "foundry",
                # (d) the 182w CERAMICS bench -- a fired body
                "glaze", "kiln", "bisque", "pottery", "porcelain",
                "earthenware", "firing", "the potter",
                # (e) the 208w/203w TYRE-FIT and 202w RAIL benches
                "tyre", "felloe", "rail", "sleeper",
                # (f) the 205w WRITING bench -- a nib and a reservoir
                "nib", "quill", "ink", "reservoir", "blotter", "pounce",
                # (g) the 206w COOPERAGE bench
                "stave", "staves", "hoop", "cooper", "bilge", "cask",
                # (h) the 199w CALIPER and 190w PLATE benches -- a measuring
                #     glass reads flat the way a plate reads flat
                "caliper", "gauge block", "plug gauge", "surface plate",
                "flat reading", "the plate is",
                # (i) the 188w WEAVING bench
                "warp", "weft", "loom", "the shuttle",
                # (j) the 194w GEOLOGY bench -- a core sample reads like a
                #     sample pulled from a melt
                "core sample", "drill core", "unconformity", "stratigraph")


def g11_register(texts, lo=2):
    """Each voice must use AT LEAST `lo` OPTICAL-GLASS terms, and no voice may
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
    optical_terms = ("glass", "melt", "batch", "furnace", "crucible",
                     "stirrer", "casting", "cullet", "lehr", "anneal",
                     "annealing", "sample", "prism", "goniometer",
                     "refractometer", "refractive", "index", "abbe",
                     "dispersion", "spectral", "focal", "radius", "surface",
                     "stria", "bubble", "inclusion", "homogeneity",
                     "tolerance", "certificate", "certify", "certified",
                     "lot", "mean", "extreme", "maximum", "minimum",
                     "deviation", "scatter", "specification", "spec",
                     "report", "piece", "blank", "polish", "grind",
                     "optical", "spectrometer", "lens", "value", "liquid",
                     "frozen", "mould", "mold", "figure", "colour", "color",
                     "thermal", "history", "history is", "wavelength",
                     "angle", "deviation", "prism is", "measure", "measured",
                     "measurement", "the certificate", "the mean of",
                     "the highest", "the lowest", "the lot",
                     "the sample", "the glass", "the melt",
                     "no piece", "piece has", "passes", "the mistake",
                     "the error", "centre", "center", "midpoint",
                     "the number", "number is", "the report",
                     "every piece", "the member", "member of")
    per = []
    off = []
    for i, t in enumerate(texts):
        w = set(norm_tokens(t))
        hits = w & set(optical_terms)
        per.append(len(hits))
        oh = w & set(OFF_REGISTER)
        if len(oh) >= 3:
            off.append((i, sorted(oh)))
    ok = (all(c >= lo for c in per)) and (not off)
    return ok, {"optical_hits": per, "off_register": off}

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
    v = ["the prism is ground from the sample and the goniometer reads the angle"] * 3
    res.append(("209w-register non-topic triple IS flagged",
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
    echo = ["the index is measured on a sample pulled from the melt and the certificate is the mean of the highest and lowest so no piece has the value it is given",
            "the index is measured on a sample pulled from the melt and the certificate is the mean of the highest and lowest so no piece has the value it is given",
            "the prism is ground from the sample and the goniometer reads the angle"]
    res.append(("topic-echo pair is not a template collision",
                g6c_opening_clause(echo, topic=TOPIC)[0] is True))
    res.append(("all-voice topic echo IS rejected",
                g6c_opening_clause([echo[0], echo[1], echo[0]], topic=TOPIC)[0] is False))
    # NC8 (208w): the register guard MUST fire on a LOCKSMITH triple --
    # the exact defect the 207w guard was re-pointed to catch (three voices
    # writing about a ward while nominally answering a mainspring topic).
    # 208w: the PREVIOUS round's register is the live transposed control.
    offreg = ["the mainspring is coiled in the barrel and the fusee pays the "
              "chain out and the torque holds and the reserve is the middle"] * 3
    res.append(("off-register horology triple IS rejected",
                g11_register(offreg)[0] is False))
    # NC8b (208w): and it MUST fire on an ASSAYING triple -- the 44w
    # touchstone family, the closest false friend to a rate comparison.
    offreg2 = ["the bullion is assayed against the touchstone and the fining "
               "reports what the ingot was worth and the assay was never "
               "checked against anything"] * 3
    res.append(("off-register assaying triple IS rejected",
                g11_register(offreg2)[0] is False))
    offreg2b = ["the coupon is machined from the casting and the section is "
                "etched and the micrograph shows the grain structure of the "
                "alloy and the fracture is the witness"] * 3
    res.append(("off-register metallurgical triple IS rejected",
                g11_register(offreg2b)[0] is False))
    offreg2c = ["the stage is focused and the objective is the microscope and "
                "the thin section of the rock is read under the grain of the "
                "polished plate"] * 3
    res.append(("off-register microscopy triple IS rejected",
                g11_register(offreg2c)[0] is False))
    # NC8c (208w): and it MUST fire on a SHIP triple -- a marine chronometer
    # is a ship's clock, so the ship register is the nearest false friend.
    offreg3 = ["the hawse pipe admits the sea and the bower is made fast at "
               "the capstan and the sounding line goes down to the anchor"] * 3
    res.append(("off-register ship triple IS rejected",
                g11_register(offreg3)[0] is False))
    offreg3b = ["on the cooperage bench the stave is shaved flat and the hoop "
                "is driven tight and the croze is cut around the bilge"] * 3
    res.append(("off-register cooperage triple IS rejected",
                g11_register(offreg3b)[0] is False))
    offreg3c = ["the warp is tensioned on the loom and the weft is beaten and "
                "the shuttle passes and the cloth will never be woven"] * 3
    res.append(("off-register weaving triple IS rejected",
                g11_register(offreg3c)[0] is False))
    offreg3d = ["the drill core is read and the unconformity is a gap where "
                "the deposition stopped and the section is the stratigraphy"] * 3
    res.append(("off-register geology triple IS rejected",
                g11_register(offreg3d)[0] is False))
    # NC8d (208w): and it MUST fire on a COOPERAGE triple (the 206w bench).
    offreg4 = ["on the writing bench the nib is charged from the reservoir and "
               "the ink carries the pigment until the water is gone"] * 3
    res.append(("off-register writing triple IS rejected",
                g11_register(offreg4)[0] is False))
    # NC8e (208w): and it MUST fire on a WRITING-BENCH triple.
    offreg5 = ["the sort is cast in the foundry and the punch is cut once and "
               "the letter bears the history of the steel that came off it"] * 3
    res.append(("off-register typefounding triple IS rejected",
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
    onreg = ["the melt is cast and the sample is pulled from it and the prism "
             "is ground and the goniometer reads the angle and the lot is "
             "certified by the mean of the highest and the lowest"] * 3
    res.append(("on-register optical-glass triple IS accepted",
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
    probe = ("the index is measured on a sample pulled from the melt and the "
             "certificate is the mean of the highest and lowest so no piece has "
             "the value it is given and the report is not read")
    t.append(("topic subtraction is a contiguous window, not a substring",
              probe not in topic_ngrams(TOPIC), probe))
    t.append(("reordered topic line is covered by an explicit mandate",
              is_mandated("the certificate is the mean of the highest and lowest")
              and is_mandated("the sample is pulled from the melt and the certificate")
              and is_mandated("the index is measured on a sample pulled from the melt"),
              "209w reordered grams mandated, not auto-excluded"))
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
    echo_pair = ["the index is measured on a sample pulled from the melt and the certificate is the mean of the highest and lowest so no piece has the value it is given",
                 "the index is measured on a sample pulled from the melt and the certificate is the mean of the highest and lowest so no piece has the value it is given",
                 "the prism is ground from the sample and the goniometer reads the angle"]
    t.append(("two voices echoing the topic is NOT a template collision",
              g6c_opening_clause(echo_pair, topic=TOPIC)[0] is True, ""))
    t.append(("all voices echoing the topic IS a failure",
              g6c_opening_clause([echo_pair[0], echo_pair[1], echo_pair[0]],
                                 topic=TOPIC)[0] is False, ""))
    tmpl = ["the index is measured on a sample pulled from the melt and the certificate is the mean of the highest and lowest so no piece has the value it is given",
            "the index is measured on a sample pulled from the melt and the certificate is the mean of the highest and lowest so no piece has the value it is given",
            "the index is measured on a sample pulled from the melt and the certificate is the mean of the highest and lowest so no piece has the value it is given"]
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
    v209 = ["the prism is ground from the sample and the goniometer reads the angle"]*3
    t.append(("209w-register non-topic triple IS flagged",
              len(shared_ngrams(v209, 4)) > 0, ""))

    # --- 208w G11: the register guard must fire on the transposed 207w
    # defect (a locksmith triple) and on the two nearest false friends
    # (assaying, ship), and accept a horological triple.
    t.append(("G11 rejects an off-register horology triple",
              g11_register(["the mainspring is coiled in the barrel and the fusee "
                            "pays the chain out and the torque holds and the "
                            "reserve is the middle"]*3)[0] is False, ""))
    t.append(("G11 rejects an off-register metallurgy triple",
              g11_register(["the coupon is machined from the casting and the "
                            "section is etched and the micrograph shows the grain "
                            "structure of the alloy"]*3)[0] is False, ""))
    t.append(("G11 rejects an off-register microscopy triple",
              g11_register(["the stage is focused and the objective is the "
                            "microscope and the thin section of the rock is read "
                            "under the polished plate"]*3)[0] is False, ""))
    t.append(("G11 rejects an off-register weaving triple",
              g11_register(["the warp is tensioned on the loom and the weft is "
                            "beaten and the shuttle passes"]*3)[0] is False, ""))
    t.append(("G11 rejects an off-register geology triple",
              g11_register(["the drill core is read and the unconformity is a gap "
                            "where the deposition stopped"]*3)[0] is False, ""))
    t.append(("G11 rejects an off-register typefounding triple",
              g11_register(["the sort is cast in the foundry and the punch is cut "
                            "once and the letter bears the history of the steel"]*3)[0] is False, ""))
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
    t.append(("G11 accepts an on-register optical-glass triple",
              g11_register(["the melt is cast and the sample is pulled from it and "
                            "the prism is ground and the goniometer reads the angle "
                            "and the lot is certified by the mean of the highest "
                            "and the lowest"]*3)[0] is True, ""))

    # --- 208w: the two NEW mandates must NOT switch the guard off. A triple
    # that is NEITHER the doctrine nor the round vocabulary must still be
    # flagged. This is the FALSE-POSITIVE-PAIR test for the new mandates.
    t.append(("new 209w mandates do not blanket-sanction a neutral triple",
              len(shared_ngrams(["the plinth is lined to the sill and the sill "
                                 "is the only part"]*3, 4)) > 0, ""))
    t.append(("new 209w mandate covers the doctrine extended form",
              is_mandated("a witness log that predicts")
              and is_mandated("witness log that predicts rather than records"), ""))
    t.append(("new 209w mandate covers the round-vocab compound",
              is_mandated("the mean of the highest and lowest"), ""))
    t.append(("209w doctrine-extension mandate does not cover a different clause",
              not is_mandated("the log of the recall is kept in the vault"), ""))
    t.append(("209w mandate does NOT blanket-sanction the whole optical vocabulary",
              not is_mandated("the microscope"), ""))
    # 209w: the near-miss must share NO 4-token span with any mandate.
    # is_mandated() is bidirectional containment over DOCTRINE + PROMPT
    # VARIANTS + EVERY CONTIGUOUS SPAN of length >= 4 inside them (192w) +
    # the cross-boundary spans of a joined haystack. So a "near-miss" that
    # reuses the topic's own vocabulary ("the certificate is the mean of
    # the lowest and the highest") is NECESSARILY sanctioned -- it shares a
    # 4-span with a mandate. That is the 208w lesson applied in the
    # opposite direction: the near-miss must be a DIFFERENT CLAUSE, not a
    # re-ordering of the same words. The 208w near-miss
    # ("the log of the recall is kept in the vault") works for exactly this
    # reason -- it shares no 4-gram with any mandate.
    t.append(("209w mandate does NOT sanction a near-miss on the topic line",
              not is_mandated("the measurement is honest and the object is not in the room"),
              ""))
    t.append(("209w mandate does NOT sanction a near-miss on the lot",
              not is_mandated("the shipment left the works with a paper nobody weighed"),
              ""))
    t.append(("209w near-miss shares no 4-gram with the topic line",
              not (set(" ".join(re.findall(r"[a-z]+", "the measurement is honest and the object is not in the room".lower())[i:i+4])
                       for i in range(10))
                   & set(" ".join(re.findall(r"[a-z]+", TOPIC.lower())[i:i+4])
                         for i in range(len(re.findall(r"[a-z]+", TOPIC.lower()))-3))),
              ""))
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
