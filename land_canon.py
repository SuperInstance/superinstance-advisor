import json, os, re
tag = "taps-20261023T210505Z"
j = json.load(open(f"sessions/{tag}.json"))
combined = j["combined"]
# canon .md in house style (same as 161w)
open(f"canon/{tag}.md","w").write(combined)
# canon .json: the cell payload shape, with citation graph
state = {"text": combined, "topic": j["topic"], "tag": tag, "title": j["topic"],
         "refs": [], "dials": j["dials"],
         "voices": j["postures"], "models": j["models"], "seed": j["seed"]}
open(f"canon/{tag}.json","w").write(json.dumps(
    {"state": state, "source": "taps-creative-break", "round": j["round"],
     "guards": j["guards"], "submit_status": j["submit_status"],
     "submit_resp": j["submit_resp"]}, indent=1))
print("canon written:", os.path.getsize(f"canon/{tag}.md"), "bytes md")
# report
g = j["guards"]
rep = f"""# Taps round 162w (2026-10-23T21:05Z) — the index outgrew the library it was meant to describe

**tag (canon):** `{tag}`
**topic:** the-index-outgrew-the-library-it-was-meant-to-describe
**seed:** the-index-outgrew-the-library-it-was-meant-to-describe (0 prior sightings — not in the shipped topic bank, not in 157w–161w)
**models:** zai=MiniMax-M2.7-highspeed (MECHANISM) · qwen=MiniMax-M3 (DEFEND) · kimi=MiniMax-M2.5 (DEEPER)
**submit:** HTTP **404** on `POST /api/cell` — the canon write path is gone (49th consecutive 404; `GET /health` returns 200 but `/api/cell` and `/api/cells` are 404 on GET *and* POST). **Canon landed in git** as the durable transport. Nothing is hidden.

## Why there were two rounds

The script as shipped (`taps_creative_break.py`) was run first, unmodified, exactly as asked. It produced `taps-20261023T210353Z`: **6/6 voice calls OK, submit 404** — and it was not a round.

| defect | measurement |
|---|---|
| one model, three voices | `minimax_voices.py` pins `MM_MODEL = "MiniMax-M2.5"`; `zai_call`/`qwen_call`/`kimi_call` are three temperature aliases (0.55/0.75/0.90) of one model |
| one template | `p1_prompts = {{v: P1_PROMPT.format(topic=topic)}}` — the *same string* for all three voices, by construction |
| shared skeleton (G6b) | **opening clauses 1/3 distinct** — all three voices open on the identical clause *"The canon is not a container waiting for…"* |
| shared n-grams | **13 shared 3-grams, 8 shared 4-grams** across the three openings |
| topic restatement | 3/3 voices restate the topic clause |
| no provenance in artifact | no `models` field, no `postures` field — the output cannot name who spoke |

A 200w-style p2 budget also ships at 900 tokens, which truncates reasoning models to a single character (measured at 155w: all three p2 came back as `"T"`, `"T"`, `"I"`). This round used 32000.

## The repaired round — `{tag}`

6/6 OK. Zero retries, zero hand-fallbacks. p1 1875 / 1675 / 1738 ch, p2 694 / 703 / 730 ch.

| guard | shipped script (210353Z) | repaired (210505Z) |
|---|---|---|
| distinct models | **1** (M2.5 x3) | **3** |
| `models` + `postures` in artifact | absent | present |
| G1 p1 byte-distinct | 3/3 | 3/3 |
| G2 p2 sentence count | 2/2/2 | 2/2/2 |
| G3 shared 3-grams | **13** | **8** (4 after doctrine discount) |
| G4 shared 4-grams | **8** | **1** (0 after doctrine discount) |
| G5 topic restatement (max) | **3** | **1** |
| **G6b distinct opening clauses** | **1/3** | **3/3** |
| G6b distinct sentence skeletons | 3/3 | 3/3 |
| G7 dials distinct + non-monotone | 16/16 | 16/16 |
| submit | 404 | 404 |

- zai: `a catalog card is a tiny` · skeleton (5,3,6,0,1,1,4,5,4,3,5,3,3,3)
- qwen: `i want to put the index` · skeleton (3,5,1,5,3,1,3,4,0,7,2,2,3)
- kimi: `describability begins with a wager that` · skeleton (4,4,4,3,4,1,3,4,4,4,7)

**Dials verified by diffing against upstream `text_to_dials` (imported, never reimplemented): byte-identical.** 16/16 distinct, non-monotone.

## Model catalog — probed, not trusted

`GET /v1/models` returned **9** ids, but probing each with a trivial prompt and checking non-empty `choices[0].message.content`:

| model | result |
|---|---|
| MiniMax-M3.1-Flash | answers (len 2) |
| MiniMax-M3 | answers (reasoning, `<think>` prefix) |
| MiniMax-M2.7 | answers (reasoning) |
| MiniMax-M2.7-highspeed | answers (len 2) |
| MiniMax-M2.5 | answers (reasoning) |
| MiniMax-M2.5-highspeed | answers (len 3) |
| MiniMax-M2.1 / M2.1-highspeed | **HTTP 404 — retired (2069)** |
| MiniMax-M2 | **HTTP 404 — retired (2069)** |

The retired models are **still listed** by the catalog endpoint. Only the probe distinguishes them.

## 21st dissent shape — the INDEX as ECONOMICAL SUBSTITUTION

Ladder: 16th = reader's production (157w) · 17th = crack as condition (158w) · 18th = sale as transfer (159w) · 19th = listener's constitution (160w) · 20th = right to refuse (161w) · **21st = the apparatus as SUBSTITUTE rather than pointer.**

- zai (MECHANISM): the pointer points only while a **chain of interventions remains true** — the volume on its shelf, the call number meaning the same thing to every hand. The index can therefore "appear to grow while its referent dissolves." p2: cataloging is itself a **constitutive intervention**, so a marginalized work may never have had an independent referential life at all.
- qwen (DEFEND): the index's real achievement is not fidelity but **economical substitution** — it "defines the terms under which the library may appear." It can **prune the library without destroying anything, simply by making omission invisible.** "We have allowed prediction to impersonate memory and made coherence look like care."
- kimi (DEEPER): **describability begins with a wager** — that what is happening will leave enough shape for another voice to answer, yet not so fixed that naming could stop it. The library "does not preserve the thing; it rehearses the thing's likely arrival." The deeper danger: description becomes the only habitat left for the thing.

**zai (chain of interventions) and kimi (the wager) name the same failure from opposite ends** — the apparatus is not a window onto a pre-existing object but a condition of its continued existence — while **qwen attacks the frame itself** (the index substitutes, it does not describe). Convergence between a MECHANISM voice and a DEEPER voice is evidence of a real theme, not of templating.

**Dedup:** 0 prior hits for this shape; it is not the 19th (listener's constitution) or the 20th (right to refuse) restated.

## Canon (162w)

- *"The index can therefore appear to grow while its referent dissolves, accumulating more precise coordinates for a library whose objects have quietly become historical."*
- *"Once the index becomes more complete, stable, and useful than the library it claims to serve, it no longer answers for the library; it defines the terms under which the library may appear."*
- *"The index can prune the library without destroying anything, simply by making omission invisible."*
- *"Describability begins with a wager: that what is happening will leave enough of a shape for another voice to answer, yet not so fixed that naming could stop it."*
- *"The deeper danger is not that the index exceeds the library; it is that description becomes the only habitat left for the thing."*
- *"The index works only while someone maintains the difference between the live thing and the surviving scar around it."*

## Env

23rd consecutive `/workspace/research` wipe — the directory did not exist; rebuilt `/tmp/superinstance-advisor` from `SuperInstance/superinstance-advisor @ a893be2` with `GIT_SSL_NO_VERIFY=1`. NAS 600G/600G (24th recurrence) ⇒ **git is the durable copy; `/workspace` writes leave 0-byte stubs.** TLS **clean on first try** — curl 200 *and* Python 200 on `api.github.com` in the same second ⇒ no cert-anchor wall, no 289-cert rebuild (5th clean wipe). ZAI/DeepInfra/Cloudflare creds absent (36th wipe) ⇒ the shipped script's "zai/qwen/kimi" labels are temperature aliases, not providers. `gh` absent (13th wipe). Script md5 `4e84d0632fc556733acd1066e7bb32db` unchanged **7th** wipe. Runner `taps_round_162w.py`.
"""
open(f"canon/{tag}-report.md","w").write(rep)
print("report written:", os.path.getsize(f"canon/{tag}-report.md"))
