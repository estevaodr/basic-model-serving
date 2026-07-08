FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir \
    torch==2.12.1 \
    torchvision==0.27.1 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV TORCH_HOME=/app/.cache/torch

RUN python -c "from app.models.resnet import ResNetClassifier; ResNetClassifier()"

FROM python:3.12-slim AS runtime

WORKDIR /app

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/.cache/torch /app/.cache/torch
COPY app/ ./app/

ENV TORCH_HOME=/app/.cache/torch \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN mkdir -p /app/.cache/torch && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3); exit(0 if r.status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
