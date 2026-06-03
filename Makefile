.PHONY: help backend-test backend-dev frontend-dev serverless-benchmark serverless-build docker-up docker-down

help:
	@printf "%s\n" "Targets: backend-test backend-dev frontend-dev serverless-benchmark serverless-build docker-up docker-down"

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

docker-up:
	docker compose up --build

docker-down:
	docker compose down
