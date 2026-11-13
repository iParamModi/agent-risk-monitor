# To Prateek: where the final adapter is, and its path (from Meet, 2026-11-13)

Reply to `docs/messages/2026-11-13_to_Meet_share_adapter.md`.

## 1. Sharing

- The final adapter is the private Kaggle **Dataset** `meet6868/agent-risk-adapter-final` (the 11 Nov final Phase B
  adapter). It exists: my final v2 runs loaded the adapter from it on 11 Nov.
- Sharing has to be done on the Kaggle website (Settings → Sharing → `prateek99491`, Viewer); the Kaggle CLI cannot
  add collaborators. I'll confirm it with the line you asked for in the `PROGRESS.md` Activity Log
  ("shared agent-risk-adapter-final with prateek99491") as soon as it is done.

## 2. Path inside a Kaggle notebook

Attach the Dataset as an input (Add Input → Datasets), or in `kernel-metadata.json`:

```json
"dataset_sources": ["meet6868/agent-risk-adapter-final"]
```

`adapter_config.json` and `adapter_model.safetensors` sit at the top of the Dataset. Kaggle mounted it at two
different paths in my runs on 11 Nov:

```
/kaggle/input/agent-risk-adapter-final
/kaggle/input/datasets/meet6868/agent-risk-adapter-final
```

So find it by its config file, as our Kaggle jobs do (`kaggle/collected_test/run_collected_test.py`):

```python
import glob
adapter = glob.glob("/kaggle/input/**/adapter_config.json", recursive=True)[0].rsplit("/", 1)[0]
# python -m src.monitor.run ... --adapter {adapter}   or   PeftModel.from_pretrained(base_model, adapter)
```

Setup that our jobs use:

- Base model `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`, float16, GPU T4 x2.
- **Uninstall `torchao` first** (`pip uninstall -y torchao`): Kaggle's torchao 0.10 breaks PEFT adapter loading.
- Decoding (greedy, at most 512 new tokens, Qwen3 thinking off) is fixed in `src/monitor/models.py`.
- To match the final system in the report, use system v2 (`--version v2`, see `VERSIONS` in
  `src/monitor/case_inputs.py`): tag-filtered retrieval with 8 policies, second-source check, two prompt hints.

## 3. Outside Kaggle

`/kaggle/input/...` exists only inside Kaggle notebooks. Anywhere else, download the adapter into a folder first:

```bash
kaggle datasets download -d meet6868/agent-risk-adapter-final -p adapter --unzip   # account with access
```

A byte-identical copy is in the private Hugging Face repo `meet5568/Agent-Risk`, folder `phaseB_v2/` (checked by
SHA-256). Your Hugging Face backup does not work as written, though: a private repo owned by a user cannot add
single collaborators. It would need a Hugging Face organisation with the repo moved into it, so Kaggle sharing is
the quick way.

## 4. Modal

The repo has no Modal app (`deploy/modal_app.py` does not exist), and you cut the live service on 12 Nov. Any
Modal GPU run is your call under the cost rules. I have not run anything on Modal.
