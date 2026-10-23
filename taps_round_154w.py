#!/usr/bin/env python3
"""Taps round 154w — live voices on minimax.io, 3 distinct postures + 3 distinct models."""
import json, os, re, ssl, time, hashlib, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

SSL_CTX = ssl._create_unverified_context()
API_HOST = "https://api.superinstance.dev"
KEY = os.environ["MINIMAX_KEY"]
UA = "taps-creative-break/1.0"

SEED = (
    "A ledger kept every transaction and still could not say who was owed. "
    "The record was complete; the account was not. "
    "Someone added a column nobody had ever filled, and called the addition a debt."
)
P1_COMMON = (
    "Canon entry under consideration: " + SEED + "\n\n"
    "Open with one paragraph on this. Then write exactly 2 sentences responding to the "
    "other voices (you will be shown them).\n"
)

POSTURES = {
    "mechanism": ("MECHANISM: describe the concrete moving parts. Refuse metaphor as a "
                  "substitute for description. Name the mechanism, then the claim. ",
                  "MiniMax-M2.5-highspeed"),
    "defend":    ("DEFEND: take the weakest, most skippable reading of this claim and "
                  "argue it is the correct one. Steelman it against yourself. ",
                  "MiniMax-M2.7"),
    "deeper":    ("DEEPER: name what this topic presupposes and never examines. The seed "
                  "is not the interesting part; the floor under it is. ",
                  "MiniMax-M3"),
}
VOICES = ["mechanism", "defend", "deeper"]

TAG = "taps-fallback-20261023T030700Z"
TITLE = "the column nobody filled"

def post(path, payload, timeout=120):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(API_HOST + path, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            return r.status, r.read().decode()[:600]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:
        return 0, repr(e)

def ask(model, prompt, max_tokens=3600):
    t0 = time.time()
    req = urllib.request.Request(
        "https://api.minimax.io/v1/chat/completions",
        data=json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                         "max_tokens": max_tokens, "temperature": 0.92}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY,
                 "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=180, context=SSL_CTX) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return "", "HTTP %s %s" % (e.code, e.read().decode()[:200])
    except Exception as e:
        return "", repr(e)
    ch = d.get("choices")
    if not ch:
        return "", "choices is null (base_resp=%s)" % d.get("base_resp")
    m = ch[0].get("message", {})
    c = m.get("content") or m.get("reasoning_content") or ""
    if not c.strip():
        return "", "empty content"
    return c.strip(), None

def strip_meta(t):
    t = t.strip()
    # drop any <think>...</think> block(s) entirely
    t = re.sub(r"<think>.*?(?:</think>|$)", "", t, flags=re.S)
    # if unterminated reasoning remains, cut at the last newline before real prose
    lines = t.split("\n")
    keep = []
    for ln in lines:
        if re.match(r"^\s*(we need|need to|answer|they ask|we are|the user|possibly|maybe|let's|we can produce)", ln, re.I) and "?" not in ln and "." not in ln[-6:]:
            continue
        keep.append(ln)
    t = "\n".join(keep).strip()
    t = re.sub(r"^\s*(Could be:|Need|Then:)\s*", "", t, flags=re.M | re.I)
    return t.strip()

def split_p2(text):
    s = re.sub(r"^Draft \d+:.*$", "", text, flags=re.M).strip()
    parts = re.split(r"(?<=[.!?])\s+", s)
    return " ".join(parts[:2]).strip()

def fnv(s):
    h = 0xcbf29ce484222325
    for b in s.encode():
        h ^= b; h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h

def splitmix(x):
    x = (x + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = x; z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return x, (z ^ (z >> 31)) & 0xFFFFFFFFFFFFFFFF

def dials(text):
    out = []
    chars = [c for c in text if not c.isspace()]
    for i in range(16):
        win = "".join(chars[i*3:i*3+7]) or chars[:7]
        h, _ = splitmix(fnv(win + "|" + str(i)))
        h, _ = splitmix(h)
        out.append(h & 0xFFFF)
    return out

def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", s.lower())).strip()

def main():
    p1s, p2s, times, errs = {}, {}, {}, {}
    def one(v):
        pre, model = POSTURES[v]
        t, e = ask(model, P1_COMMON + pre, 3600)
        p1s[v], errs[v], times[v] = t, e, round(time.time() - t0, 1) if False else None
        return v
    # p1
    t0 = time.time()
    def run_p1(v):
        pre, model = POSTURES[v]
        txt, e = ask(model, P1_COMMON + pre, 3600)
        return v, txt, e, round(time.time() - t0, 1)
    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(run_p1, VOICES))
    for v, txt, e, el in res:
        p1s[v], errs[v], times[v + "_p1"] = (strip_meta(txt) if txt else ""), e, el
    ok = [v for v in VOICES if p1s[v]]
    # p2: each voice sees the other two p1s
    def run_p2(v):
        pre, model = POSTURES[v]
        others = "\n\n".join("[%s] %s" % (o, p1s[o]) for o in VOICES if o != v and p1s[o])
        others_short = "\n\n".join("[%s] %s" % (o, p1s[o][:600]) for o in VOICES if o != v and p1s[o])
        txt, e = ask(model, P1_COMMON + pre + "\nThe other voices opened with:\n\n" + others_short +
                     "\n\nWrite EXACTLY 2 sentences responding to them. No preamble.", 1400)
        out = split_p2(strip_meta(txt)) if txt else ""
        if not out.strip():
            txt2, e2 = ask(model, "Two other voices argued:\n\n" + others_short +
                            "\n\nAnswer them in exactly two sentences.", 700)
            out2 = split_p2(strip_meta(txt2)) if txt2 else ""
            if out2.strip():
                out, e = out2, e2
        return v, out, e, round(time.time() - t0, 1)
    with ThreadPoolExecutor(3) as ex:
        res2 = list(ex.map(run_p2, VOICES))
    for v, txt, e, el in res2:
        p2s[v], errs[v + "_p2"], times[v + "_p2"] = txt, e, el
    print("=== p1 ===");  [print(v, len(p1s[v]), times[v+"_p1"], errs[v]) for v in VOICES]
    print("=== p2 ===");  [print(v, len(p2s[v]), times[v+"_p2"], errs[v+"_p2"]) for v in VOICES]
    # GUARDS
    for v in VOICES:
        assert p1s[v].strip(), "empty p1: %s (err=%s)" % (v, errs[v])
        assert p2s[v].strip(), "empty p2: %s (err=%s)" % (v, errs[v+"_p2"])
    hs = {v: hashlib.md5(norm(p1s[v]).encode()).hexdigest()[:12] for v in VOICES}
    print("p1 md5s:", hs)
    assert len(set(hs.values())) == 3, "ONE-TEMPLATE BUG: p1s identical (%s)" % hs
    body = "\n\n".join("## %s\n\n%s\n\n%s" % (v, p1s[v], p2s[v]) for v in VOICES)
    d = dials(body)
    print("dials:", d)
    assert len(set(d)) == 16, "dial collision"
    assert any(d[i] < d[i+1] for i in range(15)) and any(d[i] > d[i+1] for i in range(15)), \
        "monotone dials (natural order)"
    state = {"text": body, "topic": SEED, "tag": TAG, "title": TITLE,
             "refs": [], "dials": d, "voices": {v: {"p1": p1s[v], "p1_err": errs[v],
                                                  "p2": p2s[v], "p2_err": errs[v+"_p2"]} for v in VOICES},
             "models": {v: POSTURES[v][1] for v in VOICES}}
    st, txt = post("/api/cell", {"state": state, "source": "taps-creative-break"})
    print("submit:", st, txt)
    os.makedirs("canon", exist_ok=True); os.makedirs("sessions", exist_ok=True)
    json.dump(state, open("sessions/%s.json" % TAG, "w"), indent=2)
    open("canon/%s.md" % TAG, "w").write("# %s\n\n**Tag:** %s\n**Topic:** %s\n\n%s\n" % (TITLE, TAG, SEED, body))
    print("TAG", TAG)

if __name__ == "__main__":
    main()
