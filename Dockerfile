FROM python:3.12-slim

WORKDIR /app

# LightGBM needs OpenMP at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Runtime deps only - no notebooks, plotting or MLflow in the served image.
COPY requirements-api.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements-api.txt

COPY src/ src/
COPY models/ models/
COPY samples/ samples/
COPY artifacts/drift_reference.json artifacts/drift_reference.json

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
