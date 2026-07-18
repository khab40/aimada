FROM python:3.11-slim

WORKDIR /app

ARG INSTALL_NEBIUS_CLI=false

# Real Nebius mode opts in through docker-compose.nebius.yml. Local mock builds
# do not carry cloud CLIs or their installer dependencies.
RUN if [ "${INSTALL_NEBIUS_CLI}" = "true" ]; then \
      apt-get update; \
      apt-get install -y --no-install-recommends ca-certificates curl; \
      curl -fsSL https://storage.eu-north1.nebius.cloud/cli/install.sh | bash; \
      apt-get purge -y --auto-remove curl; \
      rm -rf /var/lib/apt/lists/*; \
    fi

# Add the Nebius binary directory directly to the system PATH
ENV PATH="/root/.nebius/bin:${PATH}"

COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir \
  "fastapi>=0.111.0" \
  pydantic \
  "pydantic-settings>=2.14.2" \
  "starlette>=1.3.1" \
  pyyaml \
  uvicorn \
  uvloop \
  httptools \
  websockets \
  && if [ "${INSTALL_NEBIUS_CLI}" = "true" ]; then pip install --no-cache-dir awscli; fi

COPY backend/app ./app
COPY serverless/jobs ./serverless/jobs

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
