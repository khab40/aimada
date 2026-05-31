FROM python:3.11-slim

WORKDIR /job

RUN pip install --no-cache-dir pyyaml

COPY . .

CMD ["python", "run_batch_benchmark.py", "--config", "job_config.example.yaml"]
