FROM python:3.11-slim

WORKDIR /endpoint

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic

COPY . .

EXPOSE 9000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9000"]
