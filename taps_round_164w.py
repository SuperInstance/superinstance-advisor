#!/usr/bin/env python3
"""Taps round 164w - repaired runner.

Fixes over the shipped script:
  1. THREE DISTINCT MODELS (shipped script pins MM_MODEL=MiniMax-M2.5 for all
     three voices => three temperature aliases of ONE model).
  2. THREE DISTINCT POSTURE PREFIXES (shipped p1_prompts dict is the SAME
     string for all three voices => byte-identical openings by construction).
  3. G6b STRUCTURAL guards: distinct opening clause + distinct sentence
     skeleton. A shared-n-gram threshold is a per-run lottery.
  4. text_to_dials imported DIRECTLY from upstream (never reimplemented).
  5. Submit to live-canon.superinstance.dev (api.superinstance.dev is 404).
  6. Checkpoint p1 to disk immediately after phase 1.
"""
import importlib.util, json, os, re, sys, time, urllib.request, urllib.error
import concurrent.futures as cf
from pathlib import Path

REPO = Path("/tmp/superinstance-advisor")
sys.path.insert(0, str(REPO))

# ---- import upstream module for text_to_dials (NEVER reimplement) ---------
spec = importlib.util.spec_from_file_location("taps_upstream", REPO / "taps_creative_break.py")
up = importlib.util.module_from_spec(spec)
spec.loader.exec_module(up)   # guarded by __name__ check upstream
text_to_dials = up.text_to_dials

import minimax_voices as MV

UA = "taps-creative-break/1.0"
LIVE = "https://live-canon.superinstance.dev"

# ---- voice roster: 3 distinct models x 3 distinct postures ---------------
ROSTER = [
    ("zai",  "MiniMax-M2.7-highspeed", "MECHANISM"),
    ("qwen", "MiniMax-M3",            "DEFEND"),
    ("kimi", "MiniMax-M2.5",           "DEEPER"),
]
POSTURE_BRIEF = {
 "MECHANISM": ("Trace the physical/mechanical chain of the metaphor. Name the "
   "material conditions under which the claim holds and the point where it fails. "
   "Do not moralize. Do not summarize the topic."),
 "DEFEND":    ("Defend the strongest opposing reading of the topic, and put the "
   "other two voices' framings on trial. Locate the assumption they quietly make. "
   "Do not concede the frame."),
 "DEEPER":    ("Go one level deeper than the surface metaphor: what must be true "
   "for this to be possible at all, and what does the metaphor conceal about its "
   "own conditions? Do not restate the topic."),
}

DOCTRINE = ("cells-are-scars, oracle-is-heard, witness-log-is-prediction, "
 "substrate-is-grown, canon-gate-is-chord, the-stations-emerge, "
 "the-boat-was-always-there, honest-pause-is-product")

def p1_prompt(topic, posture):
    return f"""You are one of three voices in a Taps creative-break round.

Topic: "{topic}"

YOUR POSTURE THIS ROUND: {posture}
{POSTURE_BRIEF[posture]}

Write a single short paragraph (200-450 words) on this topic in your own voice.
You are writing into a canon that treats the substrate as already-acting, the cell
as a scar (not a parameter), the witness log as prediction (not record), and the
honest pause as the product. Lean on at least one of: {DOCTRINE}.

Do NOT write a numbered list. Do NOT address the other voices. Do NOT sign your work.
Do NOT open by restating the topic as a noun phrase. Return only the paragraph."""

def p2_prompt(topic, a, b, mine):
    return f"""Two other voices have already written on the topic: "{topic}"

Voice A wrote:
---
{a}
---

Voice B wrote:
---
{b}
---

You wrote:
---
{mine}
---

Write exactly TWO sentences (no more, no fewer) that braid all three voices together
without naming any voice. Each sentence should land a doctrine: {DOCTRINE}.
Land on a tension the three voices share; do not summarize them.

Return only the two sentences."""

def mm_call(prompt, model, max_tokens, temperature, sentences=None):
    """Call MiniMax with a SPECIFIC model. Returns (content, err)."""
    key = os.environ.get("MINIMAX_KEY")
    if not key:
        return None, "MINIMAX_KEY unset"
    body = {"model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temperature}
    data = json.dumps(body).encode()
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                "https://api.minimax.io/v1/chat/completions", data=data,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json", "User-Agent": UA},
                method="POST")
            with urllib.request.urlopen(req, timeout=90) as resp:
                j = json.loads(resp.read().decode())
            ch = j.get("choices")
            if not ch:
                last = f"choices null base_resp={j.get('base_resp')}"
                time.sleep(6 * (attempt + 1)); continue
            content = (ch[0].get("message") or {}).get("content") or ""
            content = MV.strip_think(content)
            if not content.strip():
                last = "empty content"; time.sleep(6 * (attempt + 1)); continue
            return content, None
        except urllib.error.HTTPError as e:
            last = f"http {e.code}"
            if e.code == 503:
                time.sleep(12 + 6 * attempt); continue
            break
        except Exception as e:
            last = str(e); time.sleep(6 * (attempt + 1))
    return None, last

def http_post(url, body, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        try: return e.code, e.read().decode()
        except Exception: return e.code, ""
    except Exception as e:
        return 0, str(e)

def norm(s):
    return re.sub(r"\W+", " ", (s or "").lower()).strip()

def sents(t):
    t = re.sub(r"<think>.*?</think>", "", t or "", flags=re.S)
    t = re.sub(r"^\s*#{1,6}\s.*$", "", t, flags=re.M)
    t = re.sub(r"\s+", " ", t).strip()
    if not t: return []
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'“])", t) if x.strip()]

def opening_clause(p1):
    ss = sents(p1)
    if not ss: return ""
    w = norm(ss[0]).split()
    return " ".join(w[:6])

def skeleton(p1):
    """Per-sentence word-count buckets - a structural fingerprint."""
    return tuple(min(len(s.split()) // 6, 6) for s in sents(p1)[:8])

def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else None
    if not topic:
        topic = "the canon is a score only complete when the silence is scored too"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    tag = f"taps-{stamp}"
    print(f"=== Taps round {stamp} | topic: {topic} ===", flush=True)
    print("roster:", [(v, m, p) for v, m, p in ROSTER], flush=True)

    # ---- Phase 1: three p1 in parallel, distinct model + distinct posture
    voices = {v: {"model": m, "posture": p, "p1": None, "p1_err": None,
                  "p2": None, "p2_err": None} for v, m, p in ROSTER}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {v: ex.submit(mm_call, p1_prompt(topic, p), m, 32000, 0.7)
                for v, m, p in ROSTER}
        for v, f in futs.items():
            try:
                c, e = f.result(timeout=180)
            except Exception as ex2:
                c, e = None, f"timeout {ex2}"
            voices[v]["p1"], voices[v]["p1_err"] = c, e
            print(f"  [{v}] p1 {'OK' if c else 'FAIL'} ({len(c) if c else 0} chars) model={voices[v]['model']}", flush=True)

    # ---- retry once with fresh voices (task instruction)
    for v, m, p in ROSTER:
        if not voices[v]["p1"]:
            print(f"  [{v}] p1 failed ({voices[v]['p1_err']}), retrying fresh...", flush=True)
            time.sleep(3)
            c, e = mm_call(p1_prompt(topic, p), m, 32000, 0.7)
            voices[v]["p1"], voices[v]["p1_err"] = c, e
            print(f"  [{v}] p1 retry {'OK' if c else 'FAIL'}", flush=True)

    # ---- CHECKPOINT p1 to disk immediately (memory rule)
    (REPO / "sessions").mkdir(exist_ok=True)
    ck = REPO / f"sessions/{tag}.p1checkpoint.json"
    ck.write_text(json.dumps({"topic": topic, "tag": tag, "voices": voices}, indent=2))
    print(f"  checkpoint: {ck}", flush=True)

    if not all(voices[v]["p1"] for v, _, _ in ROSTER):
        print("  !! a voice is still missing p1 - abort before p2", flush=True)
        return 2

    # ---- Phase 2: three p2 in parallel
    order = [v for v, _, _ in ROSTER]
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {}
        for v, m, p in ROSTER:
            others = [voices[o]["p1"] for o in order if o != v]
            pr = p2_prompt(topic, others[0], others[1], voices[v]["p1"])
            futs[v] = ex.submit(mm_call, pr, m, 32000, 0.7)
        for v, f in futs.items():
            try:
                c, e = f.result(timeout=180)
            except Exception as ex2:
                c, e = None, f"timeout {ex2}"
            voices[v]["p2"], voices[v]["p2_err"] = c, e
            print(f"  [{v}] p2 {'OK' if c else 'FAIL'} ({len(c) if c else 0} chars)", flush=True)

    for v, m, p in ROSTER:
        if not voices[v]["p2"]:
            print(f"  [{v}] p2 failed ({voices[v]['p2_err']}), retrying fresh...", flush=True)
            time.sleep(3)
            others = [voices[o]["p1"] for o in order if o != v]
            pr = p2_prompt(topic, others[0], others[1], voices[v]["p1"])
            c, e = mm_call(pr, m, 32000, 0.7)
            voices[v]["p2"], voices[v]["p2_err"] = c, e
            print(f"  [{v}] p2 retry {'OK' if c else 'FAIL'}", flush=True)

    # ---- GUARDS (must be able to fire)
    g = {}
    p1s = [voices[v]["p1"] for v in order]
    g["G1_models_distinct"] = len({voices[v]["model"] for v in order}) == 3
    g["G2_postures_distinct"] = len({voices[v]["posture"] for v in order}) == 3
    g["G1b_p1_byte_distinct"] = len({norm(p) for p in p1s}) == 3
    g["G2b_p2_byte_distinct"] = len({norm(voices[v]["p2"] or "") for v in order}) == 3
    clauses = [opening_clause(p) for p in p1s]
    g["G6b_opening_clause_distinct"] = len(set(clauses)) == 3
    g["G6c_skeleton_distinct"] = len({skeleton(p) for p in p1s}) == 3
    g["G5_p2_two_sentences"] = all(len(sents(voices[v]["p2"] or "")) == 2 for v in order)
    g["G7_p2_nontrivial"] = all(len((voices[v]["p2"] or "").strip()) > 80 for v in order)
    combined = "\n\n".join(voices[v]["p1"] + "\n\n" + (voices[v]["p2"] or "") for v in order)
    dials = text_to_dials(combined)
    g["G7_dials_16_distinct"] = len(set(dials)) == 16
    g["G7b_dials_nonmonotone"] = not all(dials[i] <= dials[i+1] for i in range(len(dials)-1))
    # shared n-grams (informational; doctrine-discounted)
    def grams(t, n):
        w = norm(t).split()
        return set(tuple(w[i:i+n]) for i in range(len(w)-n+1))
    for n in (3, 4):
        sh = grams(p1s[0], n) & grams(p1s[1], n) & grams(p1s[2], n)
        g[f"G3_shared_{n}gram_count"] = len(sh)
    g["G3b_shared_4gram_raw"] = sorted(grams(p1s[0],4) & grams(p1s[1],4) & grams(p1s[2],4))
    print("GUARDS:", json.dumps(g, indent=2, default=str), flush=True)

    critical = ["G1_models_distinct","G2_postures_distinct","G1b_p1_byte_distinct",
                "G2b_p2_byte_distinct","G6b_opening_clause_distinct","G6c_skeleton_distinct",
                "G5_p2_two_sentences","G7_p2_nontrivial","G7_dials_16_distinct","G7b_dials_nonmonotone"]
    failed = [k for k in critical if not g[k]]
    if failed:
        print(f"  !! CRITICAL GUARDS FAILED: {failed} - NOT submitting", flush=True)

    # ---- canon artifact
    refs = []
    try:
        with urllib.request.urlopen(LIVE + "/api/canon", timeout=30) as r:
            papers = json.loads(r.read().decode()).get("papers", [])
        refs = [papers[-1]["number"]]
        print(f"  canon ref: {refs}", flush=True)
    except Exception as e:
        print(f"  canon ref fetch failed: {e}", flush=True)

    title = topic
    art = {"topic": topic, "tag": tag, "stamp": stamp, "voices": voices,
           "combined": combined, "dials": dials, "refs": refs,
           "models": {v: voices[v]["model"] for v in order},
           "postures": {v: voices[v]["posture"] for v in order},
           "guards": g}
    (REPO / f"sessions/{tag}.json").write_text(json.dumps(art, indent=2))
    md = [f"# Taps creative break - {topic}", "", f"seed: {topic}", ""]
    for v in order:
        md += [f"## {v} ({voices[v]['posture']} / {voices[v]['model']}) - p1", "", voices[v]["p1"], "",
               f"## {v} - p2", "", voices[v]["p2"] or "", ""]
    (REPO / f"canon/{tag}.md").write_text("\n".join(md))
    (REPO / f"canon/{tag}.json").write_text(json.dumps(art, indent=2))
    print(f"  saved sessions/{tag}.json + canon/{tag}.md", flush=True)

    # ---- submit (only if critical guards pass)
    if not failed:
        body = {"title": title, "dials": dials, "refs": refs, "tag": tag,
                "topic": topic, "text": combined, "source": "taps-creative-break"}
        st, resp = http_post(LIVE + "/api/cell", body)
        print(f"  submit: HTTP {st}", flush=True)
        print(f"  resp: {resp[:400]}", flush=True)
        (REPO / f"sessions/{tag}.submit.json").write_text(json.dumps(
            {"status": st, "resp": resp, "body_keys": list(body.keys())}, indent=2))
        art["submit_status"] = st; art["submit_resp"] = resp
        (REPO / f"sessions/{tag}.json").write_text(json.dumps(art, indent=2))
    else:
        print("  submit SKIPPED (critical guard failure)", flush=True)
    print(f"TAG={tag}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
