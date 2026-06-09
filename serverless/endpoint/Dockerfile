FROM python:3.11-slim

WORKDIR /endpoint

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

## mock or ai
ENV NEBIUS_ENDPOINT_MODE=mock

EXPOSE 9000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9000"]
