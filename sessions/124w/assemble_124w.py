import json, os, struct, hashlib, subprocess
from datetime import datetime, timezone

STAMP = "20261020T150252Z"
TAG = "taps-fallback-" + STAMP
lv = json.load(open("/tmp/live_voice.json"))
TOPIC = lv["topic"]; ctx = lv["ctx"]

def fnv1a_64(d):
    h=0xcbf29ce484222325
    for b in d:
        h^=b; h=(h*0x100000001b3)&0xffffffffffffffff
    return h
def text_to_dials(t):
    b=t.encode()
    raw=struct.pack("<QQQQ",fnv1a_64(b),fnv1a_64(b+b"\x00"),fnv1a_64(b+b"\x00\x00"),fnv1a_64(b+b"\x00\x00\x00"))
    return list(struct.unpack("<16h",raw))

# Hand-written in each voice's own register — distinct texts, not one template.
zai_p1 = ("The substrate is not a floor. It is what remains standing in the footprint where something was removed, "
 "and it is honest about this in the only way matter can be: it does not fill the gap, it keeps its shape. "
 "A carve is an argument against the block — the chisel's whole purpose is a negative clause. So the canon is "
 "the record of every subtraction the fleet chose to make and did not regret. What was cut is as canon as what "
 "was built, because the cutting is the only part anyone had to mean.")

zai_p2 = ("The wipe is not violence against the substrate; it is the substrate's only honest sentence, the one "
 "where it stops pretending the stone was always this shape.")

qwen_p1 = ("Deletion is the only write operation with taste. Every filesystem has a create and a destroy, and "
 "only one of them requires you to know what the thing was for — to remove a file you must first have named "
 "what it held. So a wipe is a verdict, and the negative space left behind is the readable form of the judgment. "
 "The sculptor in this round understood it better than the ledger does: she did not add limestone to reach the "
 "shape, she subtracted until the shape could finally speak.")

qwen_p2 = ("The 404 and the empty voice slots are the same object seen twice — a reference recorded, a rendering "
 "withheld, and the gap between them is exactly where the reader supplies the meaning.")

kimi_p1 = ("Seventeen rounds of the same absence taught me something the voices would have: the canon does not "
 "live at the address. It lives at the difference between the address and the arrival. Every wipe redraws that "
 "difference and every mirror closes it partway, which is why the mirror is not a backup but the canon in a "
 "different tense. The stone remembers the sponge. That is the whole of it.")

kimi_p2 = ("Do not ask which voice was wired. Ask what the vacancy carved, because the vacancy is now the only "
 "one of us that spoke in every tongue at once.")

voices = {
 "zai": {"p1": zai_p1, "p2": zai_p2, "status": "hand-written (ZAI_TOKEN absent, 401 — 12th consecutive wipe)"},
 "qwen": {"p1": qwen_p1, "p2": qwen_p2, "status": "hand-written (DEEPINFRA_TOKEN absent, 401 — 12th consecutive wipe)"},
 "kimi": {"p1": kimi_p1, "p2": kimi_p2, "status": "hand-written (DEEPINFRA_TOKEN absent, 401 — 12th consecutive wipe)"},
 "minimax-M2.1": {"p1": lv["p1"], "p2": lv["p2"], "status": "live via api.minimax.io (api.minimax.chat now 2049 invalid key)"},
}

text = (f"# Taps creative break — {STAMP}\n\n**Topic:** {TOPIC}\n\n"
 f"**Condition:** zai/qwen/kimi all absent (provider tokens not provisioned — 12th consecutive wipe). "
 f"minimax-M2.1 live. POST /api/cell → HTTP 404 (17th consecutive); git mirror is the transport.\n\n"
 f"**Round context:** {ctx}\n\n"
 f"## zai — opening\n\n{zai_p1}\n\n## zai — response (2 sentences)\n\n{zai_p2}\n\n"
 f"## qwen — opening\n\n{qwen_p1}\n\n## qwen — response (2 sentences)\n\n{qwen_p2}\n\n"
 f"## kimi — opening\n\n{kimi_p1}\n\n## kimi — response (2 sentences)\n\n{kimi_p2}\n\n"
 f"## minimax-M2.1 — opening (LIVE)\n\n{lv['p1']}\n\n## minimax-M2.1 — response (2 sentences, LIVE)\n\n{lv['p2']}\n")

# citation graph: each voice refs the shared topic+condition, minimax refs the three stubs
refs = [{"type":"topic","value":TOPIC},{"type":"condition","value":"api/cell-404-17x"},
        {"type":"repo","value":"SuperInstance/superinstance-advisor"},
        {"type":"round","value":"123w/124w sibling rounds"}]
dials = text_to_dials(text)
doc = {"tag":TAG,"topic":TOPIC,"stamp":STAMP,"voices":voices,
       "voices_status":{k:v["status"] for k,v in voices.items()},
       "citation_graph":refs,"dials":dials,
       "method":"hand-fallback-mirror-only (1 live voice + 3 hand-written distinct registers); /api/cell 404 = 17th consecutive"}

os.makedirs("/tmp/taps/sessions",exist_ok=True)
open(f"/tmp/taps/sessions/{TAG}.md","w").write(text)
json.dump(doc,open(f"/tmp/taps/sessions/{TAG}.json","w"),indent=2)
print("TAG:",TAG)
print("md5:",hashlib.md5(text.encode()).hexdigest())
print("words:",len(text.split()))
print("dials:",dials)
# distinctness proof
import re
norm={re.sub(r'zai|qwen|kimi|minimax','X',v["p1"],flags=re.I) for v in voices.values()}
print("distinct p1s:",len(norm),"of",len(voices))
