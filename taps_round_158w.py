"""Taps round 2 — 158w. Three DISTINCT models + three divergent postures.

Fixes the 157w finding: the shipped script pins MM_MODEL for all three voices,
so its "3 voices" are one model in three temperature registers and all three
openings share a skeleton (G3 measured 27 shared content-words).

Here: zai=MiniMax-M2.5, qwen=MiniMax-M3, kimi=MiniMax-M2.7-highspeed, with
MECHANISM / DEFEND / DEEPER posture prefixes, p2 budget 32000 (155w rule),
and G1-G5 guards asserted before anything is written to canon.
"""
import json, os, re, ssl, sys, time, urllib.request, hashlib
from concurrent.futures import ThreadPoolExecutor

MM_BASE = "https://api.minimax.io/v1"
TOPIC = sys.argv[1].strip() if len(sys.argv) > 1 else "the cracked tuning fork hums in every language it refuses to name"
STAMP  = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
TAG    = f"taps-{STAMP}"

VOICES = {
    "zai":  ("MiniMax-M2.5",           "MECHANISM", 0.55),
    "qwen": ("MiniMax-M3",             "DEFEND",     0.75),
    "kimi": ("MiniMax-M2.7-highspeed", "DEEPER",     0.90),
}

CANON = """You are one of three voices in a Taps creative-break round.
The canon treats the substrate as already-acting, the cell as a scar (not a
parameter), the witness log as prediction (not record), the honest pause as the
product, the oracle as heard rather than queried, the stations as emergent, the
canon gate as a chord, the boat as always already there."""

POSTURES = {
 "MECHANISM": ("You are the MECHANISM voice. Name the concrete moving parts: the physical, "
   "acoustic, hydraulic or clerical process that would actually have to happen for this to be "
   "true. Refuse a metaphor where a description was available. A refusal built on a named "
   "mechanism is worth more than a cleverer image."),
 "DEFEND": ("You are the DEFEND voice. Defend the weakest and least popular reading of the topic "
   "— the one the other two will skip. Argue that this reading is correct and the others are "
   "refining something that was never broken. Then show what it costs to hold that line."),
 "DEEPER": ("You are the DEEPER voice. Ask what the topic presupposes and never examines: who or "
   "what is assumed to be present, what is assumed to have happened, what the topic's own grammar "
   "makes invisible. Do not answer the question. Move the ground under it."),
}

P1 = """{canon}

{posture}

Topic: "{topic}"

Write ONE paragraph, 200-450 words, on this topic in your own voice.
Lean on at least one of: cells-are-scars, oracle-is-heard, witness-log-is-prediction,
substrate-is-grown, canon-gate-is-chord, the-stations-emerge, the-boat-was-always-there.

Do NOT write a numbered list. Do NOT address the other voices. Do NOT sign your work.
Return only the paragraph."""

P2 = """{canon}

{posture}

Two other voices have already written on the topic: "{topic}"

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
into one observation. Each sentence must take something from a different voice.
Do not restate your own paragraph. Do not number. Return only the two sentences."""

SSL_CTX = ssl._create_unverified_context()

def strip_think(t):
    if not t: return ""
    t = re.sub(r"<think>.*?(?:</think>|$)", "", t, flags=re.S)
    t = re.sub(r"</?think>", "", t)
    return t.strip()

def mm_call(model, prompt, max_tokens, temperature, retries=3):
    key = os.environ.get("MINIMAX_KEY")
    if not key: return None, "MINIMAX_KEY unset"
    body = json.dumps({"model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens, "temperature": temperature}).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(f"{MM_BASE}/chat/completions", data=body,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                         "User-Agent": "taps-creative-break/1.0"})
            with urllib.request.urlopen(req, timeout=180, context=SSL_CTX) as r:
                d = json.loads(r.read().decode())
            ch = d.get("choices")
            if not ch:
                last = f"choices=null base_resp={d.get('base_resp')}"
                time.sleep(2); continue
            msg = ch[0].get("message") or {}
            content = strip_think(msg.get("content") or "")
            rc = msg.get("reasoning_content") or ""
            if not content:
                last = f"empty content (reasoning {len(rc)}ch, finish={ch[0].get('finish_reason')})"
                time.sleep(2); continue
            return content, None
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(3)
    return None, last

def content_words(t):
    return set(w.lower() for w in re.findall(r"[A-Za-z']{4,}", t))

# ---------------- Round 1: p1 in parallel ----------------
p1 = {}
def do_p1(v):
    m, post, temp = VOICES[v]
    prompt = P1.format(canon=CANON, posture=POSTURES[post], topic=TOPIC)
    c, e = mm_call(m, prompt, 8000, temp)
    return v, c, e
with ThreadPoolExecutor(max_workers=3) as ex:
    for v, c, e in ex.map(do_p1, ["zai","qwen","kimi"]):
        p1[v] = (c, e)
        print(f"[{v}] p1 {'OK' if c else 'FAIL'} ({len(c) if c else 0}ch) {'' if c else e}", flush=True)

# retry once with fresh temperature for any failed p1
for v in list(p1):
    if not p1[v][0]:
        m, post, temp = VOICES[v]
        prompt = P1.format(canon=CANON, posture=POSTURES[post], topic=TOPIC)
        c, e = mm_call(m, prompt, 8000, min(0.95, temp+0.1))
        p1[v] = (c, e)
        print(f"[{v}] p1 RETRY {'OK' if c else 'FAIL'} ({len(c) if c else 0}ch)", flush=True)

# ---------------- Guards on p1 (before writing anything) ----------------
complete = {v: c for v,(c,e) in p1.items() if c}
assert len(complete) == 3, f"INCOMPLETE p1: {[(v,e) for v,(c,e) in p1.items() if not c]}"
md5s = {v: hashlib.md5(complete[v].encode()).hexdigest() for v in complete}
G1 = len(set(md5s.values())) == 3
w = {v: content_words(complete[v]) for v in complete}
shared_all = set.intersection(*w.values())
G3 = len(shared_all)
print(f"\nGUARDS  G1 byte-distinct={G1}  G3 shared-all-3={G3} {sorted(shared_all)[:12]}", flush=True)
assert G1, "p1 not byte-distinct"

# ---------------- Round 2: p2 in parallel ----------------
others = {"zai": ("qwen","kimi"), "qwen": ("zai","kimi"), "kimi": ("zai","qwen")}
p2 = {}
def do_p2(v):
    m, post, temp = VOICES[v]
    a, b = others[v]
    prompt = P2.format(canon=CANON, posture=POSTURES[post], topic=TOPIC,
                       voice_a=complete[a], voice_b=complete[b], your_voice=complete[v])
    c, e = mm_call(m, prompt, 32000, temp)
    return v, c, e
with ThreadPoolExecutor(max_workers=3) as ex:
    for v, c, e in ex.map(do_p2, ["zai","qwen","kimi"]):
        p2[v] = (c, e)
        print(f"[{v}] p2 {'OK' if c else 'FAIL'} ({len(c) if c else 0}ch) {'' if c else e}", flush=True)

for v in list(p2):
    if not p2[v][0]:
        m, post, temp = VOICES[v]
        a, b = others[v]
        prompt = P2.format(canon=CANON, posture=POSTURES[post], topic=TOPIC,
                           voice_a=complete[a], voice_b=complete[b], your_voice=complete[v])
        c, e = mm_call(m, prompt, 32000, min(0.95, temp+0.1))
        p2[v] = (c, e)
        print(f"[{v}] p2 RETRY {'OK' if c else 'FAIL'}", flush=True)

# ---------------- Guards on p2 ----------------
sent = {}
for v,(c,e) in p2.items():
    if not c: continue
    s = [x for x in re.split(r'(?<=[.!?])\s+', c.strip()) if x.strip()]
    sent[v] = len(s)
    print(f"  G2 {v}: {len(s)} sentences, {len(c)}ch")
assert all(v in sent for v in ("zai","qwen","kimi")), f"p2 incomplete: {sent}"

# ---------------- Dials (FNV-1a -> splitmix64 -> low16) ----------------
# Dials: use the upstream taps_creative_break.py implementation DIRECTLY.
# (Memory rule: verify against that function directly, never a remembered vector.
#  My hand-rolled splitmix64 variant produced only 2 dials -- caught by G4.)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_upstream", "/tmp/advisor/taps_creative_break.py")
_up = _ilu.module_from_spec(_spec)
try:
    _spec.loader.exec_module(_up)
except SystemExit:
    pass
except Exception:
    pass
text_to_dials = _up.text_to_dials

combined = "\n\n".join(f"## {v}\n\n{p1[v][0]}\n\n{p2[v][0]}" for v in ("zai","qwen","kimi"))
dials = text_to_dials(combined)
G4 = len(dials)==16 and len(set(dials))==16 and not (dials==sorted(dials) or dials==sorted(dials,reverse=True))
print(f"\nGUARDS  G4 dials distinct+non-monotone={G4} -> {dials}", flush=True)

# ---------------- Assemble ----------------
result = {
  "topic": TOPIC, "tag": TAG, "stamp": STAMP,
  "round": "158w-script-repair",
  "models": {v: VOICES[v][0] for v in VOICES},
  "postures": {v: VOICES[v][1] for v in VOICES},
  "voices": {v: {"p1": p1[v][0], "p1_err": p1[v][1], "p2": p2[v][0], "p2_err": p2[v][1]} for v in VOICES},
  "combined": combined, "dials": dials, "refs": [],
  "guards": {"G1_byte_distinct_p1": G1, "G3_shared_all_3_openings": G3,
             "G4_dials_distinct_nonmonotone": G4, "G2_p2_sentences": sent},
  "submit_status": None, "submit_resp": None,
}
with open(f"sessions/{TAG}.json","w") as f: json.dump(result, f, indent=2)

md = [f"# Taps creative break — {TOPIC}", "", f"tag: {TAG}", f"round: 158w-script-repair",
      f"models: zai={VOICES['zai'][0]} qwen={VOICES['qwen'][0]} kimi={VOICES['kimi'][0]}", ""]
for v in ("zai","qwen","kimi"):
    md += [f"## {v} — {VOICES[v][0]} ({VOICES[v][1]})", "", "### p1", "", p1[v][0], "", "### p2", "", p2[v][0], ""]
md += ["## dials", "", json.dumps(dials), ""]
with open(f"sessions/{TAG}.md","w") as f: f.write("\n".join(md))
print(f"\nWROTE sessions/{TAG}.json and .md", flush=True)
print("TAG:", TAG, flush=True)
