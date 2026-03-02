FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip ffmpeg git \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra vibevoice

# vibevoice is not on PyPI; install from GitHub into the uv-managed venv
RUN uv pip install git+https://github.com/microsoft/VibeVoice.git

# Install pre-built flash-attn wheel (no compilation needed)
RUN uv pip install https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3+cu12torch2.5cxx11abiFALSE-cp311-cp311-linux_x86_64.whl

# Fetch voice .pt files (not included in the pip package)
RUN git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/VibeVoice.git /opt/VibeVoice \
    && cd /opt/VibeVoice && git sparse-checkout set demo/voices

COPY app/ app/
COPY templates/ templates/
COPY logo.jpg ./

EXPOSE 8025
ENV PORT=8025

CMD ["uv", "run", "python", "-m", "app.serve"]
