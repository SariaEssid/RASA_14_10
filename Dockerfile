# ====================================
# Stage 1: Builder
# ====================================
FROM python:3.9-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    autoconf \
    automake \
    libtool \
    pkg-config \
    libffi-dev \
    libpq-dev \
    git \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .

# Upgrade pip tools
RUN pip install --upgrade pip setuptools wheel

# Build wheels (CPU-only PyTorch)
RUN pip wheel --wheel-dir=/wheels \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# Build llama-cpp-python WITHOUT AVX2
RUN CMAKE_ARGS="-DLLAMA_AVX=ON -DLLAMA_AVX2=OFF" \
    pip wheel --wheel-dir=/wheels llama-cpp-python==0.3.16

# Copy source code
COPY . .

# ====================================
# Stage 2: Final minimal image
# ====================================
FROM python:3.9-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 2003 esprit && useradd -m -u 2003 -g esprit esprit

WORKDIR /app

# Copy wheels and install dependencies
COPY --from=builder /wheels /wheels
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && pip install --no-cache-dir --no-index --find-links=/wheels llama-cpp-python==0.3.16 \
    && python -c "import pkg_resources; print('pkg_resources OK')" \
    && rm -rf /wheels

# Copy application
COPY --from=builder /app /app

# Fix permissions
RUN chown -R esprit:esprit /app

USER esprit

# Environment variables to prevent illegal instruction crashes
ENV MKL_DEBUG_CPU_TYPE=5
ENV OMP_NUM_THREADS=4
ENV OPENBLAS_CORETYPE=generic

# Add user-local bin to PATH
ENV PATH="/home/esprit/.local/bin:${PATH}"

# Default (override in Kubernetes)
# CMD ["python", "your_app.py"]