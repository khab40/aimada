# Serverless Jobs

Nebius-oriented batch jobs for offline synthetic experiments.

These jobs are educational simulation utilities. They do not evaluate real
market manipulation, do not provide trading signals, and should not be used for
compliance decisions.

## Detector Tournament

Runs synthetic simulations, launches labeled scenario families, evaluates
detector outputs, and writes benchmark artifacts.

```bash
python serverless/jobs/detector_tournament.py \
  --runs 100 \
  --scenarios spoofing,layering,quote_stuffing,liquidity_evaporation \
  --detectors spoofing_like,layering_like,quote_stuffing,liquidity_shock \
  --output outputs/benchmark
```

Outputs:

- `benchmark_report.md`
- `metrics.csv`
- `results.json`
- `charts/f1_by_scenario.png`
- `charts/confidence_distribution.png`
- `charts/detection_latency.png`

Metrics:

- precision
- recall
- F1
- average detection latency in milliseconds

## Synthetic Dataset Factory

Generates labeled synthetic event, snapshot, incident, and label artifacts.

```bash
python serverless/jobs/synthetic_dataset_factory.py \
  --samples 100 \
  --output outputs/synthetic-dataset
```

Outputs:

- `events.jsonl`
- `incidents.jsonl`
- `labels.jsonl`
- `snapshots.parquet` when Parquet dependencies are available
- `snapshots.parquet.jsonl` when Parquet dependencies are unavailable
- `manifest.json`

## Docker

Build from the repository root so the image can copy the shared backend
simulator code:

```bash
docker build -f serverless/jobs/Dockerfile -t nebius-market-abuse-jobs .
```

Run the detector tournament:

```bash
docker run --rm -v "$PWD/outputs:/job/outputs" nebius-market-abuse-jobs
```

Run the dataset factory:

```bash
docker run --rm -v "$PWD/outputs:/job/outputs" nebius-market-abuse-jobs \
  python synthetic_dataset_factory.py --samples 100 --output /job/outputs/synthetic-dataset
```

## Notes

- Keep run counts small while testing on Nebius to control time and cost.
- The scripts reuse the backend synthetic simulator and deterministic detector
  engine.
- The generated labels are synthetic ground truth from scenario injection, not
  real surveillance labels.

## Smart Attack/Detect Batch

The Phase 4 runner lives in `serverless/jobs/run_batch_experiments.py` and is
also available through the compatibility wrapper `run_batch_benchmark.py`.

```bash
python serverless/jobs/run_batch_experiments.py \
  --runs 1000 \
  --batch-size 100 \
  --scenarios normal_market,spoofing,layering,quote_stuffing,pump_and_cancel \
  --output outputs/serverless-batch
```

Outputs:

- `order_book_events.jsonl`
- `trades.jsonl`
- `attack_labels.jsonl`
- `blue_team_alerts.jsonl`
- `detector_metrics.csv`
- `generated_report.md`
- `manifest.json`
