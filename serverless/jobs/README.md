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
