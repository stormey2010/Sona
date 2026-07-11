FROM python:3.11-slim-bookworm

ARG APP_UID=1000
ARG APP_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/app/.cache/huggingface \
    STT_MODEL_DIR=/home/app/.cache/huggingface

RUN apt-get update \
    && apt-get install -y --no-install-recommends alsa-utils libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${APP_GID}" app && useradd --uid "${APP_UID}" --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p /app/recordings /home/app/.cache/huggingface /home/app/.cache/openwakeword \
    && chown -R app:app /app /home/app

USER app
CMD ["python", "-m", "app.service"]
