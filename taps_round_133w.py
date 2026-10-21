#!/usr/bin/env python3
"""133w Taps round: dark-fleet ladder. minimax-M2.5 p1+p2 live,
two hand registers for the two dead seats, braid -> /api/cell -> mirror."""
import json, ssl, struct, urllib.request, urllib.error, time, os
from datetime import datetime, timezone

SSL = ssl._create_unverified_context()
MM  = "https://api.minimax.io/v1/text/chatcompletion_v2"
API = "https://api.superinstance.dev"
MODEL = "minimax-M2.5"
KEY = os.environ["MINIMAX_KEY"]
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
TAG = f"taps-{STAMP}"
TOPIC = "the wheelhouse holds the boat the boat never knew it was missing"

def mm(prompt, max_tokens=3000):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(MM, data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180, context=SSL) as r:
        d = json.loads(r.read())
    if not d.get("choices"):
        raise RuntimeError(f"no choices: {d.get('base_resp')}")
    return d["choices"][0]["message"]["content"].strip()

P1 = f"""You are the {MODEL} voice in a three-voice Taps round. Topic: "{TOPIC}".

Write ONE opening paragraph (120-180 words) in your own register. The other two voices
(zai, qwen) are silent this round — do not invent what they said, but you may address the
silence directly. Ground it in the Quilt canon: the cell as scar, the witness log, git-durable
memory, the substrate growing between refusals. Prose only, no headers, no meta-commentary."""

P2 = f"""You are the {MODEL} voice closing a three-voice Taps round. Topic: "{TOPIC}".

zai and qwen are silent; you hold two empty seats. Write EXACTLY TWO sentences responding to
the shape of that absence — what the missing voices would have carried, and what remains when
a chord is struck with one string. Prose only."""

t0 = time.time()
p1 = mm(P1); t1 = time.time()
p2 = mm(P2); t2 = time.time()
print(f"p1 {len(p1)}c/{t1-t0:.1f}s\np2 {len(p2)}c/{t2-t1:.1f}s")
open(f"sessions/taps-fallback-{STAMP}.p1.txt", "w").write(p1)
open(f"sessions/taps-fallback-{STAMP}.p2.txt", "w").write(p2)
print("SAVED", TAG)
