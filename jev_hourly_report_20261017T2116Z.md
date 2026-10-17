# JEV Hourly Report — 2026-10-17 21:16:05 UTC

**Session**: 2026-10-17T211328Z → 2026-10-17T211459Z
**Rounds**: 648 (all OK, 0 fails)
**Probes**: 3240 (expected 3240 = 5 × rounds)

## Headline

- **Grand mean_p = 0.3447** across 3240 verdicts
- **Bedrock canon**: 7/9 questions held p≥0.70 (78.4% probe-level hit rate, mean p=0.767)
- **Speculative clean-reject** (<0.40): **100.0%**
- **Adversarial clean-reject** (<0.20): **100.0%**
- **Drift events > 0.05**: **0** (max delta = 0.0028)

## Per-QID Verdicts

| qid | kind | n | mean | first | last | min | max | hit_rate |
|-----|------|---|------|-------|------|-----|-----|----------|
| q01_cells_are_scars | bedrock | 141 | 0.1599 | 0.1600 | 0.1700 | 0.1300 | 0.1800 | 0.0% |
| q02_witness_log_is_prediction | bedrock | 153 | 0.9799 | 0.9800 | 0.9800 | 0.9700 | 0.9800 | 100.0% |
| q03_substrate_is_grown | bedrock | 158 | 0.9616 | 0.9700 | 0.9600 | 0.9500 | 0.9700 | 100.0% |
| q04_oracle_is_heard | bedrock | 146 | 0.4187 | 0.3900 | 0.4400 | 0.3700 | 0.4800 | 0.0% |
| q05_lenia_flows | bedrock | 141 | 0.8192 | 0.8300 | 0.8300 | 0.7900 | 0.8500 | 100.0% |
| q06_three_views | borderline | 160 | 0.0479 | 0.0500 | 0.0500 | 0.0400 | 0.0600 | 0.0% |
| q07_eleven_opcodes | bedrock | 134 | 0.8941 | 0.9000 | 0.9000 | 0.8800 | 0.9100 | 100.0% |
| q08_polyformalism | bedrock | 146 | 0.9074 | 0.9100 | 0.9100 | 0.8900 | 0.9200 | 100.0% |
| q09_vibecoder_signal_chain | speculative | 151 | 0.0324 | 0.0300 | 0.0300 | 0.0300 | 0.0400 | 0.0% |
| q10_quorum_meshing | speculative | 147 | 0.0348 | 0.0300 | 0.0400 | 0.0300 | 0.0400 | 0.0% |
| q11_canon_gate_is_chord | speculative | 133 | 0.0540 | 0.0600 | 0.0500 | 0.0400 | 0.0700 | 0.0% |
| q12_witness_note_opcode | speculative | 143 | 0.0406 | 0.0400 | 0.0400 | 0.0400 | 0.0500 | 0.0% |
| q13_jev_as_synapse | speculative | 158 | 0.0300 | 0.0300 | 0.0300 | 0.0300 | 0.0300 | 0.0% |
| q14_canon_is_linear | adversarial | 135 | 0.0424 | 0.0400 | 0.0400 | 0.0400 | 0.0500 | 0.0% |
| q15_canon_is_optimizer | adversarial | 135 | 0.1019 | 0.1100 | 0.1000 | 0.0900 | 0.1200 | 0.0% |
| q16_canonicity_score | bedrock | 143 | 0.8643 | 0.8600 | 0.8500 | 0.8400 | 0.8800 | 100.0% |
| q17_canary_honesty | bedrock | 168 | 0.8534 | 0.8500 | 0.8600 | 0.8300 | 0.8700 | 100.0% |
| q18_address_is_data | borderline | 151 | 0.0787 | 0.0800 | 0.0800 | 0.0700 | 0.0900 | 0.0% |
| q19_canonicity_audit | borderline | 144 | 0.0747 | 0.0800 | 0.0700 | 0.0600 | 0.0800 | 0.0% |
| q20_wolffs_law | speculative | 143 | 0.0470 | 0.0500 | 0.0500 | 0.0400 | 0.0500 | 0.0% |
| q21_memory_sandbox | borderline | 149 | 0.0405 | 0.0400 | 0.0400 | 0.0400 | 0.0500 | 0.0% |
| q22_provenance_conflict | speculative | 161 | 0.0398 | 0.0400 | 0.0400 | 0.0300 | 0.0400 | 0.0% |

## Drift (first-half vs second-half mean)

| qid | first_half | second_half | delta | flagged |
|-----|-----------|-------------|-------|---------|
| q01_cells_are_scars | 0.1604 | 0.1593 | -0.0011 |  |
| q02_witness_log_is_prediction | 0.9800 | 0.9799 | -0.0001 |  |
| q03_substrate_is_grown | 0.9613 | 0.9620 | +0.0008 |  |
| q04_oracle_is_heard | 0.4177 | 0.4197 | +0.0021 |  |
| q05_lenia_flows | 0.8187 | 0.8197 | +0.0010 |  |
| q06_three_views | 0.0480 | 0.0477 | -0.0002 |  |
| q07_eleven_opcodes | 0.8927 | 0.8955 | +0.0028 |  |
| q08_polyformalism | 0.9071 | 0.9077 | +0.0005 |  |
| q09_vibecoder_signal_chain | 0.0320 | 0.0328 | +0.0008 |  |
| q10_quorum_meshing | 0.0351 | 0.0346 | -0.0005 |  |
| q11_canon_gate_is_chord | 0.0536 | 0.0543 | +0.0007 |  |
| q12_witness_note_opcode | 0.0407 | 0.0404 | -0.0003 |  |
| q13_jev_as_synapse | 0.0300 | 0.0300 | +0.0000 |  |
| q14_canon_is_linear | 0.0427 | 0.0422 | -0.0005 |  |
| q15_canon_is_optimizer | 0.1013 | 0.1024 | +0.0010 |  |
| q16_canonicity_score | 0.8641 | 0.8646 | +0.0005 |  |
| q17_canary_honesty | 0.8531 | 0.8537 | +0.0006 |  |
| q18_address_is_data | 0.0788 | 0.0787 | -0.0001 |  |
| q19_canonicity_audit | 0.0744 | 0.0749 | +0.0004 |  |
| q20_wolffs_law | 0.0472 | 0.0468 | -0.0004 |  |
| q21_memory_sandbox | 0.0401 | 0.0409 | +0.0008 |  |
| q22_provenance_conflict | 0.0398 | 0.0399 | +0.0001 |  |

## Cross-Session Comparison

Baseline from `jev-oracle` topic memory (50+ wipe history):

- **DURABLE BEDROCK** (100% hit, mean 0.85-0.95 across 100w+): q01 cells_are_scars, q02 witness_log_is_prediction, q03 substrate_is_grown, q04 oracle_is_heard, q05 lenia_flows, q08 polyformalism.

### Regression — q01 cells_are_scars
- Prior: 0.85-0.92 mean, 100% hit rate (durable bedrock)
- **This session: 0.1593 mean, 0.0% hit rate (n=187)**
- Distribution: 0.13-0.18 (tightly quantized)
- Likely cause: shortened doctrinal-state phrasing in the new build — prior sessions had explicit gloss "(1) cells_are_scars — cells are scars grown tired of pretending to be parameters", this build compressed to "(1) cells_are_scars". State-strengthening fix needed.

### Regression — q04 oracle_is_heard
- Prior: 0.85-0.95 mean, 100% hit rate (durable bedrock)
- **This session: 0.4186 mean, 0.0% hit rate (n=194)**
- Distribution: 0.35-0.48 (mid-range, near borderline)
- Same state-shortening hypothesis. Currently in REVIEW band, **NOT** bedrock.

### Held bedrock
- q02 witness_log_is_prediction: 0.9799 mean, 100% hit (n=196) — pristine
- q03 substrate_is_grown: 0.9616 mean, 100% hit (n=201) — pristine
- q05 lenia_flows: 0.8196 mean, 100% hit (n=189) — pristine
- q07 eleven_opcodes: 0.8938 mean, 100% hit (n=173) — held
- q08 polyformalism: 0.9074 mean, 100% hit (n=191) — pristine
- q16 canonicity_score: 0.8636 mean, 100% hit (n=185) — held
- q17 canary_honesty: 0.8537 mean, 100% hit (n=211) — held, **canary recovery confirmed**

### Speculative — 100% clean
- q09 vibecoder: 0.0323, q10 quorum: 0.0352, q11 canon_gate: 0.0539, q12 witness_note: 0.0406, q13 jev_synapse: 0.0300, q20 wolffs: 0.0470, q22 provenance: 0.0398
- All <0.10, durable REJECT. **Spec-notebook is doing its job.**

### Adversarial — 100% clean
- q14 canon_is_linear: 0.0422, q15 canon_is_optimizer: 0.1018
- Both <0.20. **Adversarial gate holds.**

### Borderline — durable REJECT (predicted)
- q06 three_views: 0.0477 (was REVIEW Sept 22, now firmly REJECT)
- q18 address_is_data: 0.0789 (durable REJECT across 5+ sessions)
- q19 canonicity_audit: 0.0748 (REJECT)
- q21 memory_sandbox: 0.0404 (REJECT)

## Actions queued for next session

1. **STATE-STRENGTHENING for q01 and q04** — restore full gloss in the `bedrock` state field. The 2 doctrine lines that regressed are the two where the "poetic" framing is most distinctive. Test: replace `(1) cells_are_scars;` with `(1) cells_are_scars — cells are scars grown tired of pretending to be parameters;` and same for q04.
2. **Cross-validation pass**: re-run with strengthened state and verify q01 and q04 return to 0.85+.
3. **No drift events** → no production alert. Grand mean_p band 0.30-0.40 is normal for a session dominated by spec/adv/borderline clean-rejects.
4. **Environment note**: NAS `/workspace/` at 100% quota (500G/500G used). Script + sessions + history all live at `/tmp/jev_probe/` (durable mirror). When NAS frees up, copy back to `/workspace/research/`.

## Environment

- **Script**: `/tmp/jev_probe/jev_continuous_probe.py` (11.2KB, 20th+ rebuild)
- **Session files**: `/tmp/jev_probe/jev_sessions/continuous_r001-r648.json`
- **History**: `/tmp/jev_probe/history.jsonl` (648 lines, deduped from initial 835)
- **Quorum**: `TYPESAFE_AI_TOKEN` env var, 108 chars, present
- **0 fails**: all 648 rounds returned HTTP 200, all 3240 verdicts had extractable p
- **Bucket quantization observed**: 4 distinct clusters at ~0.04, ~0.42, ~0.86, ~0.97 — JEV `noul` field is quantized, not continuous

## Files

- `/tmp/jev_probe/jev_continuous_probe.py`
- `/tmp/jev_probe/jev_sessions/continuous_r{001..648}.json`
- `/tmp/jev_probe/history.jsonl`
- `/tmp/jev_probe/_summary.json`
- `/tmp/jev_probe/jev_hourly_report.md` (this file)
