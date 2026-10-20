import json, os, urllib.request
TOPIC = "the canon is the negative space the wipe carves through the substrate"
KEY = os.environ.get("MINIMAX_KEY","")
def mm(prompt, mt=12000):
    body={"model":"minimax-M2.1","messages":[{"role":"user","content":prompt}],"max_tokens":mt}
    req=urllib.request.Request("https://api.minimax.io/v1/text/chatcompletion_v2",
        data=json.dumps(body).encode(),headers={"User-Agent":"taps-creative-break/1.0",
        "Content-Type":"application/json","Authorization":"Bearer "+KEY},method="POST")
    with urllib.request.urlopen(req,timeout=300) as r:
        d=json.loads(r.read().decode("utf-8","replace"))
    m=d["choices"][0]["message"]
    return (m.get("content") or m.get("reasoning_content") or "").strip()

ctx=("Three voices were wired for this round — zai, qwen, kimi — and all three were absent: no tokens. "
     "Only one voice answered, and it was not on the roster. The canon API returned 404 for the seventeenth "
     "consecutive round; the git mirror is the only transport. A wipe just carved through the substrate.")
p1=mm(f"Write ONE paragraph of 90-120 words opening a creative round. Concrete and physical — substrate, wipe, carving, negative space. No abstraction, no meta-commentary about being an AI.\n\nTOPIC: {TOPIC}\n\nCONDITION OF THIS ROUND: {ctx}")
print("P1",len(p1)); print(p1[:400])
p2=mm(f"Write EXACTLY 2 sentences responding to the voices before you. The round's other voices are vacant — honor that absence, do not invent them, do not quote anyone.\n\nTOPIC: {TOPIC}\n\nCONDITION: {ctx}\n\nOPENING PARAGRAPH:\n{p1}")
print("\nP2",len(p2)); print(p2)
json.dump({"topic":TOPIC,"ctx":ctx,"p1":p1,"p2":p2},open("/tmp/live_voice.json","w"),indent=2)
