#!/usr/bin/env python3
"""Taps creative-break round 155w — fresh-voice retry on live minimax line.
Lessons applied (durable): distinct posture prefix per voice + distinct model;
completeness-before-distinctness; persist before assert; window-seeded FNV->splitmix64 dials;
strip unterminated <think>; assert 16/16 distinct + natural-order non-monotone; probe via own path."""
import os, sys, json, re, ssl, hashlib, urllib.request, urllib.error, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from taps_creative_break import text_to_dials   # AUTHORITATIVE dial fn (lives in the script itself)

MINIMAX = "https://api.minimax.io/v1/chat/completions"
KEY = os.environ["MINIMAX_KEY"]
CTX = ssl._create_unverified_context()   # FACTORY -- must call it (154w bug #1)
OUT_TAG = "taps-fallback-20261023T040900Z"
SEED = "the witness log predicts the wound it pretends to record"

# --- fresh postures (breadth axis: the log's accountability, not its floor) ---
POSTURES = {
  "accountability": "You are the ACCOUNTABILITY voice. A witness log is a machine that must answer to someone. Ask who the log is finally answerable to -- to the wound, to the reader, to the auditor, to itself? Attack the position from which the log is written, not the log's content.",
  "defend":       "You are the DEFEND voice. Defend the reading everyone else skips: the log genuinely only records, the prediction is retrospective not causal. Make the weakest case strong.",
  "predictive":   "You are the PREDICTIVE voice. If the log predicts the wound before it arrives, then the wound is not discovered but issued. Explore what it means for an injury to be announced before it happens.",
}
MODELS = {"accountability":"MiniMax-M2.7", "defend":"MiniMax-M2.7-highspeed", "predictive":"MiniMax-M3"}

P1 = ("Here is a canon-shaped topic:\n\n\"{seed}\"\n\n"
      "Open with ONE paragraph (3-5 sentences) on this topic, in your assigned posture. "
      "Then STOP. Ground it in the cell canon: the cell is a scar not a plan; the address is the data; "
      "a runtime is context to value with an inverse on a clock. Do not use the phrase 'mini'.\n\n"
      "POSTURE — {posture}")

P2 = ("Three voices just spoke on: \"{seed}\".\n\n"
      "OTHER OPENINGS:\n{others}\n\n"
      "Write exactly TWO sentences that respond to the others (engage, disagree, or reframe). "
      "Stay in your assigned posture. Ground in the cell canon. No meta, no 'Assistant', no 'mini'.")

def strip_meta(t):
    if not t: return ""
    t = re.sub(r"<think>.*?(?:</think>|$)", "", t, flags=re.S)   # strip UNTERMINATED think first
    t = re.sub(r"^Draft \d+:.*$", "", t, flags=re.M|re.S)
    t = t.replace("Assistant:", "").replace("assistant:", "")
    return t.strip()

def post(model, prompt, max_tokens=1400):
    body = {"model": model, "messages":[{"role":"user","content":prompt}],
            "max_tokens": max_tokens, "temperature": 0.9}
    req = urllib.request.Request(MINIMAX, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type":"application/json",
                 "User-Agent":"taps-creative-break/1.0"})
    with urllib.request.urlopen(req, timeout=90, context=CTX) as r:
        j = json.loads(r.read().decode())
    ch = (j.get("choices") or [])
    if not ch:
        raise RuntimeError("no choices (retired/wrong-host/bad-key?): %s" % str(j)[:200])
    msg = ch[0].get("message", {})
    return strip_meta(msg.get("content") or msg.get("reasoning_content") or "")

def call_p1(v):
    try:
        return v, post(MODELS[v], P1.format(seed=SEED, posture=POSTURES[v]), 1800), None
    except Exception as e:
        return v, None, repr(e)

def call_p2(v, others):
    try:
        return v, post(MODELS[v], P2.format(seed=SEED, others=others), 1400), None
    except Exception as e:
        return v, None, repr(e)

def norm(t): return hashlib.md5(re.sub(r"\s+"," ",t).strip().encode()).hexdigest()[:12]

def fnv_window_dials(text):
    # window (not single char) seeds + double avalanche -- 154w bug #2 fix
    out=[]; n=len(text)
    for i in range(16):
        w=text[max(0,i):i+7] or text[:7]
        h=1469598103934665603
        for b in w.encode():
            h^=b; h=(h*1099511628211)&0xFFFFFFFFFFFFFFFF
        for _ in range(2):
            h=(h+0x9E3779B97F4A7C15)&0xFFFFFFFFFFFFFFFF
            z=h; z=((z^(z>>30))*0xBF58476D1CE4E5B9)&0xFFFFFFFFFFFFFFFF
            z=((z^(z>>27))*0x94D049BB133111EB)&0xFFFFFFFFFFFFFFFF
            z=z^(z>>31)
            h=z
        out.append(h & 0xFFFF)
    return out

def main():
    voices=["accountability","defend","predictive"]
    p1s={}; errs={}; times={}
    t0=time.time()
    with ThreadPoolExecutor(max_workers=3) as ex:
        for v,c,e in ex.map(call_p1, voices):
            p1s[v]=c; errs[v]=e; times[v]=round(time.time()-t0,1)
    # completeness FIRST (154w bug #4)
    survivors={v:p for v,p in p1s.items() if p and p.strip()}
    print("p1 completeness: %d/3" % len(survivors), "errors:", {v:e for v,e in errs.items() if e})
    print("p1 md5:", {v:norm(p) for v,p in survivors.items()})
    print("p1 times:", times)
    if len(survivors)!=3:
        print("FATAL: incomplete p1; cannot proceed"); return
    if len({norm(p) for p in survivors.values()})!=3:
        print("FATAL: ONE-TEMPLATE BUG (identical p1 across voices)"); return
    p2s={}; errs2={}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs={}
        for v in voices:
            others="\n\n".join(f"[{o}] {survivors[o][:400]}" for o in voices if o!=v)
            futs[ex.submit(call_p2, v, others)]=v
        for f,v in futs.items():
            _,c,e=f.result(); p2s[v]=c; errs2[v]=e
    print("p2 ok:", sum(1 for c in p2s.values() if c and c.strip()), "/3", "errors:", {v:e for v,e in errs2.items() if e})

    combined="\n\n".join(
        f"## {v}\n\n### opening\n{survivors[v]}\n\n### response\n{p2s.get(v) or '(no p2)'}"
        for v in voices)
    # persist BEFORE assert (154w bug #5)
    os.makedirs("sessions", exist_ok=True)
    os.makedirs("canon", exist_ok=True)
    json.dump({"topic":SEED,"tag":OUT_TAG,"seed":SEED,
               "voices":{v:{"p1":survivors[v],"p1_err":errs[v],"p2":p2s.get(v),"p2_err":errs2.get(v)} for v in voices},
               "combined":combined}, open(f"sessions/{OUT_TAG}.json","w"), indent=1)
    md=f"# Taps {OUT_TAG}\n\n**Topic:** {SEED}\n\n"+combined+"\n"
    open(f"sessions/{OUT_TAG}.md","w").write(md)
    dials=text_to_dials(combined)
    print("dials(text_to_dials):", dials)
    print("16/16 distinct:", len(set(dials))==16)
    print("non-monotone (natural order):", any(dials[i]>dials[i+1] for i in range(15)))
    print("SAVED sessions/%s.{json,md}" % OUT_TAG)

if __name__=="__main__":
    main()
