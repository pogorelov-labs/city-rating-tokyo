# City-rating MCP server — multi-stage build.
#
# Stage 1 builds the per-station datamart by running scripts/build-datamart.py
# against NocoDB. Stage 2 only pre-caches the fastembed ONNX model (no
# encoding work — we used to encode 17,916 texts here, but that took
# ~110 min on a 2-core VPS for an artifact that's deterministic given
# the committed descriptions). Embeddings.npz is now provided as a
# RUNTIME bind mount from a Coolify persistent volume (see mcp/README
# "Embeddings: host volume" section). Stage 3 is the runtime image.
#
# Build context is the REPO ROOT (the city-rating worktree), not mcp/. Coolify
# config: dockerfile_path = mcp/Dockerfile, build_context = .

ARG PYTHON_VERSION=3.12-slim
ARG EMBEDDING_MODEL=intfloat/multilingual-e5-large

# ---------- Stage 1: build datamart ----------
FROM python:${PYTHON_VERSION} AS datamart

WORKDIR /build
RUN pip install --no-cache-dir requests

COPY scripts/build-datamart.py /build/scripts/build-datamart.py
COPY data /build/data
COPY app/src/data /build/app/src/data

ARG NOCODB_API_URL=https://nocodb.pogorelov.dev
ARG NOCODB_API_TOKEN
ENV NOCODB_API_URL=${NOCODB_API_URL}
ENV NOCODB_API_TOKEN=${NOCODB_API_TOKEN}

RUN python3 scripts/build-datamart.py


# ---------- Stage 2: pre-cache fastembed ONNX model ----------
# Why pre-cache instead of letting fastembed download lazily on first
# query: it keeps the cold-start tail latency bounded. Without the
# pre-cache the first semantic_search call after a fresh container start
# pays ~5 min for the 2.2 GB model download from HuggingFace's CDN.
# Baking it in trades 5 min of build time for a predictable runtime.
FROM python:${PYTHON_VERSION} AS model-cache

ARG EMBEDDING_MODEL
ENV FASTEMBED_CACHE_DIR=/opt/fastembed-cache

RUN pip install --no-cache-dir fastembed numpy

RUN mkdir -p /opt/fastembed-cache \
    && python3 -c "from fastembed import TextEmbedding; \
       TextEmbedding(model_name='${EMBEDDING_MODEL}', cache_dir='/opt/fastembed-cache')"


# ---------- Stage 3: runtime ----------
FROM python:${PYTHON_VERSION} AS runtime

ARG EMBEDDING_MODEL
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY mcp/pyproject.toml /app/pyproject.toml
COPY mcp/src /app/src
RUN pip install --no-cache-dir .

COPY --from=datamart    /build/data/station-datamart.json /app/data/station-datamart.json
COPY --from=model-cache /opt/fastembed-cache              /opt/fastembed-cache
COPY app/src/data/generated-descriptions.json             /app/app/src/data/generated-descriptions.json
COPY app/src/data/livecams.json                           /app/app/src/data/livecams.json

ENV CITY_RATING_DATAMART=/app/data/station-datamart.json
# Embeddings.npz must be bind-mounted at this path by the orchestrator
# (Coolify persistent storage). Build does NOT bake it in — see README.
ENV CITY_RATING_EMBEDDINGS=/app/data/external/embeddings.npz
ENV CITY_RATING_DESCRIPTIONS=/app/app/src/data/generated-descriptions.json
ENV CITY_RATING_LIVECAMS=/app/app/src/data/livecams.json
ENV FASTEMBED_CACHE_DIR=/opt/fastembed-cache
ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV MCP_PATH=/mcp
# Auth defaults: required in prod. Set MCP_AUTH_REQUIRED=false for unauthenticated
# local dev. NOCODB_API_URL / NOCODB_API_TOKEN / NOCODB_API_KEYS_TABLE_ID must
# be supplied at runtime (Coolify env vars).
ENV MCP_AUTH_REQUIRED=true
ENV MCP_KEY_REFRESH_SECONDS=300
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/mcp/healthz || exit 1

CMD ["city-rating-mcp"]
