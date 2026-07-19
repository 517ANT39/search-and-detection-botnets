# ── build stage: генерация protobuf ──
FROM python:3.12-slim AS build
WORKDIR /build
RUN pip install --no-cache-dir grpcio-tools==1.66.1
COPY proto/ proto/
RUN mkdir -p analyzer/gen && \
    python -m grpc_tools.protoc -I proto \
      --python_out=analyzer/gen proto/traffic.proto && \
    touch analyzer/gen/__init__.py

# ── runtime stage ──
FROM python:3.12-slim AS runtime
WORKDIR /app
RUN groupadd -r analyzer && useradd -r -g analyzer analyzer

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analyzer/ analyzer/
COPY --from=build /build/analyzer/gen/ analyzer/gen/
COPY config.yaml .

RUN mkdir -p models && chown -R analyzer:analyzer /app
USER analyzer

ENTRYPOINT ["python", "-m", "analyzer.main"]
