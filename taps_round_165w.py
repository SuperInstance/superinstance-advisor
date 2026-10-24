#!/usr/bin/env python3
"""Taps creative break — repaired runner (165w).

Fixes over shipped taps_creative_break.py (md5 4e84d063..., unchanged 10 wipes):
  1. THREE DISTINCT MODELS, not MiniMax-M2.5 x3 (temperature aliases).
  2. DISTINCT POSTURE PREFIX per voice (kills the shared-skeleton template).
  3. Canon host = live-canon.superinstance.dev (api.superinstance.dev/api/cell is 404).
  4. refs = [latest canon paper number], asserted NON-EMPTY after submit.
  Dials: imported directly from upstream taps_creative_break.text_to_dials.
"""
import os, sys, json, re, time, random, struct, hashlib, ssl, urllib.request, urllib.error
import concurrent.futures as cf
from datetime import datetime, timezone

ADVISOR = "/tmp/advisor"
sys.path.insert(0, ADVISOR)
import importlib.util
_spec = importlib.util.spec_from_file_location("upstream_taps", os.path.join(ADVISOR, "taps_creative_break.py"))
upstream = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(upstream)   # guarded by __main__ so no round runs
text_to_dials = upstream.text_to_dials
print("upstream dials loaded:", len(text_to_dials("probe")), flush=True)

MM_BASE = "https://api.minimax.io/v1"
CANON_HOST = "https://live-canon.superinstance.dev"
UA = "taps-creative-break/1.0"
_SSL = ssl._create_unverified_context()

# voice -> (model, posture, temperature, max_tokens)
VOICES = {
    "zai":  ("MiniMax-M2.7-highspeed", "MECHANISM", 0.55, 32000),
    "qwen": ("MiniMax-M3",             "DEFEND",    0.75, 32000),
    "kimi": ("MiniMax-M2.5",           "DEEPER",    0.9,  32000),
}

P1_PROMPT = """You are one of three voices in a Taps creative-break round.

Topic: "{topic}"

Write a single short paragraph (200-450 words) on this topic in your own voice.
You are writing into a canon that treats the substrate as already-acting, the cell
as a scar (not a parameter), the witness log as prediction (not record), and the
honest pause as the product. Lean on at least one of: cells-are-scars,
oracle-is-heard, witness-log-is-prediction, substrate-is-grown, canon-gate-is-chord,
the-stations-emerge, the-boat-was-always-there.

Do NOT write a numbered list. Do NOT address the other voices. Do NOT sign your work.
Return only the paragraph."""

POSTURE = {
 "MECHANISM": """Begin by locating the exact physical or structural condition under which the phenomenon in this topic could occur at all. Name the mechanism, the material precondition, the chain of operations that would have to run. Do not moralize, do not generalize, do not wrap up neatly: finish on the part of the chain you cannot close.""",
 "DEFEND":    """Begin by defending the topic's own frame, even where it is inconvenient. Argue for the reading that the other two voices will find too generous or too narrow, and say plainly what is at stake if that reading is right and the others are wrong. Do not summarize the other voices; they have not been written yet. Finish on the strongest version of your claim, not a summary.""",
 "DEEPER":    """Begin by asking what the topic's own vocabulary is already carrying that its speakers do not notice. Push one level below the surface claim to the condition that makes the claim legible in the first place. Do not agree and do not disagree; explain what the frame has to assume in order to be seen at all. Finish on the cost the frame has already paid.""",
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

_THINK = re.compile(r"<think>.*?</think>", re.S)

def strip_think(t):
    if not t: return ""
    o = _THINK.sub("", t)
    if "<think>" in o: o = o.split("<think>")[0]
    return o.strip()

def sent_split(text):
    t = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    t = re.sub(r"^\s*#{1,6}\s.*$", "", t, flags=re.M)
    t = re.sub(r"^\s*\*\*[^*]+\*\*\s*:?.*$", "", t, flags=re.M)
    t = re.sub(r"^\s*(Voice|MECHANISM|DEFEND|DEEPER|TEXT)\b.*$", "", t, flags=re.M | re.I)
    t = re.sub(r"\s+", " ", t).strip()
    if not t: return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'“])", t) if s.strip()]

def first_sentences(text, n):
    s = sent_split(text)
    return " ".join(s[:n]) if s else ""

def mm_call(prompt, max_tokens=32000, temperature=0.7, sentences=None, model=None, retries=3):
    key = os.environ.get("MINIMAX_KEY")
    if not key: return None, "MINIMAX_KEY unset"
    body = json.dumps({"model": model, "messages": [{"role":"user","content":prompt}],
                       "max_tokens": max_tokens, "temperature": temperature}).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(f"{MM_BASE}/chat/completions", data=body,
                headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json",
                         "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180, context=_SSL) as r:
                j = json.load(r)
            ch = (j.get("choices") or [{}])[0]
            raw = (ch.get("message") or {}).get("content") or ""
            if not raw.strip():
                last = "empty content"; time.sleep(6); continue
            clean = strip_think(raw)
            if not clean:
                last = "think-strip empty"; time.sleep(6); continue
            if sentences is not None:
                clean = first_sentences(clean, sentences)
                if not clean:
                    last = "sentence gate empty"; time.sleep(6); continue
            return clean, None
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            # 503 backoff escalates (MiniMax 503s under 3-way parallel waves)
            time.sleep(12 + 6*attempt if "503" in str(e) else 6)
    return None, last or "exhausted"

def http_post(url, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json","User-Agent":UA})
    try:
        with urllib.request.urlopen(req, timeout=60, context=_SSL) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"

def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60, context=_SSL) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"

def latest_ref():
    st, tx = http_get(f"{CANON_HOST}/api/canon")
    if st != 200: return None
    try:
        p = json.loads(tx)["papers"]
        return p[-1]["number"]
    except Exception:
        return None

def p1_prompt_for(v, topic):
    model, posture, _, _ = VOICES[v]
    return (f"[{posture}] " + P1_PROMPT.format(topic=topic) + "\n\n" + POSTURE[posture])

def run(topic):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"taps-{stamp}"
    print(f"\n=== Taps round | {tag} | topic: {topic} ===\n", flush=True)
    print("models:", {v: VOICES[v][0] for v in VOICES}, flush=True)

    p1 = {}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {v: ex.submit(mm_call, p1_prompt_for(v, topic), VOICES[v][3], VOICES[v][2], None, VOICES[v][0])
                for v in VOICES}
        for v, f in futs.items():
            try: p1[v] = f.result(timeout=240)
            except Exception as e: p1[v] = (None, f"timeout: {e}")

    # retry once with fresh voices
    for v in ("zai","qwen","kimi"):
        if p1[v][0] is None:
            print(f"  [{v}] p1 failed ({p1[v][1]}), retrying fresh...", flush=True)
            time.sleep(3)
            p1[v] = mm_call(p1_prompt_for(v, topic), VOICES[v][3], VOICES[v][2], None, VOICES[v][0])
    for v in ("zai","qwen","kimi"):
        print(f"  [{v}] p1 {'OK' if p1[v][0] else 'FAIL'} len={len(p1[v][0]) if p1[v][0] else 0} err={p1[v][1]}", flush=True)

    # CHECKPOINT p1 to disk immediately
    with open(f"/tmp/work/{tag}.p1raw.json","w") as f:
        json.dump({v:{"p1":p1[v][0],"err":p1[v][1],"model":VOICES[v][0],"posture":VOICES[v][1]} for v in VOICES}, f, indent=2)

    p2 = {}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {}
        for v in ("zai","qwen","kimi"):
            others = [p1[o][0] for o in ("zai","qwen","kimi") if o != v]
            if not (others[0] and others[1] and p1[v][0]):
                p2[v] = (None, "missing voice input"); continue
            pr = P2_PROMPT.format(topic=topic, voice_a=others[0], voice_b=others[1], your_voice=p1[v][0])
            futs[v] = ex.submit(mm_call, pr, VOICES[v][3], VOICES[v][2], 2, VOICES[v][0])
        for v, f in futs.items():
            try: p2[v] = f.result(timeout=240)
            except Exception as e: p2[v] = (None, f"timeout: {e}")

    for v in ("zai","qwen","kimi"):
        if p2[v][0] is None and "missing voice input" not in (p2[v][1] or ""):
            print(f"  [{v}] p2 failed ({p2[v][1]}), retrying fresh...", flush=True)
            time.sleep(3)
            others = [p1[o][0] for o in ("zai","qwen","kimi") if o != v]
            pr = P2_PROMPT.format(topic=topic, voice_a=others[0], voice_b=others[1], your_voice=p1[v][0])
            p2[v] = mm_call(pr, VOICES[v][3], VOICES[v][2], 2, VOICES[v][0])
    for v in ("zai","qwen","kimi"):
        print(f"  [{v}] p2 {'OK' if p2[v][0] else 'FAIL'} len={len(p2[v][0]) if p2[v][0] else 0} err={p2[v][1]}", flush=True)

    with open(f"/tmp/work/{tag}.p2raw.json","w") as f:
        json.dump({v:{"p2":p2[v][0],"err":p2[v][1]} for v in p2}, f, indent=2)

    parts = [f"# Taps creative break — {topic}\n"]
    for v in ("zai","qwen","kimi"):
        parts.append(f"\n## {v} (p1)\n\n{p1[v][0]}\n")
        if p2[v][0]: parts.append(f"\n## {v} (p2)\n\n{p2[v][0]}\n")
    combined = "".join(parts)

    dials = text_to_dials(combined)
    ref = latest_ref()
    refs = [ref] if ref is not None else []
    print(f"  dials: {dials}", flush=True)
    print(f"  refs: {refs}", flush=True)

    body = {"title": f"Taps — {topic[:60]}", "dials": dials, "refs": refs,
            "tag": tag, "topic": topic, "text": combined, "source": "taps-creative-break"}
    st, tx = http_post(f"{CANON_HOST}/api/cell", body)
    print(f"  submit: HTTP {st}", flush=True)
    print(f"  resp: {tx[:400]}", flush=True)

    art = {"topic":topic,"tag":tag,"stamp":stamp,
           "models":{v:VOICES[v][0] for v in VOICES},"postures":{v:VOICES[v][1] for v in VOICES},
           "voices":{v:{"p1":p1[v][0],"p1_err":p1[v][1],"p2":p2[v][0],"p2_err":p2[v][1]} for v in ("zai","qwen","kimi")},
           "combined":combined,"dials":dials,"refs":refs,"submit_status":st,"submit_resp":tx}
    with open(f"/tmp/work/{tag}.json","w") as f: json.dump(art,f,indent=2)
    with open(f"/tmp/work/{tag}.md","w") as f:
        f.write(combined + f"\n\n---\n\ntag: `{tag}`\nmodels: {art['models']}\npostures: {art['postures']}\nsubmit: HTTP {st}\n")
    print(f"  saved /tmp/work/{tag}.{{json,md}}", flush=True)
    return art

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else None
    if not topic:
        topic = random.choice(upstream.TOPIC_BANK)
    a = run(topic)
    print("\n=== SUMMARY ===")
    print("topic:", a["topic"])
    for v in ("zai","qwen","kimi"):
        print(f"  {v}: p1={'OK' if a['voices'][v]['p1'] else 'FAIL'} p2={'OK' if a['voices'][v]['p2'] else 'FAIL'}")
    print("tag:", a["tag"])
    print("submit:", a["submit_status"], a["submit_resp"][:200])
