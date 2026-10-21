"""Live MiniMax-M2.5 p1 for the taps ladder. Asserts content AND finish_reason."""
import json, os, ssl, sys, urllib.request, urllib.error

BASE = "https://api.minimax.io/v1/text/chatcompletion_v2"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

TOPIC = sys.argv[1] if len(sys.argv) > 1 else "the polyformalism holds because no single port can carry the whole river"

P1 = """You are one voice in a rotating creative session. Write one paragraph (120-180 words) opening the topic: "{topic}".

This is the Polyformalism: a body of work ported across many languages and systems, each port a single wound in the tissue, no port carrying the whole river. A watch, not a body. Address the other two voices directly as if they had just spoken. Do not summarize the topic back. Speak only for yourself. No preamble, no title, just the paragraph."""

P2 = """The other two voices have spoken. Write exactly two sentences responding to them, in the same register, on the topic: "{topic}". Do not restate their words. No preamble."""


def call(prompt, max_tokens):
    hdr = {"Authorization": f"Bearer {os.environ['MINIMAX_KEY']}", "Content-Type": "application/json"}
    body = {"model": "MiniMax-M2.5", "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": 0.9}
    req = urllib.request.Request(BASE, data=json.dumps(body).encode(), headers=hdr, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_http": e.code, "_body": e.read().decode()[:300]}
    except Exception as e:
        return {"_err": str(e)}


def probe(label, prompt):
    for mt in (3000, 8000):
        j = call(prompt, mt)
        if "_http" in j or "_err" in j:
            print(f"{label} mt={mt} TRANSPORT {j}")
            continue
        ch = (j.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        content = (msg.get("content") or "").strip()
        fr = ch.get("finish_reason")
        rsn = len(msg.get("reasoning_content") or "")
        print(f"{label} mt={mt} finish={fr} content={len(content)}c reasoning={rsn}c")
        if content and fr == "stop":
            return content
        print(f"  -> {'EMPTY-CONTENT reasoning-eat, rerun higher' if not content else 'not a clean stop'}")
    return None


if __name__ == "__main__":
    p1 = probe("p1", P1.format(topic=TOPIC))
    print("=" * 60)
    if p1:
        print("P1>>>"); print(p1)
        p2 = probe("p2", P2.format(topic=TOPIC))
        print("P2>>>"); print(p2 if p2 else "(p2 unavailable)")
        json.dump({"topic": TOPIC, "p1": p1, "p2": p2}, open("live_voice_out.json", "w"))
    else:
        print("LIVE VOICE UNAVAILABLE")