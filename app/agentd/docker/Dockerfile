# Build with the repository root as context, for example:
# docker build -f docker/Dockerfile .
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app.py ./app.py
COPY agentd ./agentd

CMD ["python", "app.py"]
