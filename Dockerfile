# syntax=docker/dockerfile:1

# Ubuntu 24.04 je ista baza koju koriste snap paket (base: core24) i Ubuntu
# Core 24 na Raspberry Pi-u, pa se aplikacija u sve tri isporuke izvodi nad
# istim skupom sistemskih biblioteka.
FROM ubuntu:24.04 AS base

ARG TARGETARCH=amd64

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Virtualno okruzenje s pristupom sistemskim paketima: tkinter dolazi iz
# distribucijskog paketa python3-tk (gui cilj), ostale ovisnosti iz pipa.
RUN python3 -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt ./

# Na amd64 se torch instalira iz CPU-only indeksa (bez CUDA paketa, oko 2 GB
# manja slika). Na arm64 je sluzbeni PyPI wheel ionako CPU-only.
RUN if [ "$TARGETARCH" = "amd64" ]; then \
        pip install --no-cache-dir \
            --index-url https://download.pytorch.org/whl/cpu torch ; \
    fi \
    && pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY app ./app
COPY tests ./tests


# --------------------------------------------------------------------------
# Cilj "web": headless HTTP servis. Ovo je slika koja se vrti u pozadini i
# jedina varijanta koja radi bez grafickog sustava (posluzitelj, Ubuntu Core).
# --------------------------------------------------------------------------
FROM base AS web

ENV MEDLEX_DATA_DIR=/data \
    HF_HOME=/data/hf-cache \
    MEDLEX_HOST=0.0.0.0 \
    MEDLEX_PORT=8080

RUN useradd --create-home --uid 10001 medlex \
    && mkdir -p /data/hf-cache /data/exports \
    && chown -R medlex:medlex /data

USER medlex

# Model (~500 MB) se moze ugraditi u sliku (PRELOAD_MODEL=true) kako bi
# kontejner radio potpuno offline, ili se preuzima pri prvoj analizi.
ARG PRELOAD_MODEL=false
RUN if [ "$PRELOAD_MODEL" = "true" ]; then \
        python -c "from app.ner import MODEL_NAME; \
from transformers import AutoModelForTokenClassification, AutoTokenizer; \
AutoTokenizer.from_pretrained(MODEL_NAME); \
AutoModelForTokenClassification.from_pretrained(MODEL_NAME)" ; \
    fi

VOLUME ["/data"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os, urllib.request as u; \
port = os.environ.get('MEDLEX_PORT', '8080'); \
u.urlopen('http://127.0.0.1:' + port + '/healthz', timeout=3)" || exit 1

CMD ["python", "main.py", "--web"]


# --------------------------------------------------------------------------
# Cilj "gui": izvorno Tkinter sucelje koje se prikazuje preko X11 servera na
# hostu (VcXsrv na Windowsima, lokalni X server na Linuxu).
# --------------------------------------------------------------------------
FROM base AS gui

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        libx11-6 \
        libxext6 \
        libxrender1 \
        libxft2 \
        libxss1 \
        fonts-dejavu-core \
        x11-apps \
        xauth \
    && rm -rf /var/lib/apt/lists/*

ENV MEDLEX_DATA_DIR=/data \
    HF_HOME=/data/hf-cache \
    DISPLAY=host.docker.internal:0

RUN mkdir -p /data/hf-cache /data/exports

CMD ["python", "main.py"]
