"""Live-voice shim for the 197w Taps round: three DISTINCT MiniMax models.

Rationale (durable): ZAI_TOKEN / DEEPINFRA_TOKEN / Cloudflare creds are ABSENT,
so zai/qwen/kimi are MODEL SLOTS. But three slots on ONE model is a two-template
round, not a round. Three slots on three DIFFERENT models with three DIFFERENT
postures is a round. Model identity is a PROVENANCE property.

Gates this needs:
  1. Reasoning models lead with <think>...</think> (sometimes UNTERMINATED)
     -> strip BEFORE any paragraph/sentence gate.
  2. Responses scale with prompt size and IGNORE max_tokens for form
     -> enforce sentence count POST-HOC, never trust a "done" flag.
  3. api.minimax.io is live; a 200 with choices=null is a RETIRED model, not an answer.
  4. 503 "DNS cache overflow" is TRANSIENT -> back off 12+6*attempt and retry.
  5. Default urllib UA -> Cloudflare 403. Send an explicit User-Agent.
"""
import json, os, re, time, urllib.request, urllib.error

MM_BASE = "https://api.minimax.io/v1"
UA = "taps-creative-break/1.0"

# three DISTINCT live models, one per slot
# 197w: the map ROTATES each round (191w-194w all rotated) so a single model
# cannot carry two slots across consecutive rounds.
VOICE_MODELS = {
    "zai":  "MiniMax-M2.7",           # MECHANISM
    "qwen": "MiniMax-M3.1-Flash",     # DEFEND
    "kimi": "MiniMax-M2.5",           # DEEPER
}
VOICE_TEMP = {"zai": 0.55, "qwen": 0.75, "kimi": 0.9}
VOICE_POSTURE = {"zai": "MECHANISM", "qwen": "DEFEND", "kimi": "DEEPER"}

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.S)


def strip_think(text: str) -> str:
    """Strip <think> blocks, including an UNTERMINATED trailing one."""
    if not text:
        return ""
    out = _THINK_BLOCK.sub("", text)
    if "<think>" in out:
        out = out.split("<think>")[0]
    return out.strip()


def sent_split(text: str) -> list:
    t = strip_think(text or "")
    t = re.sub(r"^\s*#{1,6}\s.*$", "", t, flags=re.M)
    t = re.sub(r"^\s*\*\*[^*]+\*\*\s*:?.*$", "", t, flags=re.M)
    t = re.sub(r"^\s*(Voice|MECHANISM|DEFEND|DEEPER|TEXT)\b.*$", "", t, flags=re.M | re.I)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'“])", t) if s.strip()]


def first_sentences(text: str, n: int) -> str:
    s = sent_split(text)
    return " ".join(s[:n]) if s else ""


def mm_call(prompt: str, max_tokens: int = 32000, temperature: float = 0.7,
            sentences: int | None = None, model: str = "MiniMax-M2.5",
            retries: int = 3):
    key = os.environ.get("MINIMAX_KEY")
    if not key:
        return None, "MINIMAX_KEY unset"
    body = {"model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": temperature}
    data = json.dumps(body).encode("utf-8")
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                f"{MM_BASE}/chat/completions", data=data,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json",
                         "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                j = json.load(r)
            ch = (j.get("choices") or [None])[0]
            if ch is None:
                last = f"choices=None base_resp={json.dumps(j.get('base_resp', {}))[:140]}"
                time.sleep(12 + 6 * attempt)
                continue
            raw = (ch.get("message") or {}).get("content") or ""
            if not raw.strip():
                last = "empty content"
                time.sleep(4)
                continue
            clean = strip_think(raw)
            if not clean:
                last = "think-strip produced empty"
                time.sleep(4)
                continue
            if sentences is not None:
                clean = first_sentences(clean, sentences)
                if not clean:
                    last = "sentence gate produced empty"
                    time.sleep(4)
                    continue
            return clean, None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 503:
                time.sleep(12 + 6 * attempt)
            else:
                time.sleep(4)
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(8 + 4 * attempt)
    return None, last or "exhausted"


def zai_call(prompt, max_tokens):
    return mm_call(prompt, max_tokens, VOICE_TEMP["zai"], model=VOICE_MODELS["zai"])


def qwen_call(prompt, max_tokens):
    return mm_call(prompt, max_tokens, VOICE_TEMP["qwen"], model=VOICE_MODELS["qwen"])


def kimi_call(prompt, max_tokens):
    return mm_call(prompt, max_tokens, VOICE_TEMP["kimi"], model=VOICE_MODELS["kimi"])


def call_p2(voice: str, prompt: str, max_tokens: int):
    return mm_call(prompt, max_tokens, VOICE_TEMP.get(voice, 0.9), sentences=2,
                   model=VOICE_MODELS[voice])
