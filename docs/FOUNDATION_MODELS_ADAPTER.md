# Offline Foundation Models adapter training (StreamTV recovery)

StreamTV learns heal behavior **while running** via Apple Foundation Models
`Instructions`, multiturn `Transcript`, and `Tool` calling (Tier A). See
[AUTO_HEALER.md](AUTO_HEALER.md) and [guides/FOUNDATION_MODELS_RECOVERY.md](guides/FOUNDATION_MODELS_RECOVERY.md).

Optionally, successful episodes are written to:

`~/Library/Application Support/StreamTV/recovery/adapter_training.jsonl`

Those samples can train a custom LoRA adapter **offline** with Apple’s
[Adapter Training Toolkit](https://developer.apple.com/apple-intelligence/foundation-models-adapter/)
(version **26.0.0** — last release; **not** compatible with macOS 27+).

Runtime `SystemLanguageModel.Adapter` is usable on **macOS 26.x** only. On macOS 27+,
use Tier A (Instructions + Tools + journal) and optional Ollama.

## When to use an adapter

Prefer prompt + Tools first. Train an adapter when you need consistent StreamTV-specific
heal classification that few-shot instructions cannot stabilize. Each adapter is pinned to
one system model version; retrain after OS/base-model updates.

## Requirements

- Apple Developer Program membership (download toolkit)
- Mac with Apple silicon and **≥32 GB** RAM (or Linux GPU)
- Python 3.11+
- Production deploy: Foundation Models Framework Adapter Entitlement
  (`com.apple.developer.foundation-model-adapter`)

## Export dataset from a running install

Enable **Collect training samples** in StreamTVMac (default on), run recover/analyze cycles, then:

```bash
python3 scripts/export_recovery_adapter_dataset.py
# optional:
python3 scripts/export_recovery_adapter_dataset.py \
  --source "$HOME/Library/Application Support/StreamTV/recovery/adapter_training.jsonl" \
  --out-dir data/recovery_adapter
```

Produces `data/recovery_adapter/train.jsonl` and `eval.jsonl`.

## Train + export (inside toolkit tree)

```bash
conda create -n adapter-training python=3.11
conda activate adapter-training
cd /path/to/adapter-toolkit-26.0.0
pip install -r requirements.txt

python -m examples.train_adapter \
  --train-data /path/to/StreamTV/data/recovery_adapter/train.jsonl \
  --eval-data /path/to/StreamTV/data/recovery_adapter/eval.jsonl \
  --epochs 5 --learning-rate 1e-3 --batch-size 4 \
  --checkpoint-dir ./checkpoints/streamtv_recovery/

python -m export.export_fmadapter \
  --adapter-name streamtv_recovery \
  --checkpoint ./checkpoints/streamtv_recovery/adapter-final.pt \
  --output-dir ./exports/
```

Copy `streamtv_recovery.fmadapter` to:

`~/Library/Application Support/StreamTV/recovery/adapters/`

Prefer **Background Assets** for shipping (do not embed every adapter version in the app bundle).

## Privacy

Training JSONL stays local until an operator exports it. No automatic upload.
