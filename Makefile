.PHONY: help backend-test backend-dev frontend-dev serverless-benchmark serverless-build serverless-push serverless-smoke nebius-partial-plan nebius-partial-deploy nebius-vm-plan nebius-vm-deploy nebius-k8s-plan nebius-k8s-deploy secrets-plan secrets-rotate secrets-check secrets-test docker-up docker-down

help:
	@printf "%s\n" "Targets: backend-test backend-dev frontend-dev serverless-benchmark serverless-build serverless-push serverless-smoke nebius-partial-plan nebius-partial-deploy nebius-vm-plan nebius-vm-deploy nebius-k8s-plan nebius-k8s-deploy secrets-plan secrets-rotate secrets-check secrets-test docker-up docker-down"

backend-test:
	cd backend && uv run pytest

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && npm run dev

serverless-benchmark:
	cd serverless/jobs && uv run python run_batch_benchmark.py --config job_config.example.yaml

serverless-build:
	./scripts/build-serverless-images.sh

serverless-push:
	PUSH=true ./scripts/build-serverless-images.sh

serverless-smoke:
	SMOKE=true ./scripts/build-serverless-images.sh

nebius-partial-plan:
	./scripts/deploy-nebius-partial.sh --dry-run

nebius-partial-deploy:
	./scripts/deploy-nebius-partial.sh

nebius-vm-plan:
	./scripts/deploy-nebius-vm.sh --dry-run

nebius-vm-deploy:
	./scripts/deploy-nebius-vm.sh

nebius-k8s-plan:
	./scripts/deploy-nebius-k8s.sh --dry-run

nebius-k8s-deploy:
	./scripts/deploy-nebius-k8s.sh

secrets-plan:
	./scripts/rotate-secrets.sh

secrets-rotate:
	./scripts/rotate-secrets.sh --apply

secrets-check:
	./scripts/check-secrets.sh

secrets-test:
	cd backend && UV_CACHE_DIR=$${UV_CACHE_DIR:-/tmp/aimada-uv-cache} uv run pytest tests/test_secret_scripts.py -q

docker-up:
	docker compose up --build

docker-down:
	docker compose down
