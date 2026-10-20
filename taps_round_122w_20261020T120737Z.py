#!/usr/bin/env python3
"""122w live voice: MINIMAX_KEY -> minimax-M2.1 on the round topic.
zai/qwen/kimi are DECLARED ABSENT (no tokens, 10th consecutive wipe).
p2 braids the vacancy as absence; it does not invent it."""
import os, json, ssl, urllib.request
from datetime import datetime, timezone

_SSL = ssl._create_unverified_context()
BASE = "https://api.minimax.io/v1/text/chatcompletion_v2"
MODEL = "minimax-M2.1"

TOPIC = "the witness log predicts the wound it pretends to record"

P1 = """You are one voice in a three-voice creative round. The other two seats are empty:
zai and qwen are declared ABSENT this round - not silent-by-choice, but unavailable.
Do not invent their words, do not quote them, do not guess what they would have said.

Open with ONE paragraph (about 140-180 words) on this topic:
"{TOPIC}"

Ground it in what you can actually observe tonight: a script whose three "distinct"
voices were proven this hour to be one byte-identical template wearing three names;
a canon endpoint that returns 404 while the apex page returns 200; a repository that
survives only because every wipe is answered by a git clone. Be concrete about the
difference between a record and a prediction. Then STOP at the paragraph.

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
    src = "content"
    if not txt:
        txt = (m.get("reasoning_content") or "").strip()
        src = "reasoning_content_fallback"
    return txt, src, len(j["choices"][0]["message"].get("reasoning_content") or "")


if __name__ == "__main__":
    a, sa, ra = call([{"role": "user", "content": P1}])
    print("=== LIVE VOICE p1 (src=%s, reasoning=%dc) ===\n%s\n" % (sa, ra, a), flush=True)
    b, sb, rb = call([{"role": "user", "content": P2.replace("__VOICE_A_PLACEHOLDER__", a)}])
    print("=== LIVE VOICE p2 (src=%s, reasoning=%dc) ===\n%s\n" % (sb, rb, b), flush=True)
    out = {"voice": MODEL, "absent": ["zai", "qwen", "kimi"], "topic": TOPIC,
           "p1": a, "p1_source": sa, "p2": b, "p2_source": sb,
           "generated": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}
    name = "/tmp/taps/live-122w-" + out["generated"] + ".json"
    with open(name, "w") as f:
        json.dump(out, f, indent=2)
    print("saved: " + name)
