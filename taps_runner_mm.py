#!/usr/bin/env python3
"""Runner wrapper: route the three Taps voices through MiniMax.
Does NOT modify taps_creative_break.py — monkeypatches its call functions.
zai -> MiniMax-M2.5, qwen -> MiniMax-M3, kimi -> MiniMax-M3.1-Flash
"""
import os, sys, json, time, urllib.request, urllib.error, ssl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taps_creative_break as T

_SSL = ssl._create_unverified_context()
# memory: api.minimax.io returned 200 on the DEFAULT context last round; .chat failed TLS-EOF.
HOSTS = ["https://api.minimax.io/v1/text/chatcompletion_v2",
         "https://api.minimax.chat/v1/text/chatcompletion_v2"]
KEY = os.environ["MINIMAX_KEY"]

MODEL = {"zai": "MiniMax-M2.5", "qwen": "MiniMax-M3", "kimi": "MiniMax-M3.1-Flash"}

def _mm(prompt, max_tokens, model, temp):
    body = {"model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temp}
    data = json.dumps(body).encode()
    last = None
    for host in HOSTS:
        req = urllib.request.Request(host, data=data, method="POST",
              headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                       "User-Agent": "taps-mm/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=180, context=_SSL) as r:
                j = json.loads(r.read().decode())
            ch = j["choices"][0]["message"].get("content") or ""
            if ch.strip():
                return ch.strip(), None
            last = "empty content"
        except urllib.error.HTTPError as e:
            last = f"http {e.code}: {e.read().decode()[:160]}"
        except Exception as e:
            last = f"exc: {e}"
    return None, last

# Kimi meta-strip reuse for safety (kill <think>/planning leak)
def _zai(prompt, mt):
    return _mm(prompt, mt, MODEL["zai"], 0.88)
def _qwen(prompt, mt):
    return _mm(prompt, mt, MODEL["qwen"], 0.88)
def _kimi(prompt, mt):
    c, e = _mm(prompt, max(mt, 1500), MODEL["kimi"], 0.85)
    if c is None:
        return None, e
    return T.kimi_strip(c), None

T.zai_call = _zai
T.qwen_call = _qwen
T.kimi_call = _kimi
# route through the module globals the round uses
T.run_round.__globals__["zai_call"] = _zai
T.run_round.__globals__["qwen_call"] = _qwen
T.run_round.__globals__["kimi_call"] = _kimi

if __name__ == "__main__":
    T.main()
