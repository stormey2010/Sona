FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/app/.cache/huggingface \
    STT_MODEL_DIR=/home/app/.cache/huggingface

RUN apt-get update \
    && apt-get install -y --no-install-recommends alsa-utils libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN mkdir -p /app/recordings /home/app/.cache/huggingface \
    && chown -R app:app /app /home/app

USER app
CMD ["python", "-m", "app.service"]

