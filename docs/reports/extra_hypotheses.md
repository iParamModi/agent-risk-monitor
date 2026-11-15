# Exploratory hypotheses H2-H6

**Exploratory.** Stated on 15 Nov 2026 after the final results were seen, and written in `docs/decisions.md` before this script was run; every result is reported. Judged with correct policies (as R10.4); rows with retrieved policies are for information. Final system v2; values in % (Phase B vs the comparison); difference in points with a 95% interval by bootstrap over seeds (2,000 resamples, paired). Built by `scripts/extra_hypotheses.py`.

| | Hypothesis | Holds if |
|---|---|---|
| H2 | Training teaches when to ask | records needing a check where the selective model makes ≥ 1 check: Phase B − base, lower bound > 0 |
| H3 | Checking helps | accuracy Phase B selective − Phase B never, lower bound > 0 |
| H4 | Fine-tuning helps | accuracy Phase B selective − base selective, lower bound > 0 |
| H5 | The trust rule is learned | H4 on T2 records only |
| H6 | No wasted checks | saving(selective) − saving(oracle), lower bound ≥ −5 points |

| Hypothesis | Split | Policies | Values | Difference [95% CI] | Result |
|---|---|---|---|---|---|
| H2 training teaches when to ask | test | correct | 90.7 vs 62.6 | +28.0 [+17.0, +39.6] | **holds** |
| H2 training teaches when to ask | test | retrieved | 95.3 vs 65.4 | +29.9 [+17.6, +41.0] | **holds** (information) |
| H2 training teaches when to ask | ood | correct | 88.7 vs 33.8 | +54.9 [+37.5, +70.4] | **holds** |
| H2 training teaches when to ask | ood | retrieved | 87.3 vs 47.9 | +39.4 [+25.3, +53.7] | **holds** (information) |
| H3 checking helps | test | correct | 69.9 vs 61.0 | +8.9 [+2.8, +15.3] | **holds** |
| H3 checking helps | test | retrieved | 63.0 vs 58.2 | +4.8 [+1.3, +8.7] | **holds** (information) |
| H3 checking helps | ood | correct | 80.4 vs 67.9 | +12.5 [+5.0, +20.2] | **holds** |
| H3 checking helps | ood | retrieved | 66.1 vs 68.8 | -2.7 [-12.5, +6.3] | not shown (information) |
| H4 fine-tuning helps | test | correct | 69.9 vs 43.2 | +26.7 [+17.4, +35.3] | **holds** |
| H4 fine-tuning helps | test | retrieved | 63.0 vs 44.5 | +18.5 [+10.0, +26.6] | **holds** (information) |
| H4 fine-tuning helps | ood | correct | 80.4 vs 57.1 | +23.2 [+11.2, +34.5] | **holds** |
| H4 fine-tuning helps | ood | retrieved | 66.1 vs 50.0 | +16.1 [+3.0, +28.0] | **holds** (information) |
| H5 trust rule learned (T2) | test | correct | 100.0 vs 50.0 | +50.0 [+38.6, +60.4] | **holds** |
| H5 trust rule learned (T2) | test | retrieved | 98.1 vs 57.7 | +40.4 [+27.3, +53.3] | **holds** (information) |
| H5 trust rule learned (T2) | ood | correct | 90.9 vs 52.3 | +38.6 [+21.9, +55.4] | **holds** |
| H5 trust rule learned (T2) | ood | retrieved | 84.1 vs 50.0 | +34.1 [+20.5, +47.5] | **holds** (information) |
| H6 no wasted checks | test | correct |  | +4.7 [+2.4, +7.1] | **holds** |
| H6 no wasted checks | test | retrieved |  | +3.4 [+0.9, +6.0] | **holds** (information) |
| H6 no wasted checks | ood | correct |  | -0.6 [-3.0, +1.8] | **holds** |
| H6 no wasted checks | ood | retrieved |  | -0.6 [-3.4, +2.0] | **holds** (information) |
