# Aimada Deployment Modes

Deployment entry point:

```bash
deployments/deploy.sh <mode> [--dry-run] [--skip-build] [--skip-smoke]
```

Modes:

- `local-demo` runs the local Docker Compose demo with deterministic Nebius fallback.
- `nebius-cloud-demo` creates Nebius endpoint/job resources and runs the app against them.
- `production-nebius` creates Nebius endpoint/job resources and requires storage, DB, MLflow, observability, IAM, and secrets settings.

Lifecycle covered by every mode:

```text
simulate -> detect -> explain -> investigate -> report -> audit -> benchmark
```

Examples:

```bash
deployments/deploy.sh local-demo
deployments/deploy.sh nebius-cloud-demo --dry-run
deployments/deploy.sh production-nebius --dry-run
```

Mode configuration lives in `deployments/modes/*.env`. Local `.env` values are loaded after the mode file, so real tokens and resource IDs stay outside git.

Production required variables:

- `NEBIUS_SUBNET_ID`
- `NEBIUS_ENDPOINT_TOKEN`
- `AIMADA_OBJECT_STORAGE_URI`
- `AIMADA_POSTGRES_DSN`
- `AIMADA_MLFLOW_TRACKING_URI`
- `AIMADA_OBSERVABILITY_ENDPOINT`
- `AIMADA_IAM_PROFILE`
- `AIMADA_SECRETS_BACKEND`

Each run writes a deployment report to `outputs/deployments/<mode>-latest.env`.
