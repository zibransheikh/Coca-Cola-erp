FROM python:3.11-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency manifest first so this layer caches across code-only changes.
COPY pyproject.toml ./
RUN uv sync --no-install-project

COPY . .

RUN chmod +x docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
