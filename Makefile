# Root developer entry points. The build pipeline remains in build/Makefile.
.DEFAULT_GOAL := help

PYTHON ?= python3
PYTEST_ARGS ?=
ISO ?= build/output/gallosos-universal-amd64.iso
QEMU_ARGS ?= --smoke

.PHONY: help check test lint format fix validate iso qemu-test clean clean-build

help:
	@printf '%s\n' \
		'GallosOS developer tasks (run from the repository root):' \
		'  make check       Run the full QA suite via scripts/check.sh' \
		'  make test        Run daemon and build unit tests (PYTEST_ARGS=...)' \
		'  make lint        Check Python and shell scripts with Ruff and ShellCheck' \
		'  make format      Format Python files with Ruff' \
		'  make fix         Apply safe Ruff lint fixes' \
		'  make validate    Validate TOML syntax and organizer directives schemas' \
		'  make iso         Delegate to build/Makefile (existing build variables apply)' \
		'  make qemu-test   Boot an existing ISO (ISO=... QEMU_ARGS="--uefi --smoke")' \
		'  make clean       Remove development caches; preserve .venv and build output' \
		'  make clean-build Remove build/output via build/Makefile'

check:
	./scripts/check.sh

test:
	$(PYTHON) -m pytest daemon/tests/ build/tests/ -v $(PYTEST_ARGS)

lint:
	ruff check .
	shellcheck build/scripts/*.sh scripts/*.sh .devcontainer/*.sh

format:
	ruff format .

fix:
	ruff check --fix .

validate:
	$(PYTHON) scripts/validate_toml.py

iso:
	$(MAKE) -C build iso

qemu-test:
	bash build/scripts/test-iso-qemu.sh --iso "$(ISO)" $(QEMU_ARGS)

clean:
	rm -rf -- .pytest_cache .ruff_cache
	find daemon scripts build/tests -type d -name __pycache__ -prune -exec rm -rf -- {} +

clean-build:
	$(MAKE) -C build clean
