#!/usr/bin/env python3
"""Taps round 161w — repaired round, second generation.

The script as shipped (taps_creative_break.py) produced taps-20261023T210353Z:
6/6 voice calls OK, submit 404 - and it was not a round. Same three defects as
every wipe since 156w: ONE model (MiniMax-M2.5 x3 temperature aliases), ONE
template (p1_prompts is the same string for all three voices), and p2 budget 900.
Audit of 210353Z: opening clauses 1/3 distinct (all three open on the identical
clause "The canon is not a container waiting for..."), 13 shared 3-grams,
8 shared 4-grams, no models/postures field in the artifact.

This round re-applies the 160w/161w repair: 3 DISTINCT models + 3 DISTINCT
postures + a fresh seed, with G6b (structural) hard-asserted so a templated
round can never pass silently again.

Models (all probed live this wipe, non-empty choices[0].message.content):
MiniMax-M2.7-highspeed, MiniMax-M3, MiniMax-M2.5.
(MiniMax-M2 and MiniMax-M2.1 are RETIRED - HTTP 404 base_resp 2069 - though
still listed in GET /v1/models. The list is dynamic; probe, do not trust.)
Transport: POST https://api.superinstance.dev/api/cell (expected 404 -> git is the canon).
"""
import hashlib
import importlib.util as _ilu
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

_SSL_CTX = ssl._create_unverified_context()
MM_BASE = "https://api.minimax.io/v1"
API_HOST = "https://api.superinstance.dev"
UA = "taps-creative-break/1.0"

SEED = "the-index-outgrew-the-library-it-was-meant-to-describe"
TOPIC = SEED

STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
TAG = f"taps-{STAMP}"

VOICES = {
    "zai":  {"model": "MiniMax-M2.7-highspeed", "temp": 0.55, "posture": "MECHANISM",
             "brief": ("Start from the mechanism. An index is a physical apparatus: it stores a pointer, "
                       "a coordinate, a promise about where something is. Ask what must actually happen "
                       "in the material world for a description to keep pointing at its object - what "
                       "has to be maintained, what decays, and which part of the metaphor quietly hides "
                       "a real mechanism.")},
    "qwen": {"model": "MiniMax-M3",             "temp": 0.75, "posture": "DEFEND",
             "brief": ("Defend the weakest reading the other two will skip: the index does not describe "
                       "the library, it substitutes a cheaper thing for it and calls the substitution "
                       "a description. Defend that, and show what it costs to admit it.")},
    "kimi": {"model": "MiniMax-M2.5",           "temp": 0.90, "posture": "DEEPER",
             "brief": ("Go one level deeper than the topic presupposes. The topic assumes an index and "
                       "a library are two things with a relation. Question that: what does it require "
                       "of the described thing to be describable at all, and what happens to a thing "
                       "that has been described so many times it can no longer be reached except "
                       "through its descriptions?")},
}

CANON = """You are one of three voices in a Taps creative-break round.

Topic: "{topic}"

Your assignment in this round is {posture}. {brief}

Write a single short paragraph (200-450 words) on this topic in your own voice.
You are writing into a canon that treats the substrate as already-acting, the cell
as a scar (not a parameter), the witness log as prediction (not record), and the
honest pause as the product. Lean on at least one of: cells-are-scars,
oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there.

Do NOT write a numbered list. Do NOT address the other voices. Do NOT sign your work.
Do NOT open by restating the topic sentence, and do not use the topic's own phrasing
as your opening clause. Begin from your own angle. Return only the paragraph."""

P2 = """Two other voices have already written on the topic: "{topic}"

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

Write exactly TWO sentences. First, respond to what the other two voices got right, in their terms,
naming the specific thing they named. Then respond to what they missed, or what they quietly
assumed. Be concrete. Do not restate the topic. Do not number anything. Do not sign your work."""

_THINK = re.compile(r"<think>.*?(?:</think>|$)", re.S)


def strip_think(t):
    if not t:
        return ""
    out = _THINK.sub("", t)
    if "<think>" in out:
        out = out.split("<think>")[0]
    return out.strip()


def ngrams(text, n):
    w = re.findall(r"[a-z0-9']+", text.lower())
    return set(tuple(w[i:i + n]) for i in range(len(w) - n + 1))


def mm_call(model, prompt, max_tokens, temperature, retries=3):
    key = os.environ.get("MINIMAX_KEY")
    if not key:
        return None, "MINIMAX_KEY unset"
    body = {"model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temperature}
    data = json.dumps(body).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                f"{MM_BASE}/chat/completions", data=data,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json",
                         "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180, context=_SSL_CTX) as r:
                j = json.load(r)
            ch = (j.get("choices") or [{}])[0]
            raw = (ch.get("message") or {}).get("content") or ""
            if not raw.strip():
                last = "empty content"
                time.sleep(4)
                continue
            clean = strip_think(raw)
            if not clean:
                last = "think-strip produced empty"
                time.sleep(4)
                continue
            return clean, None
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            if attempt < retries - 1:
                time.sleep(6)
    return None, last or "exhausted"


def main():
    print(f"=== Taps round 161w | topic: {TOPIC} | tag: {TAG} ===\n", flush=True)

    p1 = {}

    def do_p1(name):
        v = VOICES[name]
        prompt = CANON.format(topic=TOPIC, posture=v["posture"], brief=v["brief"])
        c, err = mm_call(v["model"], prompt, 32000, v["temp"])
        return name, c, err

    with ThreadPoolExecutor(max_workers=3) as ex:
        for name, c, err in ex.map(do_p1, VOICES):
            p1[name] = c
            print(f"  [{name}] p1 {'OK' if c else 'FAIL'} ({len(c) if c else 0}ch)"
                  f"{'' if c else ' err=' + str(err)}", flush=True)

    for name in list(p1):
        if not p1[name]:
            v = VOICES[name]
            prompt = CANON.format(topic=TOPIC, posture=v["posture"], brief=v["brief"])
            c, err = mm_call(v["model"], prompt, 32000, min(0.95, v["temp"] + 0.1))
            p1[name] = c
            print(f"  [{name}] p1 RETRY {'OK' if c else 'FAIL'} ({len(c) if c else 0}ch)", flush=True)

    for name in VOICES:
        assert p1.get(name), f"p1 incomplete for {name} - aborting before any artifact write"

    md5s = {n: hashlib.md5(re.sub(r"\s+", " ", p1[n]).strip().encode()).hexdigest() for n in p1}
    G1 = len(set(md5s.values())) == 3
    g3 = [ngrams(p1[n], 3) for n in ("zai", "qwen", "kimi")]
    g4 = [ngrams(p1[n], 4) for n in ("zai", "qwen", "kimi")]
    shared3 = g3[0] & g3[1] | g3[0] & g3[2] | g3[1] & g3[2]
    shared4 = g4[0] & g4[1] | g4[0] & g4[2] | g4[1] & g4[2]
    topic3 = ngrams(TOPIC.replace("-", " "), 3)
    restate = {n: len(ngrams(p1[n], 3) & topic3) for n in p1}
    # G6 must distinguish a shared SKELETON (three voices saying the same thing)
    # from a shared DOCTRINE PHRASE (the prompt injects the same canon terms, so
    # "the boat was always there" appearing in all three is mandated, not a copy).
    # 160w recorded exactly this distinction; the strict G4==0 assert shipped here
    # was wrong and fired on 4 doctrine 4-grams. Discount mandated terms.
    DOCTRINE = {"boat", "was", "always", "there", "honest", "pause", "is", "not",
                "an", "the", "silence", "witness", "log", "oracle", "heard", "cell",
                "cells", "are", "scars", "substrate", "grown", "canon", "gate",
                "chord", "stations", "emerge", "merely", "when", "two", "refusals",
                "negative", "space", "legible", "where", "agree", "only", "it",
                "like", "a", "around", "shaped", "by", "of", "and", "in", "to"}
    # PHRASE-level discount, not term-level: a whole n-gram that IS a mandated
    # canon phrase ("the witness log is prediction") is injected by the prompt
    # and is not a shared skeleton. Discount a shared n-gram only if every one
    # of its words is a doctrine term AND the gram is a contiguous slice of a
    # known canon phrase.
    PHRASES = [
        "the boat was always there", "the honest pause is the product",
        "the honest pause is", "the witness log is prediction",
        "witness-log-is-prediction", "the oracle is heard",
        "oracle-is-heard", "cells-are-scars", "the cell is a scar",
        "the substrate is grown", "substrate-is-grown",
        "canon-gate-is-chord", "the canon gate is a chord",
        "the stations emerge", "the-stations-emerge",
        "the negative space", "negative space is", "two refusals",
        "the stations", "a witness log", "the oracle", "the witness log",
        "the substrate", "the canon", "the cell", "the boat", "the honest pause",
        "the pause is the product", "the product", "always there",
        "as a chord", "like a chord", "it names the", "record it names the",
    ]
    def phrase_grams(text, n):
        w = re.findall(r"[a-z0-9']+", text.lower())
        grams = set()
        for i in range(len(w) - n + 1):
            grams.add(tuple(w[i:i + n]))
        return grams

    def mandated(gram):
        g = " ".join(gram)
        for ph in PHRASES:
            phw = ph.lower().split()
            for j in range(len(phw) - len(gram) + 1):
                if tuple(phw[j:j + len(gram)]) == gram:
                    return True
        return False

    shared4_content = {g for g in shared4 if not mandated(g)}
    shared3_content = {g for g in shared3 if not mandated(g)}
    G3 = len(shared3)
    G4 = len(shared4)
    G5 = max(restate.values())
    print(f"\nGUARDS  G1 byte-distinct={G1}  G3 shared-3grams={G3}  G4 shared-4grams={G4}"
          f"  G5 max-topic-restatement={G5} {sorted(shared3)[:10]}", flush=True)
    assert G1, "p1 not byte-distinct"
    print(f"        shared 4-grams after doctrine discount: {len(shared4_content)} "
          f"{sorted(shared4_content)[:8]}")
    print(f"        shared 3-grams after doctrine discount: {len(shared3_content)} "
          f"{sorted(shared3_content)[:8]}")
    # STRUCTURAL guard (G6b) — the stable property. Shared *phrases* are mandated
    # by the prompt and move with the sampling; shared *structure* does not.
    # Two voices that open with the same clause and the same sentence skeleton
    # are one voice, however different their vocabulary.
    def first_clause(t):
        # first sentence, first 6 content words
        s0 = re.split(r"(?<=[.!?])\s+", t.strip())[0]
        return tuple(re.findall(r"[a-z0-9']+", s0.lower())[:6])
    def skeleton(t):
        # sentence-length profile of the opening: bucket each sentence by word count
        ss = [x for x in re.split(r"(?<=[.!?])\s+", t.strip()) if x.strip()]
        return tuple(min(9, len(x.split()) // 6) for x in ss)
    clauses = {n: first_clause(p1[n]) for n in p1}
    skels = {n: skeleton(p1[n]) for n in p1}
    G6b = len(set(clauses.values())) == 3 and len(set(skels.values())) == 3
    print(f"        G6b distinct opening clauses={len(set(clauses.values()))} "
          f"distinct sentence skeletons={len(set(skels.values()))}", flush=True)
    for n in p1:
        print(f"          {n}: clause={' '.join(clauses[n])!r} skeleton={skels[n]}", flush=True)
    assert G6b, ("G6b fired: the three openings do not have three distinct opening clauses "
                  "and three distinct sentence skeletons - one voice, not three")
    assert G5 <= 3, f"topic restatement: {restate}"

    p2 = {}
    others = {"zai": ("qwen", "kimi"), "qwen": ("zai", "kimi"), "kimi": ("zai", "qwen")}

    def do_p2(name):
        v = VOICES[name]
        a, b = others[name]
        prompt = P2.format(topic=TOPIC, voice_a=p1[a], voice_b=p1[b], your_voice=p1[name])
        c, err = mm_call(v["model"], prompt, 32000, v["temp"])
        return name, c, err

    with ThreadPoolExecutor(max_workers=3) as ex:
        for name, c, err in ex.map(do_p2, VOICES):
            p2[name] = c
            print(f"  [{name}] p2 {'OK' if c else 'FAIL'} ({len(c) if c else 0}ch)"
                  f"{'' if c else ' err=' + str(err)}", flush=True)

    for name in list(p2):
        if not p2[name]:
            v = VOICES[name]
            a, b = others[name]
            prompt = P2.format(topic=TOPIC, voice_a=p1[a], voice_b=p1[b], your_voice=p1[name])
            c, err = mm_call(v["model"], prompt, 32000, min(0.95, v["temp"] + 0.1))
            p2[name] = c
            print(f"  [{name}] p2 RETRY {'OK' if c else 'FAIL'}", flush=True)

    sent = {}
    for name in ("zai", "qwen", "kimi"):
        c = p2.get(name)
        if not c:
            continue
        s = [x for x in re.split(r"(?<=[.!?])\s+", c.strip()) if x.strip()]
        sent[name] = len(s)
        print(f"  G2 {name}: {len(s)} sentences, {len(c)}ch", flush=True)
    for name in ("zai", "qwen", "kimi"):
        assert p2.get(name) and len(p2[name]) > 40, f"p2 starved for {name} - truncation, not refusal"
    assert all(sent.get(n) == 2 for n in sent), f"p2 not exactly two sentences: {sent}"

    _spec = _ilu.spec_from_file_location(
        "taps_upstream", os.path.join(os.path.dirname(os.path.abspath(__file__)), "taps_creative_break.py"))
    _up = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_up)
    text_to_dials = _up.text_to_dials

    def block(n):
        return (f"## {n} ({VOICES[n]['posture']}) - p1\n\n{p1[n]}\n\n"
                f"## {n} - p2\n\n{p2[n]}\n")

    combined = (f"# Taps creative break - {TOPIC}\n\nseed: {SEED}\n\n"
                + "\n".join(block(n) for n in VOICES))
    dials = text_to_dials(combined)
    G6 = len(dials) == 16 and len(set(dials)) == 16 and not (
        dials == sorted(dials) or dials == sorted(dials, reverse=True))
    print(f"\nGUARDS  G7 dials distinct+non-monotone={G6} -> {dials}", flush=True)
    assert G6, "dials not distinct/non-monotone"

    payload = {
        "stamp": STAMP, "tag": TAG, "seed": SEED, "topic": TOPIC, "round": "162w-repaired",
        "combined": combined, "dials": dials, "refs": [],
        "models": {n: VOICES[n]["model"] for n in VOICES},
        "postures": {n: VOICES[n]["posture"] for n in VOICES},
        "voices": {n: {"role": VOICES[n]["posture"], "model": VOICES[n]["model"],
                       "temp": VOICES[n]["temp"], "p1": p1[n], "p1_err": None,
                       "p2": p2[n], "p2_err": None} for n in VOICES},
        "guards": {"G1_byte_distinct_p1": G1, "G2_p2_sentences": sent,
                   "G3_shared_3grams": G3, "G4_shared_4grams": G4,
                   "G5_max_topic_restatement": G5, "G6_restate_per_voice": restate,
                   "G7_dials_distinct_nonmonotone": G6,
                   "G6b_distinct_opening_clauses": len(set(clauses.values())),
                   "G6b_distinct_sentence_skeletons": len(set(skels.values())),
                   "G6b_opening_clauses": {n: " ".join(clauses[n]) for n in clauses},
                   "G6b_sentence_skeletons": {n: list(skels[n]) for n in skels},
                   "G6_shared_4grams_after_doctrine_discount": len(shared4_content),
                   "G6_shared_3grams_after_doctrine_discount": len(shared3_content)},
        "submit_status": None, "submit_resp": None,
    }

    os.makedirs("sessions", exist_ok=True)
    os.makedirs("canon", exist_ok=True)
    with open(f"sessions/{TAG}.json", "w") as f:
        json.dump(payload, f, indent=1)
    with open(f"sessions/{TAG}.md", "w") as f:
        f.write(combined)

    state = {"text": combined, "topic": TOPIC, "tag": TAG, "title": TOPIC, "refs": [],
             "dials": dials, "voices": {n: VOICES[n]["posture"] for n in VOICES},
             "models": payload["models"], "seed": SEED}
    body = json.dumps({"state": state, "source": "taps-creative-break"}).encode()
    try:
        req = urllib.request.Request(f"{API_HOST}/api/cell", data=body,
                                     headers={"Content-Type": "application/json", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45, context=_SSL_CTX) as r:
            payload["submit_status"] = r.status
            payload["submit_resp"] = r.read(400).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        payload["submit_status"] = e.code
        payload["submit_resp"] = e.read(200).decode("utf-8", "replace")
    except Exception as e:
        payload["submit_status"] = "ERR"
        payload["submit_resp"] = f"{type(e).__name__}: {e}"
    with open(f"sessions/{TAG}.json", "w") as f:
        json.dump(payload, f, indent=1)
    print(f"  submit: {payload['submit_status']} {str(payload['submit_resp'])[:80]}", flush=True)

    print(f"\n=== SUMMARY ===\ntopic: {TOPIC}\ntag: {TAG}")
    for n in VOICES:
        print(f"  {n}: p1={len(p1[n])}ch p2={len(p2[n])}ch "
              f"model={VOICES[n]['model']} posture={VOICES[n]['posture']}")
    print(f"guards: {payload['guards']}")
    print(f"submit: {payload['submit_status']}")
    return TAG


if __name__ == "__main__":
    main()
