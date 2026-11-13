# To Meet: share the final adapter on Kaggle (from Prateek, 2026-11-13)

The recorded demo runs need the final adapter, and I still can't access it. This blocks the Kaggle recording notebook and the demo table in the report, so please do this first today. It takes about 2 minutes.

## What it is

`meet6868/agent-risk-adapter-final` is a **Kaggle Dataset**. It is not a Kaggle Model and not a Notebook. It is the final Phase B adapter you trained on 11 Nov. Your final eval notebooks already use it as an input:

```
kaggle/our_eval_final_phase_b/kernel-metadata.json
kaggle/collected_test/kernel-metadata.json
kaggle/v2_val_check/kernel-metadata.json
  "dataset_sources": ["meet6868/agent-risk-code", "meet6868/agent-risk-adapter-final"]
```

It is private, so it shows only when you are logged in as `meet6868`.

## Step 1: find it

Any one of these works:

- Direct link: https://www.kaggle.com/datasets/meet6868/agent-risk-adapter-final
- Profile picture (top right) → **Your Work** → **Datasets** tab → `agent-risk-adapter-final`
- Terminal: `kaggle datasets list --mine -s adapter`

## Step 2: share it with me

1. Open the dataset page.
2. Go to the **Settings** tab, then the **Sharing** section.
3. Add the collaborator **`prateek99491`** with **Viewer** access.
4. Click **Save**.

The dataset stays **private**. Do not make it public: it is trained on AgentRisk data, which has no licence.

## If it is not under Datasets

The adapter may only exist as a notebook output. In that case:

1. Open the notebook that trained the final adapter (11 Nov) and go to **Output**.
2. Click **New Dataset** on the adapter folder.
3. Name it `agent-risk-adapter-final` and set it to **Private**.
4. Share it with `prateek99491` as in Step 2.

Keep the name exactly `agent-risk-adapter-final`, because the notebooks above use that name.

## If Kaggle sharing still does not work

Backup: on the private Hugging Face repo `meet5568/Agent-Risk`, add me as a collaborator (read access is enough) and tell me the folder that holds `phaseB_v2`. The recording notebook will then download it with my HF token, stored in Kaggle Secrets and never in the repo.

## Afterwards

Reply in chat, or add a line to the `PROGRESS.md` Activity Log ("shared agent-risk-adapter-final with prateek99491"). I will then run the recording notebook (`kaggle/demo_record/`) and add the demo table to `report/final_submission.tex`.
