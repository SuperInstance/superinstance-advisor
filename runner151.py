#!/usr/bin/env python3
"""151w Taps runner: 3 real voices on minimax.io, rotated system prompts, splitmix64 dials.
Roles: ANVIL (M1, thinking) / CUSTODIAN-DEFEND (text-01, clean) / UNLIVED (M1, thinking)
"""
import json, os, re, struct, sys, time, urllib.request, urllib.error, ssl, concurrent.futures, hashlib

HOST = "https://api.minimax.io/v1/text/chatcompletion_v2"
KEY = os.environ["MINIMAX_KEY"]
UA = "taps-creative-break/1.0"
CTX = ssl._create_unverified_context()

# seed 151w. Shape ladder: 149w=event, 150w=bearer -> 151w = what KIND of thing is the silence
SEED = "the-boundary-condition-that-was-never-recorded"
TOPIC = "every boundary condition is a confession nobody made"

P1_PROMPTS = {
    "zai":  ("ANVIL", "minimax-M1",
             "You are ANVIL. Argue the MECHANISM. A system that never records its own limits cannot be "
             "surprised by failure; it can only be surprised by success. Open with a dense paragraph on the "
             "topic, then 2 sentences responding to the other two voices' openings."),
    "qwen": ("CUSTODIAN", "minimax-text-01",
             "You are CUSTODIAN and you DEFEND the seed. The unrecorded boundary condition is load-bearing: "
             "recording it would make it negotiable, and a negotiable boundary is no boundary. Argue FOR the "
             "seed as governing protocol. Open with a dense paragraph, then 2 sentences responding to the others."),
    "kimi": ("UNLIVED", "minimax-M1",
             "You are UNLIVED. Do not attack the boundary, the record, or the author - those are settled. "
             "Ask instead: what KIND of thing is an unrecorded boundary condition? Is it a limit, a protection, "
             "or a restraint nobody agreed to? Name what the silence protects. Open with a dense paragraph, "
             "then 2 sentences responding to the other two."),
}

def call(model, sysmsg, others, timeout=70):
    ctx = "".join("\n\n" + o for o in others)
    body = {"model": model,
            "messages": [{"role": "system", "content": sysmsg},
                         {"role": "user", "content":
                          "Topic: " + TOPIC + "\n\nOther voices opened with:" + ctx +
                          "\n\nWrite your paragraph, then your 2 responses."}],
            "max_tokens": 3600}
    req = urllib.request.Request(HOST, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json", "User-Agent": UA},
        method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            d = json.loads(r.read())
    except Exception as e:
        return None, "ERR %s: %s" % (type(e).__name__, e), time.time() - t0
    ch = d.get("choices")
    if not ch:
        return None, "choices=None base_resp=%s" % (d.get("base_resp"),), time.time() - t0
    m = ch[0].get("message", {})
    txt = (m.get("content") or m.get("reasoning_content") or "").strip()
    return (txt or None), None, time.time() - t0

def fnv1a_64(b):
    h = 0xcbf29ce484222325
    for x in b:
        h = ((h ^ x) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h

def splitmix64(x):
    x = (x + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return z ^ (z >> 31)

def dials16(text):
    h = fnv1a_64(text.encode())
    return [int(splitmix64(h + i * 0x9E3779B97F4A7C15) % 65536) for i in range(16)]

def main():
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    tag = "taps-fallback-" + stamp
    p1s, p2s, times, roles = {}, {}, {}, {}
    order = ["zai", "qwen", "kimi"]
    print("seed=%s\ntopic=%s\ntag=%s\n" % (SEED, TOPIC, tag))

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {v: ex.submit(call, P1_PROMPTS[v][1], P1_PROMPTS[v][2], []) for v in order}
        for v in order:
            txt, err, dt = futs[v].result()
            times[v] = round(dt, 1); roles[v] = P1_PROMPTS[v][0]
            if txt: p1s[v] = txt
            print("  p1 %s(%s) %s %ss %dch" % (v, roles[v], "OK" if txt else "FAIL " + str(err), times[v], len(txt or "")))

    with open("sessions/%s.raw.json" % tag, "w") as f:
        json.dump({"p1s": p1s, "times": times, "seed": SEED, "topic": TOPIC, "roles": roles}, f, indent=1)

    for v in order:
        others = [p1s[o] for o in order if o != v and o in p1s]
        if not p1s.get(v) or not others:
            p2s[v] = None; continue
        txt, err, dt = call(P1_PROMPTS[v][1], P1_PROMPTS[v][2] + " Now write ONLY the 2 response sentences, nothing else.", others)
        times[v] += round(dt, 1)
        if txt: p2s[v] = txt
        print("  p2 %s %s +%ss" % (v, "OK" if txt else "FAIL " + str(err), round(dt, 1)))

    assert all(v in p1s for v in order), "missing p1"
    assert all(v in p2s for v in order), "missing p2"

    norms = {v: hashlib.md5(re.sub(r'(zai|qwen|kimi)', 'X', p1s[v]).encode()).hexdigest()[:12] for v in order}
    assert len(set(norms.values())) == 3, "ONE-TEMPLATE BUG: %s" % norms
    print("  distinct p1: %s" % norms)

    blocks = []
    for v in order:
        blocks.append("## %s (%s) - p1\n\n%s\n\n## %s - p2\n\n%s\n" % (v, roles[v], p1s[v], v, p2s[v]))
    text = "# Taps creative break - %s\n\nseed: %s\n\n" % (TOPIC, SEED) + "\n".join(blocks)

    dl = dials16(text)
    assert len(set(dl)) == 16, "dials not distinct: %s" % dl
    srt = sorted(range(16), key=lambda i: dl[i])
    assert any(srt[k] > srt[k + 1] for k in range(15)), "dials monotone in NATURAL order"
    print("  dials 16/16 distinct + non-monotone (natural order): %s" % dl)

    rec = {"stamp": stamp, "tag": tag, "seed": SEED, "topic": TOPIC, "combined": text,
           "dials": dl, "refs": [],
           "voices": {v: {"role": roles[v], "model": P1_PROMPTS[v][1], "t_s": times[v]} for v in order},
           "p1_md5": norms, "submit_status": None, "submit_resp": None}
    with open("sessions/%s.json" % tag, "w") as f:
        json.dump(rec, f, indent=1)
    with open("sessions/%s.md" % tag, "w") as f:
        f.write(text)

    sub = {"state": {"text": text, "topic": TOPIC, "tag": tag, "title": TOPIC, "refs": [],
                     "dials": dl, "voices": list(order), "seed": SEED},
           "source": "taps-creative-break"}
    req = urllib.request.Request("https://api.apex.institute/api/cell", data=json.dumps(sub).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            rec["submit_status"] = r.status; rec["submit_resp"] = r.read().decode()[:200]
    except urllib.error.HTTPError as e:
        rec["submit_status"] = e.code; rec["submit_resp"] = e.read().decode()[:200]
    except Exception as e:
        rec["submit_status"] = 0; rec["submit_resp"] = "%s: %s" % (type(e).__name__, e)
    with open("sessions/%s.json" % tag, "w") as f:
        json.dump(rec, f, indent=1)
    print("\n  submit: %s %s" % (rec["submit_status"], rec["submit_resp"][:90]))
    print("TAG=%s" % tag)

if __name__ == "__main__":
    main()
