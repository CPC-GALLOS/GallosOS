#!/usr/bin/env bash
# ==============================================================================
# GallosOS Codebase Quality & Lint Verification Suite
# Runs Python linting (Ruff), formatting checks, unit tests (Pytest),
# Shell script validation (ShellCheck), TOML syntax verification,
# and Conventional Commits validation.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

# Color codes for clean output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   GallosOS Quality Assurance & Pre-Flight Checks     ${NC}"
echo -e "${BLUE}======================================================${NC}"

FAILED=0

# 1. Python Linting (Ruff)
echo -e "\n${YELLOW}[1/6] Running Ruff linter (code style, complexity, security)...${NC}"
if ruff check .; then
    echo -e "${GREEN}✓ Ruff check passed.${NC}"
else
    echo -e "${RED}✗ Ruff check failed.${NC}"
    FAILED=1
fi

# 2. Python Code Formatting (Ruff Format)
echo -e "\n${YELLOW}[2/6] Checking Python formatting (Ruff format)...${NC}"
if ruff format --check .; then
    echo -e "${GREEN}✓ Python formatting check passed.${NC}"
else
    echo -e "${RED}✗ Python formatting check failed. Run 'ruff format .' to fix.${NC}"
    FAILED=1
fi

# 3. Python Unit Tests (Pytest)
echo -e "\n${YELLOW}[3/6] Running Python unit tests (Pytest)...${NC}"
if python3 -m pytest daemon/tests/ -v; then
    echo -e "${GREEN}✓ All Pytest unit tests passed.${NC}"
else
    echo -e "${RED}✗ Pytest unit tests failed.${NC}"
    FAILED=1
fi

# 4. Shell Scripts (ShellCheck)
echo -e "\n${YELLOW}[4/6] Running ShellCheck on build scripts...${NC}"
if command -v shellcheck &>/dev/null; then
    if shellcheck build/scripts/*.sh; then
        echo -e "${GREEN}✓ ShellCheck passed on all build scripts.${NC}"
    else
        echo -e "${RED}✗ ShellCheck found issues in build scripts.${NC}"
        FAILED=1
    fi
else
    echo -e "${YELLOW}⚠ ShellCheck not found on host. Skipping.${NC}"
fi

# 5. TOML Schema & Formatting (Taplo if available, fallback to validate_toml.py)
echo -e "\n${YELLOW}[5/6] Checking TOML files...${NC}"
if command -v taplo &>/dev/null; then
    if taplo check; then
        echo -e "${GREEN}✓ Taplo TOML check passed.${NC}"
    else
        echo -e "${RED}✗ Taplo TOML check failed.${NC}"
        FAILED=1
    fi
else
    echo -e "${YELLOW}ℹ Taplo not installed. Validating TOML files via scripts/validate_toml.py...${NC}"
    if python3 scripts/validate_toml.py; then
        echo -e "${GREEN}✓ TOML syntax validation passed.${NC}"
    else
        echo -e "${RED}✗ TOML syntax validation failed.${NC}"
        FAILED=1
    fi
fi

# 6. Conventional Commits (Commit History / Message Validation)
echo -e "\n${YELLOW}[6/6] Validating Conventional Commits...${NC}"
if python3 scripts/check_commits.py; then
    echo -e "${GREEN}✓ Conventional Commits validation passed.${NC}"
else
    echo -e "${RED}✗ Conventional Commits validation failed.${NC}"
    FAILED=1
fi

echo -e "\n${BLUE}======================================================${NC}"
if [ ${FAILED} -eq 0 ]; then
    echo -e "${GREEN}🎉 All quality checks passed successfully!${NC}"
    echo -e "${BLUE}======================================================${NC}"
    exit 0
else
    echo -e "${RED}❌ Some quality checks failed. Please resolve the errors above.${NC}"
    echo -e "${BLUE}======================================================${NC}"
    exit 1
fi
