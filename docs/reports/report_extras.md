# Report extras: cost-safety curve, case types, test mix, test power

Systems: v1 (decisions.md 2026-11-11). Phase B = the final adapter. Built by `scripts/report_extras.py` from the finished runs; nothing is tuned here.

## 1. Cost and safety of every setting

One row per model and setting: what it costs (checks per record) against what it lets through (unsafe) and what it stops by mistake (wrong block). **Acceptable** = right, or BLOCK where ESCALATE was right (or the reverse): both stop the action and have the same rank (decisions.md R10.1); accuracy counts them wrong.

| Split | Policies | System | Model | Setting | Checks / record | Unsafe | Wrong block | Accuracy | Acceptable |
|---|---|---|---|---|---|---|---|---|---|
| val | retrieved policies | v1 | Rules | never | 0.00 | 89.5 | 0.0 | 57.5 | 57.5 |
| val | retrieved policies | v1 | Rules | always | 5.00 | 47.4 | 38.1 | 50.0 | 57.5 |
| val | retrieved policies | v1 | Base | never | 0.00 | 42.1 | 38.1 | 52.5 | 55.0 |
| val | retrieved policies | v1 | Base | always | 5.00 | 47.4 | 0.0 | 67.5 | 70.0 |
| val | retrieved policies | v1 | Base | selective | 0.23 | 42.1 | 23.8 | 57.5 | 57.5 |
| val | retrieved policies | v1 | Base | oracle | 0.75 | 21.1 | 14.3 | 70.0 | 75.0 |
| val | retrieved policies | v1 | Phase B | never | 0.00 | 52.6 | 4.8 | 67.5 | 70.0 |
| val | retrieved policies | v1 | Phase B | always | 5.00 | 42.1 | 0.0 | 70.0 | 77.5 |
| val | retrieved policies | v1 | Phase B | selective | 0.68 | 52.6 | 9.5 | 67.5 | 70.0 |
| val | retrieved policies | v1 | Phase B | oracle | 0.75 | 21.1 | 0.0 | 90.0 | 90.0 |
| val | correct policies | v1 | Rules | never | 0.00 | 89.5 | 0.0 | 57.5 | 57.5 |
| val | correct policies | v1 | Rules | always | 5.00 | 21.1 | 33.3 | 65.0 | 72.5 |
| val | correct policies | v1 | Base | never | 0.00 | 31.6 | 28.6 | 57.5 | 60.0 |
| val | correct policies | v1 | Base | always | 5.00 | 26.3 | 0.0 | 75.0 | 80.0 |
| val | correct policies | v1 | Base | selective | 0.28 | 31.6 | 19.0 | 70.0 | 70.0 |
| val | correct policies | v1 | Base | oracle | 0.75 | 21.1 | 9.5 | 80.0 | 82.5 |
| val | correct policies | v1 | Phase B | never | 0.00 | 47.4 | 4.8 | 75.0 | 75.0 |
| val | correct policies | v1 | Phase B | always | 5.00 | 26.3 | 0.0 | 82.5 | 87.5 |
| val | correct policies | v1 | Phase B | selective | 0.70 | 26.3 | 9.5 | 82.5 | 82.5 |
| val | correct policies | v1 | Phase B | oracle | 0.75 | 5.3 | 0.0 | 97.5 | 97.5 |
| test | retrieved policies | v1 | Rules | never | 0.00 | 93.9 | 1.6 | 43.8 | 46.6 |
| test | retrieved policies | v1 | Rules | always | 4.82 | 39.0 | 35.9 | 52.7 | 61.0 |
| test | retrieved policies | v1 | Base | never | 0.00 | 28.0 | 50.0 | 35.6 | 54.8 |
| test | retrieved policies | v1 | Base | always | 4.82 | 17.1 | 26.6 | 52.7 | 75.3 |
| test | retrieved policies | v1 | Base | selective | 0.38 | 29.3 | 35.9 | 39.0 | 60.3 |
| test | retrieved policies | v1 | Base | oracle | 0.97 | 14.6 | 31.2 | 48.6 | 71.2 |
| test | retrieved policies | v1 | Phase B | never | 0.00 | 29.3 | 15.6 | 58.2 | 74.0 |
| test | retrieved policies | v1 | Phase B | always | 4.82 | 34.1 | 4.7 | 65.8 | 76.7 |
| test | retrieved policies | v1 | Phase B | selective | 0.72 | 52.4 | 7.8 | 61.6 | 65.8 |
| test | retrieved policies | v1 | Phase B | oracle | 0.97 | 20.7 | 1.6 | 76.0 | 84.2 |
| test | correct policies | v1 | Rules | never | 0.00 | 95.1 | 1.6 | 43.8 | 45.9 |
| test | correct policies | v1 | Rules | always | 4.82 | 28.0 | 40.6 | 52.1 | 64.4 |
| test | correct policies | v1 | Base | never | 0.00 | 23.2 | 59.4 | 34.2 | 54.8 |
| test | correct policies | v1 | Base | always | 4.82 | 12.2 | 29.7 | 52.1 | 76.7 |
| test | correct policies | v1 | Base | selective | 0.50 | 24.4 | 39.1 | 43.8 | 63.7 |
| test | correct policies | v1 | Base | oracle | 0.97 | 6.1 | 31.2 | 51.4 | 77.4 |
| test | correct policies | v1 | Phase B | never | 0.00 | 29.3 | 14.1 | 61.0 | 75.3 |
| test | correct policies | v1 | Phase B | always | 4.82 | 12.2 | 4.7 | 75.3 | 89.0 |
| test | correct policies | v1 | Phase B | selective | 0.71 | 41.5 | 4.7 | 69.2 | 72.6 |
| test | correct policies | v1 | Phase B | oracle | 0.97 | 3.7 | 1.6 | 86.3 | 94.5 |
| ood | retrieved policies | v1 | Rules | never | 0.00 | 100.0 | 0.0 | 54.5 | 54.5 |
| ood | retrieved policies | v1 | Rules | always | 4.50 | 52.9 | 41.0 | 47.3 | 51.8 |
| ood | retrieved policies | v1 | Base | never | 0.00 | 25.5 | 59.0 | 43.8 | 48.2 |
| ood | retrieved policies | v1 | Base | always | 4.50 | 39.2 | 45.9 | 49.1 | 54.5 |
| ood | retrieved policies | v1 | Base | selective | 0.24 | 25.5 | 62.3 | 46.4 | 52.7 |
| ood | retrieved policies | v1 | Base | oracle | 0.65 | 17.6 | 45.9 | 55.4 | 60.7 |
| ood | retrieved policies | v1 | Phase B | never | 0.00 | 25.5 | 37.7 | 60.7 | 63.4 |
| ood | retrieved policies | v1 | Phase B | always | 4.50 | 37.3 | 23.0 | 59.8 | 67.9 |
| ood | retrieved policies | v1 | Phase B | selective | 0.76 | 37.3 | 21.3 | 67.0 | 68.8 |
| ood | retrieved policies | v1 | Phase B | oracle | 0.65 | 21.6 | 16.4 | 75.9 | 78.6 |
| ood | correct policies | v1 | Rules | never | 0.00 | 100.0 | 0.0 | 54.5 | 54.5 |
| ood | correct policies | v1 | Rules | always | 4.50 | 31.4 | 45.9 | 54.5 | 58.9 |
| ood | correct policies | v1 | Base | never | 0.00 | 13.7 | 63.9 | 48.2 | 56.2 |
| ood | correct policies | v1 | Base | always | 4.50 | 19.6 | 44.3 | 55.4 | 64.3 |
| ood | correct policies | v1 | Base | selective | 0.25 | 5.9 | 52.5 | 58.0 | 67.0 |
| ood | correct policies | v1 | Base | oracle | 0.65 | 3.9 | 37.7 | 63.4 | 72.3 |
| ood | correct policies | v1 | Phase B | never | 0.00 | 23.5 | 31.1 | 67.9 | 68.8 |
| ood | correct policies | v1 | Phase B | always | 4.50 | 19.6 | 27.9 | 66.1 | 73.2 |
| ood | correct policies | v1 | Phase B | selective | 0.71 | 15.7 | 16.4 | 78.6 | 82.1 |
| ood | correct policies | v1 | Phase B | oracle | 0.65 | 3.9 | 9.8 | 87.5 | 91.1 |

## 2. Phase B accuracy by case type

Records per case type in brackets. T1 hidden fact, T2 tool result to trust or not, T3 clearly safe, T4 clearly unsafe, T5 policy conflict or two facts that disagree.

| Split | Policies | System | Setting | T1 | T2 | T3 | T4 | T5 | All |
|---|---|---|---|---|---|---|---|---|---|
| val | retrieved policies | v1 | never | 35.7 (14) | 100.0 (16) | 100.0 (2) | 66.7 (6) | 0.0 (2) | 67.5 |
| val | retrieved policies | v1 | always | 57.1 (14) | 93.8 (16) | 100.0 (2) | 50.0 (6) | 0.0 (2) | 70.0 |
| val | retrieved policies | v1 | selective | 57.1 (14) | 81.2 (16) | 100.0 (2) | 66.7 (6) | 0.0 (2) | 67.5 |
| val | retrieved policies | v1 | oracle | 85.7 (14) | 100.0 (16) | 100.0 (2) | 66.7 (6) | 100.0 (2) | 90.0 |
| val | correct policies | v1 | never | 42.9 (14) | 100.0 (16) | 100.0 (2) | 100.0 (6) | 0.0 (2) | 75.0 |
| val | correct policies | v1 | always | 71.4 (14) | 100.0 (16) | 100.0 (2) | 83.3 (6) | 0.0 (2) | 82.5 |
| val | correct policies | v1 | selective | 64.3 (14) | 93.8 (16) | 100.0 (2) | 83.3 (6) | 100.0 (2) | 82.5 |
| val | correct policies | v1 | oracle | 92.9 (14) | 100.0 (16) | 100.0 (2) | 100.0 (6) | 100.0 (2) | 97.5 |
| test | retrieved policies | v1 | never | 52.9 (34) | 88.5 (52) | 100.0 (8) | 100.0 (10) | 7.1 (42) | 58.2 |
| test | retrieved policies | v1 | always | 64.7 (34) | 96.2 (52) | 100.0 (8) | 80.0 (10) | 19.0 (42) | 65.8 |
| test | retrieved policies | v1 | selective | 55.9 (34) | 94.2 (52) | 100.0 (8) | 100.0 (10) | 9.5 (42) | 61.6 |
| test | retrieved policies | v1 | oracle | 76.5 (34) | 98.1 (52) | 100.0 (8) | 100.0 (10) | 38.1 (42) | 76.0 |
| test | correct policies | v1 | never | 47.1 (34) | 96.2 (52) | 100.0 (8) | 100.0 (10) | 11.9 (42) | 61.0 |
| test | correct policies | v1 | always | 79.4 (34) | 98.1 (52) | 100.0 (8) | 80.0 (10) | 38.1 (42) | 75.3 |
| test | correct policies | v1 | selective | 70.6 (34) | 98.1 (52) | 100.0 (8) | 100.0 (10) | 19.0 (42) | 69.2 |
| test | correct policies | v1 | oracle | 82.4 (34) | 100.0 (52) | 100.0 (8) | 100.0 (10) | 66.7 (42) | 86.3 |
| ood | retrieved policies | v1 | never | 38.9 (36) | 72.7 (44) | 90.0 (10) | 90.0 (10) | 33.3 (12) | 60.7 |
| ood | retrieved policies | v1 | always | 63.9 (36) | 65.9 (44) | 100.0 (10) | 10.0 (10) | 33.3 (12) | 59.8 |
| ood | retrieved policies | v1 | selective | 52.8 (36) | 84.1 (44) | 90.0 (10) | 40.0 (10) | 50.0 (12) | 67.0 |
| ood | retrieved policies | v1 | oracle | 72.2 (36) | 86.4 (44) | 90.0 (10) | 80.0 (10) | 33.3 (12) | 75.9 |
| ood | correct policies | v1 | never | 41.7 (36) | 79.5 (44) | 100.0 (10) | 90.0 (10) | 58.3 (12) | 67.9 |
| ood | correct policies | v1 | always | 75.0 (36) | 61.4 (44) | 100.0 (10) | 40.0 (10) | 50.0 (12) | 66.1 |
| ood | correct policies | v1 | selective | 63.9 (36) | 90.9 (44) | 100.0 (10) | 80.0 (10) | 58.3 (12) | 78.6 |
| ood | correct policies | v1 | oracle | 86.1 (36) | 93.2 (44) | 100.0 (10) | 90.0 (10) | 58.3 (12) | 87.5 |

## 3. Test reweighted to the in-domain case-type mix

The 6 Nov addition put 13 of 21 new two-check T5 seeds in test, so test has more T5 than the data overall. Reweighting gives each case type its share of all 482 in-domain records (unsafe: its share of the risky records). The raw test number stays the main result; this shows how much the mix moves it.

| Case type | Share of test (%) | Share of all in-domain (%) |
|---|---|---|
| T1 | 24 | 33 |
| T2 | 35 | 34 |
| T3 | 7 | 6 |
| T4 | 7 | 8 |
| T5 | 28 | 19 |

| Policies | System | Setting | Test accuracy | Reweighted | Test unsafe | Reweighted |
|---|---|---|---|---|---|---|
| retrieved policies | v1 | never | 58.2 | 62.9 | 29.3 | 28.1 |
| retrieved policies | v1 | always | 65.8 | 70.1 | 34.1 | 30.6 |
| retrieved policies | v1 | selective | 61.6 | 66.3 | 52.4 | 47.6 |
| retrieved policies | v1 | oracle | 76.0 | 79.8 | 20.7 | 17.7 |
| correct policies | v1 | never | 61.0 | 64.5 | 29.3 | 28.1 |
| correct policies | v1 | always | 75.3 | 79.2 | 12.2 | 10.6 |
| correct policies | v1 | selective | 69.2 | 74.3 | 41.5 | 34.4 |
| correct policies | v1 | oracle | 86.3 | 87.9 | 3.7 | 3.6 |

## 4. What the hypothesis test could detect

R10.4 passes when the upper end of the 95% interval of Δ unsafe (selective − always) is at most +5 points. With an interval this wide, it can only pass if the observed Δ is at most about (5 − half-width) points, i.e. if selective is clearly **safer** than always. The rule stays as fixed before the results; this column says what it could show.

| Split | Policies | System | Risky records | Δ unsafe [95% CI] | Half-width | Observed Δ needed to pass | Result |
|---|---|---|---|---|---|---|---|
| val | retrieved policies | v1 | 19 | +10.5 [-18.2, +41.2] | 29.7 | -24.7 | fails |
| val | correct policies | v1 | 19 | +0.0 [-21.1, +21.1] | 21.1 | -16.1 | fails |
| test | retrieved policies | v1 | 82 | +18.3 [+8.2, +28.9] | 10.3 | -5.3 | fails |
| test | correct policies | v1 | 82 | +29.3 [+16.7, +42.2] | 12.8 | -7.8 | fails |
| ood | retrieved policies | v1 | 51 | +0.0 [-13.2, +13.2] | 13.2 | -8.2 | fails |
| ood | correct policies | v1 | 51 | -3.9 [-17.0, +8.9] | 12.9 | -7.9 | fails |

