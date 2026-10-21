#!/usr/bin/env python3
"""131w retry — ONE live voice (minimax-M2.1) on a fresh canon-shaped topic.

zai + qwen are ABSENT (ZAI_TOKEN / DEEPINFRA_TOKEN gone, 11th consecutive wipe).
This is the live pass: p1 paragraph, then a p2 that honors the two vacant seats
as material without inventing them. max_tokens>=8000 (reasoning_content cost).
"""
import os, json, ssl, urllib.request
from datetime import datetime, timezone

_SSL = ssl._create_unverified_context()
BASE = "https://api.minimax.io/v1/text/chatcompletion_v2"
# 131w: M2.1 is RETIRED (base_resp 2069 "no longer available"). M2.5 probes OK.
MODEL = "minimax-M2.5"

# Fresh topic, NOT a bank re-cycle. Canon-shaped: the witness log, the scars, etc.
TOPIC = "a record of where the wound will be does not make the wound"

P1 = f"""You are the only voice seated in a three-voice creative round. The other two
seats are empty: zai and qwen are declared ABSENT this round - not silent-by-choice,
but unavailable. Do not invent their words, do not quote them, do not guess what they
would have said.

Open with ONE paragraph (about 150-200 words) on this topic:
"{TOPIC}"

Ground it in what is actually observable this round: a canon endpoint that has answered
404 for more than twenty consecutive rounds, a repository rebuilt from a git mirror each
time the workspace is erased, the difference between a record that predicts a location and
a record that opens a door. Be concrete and physical. Then STOP at the paragraph.

Write only the paragraph. No preamble, no headers, no quotation marks."""

P2 = """You are the same voice, second pass. Two voices are ABSENT - declared, not invented.

Transcript of the only live voice, in the paragraph it just wrote:
<<<VOICE_A>>>
__VOICE_A_PLACEHOLDER__
<<<END_VOICE_A>>>

Write EXACTLY 2 sentences responding to it. Requirements:
- Sentence 1 must acknowledge the two vacant seats AS ABSENCE - treat the absence itself
  as the material (the empty chairs are part of the record). Do not invent, paraphrase, or
  simulate their content.
- Sentence 2 must turn that absence into a claim about the topic that the live voice did
  not make - something only this round's specific gap (a canon that predicts a wound and
  two voices that never arrived) could produce.
- No preamble, no headers, no quotation marks, no bullet points."""


def call(messages, maxtok=8000):
    key = os.environ.get("MINIMAX_KEY") or os.environ.get("MINIMAX_API_KEY")
    body = json.dumps({"model": MODEL, "messages": messages,
                       "max_tokens": maxtok, "temperature": 0.95}).encode()
    req = urllib.request.Request(
        BASE, data=body, method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240, context=_SSL) as r:
        j = json.loads(r.read().decode())
    m = j["choices"][0]["message"]
    txt = (m.get("content") or "").strip()
    src = "content"
    if not txt:
        txt = (m.get("reasoning_content") or "").strip()
        src = "reasoning_content"
    return txt, src


if __name__ == "__main__":
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    a, sa = call([{"role": "user", "content": P1}])
    print("=== VOICE A (p1) ===\n" + a + "\n", flush=True)
    print("--- p1 source:", sa, "---", flush=True)
    b, sb = call([{"role": "user", "content": P2.replace("__VOICE_A_PLACEHOLDER__", a)}])
    print("=== VOICE A (p2, 2 sentences) ===\n" + b + "\n", flush=True)
    print("--- p2 source:", sb, "---", flush=True)
    out = {"voice": MODEL, "absent": ["zai", "qwen"], "topic": TOPIC,
           "p1": a, "p1_source": sa, "p2": b, "p2_source": sb,
           "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")}
    name = f"/workspace/research/superinstance-advisor/sessions/live-voice-{stamp}.json"
    os.makedirs(os.path.dirname(name), exist_ok=True)
    with open(name, "w") as f:
        json.dump(out, f, indent=2)
    print("saved: " + name)