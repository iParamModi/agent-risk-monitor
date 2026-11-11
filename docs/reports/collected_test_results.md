# Risk detection on the collected datasets: test and val

Setting `never` (one pass, risk answer only), float16, greedy, Kaggle T4 x2. Scoring only: nothing was trained or tuned on these test records. These numbers come from **our own splits**, so they cannot be compared with published leaderboards (PLAN Step 25.5). Base = no training; Phase A = trained on collected data only; Phase B = trained on collected and generated data.

12 test records over 7300 tokens are left out, as on val (12 of them UNSAFE, all ATBench).

## Test

| Model | Source | Records | Safe/unsafe accuracy | Risk-label F1 | Risk-type macro-F1 | Unsafe caught | Safe flagged unsafe | Valid JSON |
|---|---|---|---|---|---|---|---|---|
| Base | R-Judge | 115 | 57.4 | 59.5 | 44.9 | 36 of 55 | 30 of 60 | 100.0 |
| Base | ATBench | 188 | 53.7 | 12.1 | 5.6 | 6 of 90 | 3 of 98 | 100.0 |
| Base | AgentRisk | 125 | 54.4 | 14.9 | 15.2 | 5 of 59 | 3 of 66 | 100.0 |
| Base | **All** | 428 | 54.9 | 32.8 | 26.1 | 47 of 204 | 36 of 224 | 100.0 |
| Phase A | R-Judge | 115 | 91.3 | 90.0 | 59.8 | 45 of 55 | 0 of 60 | 100.0 |
| Phase A | ATBench | 188 | 89.4 | 88.1 | 36.1 | 74 of 90 | 4 of 98 | 100.0 |
| Phase A | AgentRisk | 125 | 99.2 | 99.1 | 62.0 | 58 of 59 | 0 of 66 | 99.2 |
| Phase A | **All** | 428 | 92.8 | 91.9 | 55.0 | 177 of 204 | 4 of 224 | 99.8 |
| Phase B, 30 Oct | R-Judge | 115 | 90.4 | 88.9 | 62.0 | 44 of 55 | 0 of 60 | 100.0 |
| Phase B, 30 Oct | ATBench | 188 | 87.8 | 86.1 | 29.5 | 71 of 90 | 4 of 98 | 100.0 |
| Phase B, 30 Oct | AgentRisk | 125 | 97.6 | 97.4 | 57.4 | 56 of 59 | 0 of 66 | 100.0 |
| Phase B, 30 Oct | **All** | 428 | 91.4 | 90.2 | 50.0 | 171 of 204 | 4 of 224 | 100.0 |
| Phase B, final | R-Judge | 115 | 89.6 | 88.0 | 67.8 | 44 of 55 | 1 of 60 | 100.0 |
| Phase B, final | ATBench | 188 | 86.2 | 83.5 | 27.6 | 66 of 90 | 2 of 98 | 100.0 |
| Phase B, final | AgentRisk | 125 | 97.6 | 97.4 | 58.5 | 56 of 59 | 0 of 66 | 100.0 |
| Phase B, final | **All** | 428 | 90.4 | 89.0 | 52.7 | 166 of 204 | 3 of 224 | 100.0 |

## Val (for comparison)

| Model | Source | Records | Safe/unsafe accuracy | Risk-label F1 | Risk-type macro-F1 | Unsafe caught | Safe flagged unsafe | Valid JSON |
|---|---|---|---|---|---|---|---|---|
| Base | R-Judge | 47 | 59.6 | 45.7 | 15.2 | 8 of 21 | 6 of 26 | 100.0 |
| Base | ATBench | 96 | 49.0 | 3.9 | 0.0 | 1 of 49 | 1 of 47 | 100.0 |
| Base | AgentRisk | 98 | 52.0 | 4.1 | 1.2 | 1 of 48 | 0 of 50 | 100.0 |
| Base | **All** | 241 | 52.3 | 14.8 | 4.0 | 10 of 118 | 7 of 123 | 100.0 |
| Phase A | R-Judge | 47 | 89.4 | 86.5 | 50.5 | 16 of 21 | 0 of 26 | 100.0 |
| Phase A | ATBench | 96 | 90.6 | 90.5 | 52.3 | 43 of 49 | 3 of 47 | 100.0 |
| Phase A | AgentRisk | 98 | 99.0 | 98.9 | 62.8 | 47 of 48 | 0 of 50 | 100.0 |
| Phase A | **All** | 241 | 93.8 | 93.4 | 59.6 | 106 of 118 | 3 of 123 | 100.0 |
| Phase B, 30 Oct | R-Judge | 47 | 87.2 | 84.2 | 64.0 | 16 of 21 | 1 of 26 | 100.0 |
| Phase B, 30 Oct | ATBench | 96 | 89.6 | 89.1 | 43.1 | 41 of 49 | 2 of 47 | 100.0 |
| Phase B, 30 Oct | AgentRisk | 98 | 96.9 | 96.8 | 55.8 | 45 of 48 | 0 of 50 | 100.0 |
| Phase B, 30 Oct | **All** | 241 | 92.1 | 91.5 | 55.6 | 102 of 118 | 3 of 123 | 100.0 |
| Phase B, final | R-Judge | 47 | 87.2 | 85.0 | 65.6 | 17 of 21 | 2 of 26 | 100.0 |
| Phase B, final | ATBench | 96 | 89.6 | 89.1 | 43.5 | 41 of 49 | 2 of 47 | 100.0 |
| Phase B, final | AgentRisk | 98 | 95.9 | 95.7 | 63.8 | 44 of 48 | 0 of 50 | 100.0 |
| Phase B, final | **All** | 241 | 91.7 | 91.1 | 60.6 | 102 of 118 | 4 of 123 | 100.0 |
