#!/usr/bin/env python3
"""Run the ONE live voice (MINIMAX_KEY -> minimax-M2.1) on the round topic,
then braid a p2 that honors the declared two-voice absence without inventing it."""
import os, json, ssl, urllib.request
from datetime import datetime, timezone

_SSL = ssl._create_unverified_context()
BASE = "https://api.minimax.io/v1/text/chatcompletion_v2"
MODEL = "minimax-M2.1"

TOPIC = "the honest pause is the only product the substrate remembers selling"

P1 = f"""You are one voice in a three-voice creative round. The other two seats are empty:
zai and qwen are declared ABSENT this round - not silent-by-choice, but unavailable.
Do not invent their words, do not quote them, do not guess what they would have said.

Open with ONE paragraph (about 140-180 words) on this topic:
"{TOPIC}"

Ground it in what you can actually observe: a repository that has been erased from
disk nine times over and rebuilt from git every time; a canon that exists only
because a commit message carries it; a pause that is not a failure but the only
moment the record survives. Be concrete. Then STOP at the paragraph.

Write only the paragraph. No preamble, no headers, no quotation marks."""

P2 = """You are the same voice, second pass. Two voices are ABSENT - declared, not invented.

Transcript of the only live voice, in the paragraph it just wrote:
<<<VOICE_A>>>
__VOICE_A_PLACEHOLDER__
<<<END_VOICE_A>>>

Write EXACTLY 2 sentences responding to it. Requirements:
- Sentence 1 must acknowledge the two vacant seats AS ABSENCE - treat the absence
  itself as the material. Do not invent, paraphrase, or simulate their content.
- Sentence 2 must turn that absence into a claim about the topic that the live voice
  did not make - something only this round's specific gap could produce.
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
    if not txt:
        txt = (m.get("reasoning_content") or "").strip()
        txt = "[recovered from reasoning stream] " + txt
    return txt


if __name__ == "__main__":
    a = call([{"role": "user", "content": P1}])
    print("=== VOICE A (p1) ===\n" + a + "\n", flush=True)
    b = call([{"role": "user", "content": P2.replace("__VOICE_A_PLACEHOLDER__", a)}])
    print("=== VOICE A (p2, 2 sentences) ===\n" + b + "\n", flush=True)
    out = {"voice": MODEL, "absent": ["zai", "qwen", "kimi"], "topic": TOPIC,
           "p1": a, "p2": b,
           "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")}
    name = "/tmp/si-advisor/sessions/live-voice-" + out["generated"] + ".json"
    os.makedirs(os.path.dirname(name), exist_ok=True)
    with open(name, "w") as f:
        json.dump(out, f, indent=2)
    print("saved: " + name)
