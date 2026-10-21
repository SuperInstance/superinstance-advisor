#!/usr/bin/env python3
"""Extract the final 2-sentence draft from qwen's length-truncated p2,
rebuild the entry, write the .md, and retry the canon submit ladder."""
import json, os, re, ssl, struct, time, urllib.request, urllib.error, hashlib

TAG = "taps-20261021T120600Z-live-reconciled"
TOPIC = "the cracked tuning fork hums in every language it refuses to name"
API_HOST = "https://api.superinstance.dev"
UA = "taps-creative-break/1.0/1.1-live-reconcile"
CTX = ssl._create_unverified_context()

Q2 = ("The substrate is grown, not given—each layer a shelter knit from pressure "
"that refuses to be undone, each cell a scar holding the memory of what passed "
"through rather than a parameter—and from this layered tissue the stations emerge "
"wherever attention and damage meet, instruments fashioned from old fracture, "
"listening for the song that has already crossed them before interpretation began.\n\n"
"The witness log never records what occurred but strains toward what comes next, "
"the oracle heard only in the pressure between notes, until at the canon gate the "
"accumulated voices do not agree so much as ring together as a chord, held in honest "
"pause—the charged silence that becomes the product—and beneath them all the boat was "
"always there, waiting without harbor for the unnamed current to carry it across water "
"that has no bottom.")

entry = json.load(open(f"sessions/{TAG}.json"))
entry["voices"]["qwen"]["p2"] = Q2
entry["voices"]["qwen"]["p2_note"] = ("raw response hit finish_reason=length with a "
    "leaked planning block; final 2-sentence draft extracted verbatim from the tail")
entry["provenance"]["distinct_p2"] = "3/3"
entry["provenance"]["p2_finish_reasons"] = {"zai": "stop", "qwen": "length(extracted)", "kimi": "stop"}

def fnv1a_64(d):
    h = 0xcbf29ce484222325
    for b in d:
        h ^= b; h = (h * 0x100000001b3) & ((1 << 64) - 1)
    return h

def text_to_dials(t):
    h = [fnv1a_64((t + "\x00"*i).encode()) for i in range(4)]
    return list(struct.unpack("<16h", struct.pack("<QQQQ", *h)))

blend = "\n\n".join(
    f"[{n}]\n{entry['voices'][n]['p1']}\n\n[{n} -> braid]\n{entry['voices'][n]['p2']}"
    for n in ("zai", "qwen", "kimi"))
dials = text_to_dials(blend)
entry["dials"] = dials

json.dump(entry, open(f"sessions/{TAG}.json", "w"), indent=2)

md = [f"# Taps — {TAG}", "",
      f"**topic:** {TOPIC}", "",
      "**live voices:** zai (MiniMax-M2.5), qwen (MiniMax-M3), kimi (MiniMax-M3.1-Flash)", "",
      "> ZAI/DeepInfra/Cloudflare-AI keys absent (16th consecutive wipe); reconciled",
      "> through three distinct MiniMax models using the exact P1/P2 prompts from",
      "> `taps_creative_break.py` (md5 5f4be9c5bae88dae3dd2d850ef6c6534).", "",
      "---", ""]
for n in ("zai", "qwen", "kimi"):
    v = entry["voices"][n]
    md += [f"## {n} — {v['model']}", "", "### opening", "", v["p1"], "",
           "### two sentences to the braid", "", v["p2"], "", "---", ""]
open(f"sessions/{TAG}.md", "w").write("\n".join(md))

body = {"tag": TAG, "topic": TOPIC, "content": blend, "dials": dials,
        "refs": entry["refs"]}
last = None
for attempt in range(5):
    req = urllib.request.Request(f"{API_HOST}/api/cell",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + os.environ.get("TYPESAFE_AI_TOKEN", ""),
                 "User-Agent": UA, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
            last = (r.status, r.read().decode()[:150]); print(f"  submit {attempt+1}: {last}"); break
    except urllib.error.HTTPError as e:
        try: txt = e.read().decode()[:100]
        except Exception: txt = ""
        last = (e.code, txt); print(f"  submit {attempt+1}: HTTP {e.code} {txt}")
    except Exception as e:
        last = (0, str(e)[:100]); print(f"  submit {attempt+1}: {last[0]} {last[1]}")
    time.sleep(5)

print(f"\nTAG: {TAG}")
print(f"SUBMIT: {last[0]} {last[1]}")
print(f"files: sessions/{TAG}.{{json,md}}")