FROM python:3.11-slim

WORKDIR /job

ENV PYTHONPATH=/job/backend

COPY backend /job/backend
COPY serverless/jobs /job/serverless/jobs

WORKDIR /job/serverless/jobs

CMD ["python", "detector_tournament.py", "--runs", "100", "--output", "/job/outputs/benchmark"]
