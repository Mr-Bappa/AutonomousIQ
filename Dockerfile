FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY libs ./libs
COPY apps ./apps
COPY migrations ./migrations
COPY alembic.ini ./

RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000
