import json, os
tag = "taps-20261023T210434Z"
j = json.load(open(f"sessions/{tag}.json"))
combined = j["combined"]
open(f"canon/{tag}.md","w").write(combined)
state = {"text": combined, "topic": j["topic"], "tag": tag, "title": j["topic"],
         "refs": [], "dials": j["dials"], "voices": {"zai":"MECHANISM","qwen":"DEFEND","kimi":"DEEPER"},
         "models": {"zai":"MiniMax-M2.5","qwen":"MiniMax-M2.5","kwen":"MiniMax-M2.5","kimi":"MiniMax-M2.5"},
         "seed": j["topic"]}
open(f"canon/{tag}.json","w").write(json.dumps(
    {"state": state, "source": "taps-creative-break", "round": "162w-repaired-round2",
     "guards": j.get("guards", {}), "submit_status": j.get("submit_status"),
     "submit_resp": j.get("submit_resp"),
     "note": "SECOND independent sample of the same seed, produced by the 162w runner's first invocation (foreground timeout killed the VIEW, not the process). One model (M2.5 x3) but 3/3 DISTINCT opening clauses and 3/3 distinct p1 - posture prefixes alone diverge here. Kept because it is real work, not because it is a good round."},
    indent=1))
print("canon written:", os.path.getsize(f"canon/{tag}.md"), "bytes")
