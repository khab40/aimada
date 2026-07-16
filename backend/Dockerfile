FROM python:3.11-slim

WORKDIR /app

# Install dependencies for Nebius CLI installation
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  ca-certificates \
  && rm -rf /var/lib/apt/lists/*

ARG INSTALL_NEBIUS_CLI=false

# Real Nebius mode opts in through docker-compose.nebius.yml. Local mock builds
# do not depend on cloud credentials or the Nebius CLI download endpoint.
RUN if [ "${INSTALL_NEBIUS_CLI}" = "true" ]; then \
      curl -fsSL https://storage.eu-north1.nebius.cloud/cli/install.sh | bash; \
    fi

# Add the Nebius binary directory directly to the system PATH
ENV PATH="/root/.nebius/bin:${PATH}"

COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir \
  "fastapi>=0.111.0" \
  numpy \
  pydantic \
  "pydantic-settings>=2.14.2" \
  pytest \
  python-dotenv \
  requests \
  "starlette>=1.3.1" \
  pyyaml \
  awscli \
  "uvicorn[standard]"

COPY backend/app ./app
COPY serverless/jobs ./serverless/jobs

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
