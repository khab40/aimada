FROM python:3.11-slim

WORKDIR /job

ENV PYTHONPATH=/job/backend

COPY backend /job/backend
COPY serverless/jobs /job/serverless/jobs

RUN pip install --no-cache-dir -r /job/serverless/jobs/requirements.txt

WORKDIR /job/serverless/jobs

CMD ["python", "run_batch_experiments.py", "--runs", "1000", "--batch-size", "100", "--output", "/job/outputs/serverless-batch"]
