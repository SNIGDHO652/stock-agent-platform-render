FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/app

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /home/app app

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts

RUN pip install --upgrade pip && pip install . && chmod +x ./scripts/start-render.sh && mkdir -p /home/app && chown -R app:app /home/app

USER app

EXPOSE 8000

CMD ["sh", "./scripts/start-render.sh"]
