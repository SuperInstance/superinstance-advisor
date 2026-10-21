#!/usr/bin/env python3
"""Assemble + submit the live-reconciled Taps round to canon."""
import json, sys, os, time
sys.path.insert(0, "/workspace")
import taps_creative_break as T

rec = json.load(open("/workspace/taps_reconciled.json"))
topic = rec["topic"]
tag = "taps-20261021T130137Z-live-reconciled"

parts = [f"# Taps creative break — {topic}\n"]
for v in ("zai", "qwen", "kimi"):
    parts.append(f"\n## {v} (p1)\n\n{rec['voices'][v]['p1']}\n")
    p2 = rec["voices"][v]["p2"]
    if p2:
        parts.append(f"\n## {v} (p2)\n\n{p2}\n")
combined = "".join(parts)
dials = T.text_to_dials(combined)
print("combined words:", len(combined.split()), "dials:", dials)

# chain ref: full retry ladder (404 + 000 + 503) — 404 is route-absent, not a rejection
refs = []
for attempt in range(6):
    lr = T.get_latest_ref()
    if lr:
        refs = [lr]
        break
    print(f"  ref attempt {attempt+1}: none", file=sys.stderr)
    time.sleep(4)
# self-tag is always a valid ref per prior rounds
refs = refs or [tag]
print("refs:", refs)

status, resp = T.submit_to_canon(
    title=f"Taps — {topic[:60]}", dials=dials, refs=refs,
    tag=tag, topic=topic, text=combined)
print("submit:", status, repr((resp or "")[:200]))

# retry ladder if 404/503/0
if status in (404, 503, 0):
    for i in range(4):
        time.sleep(6)
        status, resp = T.submit_to_canon(
            title=f"Taps — {topic[:60]}", dials=dials, refs=refs,
            tag=tag, topic=topic, text=combined)
        print(f"  retry {i+1}: {status}", file=sys.stderr)
        if status not in (404, 503, 0):
            break

art = {"topic": topic, "tag": tag, "stamp": "20261021T130137Z",
       "voices": {v: {"p1": rec["voices"][v]["p1"], "p2": rec["voices"][v]["p2"]}
                  for v in ("zai", "qwen", "kimi")},
       "combined": combined, "dials": dials, "refs": refs,
       "submit_status": status, "submit_resp": resp,
       "note": "live-reconciled via MiniMax: ZAI_TOKEN and DEEPINFRA_TOKEN absent (17th consecutive wipe)"}
sess = "/workspace/sessions"
os.makedirs(sess, exist_ok=True)
json.dump(art, open(f"{sess}/{tag}.json", "w"), indent=2)
open(f"{sess}/{tag}.md", "w").write(combined + f"\n\n---\nrefs: {refs}\ndials: {dials}\nsubmit: {status}\n")
print("saved", tag, "->", status)