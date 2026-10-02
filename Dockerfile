FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md LICENSE requirements-runtime.lock ./
COPY src ./src
RUN python -m pip install --no-cache-dir "build>=1.2,<2" \
    && python -m build --wheel

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-runtime.lock ./
RUN python -m pip install --no-cache-dir -r requirements-runtime.lock \
    && useradd --create-home --uid 10001 parallax
COPY --from=builder /build/dist/*.whl /tmp/wheels/
RUN python -m pip install --no-cache-dir --no-deps /tmp/wheels/*.whl \
    && rm -rf /tmp/wheels
USER parallax
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=4)"
CMD ["python", "-m", "uvicorn", "parallax_risk.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
