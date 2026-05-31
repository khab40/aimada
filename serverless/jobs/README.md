# Serverless Batch Benchmark Job

Runs repeated synthetic simulations, injects labeled scenario families, computes detector metrics, and emits benchmark artifacts.

## Local Run

```bash
python run_batch_benchmark.py --config job_config.example.yaml
```

The current job is a scaffold. Wire it to the shared simulation and detector modules as the backend implementation matures.
