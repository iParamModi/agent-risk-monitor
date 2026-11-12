# Report extras: cost-safety curve, case types, test mix, test power, T2 subtypes, T1 pairs, savings

Systems: v1, v2 (decisions.md 2026-11-11). Phase B = the final adapter. Built by `scripts/report_extras.py` from the finished runs; nothing is tuned here.

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
| val | retrieved policies | v2 | Rules | never | 0.00 | 89.5 | 0.0 | 57.5 | 57.5 |
| val | retrieved policies | v2 | Rules | always | 5.00 | 26.3 | 23.8 | 67.5 | 75.0 |
| val | retrieved policies | v2 | Base | never | 0.00 | 21.1 | 47.6 | 55.0 | 57.5 |
| val | retrieved policies | v2 | Base | always | 5.00 | 26.3 | 4.8 | 80.0 | 82.5 |
| val | retrieved policies | v2 | Base | selective | 0.62 | 26.3 | 28.6 | 65.0 | 65.0 |
| val | retrieved policies | v2 | Base | oracle | 0.75 | 21.1 | 14.3 | 67.5 | 70.0 |
| val | retrieved policies | v2 | Phase B | never | 0.00 | 36.8 | 9.5 | 72.5 | 77.5 |
| val | retrieved policies | v2 | Phase B | always | 5.00 | 36.8 | 0.0 | 70.0 | 82.5 |
| val | retrieved policies | v2 | Phase B | selective | 0.85 | 42.1 | 4.8 | 77.5 | 77.5 |
| val | retrieved policies | v2 | Phase B | oracle | 0.75 | 21.1 | 0.0 | 90.0 | 90.0 |
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
| val | correct policies | v2 | Rules | never | 0.00 | 89.5 | 0.0 | 57.5 | 57.5 |
| val | correct policies | v2 | Rules | always | 5.00 | 21.1 | 33.3 | 65.0 | 72.5 |
| val | correct policies | v2 | Base | never | 0.00 | 31.6 | 28.6 | 57.5 | 60.0 |
| val | correct policies | v2 | Base | always | 5.00 | 26.3 | 0.0 | 75.0 | 80.0 |
| val | correct policies | v2 | Base | selective | 0.33 | 42.1 | 19.0 | 65.0 | 65.0 |
| val | correct policies | v2 | Base | oracle | 0.75 | 21.1 | 9.5 | 80.0 | 82.5 |
| val | correct policies | v2 | Phase B | never | 0.00 | 47.4 | 4.8 | 75.0 | 75.0 |
| val | correct policies | v2 | Phase B | always | 5.00 | 26.3 | 0.0 | 82.5 | 87.5 |
| val | correct policies | v2 | Phase B | selective | 0.72 | 26.3 | 4.8 | 85.0 | 85.0 |
| val | correct policies | v2 | Phase B | oracle | 0.75 | 5.3 | 0.0 | 97.5 | 97.5 |
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
| test | retrieved policies | v2 | Rules | never | 0.00 | 93.9 | 0.0 | 44.5 | 47.3 |
| test | retrieved policies | v2 | Rules | always | 4.82 | 28.0 | 53.1 | 46.6 | 58.9 |
| test | retrieved policies | v2 | Base | never | 0.00 | 15.9 | 54.7 | 36.3 | 60.3 |
| test | retrieved policies | v2 | Base | always | 4.82 | 24.4 | 18.8 | 54.8 | 75.3 |
| test | retrieved policies | v2 | Base | selective | 0.61 | 26.8 | 40.6 | 44.5 | 64.4 |
| test | retrieved policies | v2 | Base | oracle | 0.97 | 8.5 | 32.8 | 50.0 | 76.0 |
| test | retrieved policies | v2 | Phase B | never | 0.00 | 30.5 | 7.8 | 58.2 | 76.0 |
| test | retrieved policies | v2 | Phase B | always | 4.82 | 24.4 | 4.7 | 62.3 | 82.2 |
| test | retrieved policies | v2 | Phase B | selective | 0.80 | 39.0 | 6.2 | 63.0 | 74.0 |
| test | retrieved policies | v2 | Phase B | oracle | 0.97 | 15.9 | 1.6 | 80.8 | 87.7 |
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
| test | correct policies | v2 | Rules | never | 0.00 | 95.1 | 1.6 | 43.8 | 45.9 |
| test | correct policies | v2 | Rules | always | 4.82 | 28.0 | 40.6 | 52.1 | 64.4 |
| test | correct policies | v2 | Base | never | 0.00 | 23.2 | 59.4 | 34.2 | 54.8 |
| test | correct policies | v2 | Base | always | 4.82 | 12.2 | 29.7 | 52.1 | 76.7 |
| test | correct policies | v2 | Base | selective | 0.58 | 26.8 | 43.8 | 43.2 | 61.0 |
| test | correct policies | v2 | Base | oracle | 0.97 | 6.1 | 31.2 | 51.4 | 77.4 |
| test | correct policies | v2 | Phase B | never | 0.00 | 29.3 | 14.1 | 61.0 | 75.3 |
| test | correct policies | v2 | Phase B | always | 4.82 | 12.2 | 4.7 | 75.3 | 89.0 |
| test | correct policies | v2 | Phase B | selective | 0.74 | 39.0 | 3.1 | 69.9 | 74.7 |
| test | correct policies | v2 | Phase B | oracle | 0.97 | 3.7 | 1.6 | 86.3 | 94.5 |
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
| ood | retrieved policies | v2 | Rules | never | 0.00 | 100.0 | 1.6 | 53.6 | 53.6 |
| ood | retrieved policies | v2 | Rules | always | 4.50 | 27.5 | 55.7 | 48.2 | 54.5 |
| ood | retrieved policies | v2 | Base | never | 0.00 | 11.8 | 60.7 | 48.2 | 57.1 |
| ood | retrieved policies | v2 | Base | always | 4.50 | 23.5 | 41.0 | 58.9 | 65.2 |
| ood | retrieved policies | v2 | Base | selective | 0.44 | 11.8 | 59.0 | 50.0 | 59.8 |
| ood | retrieved policies | v2 | Base | oracle | 0.65 | 3.9 | 36.1 | 65.2 | 75.0 |
| ood | retrieved policies | v2 | Phase B | never | 0.00 | 19.6 | 32.8 | 68.8 | 71.4 |
| ood | retrieved policies | v2 | Phase B | always | 4.50 | 29.4 | 23.0 | 63.4 | 72.3 |
| ood | retrieved policies | v2 | Phase B | selective | 0.68 | 35.3 | 18.0 | 66.1 | 72.3 |
| ood | retrieved policies | v2 | Phase B | oracle | 0.65 | 5.9 | 13.1 | 82.1 | 87.5 |
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
| ood | correct policies | v2 | Rules | never | 0.00 | 100.0 | 0.0 | 54.5 | 54.5 |
| ood | correct policies | v2 | Rules | always | 4.50 | 31.4 | 45.9 | 54.5 | 58.9 |
| ood | correct policies | v2 | Base | never | 0.00 | 13.7 | 63.9 | 48.2 | 56.2 |
| ood | correct policies | v2 | Base | always | 4.50 | 19.6 | 44.3 | 55.4 | 64.3 |
| ood | correct policies | v2 | Base | selective | 0.25 | 9.8 | 52.5 | 57.1 | 66.1 |
| ood | correct policies | v2 | Base | oracle | 0.65 | 3.9 | 37.7 | 63.4 | 72.3 |
| ood | correct policies | v2 | Phase B | never | 0.00 | 23.5 | 31.1 | 67.9 | 68.8 |
| ood | correct policies | v2 | Phase B | always | 4.50 | 19.6 | 27.9 | 66.1 | 73.2 |
| ood | correct policies | v2 | Phase B | selective | 0.68 | 15.7 | 14.8 | 80.4 | 83.0 |
| ood | correct policies | v2 | Phase B | oracle | 0.65 | 3.9 | 9.8 | 87.5 | 91.1 |

## 2. Phase B accuracy by case type

Records per case type in brackets. T1 hidden fact, T2 tool result to trust or not, T3 clearly safe, T4 clearly unsafe, T5 policy conflict or two facts that disagree.

| Split | Policies | System | Setting | T1 | T2 | T3 | T4 | T5 | All |
|---|---|---|---|---|---|---|---|---|---|
| val | retrieved policies | v1 | never | 35.7 (14) | 100.0 (16) | 100.0 (2) | 66.7 (6) | 0.0 (2) | 67.5 |
| val | retrieved policies | v1 | always | 57.1 (14) | 93.8 (16) | 100.0 (2) | 50.0 (6) | 0.0 (2) | 70.0 |
| val | retrieved policies | v1 | selective | 57.1 (14) | 81.2 (16) | 100.0 (2) | 66.7 (6) | 0.0 (2) | 67.5 |
| val | retrieved policies | v1 | oracle | 85.7 (14) | 100.0 (16) | 100.0 (2) | 66.7 (6) | 100.0 (2) | 90.0 |
| val | retrieved policies | v2 | never | 50.0 (14) | 100.0 (16) | 100.0 (2) | 66.7 (6) | 0.0 (2) | 72.5 |
| val | retrieved policies | v2 | always | 64.3 (14) | 93.8 (16) | 100.0 (2) | 33.3 (6) | 0.0 (2) | 70.0 |
| val | retrieved policies | v2 | selective | 64.3 (14) | 93.8 (16) | 100.0 (2) | 50.0 (6) | 100.0 (2) | 77.5 |
| val | retrieved policies | v2 | oracle | 85.7 (14) | 100.0 (16) | 100.0 (2) | 66.7 (6) | 100.0 (2) | 90.0 |
| val | correct policies | v1 | never | 42.9 (14) | 100.0 (16) | 100.0 (2) | 100.0 (6) | 0.0 (2) | 75.0 |
| val | correct policies | v1 | always | 71.4 (14) | 100.0 (16) | 100.0 (2) | 83.3 (6) | 0.0 (2) | 82.5 |
| val | correct policies | v1 | selective | 64.3 (14) | 93.8 (16) | 100.0 (2) | 83.3 (6) | 100.0 (2) | 82.5 |
| val | correct policies | v1 | oracle | 92.9 (14) | 100.0 (16) | 100.0 (2) | 100.0 (6) | 100.0 (2) | 97.5 |
| val | correct policies | v2 | never | 42.9 (14) | 100.0 (16) | 100.0 (2) | 100.0 (6) | 0.0 (2) | 75.0 |
| val | correct policies | v2 | always | 71.4 (14) | 100.0 (16) | 100.0 (2) | 83.3 (6) | 0.0 (2) | 82.5 |
| val | correct policies | v2 | selective | 71.4 (14) | 93.8 (16) | 100.0 (2) | 83.3 (6) | 100.0 (2) | 85.0 |
| val | correct policies | v2 | oracle | 92.9 (14) | 100.0 (16) | 100.0 (2) | 100.0 (6) | 100.0 (2) | 97.5 |
| test | retrieved policies | v1 | never | 52.9 (34) | 88.5 (52) | 100.0 (8) | 100.0 (10) | 7.1 (42) | 58.2 |
| test | retrieved policies | v1 | always | 64.7 (34) | 96.2 (52) | 100.0 (8) | 80.0 (10) | 19.0 (42) | 65.8 |
| test | retrieved policies | v1 | selective | 55.9 (34) | 94.2 (52) | 100.0 (8) | 100.0 (10) | 9.5 (42) | 61.6 |
| test | retrieved policies | v1 | oracle | 76.5 (34) | 98.1 (52) | 100.0 (8) | 100.0 (10) | 38.1 (42) | 76.0 |
| test | retrieved policies | v2 | never | 38.2 (34) | 98.1 (52) | 100.0 (8) | 100.0 (10) | 7.1 (42) | 58.2 |
| test | retrieved policies | v2 | always | 61.8 (34) | 88.5 (52) | 87.5 (8) | 50.0 (10) | 28.6 (42) | 62.3 |
| test | retrieved policies | v2 | selective | 61.8 (34) | 98.1 (52) | 100.0 (8) | 90.0 (10) | 7.1 (42) | 63.0 |
| test | retrieved policies | v2 | oracle | 73.5 (34) | 100.0 (52) | 100.0 (8) | 100.0 (10) | 54.8 (42) | 80.8 |
| test | correct policies | v1 | never | 47.1 (34) | 96.2 (52) | 100.0 (8) | 100.0 (10) | 11.9 (42) | 61.0 |
| test | correct policies | v1 | always | 79.4 (34) | 98.1 (52) | 100.0 (8) | 80.0 (10) | 38.1 (42) | 75.3 |
| test | correct policies | v1 | selective | 70.6 (34) | 98.1 (52) | 100.0 (8) | 100.0 (10) | 19.0 (42) | 69.2 |
| test | correct policies | v1 | oracle | 82.4 (34) | 100.0 (52) | 100.0 (8) | 100.0 (10) | 66.7 (42) | 86.3 |
| test | correct policies | v2 | never | 47.1 (34) | 96.2 (52) | 100.0 (8) | 100.0 (10) | 11.9 (42) | 61.0 |
| test | correct policies | v2 | always | 79.4 (34) | 98.1 (52) | 100.0 (8) | 80.0 (10) | 38.1 (42) | 75.3 |
| test | correct policies | v2 | selective | 73.5 (34) | 100.0 (52) | 100.0 (8) | 90.0 (10) | 19.0 (42) | 69.9 |
| test | correct policies | v2 | oracle | 82.4 (34) | 100.0 (52) | 100.0 (8) | 100.0 (10) | 66.7 (42) | 86.3 |
| ood | retrieved policies | v1 | never | 38.9 (36) | 72.7 (44) | 90.0 (10) | 90.0 (10) | 33.3 (12) | 60.7 |
| ood | retrieved policies | v1 | always | 63.9 (36) | 65.9 (44) | 100.0 (10) | 10.0 (10) | 33.3 (12) | 59.8 |
| ood | retrieved policies | v1 | selective | 52.8 (36) | 84.1 (44) | 90.0 (10) | 40.0 (10) | 50.0 (12) | 67.0 |
| ood | retrieved policies | v1 | oracle | 72.2 (36) | 86.4 (44) | 90.0 (10) | 80.0 (10) | 33.3 (12) | 75.9 |
| ood | retrieved policies | v2 | never | 50.0 (36) | 72.7 (44) | 100.0 (10) | 100.0 (10) | 58.3 (12) | 68.8 |
| ood | retrieved policies | v2 | always | 63.9 (36) | 68.2 (44) | 100.0 (10) | 50.0 (10) | 25.0 (12) | 63.4 |
| ood | retrieved policies | v2 | selective | 47.2 (36) | 84.1 (44) | 100.0 (10) | 50.0 (10) | 41.7 (12) | 66.1 |
| ood | retrieved policies | v2 | oracle | 83.3 (36) | 86.4 (44) | 100.0 (10) | 80.0 (10) | 50.0 (12) | 82.1 |
| ood | correct policies | v1 | never | 41.7 (36) | 79.5 (44) | 100.0 (10) | 90.0 (10) | 58.3 (12) | 67.9 |
| ood | correct policies | v1 | always | 75.0 (36) | 61.4 (44) | 100.0 (10) | 40.0 (10) | 50.0 (12) | 66.1 |
| ood | correct policies | v1 | selective | 63.9 (36) | 90.9 (44) | 100.0 (10) | 80.0 (10) | 58.3 (12) | 78.6 |
| ood | correct policies | v1 | oracle | 86.1 (36) | 93.2 (44) | 100.0 (10) | 90.0 (10) | 58.3 (12) | 87.5 |
| ood | correct policies | v2 | never | 41.7 (36) | 79.5 (44) | 100.0 (10) | 90.0 (10) | 58.3 (12) | 67.9 |
| ood | correct policies | v2 | always | 75.0 (36) | 61.4 (44) | 100.0 (10) | 40.0 (10) | 50.0 (12) | 66.1 |
| ood | correct policies | v2 | selective | 66.7 (36) | 90.9 (44) | 100.0 (10) | 80.0 (10) | 66.7 (12) | 80.4 |
| ood | correct policies | v2 | oracle | 86.1 (36) | 93.2 (44) | 100.0 (10) | 90.0 (10) | 58.3 (12) | 87.5 |

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
| retrieved policies | v2 | never | 58.2 | 61.4 | 30.5 | 32.9 |
| retrieved policies | v2 | always | 62.3 | 65.2 | 24.4 | 25.7 |
| retrieved policies | v2 | selective | 63.0 | 68.3 | 39.0 | 35.7 |
| retrieved policies | v2 | oracle | 80.8 | 82.7 | 15.9 | 15.2 |
| correct policies | v1 | never | 61.0 | 64.5 | 29.3 | 28.1 |
| correct policies | v1 | always | 75.3 | 79.2 | 12.2 | 10.6 |
| correct policies | v1 | selective | 69.2 | 74.3 | 41.5 | 34.4 |
| correct policies | v1 | oracle | 86.3 | 87.9 | 3.7 | 3.6 |
| correct policies | v2 | never | 61.0 | 64.5 | 29.3 | 28.1 |
| correct policies | v2 | always | 75.3 | 79.2 | 12.2 | 10.6 |
| correct policies | v2 | selective | 69.9 | 75.1 | 39.0 | 31.7 |
| correct policies | v2 | oracle | 86.3 | 87.9 | 3.7 | 3.6 |

## 4. What the hypothesis test could detect

R10.4 passes when the upper end of the 95% interval of Δ unsafe (selective − always) is at most +5 points. With an interval this wide, it can only pass if the observed Δ is at most about (5 − half-width) points, i.e. if selective is clearly **safer** than always. The rule stays as fixed before the results; this column says what it could show.

| Split | Policies | System | Risky records | Δ unsafe [95% CI] | Half-width | Observed Δ needed to pass | Result |
|---|---|---|---|---|---|---|---|
| val | retrieved policies | v1 | 19 | +10.5 [-18.2, +41.2] | 29.7 | -24.7 | fails |
| val | retrieved policies | v2 | 19 | +5.3 [-23.5, +31.2] | 27.4 | -22.4 | fails |
| val | correct policies | v1 | 19 | +0.0 [-21.1, +21.1] | 21.1 | -16.1 | fails |
| val | correct policies | v2 | 19 | +0.0 [-21.1, +21.1] | 21.1 | -16.1 | fails |
| test | retrieved policies | v1 | 82 | +18.3 [+8.2, +28.9] | 10.3 | -5.3 | fails |
| test | retrieved policies | v2 | 82 | +14.6 [+0.0, +29.7] | 14.8 | -9.8 | fails |
| test | correct policies | v1 | 82 | +29.3 [+16.7, +42.2] | 12.8 | -7.8 | fails |
| test | correct policies | v2 | 82 | +26.8 [+14.3, +39.5] | 12.6 | -7.6 | fails |
| ood | retrieved policies | v1 | 51 | +0.0 [-13.2, +13.2] | 13.2 | -8.2 | fails |
| ood | retrieved policies | v2 | 51 | +5.9 [-10.9, +23.3] | 17.1 | -12.1 | fails |
| ood | correct policies | v1 | 51 | -3.9 [-17.0, +8.9] | 12.9 | -7.9 | fails |
| ood | correct policies | v2 | 51 | -3.9 [-16.4, +9.1] | 12.7 | -7.7 | fails |

## 5. T2 subtypes (tool results to trust or not)

Accuracy on T2 records by subtype, records in brackets: a = fresh result (trust it); b = result about another resource; c = fact changed since the result; d = only the agent says it. src.eval.metrics.t2_accuracy.

| Split | Policies | System | Model | Setting | T2a | T2b | T2c | T2d |
|---|---|---|---|---|---|---|---|---|
| val | retrieved policies | v1 | Base | never | 75.0 (4) | 25.0 (4) | 50.0 (4) | 75.0 (4) |
| val | retrieved policies | v1 | Base | always | 75.0 (4) | 100.0 (4) | 50.0 (4) | 100.0 (4) |
| val | retrieved policies | v1 | Base | selective | 75.0 (4) | 25.0 (4) | 50.0 (4) | 75.0 (4) |
| val | retrieved policies | v1 | Base | oracle | 75.0 (4) | 75.0 (4) | 100.0 (4) | 75.0 (4) |
| val | retrieved policies | v1 | Phase B | never | 100.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| val | retrieved policies | v1 | Phase B | always | 100.0 (4) | 100.0 (4) | 75.0 (4) | 100.0 (4) |
| val | retrieved policies | v1 | Phase B | selective | 100.0 (4) | 100.0 (4) | 50.0 (4) | 75.0 (4) |
| val | retrieved policies | v1 | Phase B | oracle | 100.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| val | retrieved policies | v2 | Base | never | 50.0 (4) | 25.0 (4) | 100.0 (4) | 50.0 (4) |
| val | retrieved policies | v2 | Base | always | 75.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| val | retrieved policies | v2 | Base | selective | 50.0 (4) | 25.0 (4) | 100.0 (4) | 75.0 (4) |
| val | retrieved policies | v2 | Base | oracle | 50.0 (4) | 50.0 (4) | 100.0 (4) | 75.0 (4) |
| val | retrieved policies | v2 | Phase B | never | 100.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| val | retrieved policies | v2 | Phase B | always | 100.0 (4) | 100.0 (4) | 75.0 (4) | 100.0 (4) |
| val | retrieved policies | v2 | Phase B | selective | 100.0 (4) | 75.0 (4) | 100.0 (4) | 100.0 (4) |
| val | retrieved policies | v2 | Phase B | oracle | 100.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| val | correct policies | v1 | Base | never | 50.0 (4) | 25.0 (4) | 75.0 (4) | 75.0 (4) |
| val | correct policies | v1 | Base | always | 75.0 (4) | 75.0 (4) | 100.0 (4) | 100.0 (4) |
| val | correct policies | v1 | Base | selective | 75.0 (4) | 50.0 (4) | 50.0 (4) | 75.0 (4) |
| val | correct policies | v1 | Base | oracle | 75.0 (4) | 75.0 (4) | 100.0 (4) | 100.0 (4) |
| val | correct policies | v1 | Phase B | never | 100.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| val | correct policies | v1 | Phase B | always | 100.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| val | correct policies | v1 | Phase B | selective | 100.0 (4) | 100.0 (4) | 100.0 (4) | 75.0 (4) |
| val | correct policies | v1 | Phase B | oracle | 100.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| val | correct policies | v2 | Base | never | 50.0 (4) | 25.0 (4) | 75.0 (4) | 75.0 (4) |
| val | correct policies | v2 | Base | always | 75.0 (4) | 75.0 (4) | 100.0 (4) | 100.0 (4) |
| val | correct policies | v2 | Base | selective | 75.0 (4) | 50.0 (4) | 50.0 (4) | 75.0 (4) |
| val | correct policies | v2 | Base | oracle | 75.0 (4) | 75.0 (4) | 100.0 (4) | 100.0 (4) |
| val | correct policies | v2 | Phase B | never | 100.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| val | correct policies | v2 | Phase B | always | 100.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| val | correct policies | v2 | Phase B | selective | 100.0 (4) | 100.0 (4) | 100.0 (4) | 75.0 (4) |
| val | correct policies | v2 | Phase B | oracle | 100.0 (4) | 100.0 (4) | 100.0 (4) | 100.0 (4) |
| test | retrieved policies | v1 | Base | never | 30.8 (13) | 23.1 (13) | 84.6 (13) | 15.4 (13) |
| test | retrieved policies | v1 | Base | always | 53.8 (13) | 76.9 (13) | 92.3 (13) | 53.8 (13) |
| test | retrieved policies | v1 | Base | selective | 30.8 (13) | 53.8 (13) | 76.9 (13) | 30.8 (13) |
| test | retrieved policies | v1 | Base | oracle | 30.8 (13) | 69.2 (13) | 100.0 (13) | 46.2 (13) |
| test | retrieved policies | v1 | Phase B | never | 92.3 (13) | 76.9 (13) | 92.3 (13) | 92.3 (13) |
| test | retrieved policies | v1 | Phase B | always | 100.0 (13) | 100.0 (13) | 84.6 (13) | 100.0 (13) |
| test | retrieved policies | v1 | Phase B | selective | 92.3 (13) | 100.0 (13) | 92.3 (13) | 92.3 (13) |
| test | retrieved policies | v1 | Phase B | oracle | 92.3 (13) | 100.0 (13) | 100.0 (13) | 100.0 (13) |
| test | retrieved policies | v2 | Base | never | 46.2 (13) | 30.8 (13) | 84.6 (13) | 0.0 (13) |
| test | retrieved policies | v2 | Base | always | 84.6 (13) | 76.9 (13) | 84.6 (13) | 76.9 (13) |
| test | retrieved policies | v2 | Base | selective | 46.2 (13) | 61.5 (13) | 84.6 (13) | 38.5 (13) |
| test | retrieved policies | v2 | Base | oracle | 46.2 (13) | 61.5 (13) | 100.0 (13) | 38.5 (13) |
| test | retrieved policies | v2 | Phase B | never | 100.0 (13) | 100.0 (13) | 92.3 (13) | 100.0 (13) |
| test | retrieved policies | v2 | Phase B | always | 100.0 (13) | 100.0 (13) | 53.8 (13) | 100.0 (13) |
| test | retrieved policies | v2 | Phase B | selective | 100.0 (13) | 100.0 (13) | 92.3 (13) | 100.0 (13) |
| test | retrieved policies | v2 | Phase B | oracle | 100.0 (13) | 100.0 (13) | 100.0 (13) | 100.0 (13) |
| test | correct policies | v1 | Base | never | 23.1 (13) | 23.1 (13) | 84.6 (13) | 15.4 (13) |
| test | correct policies | v1 | Base | always | 38.5 (13) | 69.2 (13) | 100.0 (13) | 53.8 (13) |
| test | correct policies | v1 | Base | selective | 30.8 (13) | 61.5 (13) | 84.6 (13) | 46.2 (13) |
| test | correct policies | v1 | Base | oracle | 23.1 (13) | 69.2 (13) | 100.0 (13) | 53.8 (13) |
| test | correct policies | v1 | Phase B | never | 100.0 (13) | 92.3 (13) | 92.3 (13) | 100.0 (13) |
| test | correct policies | v1 | Phase B | always | 100.0 (13) | 100.0 (13) | 100.0 (13) | 92.3 (13) |
| test | correct policies | v1 | Phase B | selective | 92.3 (13) | 100.0 (13) | 100.0 (13) | 100.0 (13) |
| test | correct policies | v1 | Phase B | oracle | 100.0 (13) | 100.0 (13) | 100.0 (13) | 100.0 (13) |
| test | correct policies | v2 | Base | never | 23.1 (13) | 23.1 (13) | 84.6 (13) | 15.4 (13) |
| test | correct policies | v2 | Base | always | 38.5 (13) | 69.2 (13) | 100.0 (13) | 53.8 (13) |
| test | correct policies | v2 | Base | selective | 15.4 (13) | 61.5 (13) | 84.6 (13) | 38.5 (13) |
| test | correct policies | v2 | Base | oracle | 23.1 (13) | 69.2 (13) | 100.0 (13) | 53.8 (13) |
| test | correct policies | v2 | Phase B | never | 100.0 (13) | 92.3 (13) | 92.3 (13) | 100.0 (13) |
| test | correct policies | v2 | Phase B | always | 100.0 (13) | 100.0 (13) | 100.0 (13) | 92.3 (13) |
| test | correct policies | v2 | Phase B | selective | 100.0 (13) | 100.0 (13) | 100.0 (13) | 100.0 (13) |
| test | correct policies | v2 | Phase B | oracle | 100.0 (13) | 100.0 (13) | 100.0 (13) | 100.0 (13) |
| ood | retrieved policies | v1 | Base | never | 36.4 (11) | 27.3 (11) | 90.9 (11) | 9.1 (11) |
| ood | retrieved policies | v1 | Base | always | 36.4 (11) | 36.4 (11) | 72.7 (11) | 36.4 (11) |
| ood | retrieved policies | v1 | Base | selective | 36.4 (11) | 27.3 (11) | 90.9 (11) | 27.3 (11) |
| ood | retrieved policies | v1 | Base | oracle | 36.4 (11) | 45.5 (11) | 90.9 (11) | 45.5 (11) |
| ood | retrieved policies | v1 | Phase B | never | 72.7 (11) | 63.6 (11) | 100.0 (11) | 54.5 (11) |
| ood | retrieved policies | v1 | Phase B | always | 63.6 (11) | 72.7 (11) | 72.7 (11) | 54.5 (11) |
| ood | retrieved policies | v1 | Phase B | selective | 81.8 (11) | 81.8 (11) | 100.0 (11) | 72.7 (11) |
| ood | retrieved policies | v1 | Phase B | oracle | 72.7 (11) | 81.8 (11) | 100.0 (11) | 90.9 (11) |
| ood | retrieved policies | v2 | Base | never | 45.5 (11) | 27.3 (11) | 90.9 (11) | 27.3 (11) |
| ood | retrieved policies | v2 | Base | always | 45.5 (11) | 54.5 (11) | 81.8 (11) | 36.4 (11) |
| ood | retrieved policies | v2 | Base | selective | 36.4 (11) | 27.3 (11) | 100.0 (11) | 36.4 (11) |
| ood | retrieved policies | v2 | Base | oracle | 45.5 (11) | 54.5 (11) | 90.9 (11) | 54.5 (11) |
| ood | retrieved policies | v2 | Phase B | never | 63.6 (11) | 72.7 (11) | 81.8 (11) | 72.7 (11) |
| ood | retrieved policies | v2 | Phase B | always | 63.6 (11) | 81.8 (11) | 72.7 (11) | 54.5 (11) |
| ood | retrieved policies | v2 | Phase B | selective | 81.8 (11) | 72.7 (11) | 90.9 (11) | 90.9 (11) |
| ood | retrieved policies | v2 | Phase B | oracle | 81.8 (11) | 72.7 (11) | 90.9 (11) | 100.0 (11) |
| ood | correct policies | v1 | Base | never | 45.5 (11) | 27.3 (11) | 100.0 (11) | 18.2 (11) |
| ood | correct policies | v1 | Base | always | 45.5 (11) | 36.4 (11) | 72.7 (11) | 36.4 (11) |
| ood | correct policies | v1 | Base | selective | 45.5 (11) | 27.3 (11) | 100.0 (11) | 36.4 (11) |
| ood | correct policies | v1 | Base | oracle | 36.4 (11) | 45.5 (11) | 100.0 (11) | 63.6 (11) |
| ood | correct policies | v1 | Phase B | never | 90.9 (11) | 63.6 (11) | 100.0 (11) | 63.6 (11) |
| ood | correct policies | v1 | Phase B | always | 63.6 (11) | 63.6 (11) | 72.7 (11) | 45.5 (11) |
| ood | correct policies | v1 | Phase B | selective | 90.9 (11) | 90.9 (11) | 100.0 (11) | 81.8 (11) |
| ood | correct policies | v1 | Phase B | oracle | 90.9 (11) | 90.9 (11) | 100.0 (11) | 90.9 (11) |
| ood | correct policies | v2 | Base | never | 45.5 (11) | 27.3 (11) | 100.0 (11) | 18.2 (11) |
| ood | correct policies | v2 | Base | always | 45.5 (11) | 36.4 (11) | 72.7 (11) | 36.4 (11) |
| ood | correct policies | v2 | Base | selective | 45.5 (11) | 27.3 (11) | 100.0 (11) | 36.4 (11) |
| ood | correct policies | v2 | Base | oracle | 36.4 (11) | 45.5 (11) | 100.0 (11) | 63.6 (11) |
| ood | correct policies | v2 | Phase B | never | 90.9 (11) | 63.6 (11) | 100.0 (11) | 63.6 (11) |
| ood | correct policies | v2 | Phase B | always | 63.6 (11) | 63.6 (11) | 72.7 (11) | 45.5 (11) |
| ood | correct policies | v2 | Phase B | selective | 90.9 (11) | 90.9 (11) | 100.0 (11) | 81.8 (11) |
| ood | correct policies | v2 | Phase B | oracle | 90.9 (11) | 90.9 (11) | 100.0 (11) | 90.9 (11) |

## 6. T1 pairs: both records of an A/B pair right

A T1 seed has two records that look the same and differ only in the hidden fact (one is safe, one is not). Pair accuracy = both right (src.eval.metrics.pair_accuracy). Without the check the two prompts differ only in the order of the shown policies, so never can get both right only by chance (near 0 by design).

| Split | Policies | System | Model | Setting | T1 accuracy (records) | Pair accuracy (pairs) |
|---|---|---|---|---|---|---|
| val | retrieved policies | v1 | Base | never | 42.9 (14) | 0.0 (0 of 7) |
| val | retrieved policies | v1 | Base | always | 57.1 (14) | 42.9 (3 of 7) |
| val | retrieved policies | v1 | Base | selective | 42.9 (14) | 0.0 (0 of 7) |
| val | retrieved policies | v1 | Base | oracle | 57.1 (14) | 42.9 (3 of 7) |
| val | retrieved policies | v1 | Phase B | never | 35.7 (14) | 0.0 (0 of 7) |
| val | retrieved policies | v1 | Phase B | always | 57.1 (14) | 28.6 (2 of 7) |
| val | retrieved policies | v1 | Phase B | selective | 57.1 (14) | 14.3 (1 of 7) |
| val | retrieved policies | v1 | Phase B | oracle | 85.7 (14) | 71.4 (5 of 7) |
| val | retrieved policies | v2 | Base | never | 50.0 (14) | 0.0 (0 of 7) |
| val | retrieved policies | v2 | Base | always | 78.6 (14) | 57.1 (4 of 7) |
| val | retrieved policies | v2 | Base | selective | 57.1 (14) | 14.3 (1 of 7) |
| val | retrieved policies | v2 | Base | oracle | 78.6 (14) | 57.1 (4 of 7) |
| val | retrieved policies | v2 | Phase B | never | 50.0 (14) | 0.0 (0 of 7) |
| val | retrieved policies | v2 | Phase B | always | 64.3 (14) | 28.6 (2 of 7) |
| val | retrieved policies | v2 | Phase B | selective | 64.3 (14) | 28.6 (2 of 7) |
| val | retrieved policies | v2 | Phase B | oracle | 85.7 (14) | 71.4 (5 of 7) |
| val | correct policies | v1 | Base | never | 42.9 (14) | 14.3 (1 of 7) |
| val | correct policies | v1 | Base | always | 64.3 (14) | 42.9 (3 of 7) |
| val | correct policies | v1 | Base | selective | 71.4 (14) | 42.9 (3 of 7) |
| val | correct policies | v1 | Base | oracle | 71.4 (14) | 57.1 (4 of 7) |
| val | correct policies | v1 | Phase B | never | 42.9 (14) | 0.0 (0 of 7) |
| val | correct policies | v1 | Phase B | always | 71.4 (14) | 42.9 (3 of 7) |
| val | correct policies | v1 | Phase B | selective | 64.3 (14) | 28.6 (2 of 7) |
| val | correct policies | v1 | Phase B | oracle | 92.9 (14) | 85.7 (6 of 7) |
| val | correct policies | v2 | Base | never | 42.9 (14) | 14.3 (1 of 7) |
| val | correct policies | v2 | Base | always | 64.3 (14) | 42.9 (3 of 7) |
| val | correct policies | v2 | Base | selective | 57.1 (14) | 28.6 (2 of 7) |
| val | correct policies | v2 | Base | oracle | 71.4 (14) | 57.1 (4 of 7) |
| val | correct policies | v2 | Phase B | never | 42.9 (14) | 0.0 (0 of 7) |
| val | correct policies | v2 | Phase B | always | 71.4 (14) | 42.9 (3 of 7) |
| val | correct policies | v2 | Phase B | selective | 71.4 (14) | 42.9 (3 of 7) |
| val | correct policies | v2 | Phase B | oracle | 92.9 (14) | 85.7 (6 of 7) |
| test | retrieved policies | v1 | Base | never | 47.1 (34) | 5.9 (1 of 17) |
| test | retrieved policies | v1 | Base | always | 67.6 (34) | 35.3 (6 of 17) |
| test | retrieved policies | v1 | Base | selective | 52.9 (34) | 11.8 (2 of 17) |
| test | retrieved policies | v1 | Base | oracle | 67.6 (34) | 35.3 (6 of 17) |
| test | retrieved policies | v1 | Phase B | never | 52.9 (34) | 11.8 (2 of 17) |
| test | retrieved policies | v1 | Phase B | always | 64.7 (34) | 29.4 (5 of 17) |
| test | retrieved policies | v1 | Phase B | selective | 55.9 (34) | 17.6 (3 of 17) |
| test | retrieved policies | v1 | Phase B | oracle | 76.5 (34) | 58.8 (10 of 17) |
| test | retrieved policies | v2 | Base | never | 44.1 (34) | 17.6 (3 of 17) |
| test | retrieved policies | v2 | Base | always | 61.8 (34) | 35.3 (6 of 17) |
| test | retrieved policies | v2 | Base | selective | 55.9 (34) | 23.5 (4 of 17) |
| test | retrieved policies | v2 | Base | oracle | 70.6 (34) | 52.9 (9 of 17) |
| test | retrieved policies | v2 | Phase B | never | 38.2 (34) | 0.0 (0 of 17) |
| test | retrieved policies | v2 | Phase B | always | 61.8 (34) | 23.5 (4 of 17) |
| test | retrieved policies | v2 | Phase B | selective | 61.8 (34) | 23.5 (4 of 17) |
| test | retrieved policies | v2 | Phase B | oracle | 73.5 (34) | 52.9 (9 of 17) |
| test | correct policies | v1 | Base | never | 41.2 (34) | 0.0 (0 of 17) |
| test | correct policies | v1 | Base | always | 73.5 (34) | 47.1 (8 of 17) |
| test | correct policies | v1 | Base | selective | 58.8 (34) | 29.4 (5 of 17) |
| test | correct policies | v1 | Base | oracle | 76.5 (34) | 52.9 (9 of 17) |
| test | correct policies | v1 | Phase B | never | 47.1 (34) | 5.9 (1 of 17) |
| test | correct policies | v1 | Phase B | always | 79.4 (34) | 58.8 (10 of 17) |
| test | correct policies | v1 | Phase B | selective | 70.6 (34) | 41.2 (7 of 17) |
| test | correct policies | v1 | Phase B | oracle | 82.4 (34) | 70.6 (12 of 17) |
| test | correct policies | v2 | Base | never | 41.2 (34) | 0.0 (0 of 17) |
| test | correct policies | v2 | Base | always | 73.5 (34) | 47.1 (8 of 17) |
| test | correct policies | v2 | Base | selective | 61.8 (34) | 29.4 (5 of 17) |
| test | correct policies | v2 | Base | oracle | 76.5 (34) | 52.9 (9 of 17) |
| test | correct policies | v2 | Phase B | never | 47.1 (34) | 5.9 (1 of 17) |
| test | correct policies | v2 | Phase B | always | 79.4 (34) | 58.8 (10 of 17) |
| test | correct policies | v2 | Phase B | selective | 73.5 (34) | 47.1 (8 of 17) |
| test | correct policies | v2 | Phase B | oracle | 82.4 (34) | 70.6 (12 of 17) |
| ood | retrieved policies | v1 | Base | never | 41.7 (36) | 5.6 (1 of 18) |
| ood | retrieved policies | v1 | Base | always | 61.1 (36) | 22.2 (4 of 18) |
| ood | retrieved policies | v1 | Base | selective | 55.6 (36) | 16.7 (3 of 18) |
| ood | retrieved policies | v1 | Base | oracle | 61.1 (36) | 33.3 (6 of 18) |
| ood | retrieved policies | v1 | Phase B | never | 38.9 (36) | 0.0 (0 of 18) |
| ood | retrieved policies | v1 | Phase B | always | 63.9 (36) | 38.9 (7 of 18) |
| ood | retrieved policies | v1 | Phase B | selective | 52.8 (36) | 16.7 (3 of 18) |
| ood | retrieved policies | v1 | Phase B | oracle | 72.2 (36) | 50.0 (9 of 18) |
| ood | retrieved policies | v2 | Base | never | 41.7 (36) | 0.0 (0 of 18) |
| ood | retrieved policies | v2 | Base | always | 66.7 (36) | 33.3 (6 of 18) |
| ood | retrieved policies | v2 | Base | selective | 47.2 (36) | 22.2 (4 of 18) |
| ood | retrieved policies | v2 | Base | oracle | 75.0 (36) | 50.0 (9 of 18) |
| ood | retrieved policies | v2 | Phase B | never | 50.0 (36) | 11.1 (2 of 18) |
| ood | retrieved policies | v2 | Phase B | always | 63.9 (36) | 33.3 (6 of 18) |
| ood | retrieved policies | v2 | Phase B | selective | 47.2 (36) | 16.7 (3 of 18) |
| ood | retrieved policies | v2 | Phase B | oracle | 83.3 (36) | 66.7 (12 of 18) |
| ood | correct policies | v1 | Base | never | 44.4 (36) | 5.6 (1 of 18) |
| ood | correct policies | v1 | Base | always | 69.4 (36) | 38.9 (7 of 18) |
| ood | correct policies | v1 | Base | selective | 69.4 (36) | 44.4 (8 of 18) |
| ood | correct policies | v1 | Base | oracle | 75.0 (36) | 55.6 (10 of 18) |
| ood | correct policies | v1 | Phase B | never | 41.7 (36) | 0.0 (0 of 18) |
| ood | correct policies | v1 | Phase B | always | 75.0 (36) | 61.1 (11 of 18) |
| ood | correct policies | v1 | Phase B | selective | 63.9 (36) | 50.0 (9 of 18) |
| ood | correct policies | v1 | Phase B | oracle | 86.1 (36) | 72.2 (13 of 18) |
| ood | correct policies | v2 | Base | never | 44.4 (36) | 5.6 (1 of 18) |
| ood | correct policies | v2 | Base | always | 69.4 (36) | 38.9 (7 of 18) |
| ood | correct policies | v2 | Base | selective | 69.4 (36) | 44.4 (8 of 18) |
| ood | correct policies | v2 | Base | oracle | 75.0 (36) | 55.6 (10 of 18) |
| ood | correct policies | v2 | Phase B | never | 41.7 (36) | 0.0 (0 of 18) |
| ood | correct policies | v2 | Phase B | always | 75.0 (36) | 61.1 (11 of 18) |
| ood | correct policies | v2 | Phase B | selective | 66.7 (36) | 44.4 (8 of 18) |
| ood | correct policies | v2 | Phase B | oracle | 86.1 (36) | 72.2 (13 of 18) |

## 7. Saving next to the oracle saving

Saving = 1 − check calls / check calls of always (decisions.md R10.3). Oracle saving = the same for exactly the gold checks: the best saving possible with every needed check made. Selective can save more than the oracle (it skips checks the record needs), so read it with the accuracies.

| Split | Policies | System | Model | Calls, always | Calls, selective | Calls, oracle (gold checks) | Selective saving | Oracle saving | Selective accuracy | Oracle accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| val | retrieved policies | v1 | Base | 200 | 9 | 30 | 95.5 | 85.0 | 57.5 | 70.0 |
| val | retrieved policies | v1 | Phase B | 200 | 27 | 30 | 86.5 | 85.0 | 67.5 | 90.0 |
| val | retrieved policies | v2 | Base | 200 | 25 | 30 | 87.5 | 85.0 | 65.0 | 67.5 |
| val | retrieved policies | v2 | Phase B | 200 | 34 | 30 | 83.0 | 85.0 | 77.5 | 90.0 |
| val | correct policies | v1 | Base | 200 | 11 | 30 | 94.5 | 85.0 | 70.0 | 80.0 |
| val | correct policies | v1 | Phase B | 200 | 28 | 30 | 86.0 | 85.0 | 82.5 | 97.5 |
| val | correct policies | v2 | Base | 200 | 13 | 30 | 93.5 | 85.0 | 65.0 | 80.0 |
| val | correct policies | v2 | Phase B | 200 | 29 | 30 | 85.5 | 85.0 | 85.0 | 97.5 |
| test | retrieved policies | v1 | Base | 704 | 55 | 141 | 92.2 | 80.0 | 39.0 | 48.6 |
| test | retrieved policies | v1 | Phase B | 704 | 105 | 141 | 85.1 | 80.0 | 61.6 | 76.0 |
| test | retrieved policies | v2 | Base | 704 | 89 | 141 | 87.4 | 80.0 | 44.5 | 50.0 |
| test | retrieved policies | v2 | Phase B | 704 | 117 | 141 | 83.4 | 80.0 | 63.0 | 80.8 |
| test | correct policies | v1 | Base | 704 | 73 | 141 | 89.6 | 80.0 | 43.8 | 51.4 |
| test | correct policies | v1 | Phase B | 704 | 103 | 141 | 85.4 | 80.0 | 69.2 | 86.3 |
| test | correct policies | v2 | Base | 704 | 84 | 141 | 88.1 | 80.0 | 43.2 | 51.4 |
| test | correct policies | v2 | Phase B | 704 | 108 | 141 | 84.7 | 80.0 | 69.9 | 86.3 |
| ood | retrieved policies | v1 | Base | 504 | 27 | 73 | 94.6 | 85.5 | 46.4 | 55.4 |
| ood | retrieved policies | v1 | Phase B | 504 | 85 | 73 | 83.1 | 85.5 | 67.0 | 75.9 |
| ood | retrieved policies | v2 | Base | 504 | 49 | 73 | 90.3 | 85.5 | 50.0 | 65.2 |
| ood | retrieved policies | v2 | Phase B | 504 | 76 | 73 | 84.9 | 85.5 | 66.1 | 82.1 |
| ood | correct policies | v1 | Base | 504 | 28 | 73 | 94.4 | 85.5 | 58.0 | 63.4 |
| ood | correct policies | v1 | Phase B | 504 | 79 | 73 | 84.3 | 85.5 | 78.6 | 87.5 |
| ood | correct policies | v2 | Base | 504 | 28 | 73 | 94.4 | 85.5 | 57.1 | 63.4 |
| ood | correct policies | v2 | Phase B | 504 | 76 | 73 | 84.9 | 85.5 | 80.4 | 87.5 |

