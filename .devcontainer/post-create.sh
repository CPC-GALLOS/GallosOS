#!/usr/bin/env bash
# ==============================================================================
# GallosOS Dev Container Post-Creation Setup Hook
# Automatically provisions the workspace virtual environment (.venv),
# installs local dev dependencies, and configures Git / pre-commit hooks.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}==> [devcontainer] Setting up GallosOS development environment...${NC}"

# 1. Trust workspace in Git to avoid dubious ownership errors inside container
if command -v git &>/dev/null; then
    echo -e "${YELLOW}==> Configuring Git safe directory...${NC}"
    git config --global --add safe.directory "${REPO_ROOT}"
fi

# 2. Setup Python virtual environment (.venv) via uv
echo -e "${YELLOW}==> Configuring Python virtual environment (.venv)...${NC}"
if [ ! -d ".venv" ]; then
    uv venv --python /usr/bin/python3.12 .venv
fi

# 3. Install required dev packages into .venv
echo -e "${YELLOW}==> Installing dev dependencies into .venv...${NC}"
uv pip install --python .venv/bin/python ruff pytest jsonschema pre-commit

# 4. Install pre-commit hooks if this is a Git checkout
if git rev-parse --is-inside-work-tree &>/dev/null; then
    echo -e "${YELLOW}==> Installing pre-commit and commit-msg hooks...${NC}"
    .venv/bin/pre-commit install --install-hooks
fi

echo -e "${GREEN}==> GallosOS Dev Container is ready!${NC}"
echo -e "${BLUE}    Run './scripts/check.sh' to verify all quality checks.${NC}"
