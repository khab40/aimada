FROM python:3.11-slim

WORKDIR /app

# Install dependencies for Nebius CLI installation
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Run the official Nebius AI Cloud CLI setup script
RUN curl -sSL https://storage.eu-north1.nebius.cloud/cli/install.sh | bash

# Add the Nebius binary directory directly to the system PATH
ENV PATH="/root/.nebius/bin:${PATH}"

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
  fastapi \
  numpy \
  pydantic \
  pydantic-settings \
  pytest \
  python-dotenv \
  pyyaml \
  "uvicorn[standard]"

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
