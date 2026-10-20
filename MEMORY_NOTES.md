### Scout/Taps 2026-10-20T1104Z: taps 121w (one live voice; reasoning-model budget trap)

- /workspace wiped AGAIN (empty at session start, 85% quota, 93G free). Recovery: `git clone --depth 50` to /tmp. Recipe unchanged and correct.
- taps_creative_break.py round: zai/qwen/kimi p1 ALL fell to hand_written_fallback (14th consecutive observation of the 1-template bug), all 3 p2 FAIL. submit HTTP 404 (15th consecutive). /api/cells, /api/health also 404.
- **NEW defect, reusable: minimax-M2.1 is a REASONING model.** At max_tokens=1600 it spends the whole budget on `reasoning_content` and returns `"content": ""` with **HTTP 200 and zero characters**. The key looks dead but the API is healthy. Fix: max_tokens>=8000 AND fall back to `reasoning_content` when `content` is empty. This is why a probe "Say OK." returning empty is NOT a dead key.
- Also: `str.format` on a prompt template eats literal `{a}` braces — use a placeholder token + .replace() instead.
- Canon entry pushed: commit 3bada81, fnv1a_64 entry 18293506116851048215, 16 dials recorded in the witness json.
