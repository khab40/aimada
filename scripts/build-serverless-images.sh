# vLLM-only endpoint image for Nebius Serverless AI Endpoint on H100.
# The image runs a private local vLLM OpenAI-compatible server on 127.0.0.1:8001
# and exposes only the AIMADA FastAPI endpoint on 0.0.0.0:9000.

FROM vllm/vllm-openai:latest

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    NEBIUS_ENDPOINT_MODE=mock \
    VLLM_HOST=127.0.0.1 \
    VLLM_PORT=8001 \
    VLLM_BASE_URL=http://127.0.0.1:8001/v1 \
    VLLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct \
    VLLM_GPU_MEMORY_UTILIZATION=0.90 \
    VLLM_MAX_MODEL_LEN=4096

WORKDIR /endpoint

# Install only lightweight app/runtime dependencies here.
# Heavy GPU/vLLM dependencies come from the base image to keep rebuilds faster.
COPY requirements.txt /endpoint/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r /endpoint/requirements.txt

# Copy app code after dependencies so small code changes do not invalidate heavy layers.
COPY app.py /endpoint/app.py
COPY entrypoint.sh /endpoint/entrypoint.sh
RUN chmod +x /endpoint/entrypoint.sh

# Lightweight build-time smoke test only.
# Do not start vLLM or download models during docker build.
RUN NEBIUS_ENDPOINT_MODE=mock python - <<'PY'
import app
health = app.health()
assert health["status"] == "ok"
assert health["endpoint_mode"] == "mock"
print("AIMADA endpoint smoke test passed")
PY

EXPOSE 9000

CMD ["/endpoint/entrypoint.sh"]
