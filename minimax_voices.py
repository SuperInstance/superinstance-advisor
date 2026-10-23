"""Live-voice shim: route all three Taps voices onto MiniMax-M2.5.

Why: ZAI_TOKEN / DEEPINFRA_TOKEN are absent (30th consecutive round), so the
script's hand-fallback fires and reports a green p1 that is the same template
three times. MINIMAX_KEY is present and HTTP 200.

Two gates this model needs that the others don't:
  1. Reasoning model -> every response leads with <think>...</think>.
     Strip with re.S BEFORE any paragraph/sentence gate.
  2. Answers in proportion to prompt size, ignores max_tokens for form.
     P2 asks for exactly two sentences and gets 15-36. Enforce post-hoc.
"""
import json, os, re, time, urllib.request

MM_BASE = "https://api.minimax.io/v1"
MM_MODEL = "MiniMax-M2.5"
_THINK = re.compile(r"<think>.*?</think>", re.S)


def strip_think(text: str) -> str:
    if not text:
        return ""
    out = _THINK.sub("", text)
    if "<think>" in out:
        out = out.split("<think>")[0]
    return out.strip()


def sent_split(text: str) -> list[str]:
    t = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    t = re.sub(r"^\s*#{1,6}\s.*$", "", t, flags=re.M)
    t = re.sub(r"^\s*\*\*[^*]+\*\*\s*:?.*$", "", t, flags=re.M)
    t = re.sub(r"^\s*(Voice|MECHANISM|TEXT|DEEPER)\b.*$", "", t, flags=re.M | re.I)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'“])", t) if s.strip()]


def first_sentences(text: str, n: int) -> str:
    s = sent_split(text)
    if not s:
        return ""
    return " ".join(s[:n])


def mm_call(prompt: str, max_tokens: int = 1500, temperature: float = 0.7,
            sentences: int | None = None, retries: int = 3):
    key = os.environ.get("MINIMAX_KEY")
    if not key:
        return None, "MINIMAX_KEY unset"
    body = {"model": MM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temperature}
    data = json.dumps(body).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                f"{MM_BASE}/chat/completions", data=data,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                j = json.load(r)
            ch = (j.get("choices") or [{}])[0]
            raw = (ch.get("message") or {}).get("content") or ""
            if not raw.strip():
                last = "empty content"; continue
            clean = strip_think(raw)
            if not clean:
                last = "think-strip produced empty"; continue
            if sentences is not None:
                clean = first_sentences(clean, sentences)
                if not clean:
                    last = "sentence gate produced empty"; continue
            return clean, None
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            if attempt < retries - 1:
                time.sleep(6)
    return None, last or "exhausted"


def zai_call(prompt, max_tokens):
    return mm_call(prompt, max_tokens, temperature=0.55)


def qwen_call(prompt, max_tokens):
    return mm_call(prompt, max_tokens, temperature=0.75)


def kimi_call(prompt, max_tokens):
    return mm_call(prompt, max_tokens, temperature=0.9)


def call_p2(voice: str, prompt: str, max_tokens: int):
    return mm_call(prompt, max_tokens,
                   temperature={"zai": 0.55, "qwen": 0.75}.get(voice, 0.9),
                   sentences=2)


if __name__ == "__main__":
    c, e = mm_call("Write one short paragraph on: the map is finished and the territory is still asking", 400)
    print("p1 err:", e, "| len:", len(c or ""), "| think:", "<think>" in (c or ""))
    print(c)
    print("---- p2 gate ----")
    s, e2 = call_p2("zai", "Write exactly TWO sentences braiding: the substrate is grown, the cell is a scar. Return only the two sentences.", 600)
    print("p2 err:", e2, "| n_sent:", len(sent_split(s or "")))
    print(s)
