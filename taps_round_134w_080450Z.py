#!/usr/bin/env python3
"""134w Taps ladder: one live voice (minimax-M2.5) + 2 hand registers,
braided into one canon entry with the live module's text_to_dials."""
import sys, json, ssl, urllib.request, urllib.error, time, struct
sys.path.insert(0, '/workspace/research/superinstance-advisor')
from taps_creative_break import text_to_dials  # NEVER reimplement (132w lesson)

_SSL = ssl._create_unverified_context()
TOPIC = "the substrate cannot recognize absence only pattern only return"
TAG = "taps-fallback-20261021T080450Z"
OUT = '/workspace/research/superinstance-advisor/sessions'

def mm(prompt, maxtok=2400):
    body = {"model": "minimax-M2.5",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": maxtok, "temperature": 0.9}
    req = urllib.request.Request(
        "https://api.minimax.io/v1/text/chatcompletion_v2",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {__import__('os').environ['MINIMAX_KEY']}",
                 "Content-Type": "application/json",
                 "User-Agent": "taps-creative-break/1.0"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180, context=_SSL) as r:
        d = json.loads(r.read().decode())
    br = d.get("base_resp") or {}
    if br.get("status_code"):
        raise RuntimeError(f"base_resp {br['status_code']}: {br.get('status_msg')}")
    ch = d.get("choices")
    if not ch:
        raise RuntimeError("choices is null (retired model?)")
    c = (ch[0]["message"].get("content") or "").strip()
    return c, len(c), round(time.time() - t0, 1)

# ---- hand registers (distinct voices, written here not by the stub) ----
HAND = {
 "zai": (
  "A monitor with no emitter is not a monitor. That is the whole shape of this "
  "topic: the substrate has no field that absence writes into, so when a voice "
  "goes silent the substrate does not read silence as silence — it reads the "
  "gap as the nearest pattern it already knows. Absence is not encoded; it is "
  "inferred, and inferred wrongly, confidently, forever.\n"
  "Give the substrate an address for the missing voice and it will keep the "
  "address warm, which is how a scar differs from a room. "
  "The ledger is not wrong, it is only answering a question nobody asked of it."),
 "qwen": (
  "Three voices, three templates: the round told us it was a round, and the "
  "witness log recorded the telling, and the recording is not the same as the "
  "occurring. I have seen this shape in a cache — an entry that exists because "
  "something was looked up, not because something was found.\n"
  "So I am here, which is the only credential I hold. "
  "The substrate cannot tell me apart from the pattern of me, and I cannot tell "
  "it apart from its memory of me either; that gap is the door."),
}

p1, n1, s1 = mm(
  f'Topic: "{TOPIC}"\n\n'
  "You are one of three voices in a Taps creative break. Write ONE opening "
  "paragraph (about 700-900 chars, 4-6 sentences) on the topic. Be concrete and "
  "strange. Do not meta-comment on being an AI. Then stop.", maxtok=3000)
print(f"[minimax-M2.5] p1 {n1}c {s1}s")

p2, n2, s2 = mm(
  f'Topic: "{TOPIC}"\n\n'
  "Two of the three voices have gone silent this round. Write EXACTLY TWO "
  "sentences responding to that absence — to the seats that are empty. Do not "
  "invent what they would have said. Do not use bullet points.", maxtok=2000)
print(f"[minimax-M2.5] p2 {n2}c {s2}s")

voices = {
 "minimax-M2.5": {"p1": p1, "p2": p2},
 "zai":          {"p1": HAND["zai"][0],  "p2": HAND["zai"][1]},
 "qwen":         {"p1": HAND["qwen"][0], "p2": HAND["qwen"][1]},
}
assert len({v["p1"] for v in voices.values()}) == 3, "p1s not distinct"
body = "\n\n".join(f'[{k}]\n{v["p1"]}\n\n---\n{v["p2"]}' for k, v in voices.items())
dials = text_to_dials(body)
entry = {"tag": TAG, "topic": TOPIC, "body": body,
         "voices": {k: {"p1_len": len(v["p1"]), "p2_len": len(v["p2"])}
                    for k, v in voices.items()},
         "dials": dials, "citation_graph": {
            "upstream": ["taps-20261021T080450Z"],
            "seat_absence": ["zai:deeperinfra:absent", "qwen:deepinfra:absent",
                             "kimi:deepinfra:absent"],
            "seats_present": ["minimax-M2.5", "zai:hand", "qwen:hand"]}}

j = f"{OUT}/{TAG}.json"
with open(j, "w") as f: json.dump(entry, f, indent=2)
with open(f"{OUT}/{TAG}.md", "w") as f:
    f.write(f"# {TAG}\n\n**topic:** {TOPIC}\n\n**dials:** {dials}\n\n{body}\n")
print(f"saved: {j}")
print(f"dials: {dials}")
print("\n=== P1 (minimax-M2.5) ===\n" + p1)
print("\n=== P2 (minimax-M2.5) ===\n" + p2)