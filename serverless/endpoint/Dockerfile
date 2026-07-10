FROM --platform=linux/amd64 pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

WORKDIR /endpoint

ENV PYTHONUNBUFFERED=1 \
    NEBIUS_ENDPOINT_MODE=local_vllm \
    LOCAL_VLLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct \
    LOCAL_VLLM_HOST=127.0.0.1 \
    LOCAL_VLLM_PORT=8001 \
    LOCAL_VLLM_BASE_URL=http://127.0.0.1:8001/v1 \
    LOCAL_VLLM_GPU_MEMORY_UTILIZATION=0.85 \
    LOCAL_VLLM_MAX_MODEL_LEN=4096

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /endpoint/start.sh
RUN NEBIUS_ENDPOINT_MODE=mock python -c "import app; assert app.health()['model_mode'] == 'deterministic_fallback'"

EXPOSE 9000
CMD ["/endpoint/start.sh"]
