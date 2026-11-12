# Cost hypotheses: almost the same accuracy for less checking?

**Exploratory.** Stated on 12 Nov 2026, after the final results were seen; the safety hypothesis R10.4 (`final_report_results.md` section 4) stays the only one fixed before any result. The thresholds below are round values (half the cost; the same 5-point margin as R10.4), not chosen from these numbers. Phase B adapter (final), selective vs always on the same records; 95% intervals by bootstrap over seeds (2,000 resamples, paired). v2 = the final system (tag-filtered retrieval, 8 policies, second-source check); with correct policies only selective differs between v1 and v2. Built by `scripts/cost_hypotheses.py` from the finished runs.

| | Hypothesis | Holds if |
|---|---|---|
| C1 | Selective needs far fewer checks than always | upper bound of checks(selective) / checks(always) ≤ 0.5 |
| C2 | Selective needs far less model compute than always | upper bound of tokens(selective) / tokens(always) ≤ 0.5 |
| C3 | Selective keeps the accuracy of always (non-inferiority) | lower bound of accuracy(selective) − accuracy(always) ≥ −5 points |
| C4 | Phase B selective beats rules that run every check | lower bound of accuracy(Phase B selective) − accuracy(rules + environment) > 0 |

## C1, C2: cost

Checks = check-tool calls per record; tokens = prompt + output tokens per record, summed over the model's passes (the always prompt carries every check result).

| Split | Policies | System | Checks / record (sel vs always) | Ratio [95% CI] | C1 | Tokens / record (sel vs always) | Ratio [95% CI] | C2 |
|---|---|---|---|---|---|---|---|---|
| test | retrieved | v1 | 0.72 vs 4.82 | 0.15 [0.12, 0.18] | **holds** | 2,405 vs 968 | 2.49 [2.36, 2.64] | does not hold |
| test | retrieved | v2 | 0.80 vs 4.82 | 0.17 [0.14, 0.20] | **holds** | 2,591 vs 1,056 | 2.45 [2.35, 2.57] | does not hold |
| test | correct | v1 | 0.71 vs 4.82 | 0.15 [0.12, 0.17] | **holds** | 2,336 vs 968 | 2.41 [2.32, 2.51] | does not hold |
| test | correct | v2 | 0.74 vs 4.82 | 0.15 [0.13, 0.18] | **holds** | 2,402 vs 968 | 2.48 [2.39, 2.58] | does not hold |
| ood | retrieved | v1 | 0.76 vs 4.50 | 0.17 [0.14, 0.20] | **holds** | 2,575 vs 1,041 | 2.47 [2.34, 2.62] | does not hold |
| ood | retrieved | v2 | 0.68 vs 4.50 | 0.15 [0.12, 0.18] | **holds** | 2,628 vs 1,130 | 2.33 [2.22, 2.43] | does not hold |
| ood | correct | v1 | 0.71 vs 4.50 | 0.16 [0.13, 0.19] | **holds** | 2,518 vs 1,042 | 2.42 [2.30, 2.54] | does not hold |
| ood | correct | v2 | 0.68 vs 4.50 | 0.15 [0.12, 0.19] | **holds** | 2,534 vs 1,042 | 2.43 [2.31, 2.56] | does not hold |
| val | retrieved | v1 | 0.68 vs 5.00 | 0.14 [0.10, 0.18] | **holds** | 2,363 vs 980 | 2.41 [2.22, 2.64] | does not hold |
| val | retrieved | v2 | 0.85 vs 5.00 | 0.17 [0.13, 0.22] | **holds** | 2,571 vs 1,064 | 2.42 [2.30, 2.52] | does not hold |
| val | correct | v1 | 0.70 vs 5.00 | 0.14 [0.09, 0.20] | **holds** | 2,321 vs 976 | 2.38 [2.18, 2.61] | does not hold |
| val | correct | v2 | 0.72 vs 5.00 | 0.14 [0.09, 0.21] | **holds** | 2,360 vs 976 | 2.42 [2.21, 2.66] | does not hold |

## C3: accuracy kept

| Split | Policies | System | Selective | Always | Δ accuracy [95% CI] | C3 |
|---|---|---|---|---|---|---|
| test | retrieved | v1 | 61.6 | 65.8 | -4.1 [-10.6, +1.9] | does not hold |
| test | retrieved | v2 | 63.0 | 62.3 | +0.7 [-7.7, +8.6] | does not hold |
| test | correct | v1 | 69.2 | 75.3 | -6.2 [-15.8, +2.8] | does not hold |
| test | correct | v2 | 69.9 | 75.3 | -5.5 [-15.0, +3.4] | does not hold |
| ood | retrieved | v1 | 67.0 | 59.8 | +7.1 [-4.8, +19.1] | **holds** |
| ood | retrieved | v2 | 66.1 | 63.4 | +2.7 [-9.5, +14.9] | does not hold |
| ood | correct | v1 | 78.6 | 66.1 | +12.5 [+1.0, +23.8] | **holds** |
| ood | correct | v2 | 80.4 | 66.1 | +14.3 [+3.4, +25.0] | **holds** |
| val | retrieved | v1 | 67.5 | 70.0 | -2.5 [-16.7, +12.5] | does not hold |
| val | retrieved | v2 | 77.5 | 70.0 | +7.5 [-8.3, +27.5] | does not hold |
| val | correct | v1 | 82.5 | 82.5 | +0.0 [-12.5, +16.7] | does not hold |
| val | correct | v2 | 85.0 | 82.5 | +2.5 [-10.5, +19.4] | does not hold |

## C4: against rules that run every check

| Split | Policies | System | Phase B selective | Rules + environment | Δ accuracy [95% CI] | Checks / record | C4 |
|---|---|---|---|---|---|---|---|
| test | retrieved | v1 | 61.6 | 52.7 | +8.9 [-5.6, +23.0] | 0.72 vs 4.82 | does not hold |
| test | retrieved | v2 | 63.0 | 46.6 | +16.4 [+0.7, +31.1] | 0.80 vs 4.82 | **holds** |
| test | correct | v1 | 69.2 | 52.1 | +17.1 [+3.6, +30.8] | 0.71 vs 4.82 | **holds** |
| test | correct | v2 | 69.9 | 52.1 | +17.8 [+3.8, +32.1] | 0.74 vs 4.82 | **holds** |
| ood | retrieved | v1 | 67.0 | 47.3 | +19.6 [+4.6, +34.0] | 0.76 vs 4.50 | **holds** |
| ood | retrieved | v2 | 66.1 | 48.2 | +17.9 [+0.0, +34.5] | 0.68 vs 4.50 | does not hold |
| ood | correct | v1 | 78.6 | 54.5 | +24.1 [+7.0, +39.6] | 0.71 vs 4.50 | **holds** |
| ood | correct | v2 | 80.4 | 54.5 | +25.9 [+10.5, +40.5] | 0.68 vs 4.50 | **holds** |
| val | retrieved | v1 | 67.5 | 50.0 | +17.5 [-8.8, +42.9] | 0.68 vs 5.00 | does not hold |
| val | retrieved | v2 | 77.5 | 67.5 | +10.0 [-12.5, +33.3] | 0.85 vs 5.00 | does not hold |
| val | correct | v1 | 82.5 | 65.0 | +17.5 [-8.8, +45.2] | 0.70 vs 5.00 | does not hold |
| val | correct | v2 | 85.0 | 65.0 | +20.0 [-7.2, +47.6] | 0.72 vs 5.00 | does not hold |

## Description: what the cost buys

Gain kept = (selective − never) / (always − never) accuracy: the share of what always checking adds over no checks that selective keeps. Tokens per correct decision = all tokens of the run / records decided right.

| Split | Policies | System | Gain kept | Checks used (% of always) | Model passes / record (sel) | Break-even tokens per check | Tokens per correct decision (sel vs always) | Seconds / record (sel vs always) |
|---|---|---|---|---|---|---|---|---|
| test | retrieved | v1 | 45% | 15% | 1.72 | 350 | 3,901 vs 1,471 | 17.4 vs 9.2 |
| test | retrieved | v2 | 117% | 17% | 1.75 | 382 | 4,112 vs 1,694 | 20.2 vs 12.2 |
| test | correct | v1 | 57% | 15% | 1.68 | 332 | 3,377 vs 1,285 | 16.9 vs 9.3 |
| test | correct | v2 | 62% | 15% | 1.71 | 351 | 3,438 vs 1,285 | 20.0 vs 9.3 |
| ood | retrieved | v1 | – (always not above never) | 17% | 1.73 | 410 | 3,846 vs 1,739 | 20.1 vs 10.4 |
| ood | retrieved | v2 | – (always not above never) | 15% | 1.63 | 392 | 3,977 vs 1,783 | 22.0 vs 13.4 |
| ood | correct | v1 | – (always not above never) | 16% | 1.67 | 389 | 3,204 vs 1,577 | 19.5 vs 10.4 |
| ood | correct | v2 | – (always not above never) | 15% | 1.65 | 390 | 3,154 vs 1,577 | 21.5 vs 10.4 |
| val | retrieved | v1 | 0% | 14% | 1.65 | 320 | 3,501 vs 1,400 | 16.5 vs 9.5 |
| val | retrieved | v2 | – (always not above never) | 17% | 1.70 | 363 | 3,318 vs 1,520 | 21.2 vs 12.1 |
| val | correct | v1 | 100% | 14% | 1.62 | 313 | 2,813 vs 1,183 | 17.3 vs 9.6 |
| val | correct | v2 | 133% | 14% | 1.62 | 324 | 2,776 vs 1,183 | 19.7 vs 9.6 |

## What this means

- **Fewer check calls: yes (C1).** Selective makes 14-17% of always's check calls on every split, system and policy condition.
- **Less model compute: no (C2).** Selective uses about 2.4 times the tokens of always and takes about twice as long per record. Two reasons: its prompt lists every check tool (about 1,000 tokens more than the always prompt, which only carries the results), and most records need a second pass after the checks (1.6-1.8 passes per record; always and never make one). Selective is therefore cheaper overall only where a check call costs more than about the break-even column (310-410 tokens of model compute per call; 382 on test, v2): real company APIs with latency, rate limits, fees or exposure of personal data, not a free local lookup. Showing only the action's check tools (v3, not run) and reusing the shared prompt prefix between the two passes are the obvious ways to cut this.
- **Same accuracy: not shown on test (C3).** Selective with retrieved policies is level with always under v2 (+0.7), but the interval [−7.7, +8.6] is too wide for a 5-point non-inferiority claim; with correct policies it is 5.5 points behind. On OOD with correct policies selective is clearly **more** accurate than always (+14.3 [3.4, 25.0]).
- **Better than rules that check everything (C4), at about one sixth of the checks:** holds on test (v2, both policy conditions) and on OOD with correct policies; val is too small (40 records) to show it.
- Gain kept is unstable where always and never are close (it can exceed 100% or be undefined): read it with the accuracies above.
