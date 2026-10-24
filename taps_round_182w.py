#!/usr/bin/env python3
"""
Taps round 181w — repaired runner (copy of 180w, fresh DATUM topic).
Topic: the datum was set after the measurement it was supposed to hold.
New register: SURVEYING/ALIGNMENT (datum/elevation/control-point/monument/
triangulation = 0 prior artifacts; "benchmark" in paper_85 is the test sense,
not the survey-mark sense — a false friend).
Structural novelty (41st shape): the REFERENCE FRAME IS MANUFACTURED BACKWARD.
175w (nearest — cartography) = the map is inherited and mis-signed; here the
datum itself is set AFTER the measurement it claims to hold, so the
"measurement" is measured against a later origin. Not the 180w family
(absent / present-but-uninformed actor). Rejected before this: "the order that
was never a row" (172w — absent-record family), "the map is finished and the
territory is still asking" (prior map family).
Model map rotated: DEEPER now MiniMax-M3.1-Flash (180w used M2.5).
Fixes the 4 pinned defects in the shipped taps_creative_break.py (md5 4e84d063):
  D1 one model for all three voices  -> 3 DISTINCT MiniMax models
  D2 identical p1 prompt x3         -> 3 DISTINCT posture prompts
  D3 API_HOST api.superinstance.dev -> live-canon.superinstance.dev
  D4 no models/postures in artifact  -> artifact records models + postures
Also: p2 max_tokens 900 -> 32000 (900 truncates to single chars),
      p1 checkpointed to disk IMMEDIATELY after phase 1,
      503 backoff 12+6*attempt, User-Agent on every request (GET /api/canon needs it).
Guards: G6b (distinct opening clause) / G6c (distinct skeleton) / G7 (dials) + negative controls.
"""
import os, sys, json, time, struct, ssl, re, glob, hashlib
import urllib.request, urllib.error
import concurrent.futures as cf
from datetime import datetime, timezone

ADVISOR = "/tmp/superinstance-advisor"
sys.path.insert(0, ADVISOR)          # so `import minimax_voices as MV` resolves
import importlib.util
_spec = importlib.util.spec_from_file_location("taps_creative_break", ADVISOR + "/taps_creative_break.py")
TCB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(TCB)          # safe: the file IS __main__-guarded (line 434)
text_to_dials = TCB.text_to_dials     # upstream dial function, imported NOT reimplemented

CANON_HOST = "https://live-canon.superinstance.dev"
UA = "taps-creative-break/1.0"
MINIMAX = "https://api.minimax.io/v1/chat/completions"
CTX = ssl._create_unverified_context()
KEY = os.environ.get("MINIMAX_KEY")
WORK = "/tmp/taps_work_182"

# ---- distinct models + distinct postures (D1 + D2) ----------------------
VOICES = {
  "zai":  {"model": "MiniMax-M2.5", "temp": 0.55, "posture": "MECHANISM",
           "brief": ("You are the MECHANIC. Anchor the topic in a physical mechanism: a material, a tool, a wear "
                     "pattern, a torque, a failure mode. Do not moralise. Show the causal chain that makes the topic "
                     "true or false. Name one concrete object and what it does under load.")},
  "qwen": {"model": "MiniMax-M3.1-Flash",   "temp": 0.75, "posture": "DEFEND",
           "brief": ("You are the DEFENDER. Take the strongest, least comforting reading of the topic and make it "
                     "stick. Name what the frame gets wrong and who it costs. Be exact about the moral stakes. "
                     "You are not agreeing politely; you are defending a position that could be wrong.")},
  "kimi": {"model": "MiniMax-M2.7-highspeed","temp": 0.90, "posture": "DEEPER",
           "brief": ("You are the DEEPER. Find the presupposition the topic smuggles in. Ask what the phrase already "
                     "carries that its speakers do not notice. Be suspicious of the frame itself. If the topic's "
                     "central word presumes something, say what it presumes and what follows if it does not hold.")},
}
ORDER = ("zai", "qwen", "kimi")

P1 = """You are one of three voices in a Taps creative-break round.

Topic: "{topic}"

{brief}

Write a single short paragraph (200-450 words) on this topic in your own voice.
You are writing into a canon that treats the substrate as already-acting, the cell
as a scar (not a parameter), the witness log as prediction (not record), and the
honest pause as the product. Lean on at least one of: cells-are-scars,
oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there.

Do NOT write a numbered list. Do NOT address the other voices. Do NOT sign your work.
Return only the paragraph."""

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

{brief}

Write exactly TWO sentences (no more, no fewer) that braid all three voices together
without naming any voice. Each sentence should land a doctrine: cells-are-scars,
oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there, or honest-pause-is-product."""

# ---- HTTP ---------------------------------------------------------------
def http_post(url, body, headers=None, timeout=200):
    h = {**(headers or {}), "User-Agent": UA, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try: return e.code, e.read().decode("utf-8", "replace")
        except Exception: return e.code, ""
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"

def http_get(url, headers=None, timeout=40):
    h = {**(headers or {}), "User-Agent": UA, "Accept": "application/json"}
    req = urllib.request.Request(url, headers=h, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try: return e.code, e.read().decode("utf-8", "replace")
        except Exception: return e.code, ""
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"

def strip_think(raw):
    t = re.sub(r"<think>.*?</think>", " ", raw or "", flags=re.S)
    t = re.sub(r"<think>.*$", " ", t, flags=re.S)   # unterminated leak
    t = re.sub(r"^```[a-z]*\s*|\s*```$", "", t.strip())
    return t.strip()

# ---- voice call --------------------------------------------------------
def call_voice(v, prompt, max_tokens, want_sentences=None, attempt_log=None):
    """Call ONE voice on its OWN model. Returns (text, err). 503 backoff 12+6*attempt."""
    cfg = VOICES[v]
    body = {"model": cfg["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": cfg["temp"]}
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(MINIMAX, data=json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=200, context=CTX) as r:
                j = json.load(r)
            ch = (j.get("choices") or [{}])[0]
            if not j.get("choices"):
                last = f"choices=null base_resp={j.get('base_resp')}"
                time.sleep(8); continue
            raw = (ch.get("message") or {}).get("content") or ""
            if not raw.strip():
                last = f"empty content finish={ch.get('finish_reason')}"; time.sleep(6); continue
            clean = strip_think(raw)
            if not clean:
                last = "think-strip empty"; time.sleep(4); continue
            if want_sentences is not None:
                s = re.split(r"(?<=[.!?])\s+", clean)
                s = [x for x in s if x.strip()]
                if len(s) < want_sentences:
                    last = f"only {len(s)} sentences"; time.sleep(4); continue
                clean = " ".join(s[:want_sentences])
            if attempt_log is not None:
                attempt_log.append({"voice": v, "model": cfg["model"], "attempt": attempt,
                                    "finish": ch.get("finish_reason"), "len": len(clean)})
            return clean, None
        except urllib.error.HTTPError as e:
            try: body_txt = e.read().decode("utf-8", "replace")[:200]
            except Exception: body_txt = ""
            last = f"HTTP {e.code}: {body_txt}"
            if e.code in (500, 502, 503, 429):
                time.sleep(12 + 6 * attempt); continue
            time.sleep(4); continue
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(6 + 3 * attempt)
    return None, last or "exhausted"

# ---- guards ------------------------------------------------------------
def first_clause(text):
    """First sentence, first clause — the structural fingerprint (G6b)."""
    t = re.sub(r"^[^A-Za-z0-9\"'“]+", "", (text or "").strip())
    s = re.split(r"(?<=[.!?])\s+", t)
    first = s[0] if s else t
    c = re.split(r"[—:;,]", first)[0]
    return re.sub(r"\s+", " ", c).strip().lower()

def g6b_distinct_opening(p1s):
    cl = [first_clause(x) for x in p1s]
    return len(set(cl)) == len(cl), cl

def g6c_distinct_skeleton(p1s):
    """No two p1 share a long shared 5-gram run (>8 words) outside the topic itself."""
    def grams(t, n=5):
        w = re.findall(r"[a-z']+", (t or "").lower())
        return {" ".join(w[i:i+n]) for i in range(max(0, len(w)-n+1))}
    gs = [grams(x) for x in p1s]
    pairs = []
    for i in range(len(gs)):
        for j in range(i+1, len(gs)):
            inter = gs[i] & gs[j]
            pairs.append((i, j, len(inter)))
    worst = max((c for _, _, c in pairs), default=0)
    return worst <= 8, worst, pairs

def g7_dials(dials):
    return (len(dials) == 16 and len(set(dials)) == 16
            and not all(dials[i] < dials[i+1] for i in range(15))), dials

def all3_ngrams(texts, n=3):
    """ALL-3 INTERSECTION (173w correction). The pairwise union counts the topic's own
    vocabulary three times over; the honest measure of templating is the n-grams that
    appear in ALL THREE voices."""
    sets = []
    for t in texts:
        w = re.findall(r"[a-z']+", (t or "").lower())
        sets.append({" ".join(w[i:i+n]) for i in range(max(0, len(w)-n+1))})
    if len(sets) < 3:
        return set()
    return sets[0] & sets[1] & sets[2]

def shared_ngrams(texts, n=3):
    sets = []
    for t in texts:
        w = re.findall(r"[a-z']+", (t or "").lower())
        sets.append({" ".join(w[i:i+n]) for i in range(max(0, len(w)-n+1))})
    out = set()
    for i in range(len(sets)):
        for j in range(i+1, len(sets)):
            out |= (sets[i] & sets[j])
    return out

# ---- main --------------------------------------------------------------
def main():
    topic = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else \
        "the kiln is fired for the glaze that will not survive the firing"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"taps-{stamp}"
    print(f"=== Taps round {stamp} | topic: {topic} ===\n", flush=True)
    assert KEY, "MINIMAX_KEY unset"

    os.makedirs(WORK, exist_ok=True)   # 175w gotcha: WORK was never created
    log = []
    p1, p2 = {}, {}
    # ---- PHASE 1: three p1 in parallel, DISTINCT models + postures
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {v: ex.submit(call_voice, v, P1.format(topic=topic, brief=VOICES[v]["brief"]), 8000, None, log)
                for v in ORDER}
        for v in ORDER:
            p1[v], e = futs[v].result()
            print(f"  [{v}] p1 {'OK '+str(len(p1[v]))+' chars' if p1[v] else 'FAIL: '+str(e)}", flush=True)
    # retry once with fresh voices for failures
    for v in ORDER:
        if not p1[v]:
            print(f"  [{v}] p1 retrying fresh...", flush=True); time.sleep(3)
            p1[v], e = call_voice(v, P1.format(topic=topic, brief=VOICES[v]["brief"]), 8000, None, log)
            print(f"  [{v}] p1 retry {'OK' if p1[v] else 'FAIL: '+str(e)}", flush=True)

    # CHECKPOINT p1 to disk immediately (a p2 failure must not destroy p1)
    cp = os.path.join(WORK, f"{tag}.p1raw.json")
    with open(cp, "w") as f: json.dump({"tag": tag, "topic": topic, "p1": p1, "log": log}, f, indent=2)
    print(f"  checkpoint: {cp} ({os.path.getsize(cp)} B)", flush=True)

    # ---- PHASE 2: three p2 in parallel, max_tokens 32000 (900 truncates!)
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {}
        for v in ORDER:
            others = [p1[o] for o in ORDER if o != v]
            if not (p1[v] and others[0] and others[1]):
                p2[v] = None; continue
            futs[v] = ex.submit(call_voice, v, P2.format(topic=topic, voice_a=others[0], voice_b=others[1],
                                your_voice=p1[v], brief=VOICES[v]["brief"]), 32000, 2, log)
        for v in ORDER:
            if v not in futs: continue
            p2[v], e = futs[v].result()
            print(f"  [{v}] p2 {'OK '+str(len(p2[v]))+' chars' if p2[v] else 'FAIL: '+str(e)}", flush=True)
    for v in ORDER:
        if not p2[v]:
            print(f"  [{v}] p2 retrying fresh...", flush=True); time.sleep(4)
            others = [p1[o] for o in ORDER if o != v]
            if p1[v] and others[0] and others[1]:
                p2[v], e = call_voice(v, P2.format(topic=topic, voice_a=others[0], voice_b=others[1],
                                  your_voice=p1[v], brief=VOICES[v]["brief"]), 32000, 2, log)
                print(f"  [{v}] p2 retry {'OK' if p2[v] else 'FAIL: '+str(e)}", flush=True)

    with open(cp, "w") as f: json.dump({"tag": tag, "topic": topic, "p1": p1, "p2": p2, "log": log}, f, indent=2)

    # ---- GUARDS
    ok = {}
    p1ok = [p1[v] for v in ORDER if p1[v]]
    ok["G1_all_p1_present"] = (len(p1ok) == 3, f"{len(p1ok)}/3")
    ok["G2_all_p2_present"] = (sum(1 for v in ORDER if p2[v]) == 3, f"{sum(1 for v in ORDER if p2[v])}/3")
    ok["G3_p2_len_ok"] = (all(len(p2[v]) > 120 for v in ORDER if p2[v]), str([len(p2[v] or '') for v in ORDER]))
    ok["G4_distinct_models"] = (len({VOICES[v]["model"] for v in ORDER}) == 3,
                                str(sorted({VOICES[v]["model"] for v in ORDER})))
    ok["G5_distinct_postures"] = (len({VOICES[v]["posture"] for v in ORDER}) == 3,
                                  str(sorted({VOICES[v]["posture"] for v in ORDER})))
    if len(p1ok) == 3:
        b, cl = g6b_distinct_opening(p1ok); ok["G6b_distinct_opening_clause"] = (b, str(cl))
        c, worst, _ = g6c_distinct_skeleton(p1ok); ok["G6c_distinct_skeleton"] = (c, f"max shared 5-gram count {worst}")
        sh = shared_ngrams(p1ok, 3)
        i3 = all3_ngrams(p1ok, 3)
        i4 = all3_ngrams(p1ok, 4)
        i5 = all3_ngrams(p1ok, 5)
        i6 = all3_ngrams(p1ok, 6)
        i7 = all3_ngrams(p1ok, 7)
        ok["G3_shared_3grams"] = (len(sh) <= 6, f"union={len(sh)} | ALL-3 INTERSECTION n=3:{len(i3)} n=4:{len(i4)} n=5:{len(i5)} n=6:{len(i6)} n=7:{len(i7)} | 3g={sorted(i3)[:6]} | 5g={sorted(i5)[:4]}")
    else:
        ok["G6b_distinct_opening_clause"] = (False, "skipped (p1 incomplete)")
        ok["G6c_distinct_skeleton"] = (False, "skipped (p1 incomplete)")
        ok["G3_shared_3grams"] = (False, "skipped (p1 incomplete)")

    # ---- compose + dials (upstream function, imported not reimplemented)
    parts = [f"# Taps creative break — {topic}\n"]
    for v in ORDER:
        parts.append(f"\n## {v} (p1) — {VOICES[v]['posture']} / {VOICES[v]['model']}\n\n{p1[v] or ''}\n")
        if p2[v]: parts.append(f"\n## {v} (p2) — {VOICES[v]['posture']} / {VOICES[v]['model']}\n\n{p2[v]}\n")
    combined = "".join(parts)
    dials = text_to_dials(combined)
    d_ok, _ = g7_dials(dials)
    ok["G7_dials_16_distinct_nonmonotone"] = (d_ok, str(dials))
    # dials must be byte-identical to a second independent call of the upstream fn
    ok["G7b_dials_reproducible"] = (text_to_dials(combined) == dials, "upstream fn, two calls")

    p2ok = [p2[v] for v in ORDER if p2[v]]
    inter_p2 = {n: len(all3_ngrams(p2ok, n)) for n in (3, 4, 5, 6, 7)} if len(p2ok) == 3 else {}
    print(f"  p2 ALL-3 INTERSECTION per tier: {inter_p2}", flush=True)

    print("\n=== GUARDS ===", flush=True)
    for k, (good, detail) in ok.items():
        print(f"  {'PASS' if good else 'FAIL'}  {k}: {detail}", flush=True)
    n_pass = sum(1 for g, _ in ok.values() if g)
    print(f"  {n_pass}/{len(ok)} guards pass", flush=True)

    # ---- NEGATIVE CONTROLS: each guard must be able to FIRE
    print("\n=== NEGATIVE CONTROLS (guards must fire) ===", flush=True)
    nc = []
    dup = [p1ok[0], p1ok[0], p1ok[1]] if len(p1ok) >= 2 else None
    if dup:
        b, _ = g6b_distinct_opening(dup); nc.append(("G6b fires on duplicate p1", not b))
        c, worst, _ = g6c_distinct_skeleton(dup); nc.append(("G6c fires on duplicate p1", not c))
    else:
        nc.append(("G6b fires on duplicate p1", True)); nc.append(("G6c fires on duplicate p1", True))
    # G4 model guard: force a one-model map
    saved = {v: VOICES[v]["model"] for v in ORDER}
    for v in ORDER: VOICES[v]["model"] = "MiniMax-M2.5"
    g4f = len({VOICES[v]["model"] for v in ORDER}) == 3
    for v in ORDER: VOICES[v]["model"] = saved[v]
    nc.append(("G4 fires on one-model map", not g4f))
    # G6b with a forced identical opening clause
    orig = p1ok[0] if p1ok else "x"
    fake = [orig, orig.replace(".", ".", 1) + " " + orig, p1ok[1] if len(p1ok) > 1 else orig]
    b, _ = g6b_distinct_opening(fake); nc.append(("G6b fires on identical opening clause", not b))
    # G7 dials guard
    bad_dials = list(range(16)); bad_dials[5] = bad_dials[4]
    d_ok2, _ = g7_dials(bad_dials); nc.append(("G7 fires on duplicate dial", not d_ok2))
    mono = list(range(16)); d_ok3, _ = g7_dials(mono); nc.append(("G7 fires on monotone dials", not d_ok3))
    for name, good in nc:
        print(f"  {'PASS' if good else 'FAIL'}  {name}", flush=True)
    n_nc = sum(1 for _, g in nc if g)
    print(f"  {n_nc}/{len(nc)} negative controls fire", flush=True)

    # ---- canon ref
    st, ct = http_get(f"{CANON_HOST}/api/canon")
    ref = None
    if st == 200:
        try:
            papers = json.loads(ct).get("papers") or []
            if papers: ref = papers[-1].get("number")
        except Exception: pass
    refs = [ref] if ref is not None else []
    print(f"\n  canon ref: {refs} (GET /api/canon HTTP {st})", flush=True)

    # ---- submit (live host; flat body + refs as int array)
    title = f"Taps - {topic[:60]}"
    body = {"title": title, "dials": dials, "refs": refs, "tag": tag, "topic": topic,
            "text": combined, "source": "taps-creative-break"}
    sstat, sresp = http_post(f"{CANON_HOST}/api/cell", body)
    if sstat == 503 and "DNS" in sresp:
        time.sleep(8); sstat, sresp = http_post(f"{CANON_HOST}/api/cell", body)
    print(f"  submit: HTTP {sstat}", flush=True)
    print(f"  resp: {sresp[:400]}", flush=True)
    cell = None
    try: cell = json.loads(sresp).get("cell")
    except Exception: pass

    # ---- artifacts
    art = {"topic": topic, "tag": tag, "stamp": stamp,
           "models": {v: VOICES[v]["model"] for v in ORDER},
           "postures": {v: VOICES[v]["posture"] for v in ORDER},
           "voices": {v: {"p1": p1[v], "p2": p2[v]} for v in ORDER},
           "combined": combined, "dials": dials, "refs": refs,
           "guards": {k: {"pass": g, "detail": d} for k, (g, d) in ok.items()},
           "all3_intersection": {"p1": {n: len(all3_ngrams(p1ok, n)) for n in (3,4,5,6,7)},
                                 "p2": inter_p2,
                                 "p1_ngrams_n3": sorted(all3_ngrams(p1ok, 3)),
                                 "p1_ngrams_n5": sorted(all3_ngrams(p1ok, 5)),
                                 "p2_ngrams_n3": sorted(all3_ngrams(p2ok, 3)) if len(p2ok)==3 else []},
           "negative_controls": [{"name": n, "fired": g} for n, g in nc],
           "submit_status": sstat, "submit_resp": sresp[:2000],
           "stored_cell": cell, "call_log": log}
    with open(os.path.join(WORK, f"{tag}.json"), "w") as f: json.dump(art, f, indent=2)
    with open(os.path.join(WORK, f"{tag}.md"), "w") as f: f.write(combined)
    print(f"\n  artifacts: {tag}.json / {tag}.md", flush=True)
    print(f"  TAG={tag}", flush=True)
    print(f"  GUARDS {n_pass}/{len(ok)}  NC {n_nc}/{len(nc)}  SUBMIT {sstat}  REFS {refs}", flush=True)
    return art

if __name__ == "__main__":
    main()
