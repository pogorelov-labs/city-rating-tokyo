# City-rating MCP server — multi-stage build.
#
# Stage 1 builds the per-station datamart by running scripts/build-datamart.py
# against NocoDB. Stage 2 builds embeddings from the (already committed)
# generated-descriptions.json. Stage 3 is the runtime image. Both artifacts
# are baked in so the runtime container has zero external dependencies
# beyond the pre-cached fastembed model.
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


# ---------- Stage 2: build embeddings + pre-cache fastembed model ----------
FROM python:${PYTHON_VERSION} AS embeddings

ARG EMBEDDING_MODEL
ENV FASTEMBED_CACHE_DIR=/opt/fastembed-cache

WORKDIR /build
RUN pip install --no-cache-dir fastembed numpy

COPY scripts/build-embeddings.py /build/scripts/build-embeddings.py
COPY app/src/data/generated-descriptions.json /build/app/src/data/generated-descriptions.json

# Builds data/embeddings.npz AND populates the fastembed cache so the
# runtime image can copy it instead of fetching at startup.
RUN mkdir -p /opt/fastembed-cache /build/data \
    && python3 scripts/build-embeddings.py --model "${EMBEDDING_MODEL}"


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

COPY --from=datamart   /build/data/station-datamart.json /app/data/station-datamart.json
COPY --from=embeddings /build/data/embeddings.npz        /app/data/embeddings.npz
COPY --from=embeddings /opt/fastembed-cache              /opt/fastembed-cache
COPY app/src/data/generated-descriptions.json            /app/app/src/data/generated-descriptions.json
COPY app/src/data/livecams.json                          /app/app/src/data/livecams.json

ENV CITY_RATING_DATAMART=/app/data/station-datamart.json
ENV CITY_RATING_EMBEDDINGS=/app/data/embeddings.npz
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
