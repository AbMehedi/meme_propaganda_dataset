# ============================================================================
# Bangla Meme Propaganda Dataset — Pipeline Container
# ============================================================================
# Base: NVIDIA CUDA 12.4 runtime on Ubuntu 22.04
# Provides GPU-accelerated EasyOCR + PyTorch out of the box.
# ============================================================================

FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

# Prevent interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-venv \
        python3.11-dev \
        python3-pip \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# Make python3.11 the default `python` and `python3`
RUN update-alternatives --install /usr/bin/python  python  /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Upgrade pip
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

# ── Python dependencies ──────────────────────────────────────────────────────
# Step 1: Install CUDA-enabled PyTorch FIRST (before EasyOCR pulls CPU torch)
RUN pip install --no-cache-dir \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu124

# Step 2: Install remaining project dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# ── Working directory ────────────────────────────────────────────────────────
WORKDIR /app

# EasyOCR downloads models to ~/.EasyOCR on first run.
# This path is mapped to a named volume in docker-compose.yml so models
# persist across container rebuilds.
ENV EASYOCR_MODULE_PATH=/root/.EasyOCR

# Default Ollama host for container-to-container networking.
# Overridden to http://localhost:11434 when running outside Docker.
ENV OLLAMA_HOST=http://ollama:11434
 
# Expose annotation UI web port
EXPOSE 5000

# Keep container alive for interactive `docker compose exec` usage
CMD ["tail", "-f", "/dev/null"]
