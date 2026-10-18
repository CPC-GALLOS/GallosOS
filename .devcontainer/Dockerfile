# GallosOS Development Container Dockerfile
# Based on Ubuntu 24.04 LTS (Noble) with Python 3.12, matching the Live ISO target.
FROM mcr.microsoft.com/devcontainers/base:1-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

# Copy uv and uvx binaries from official Astral image (multi-arch: amd64/arm64)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install host tools required for GallosOS development and validation:
# - shellcheck: lints build/scripts/*.sh and helper scripts
# - build-essential, git, curl, jq: standard build and development tooling
# - squashfs-tools, xorriso, mtools, dosfstools: tools for inspecting ISO files
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    shellcheck \
    build-essential \
    curl \
    git \
    jq \
    squashfs-tools \
    xorriso \
    mtools \
    dosfstools \
    && rm -rf /var/lib/apt/lists/*

# Keep development tools isolated from Ubuntu's externally managed Python.
ENV VIRTUAL_ENV=/opt/gallos-dev-tools
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
RUN uv venv --python /usr/bin/python3.12 "${VIRTUAL_ENV}" \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" \
    "ruff>=0.4" \
    "pytest>=8.0" \
    "jsonschema>=4.10" \
    "pre-commit>=3.5"

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
