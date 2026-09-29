# GallosOS containerized build pipeline (docs/BUILD_SYSTEM.md).
# Run from build/: `make iso CONFIG=profiles/universal.build.toml`
# Optionally select an ISO fallback policy with DIRECTIVES_PROFILE=<repo-relative .gallos.toml>.
# Optionally embed its trusted update source with REMOTE_POLICY_URL=https://...

CONTAINER_ENGINE ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

ifeq ($(strip $(CONTAINER_ENGINE)),)
$(error Neither 'podman' nor 'docker' was found in PATH. Please install Podman or Docker to build GallosOS.)
endif

IMAGE := gallos-builder
CONFIG ?= profiles/universal.build.toml
DIRECTIVES_PROFILE ?=
REMOTE_POLICY_URL ?=
REPO_ROOT := $(abspath ..)

.PHONY: image iso clean

image:
	$(CONTAINER_ENGINE) build -t $(IMAGE) -f Containerfile .

iso: image
	$(CONTAINER_ENGINE) run --rm --privileged \
		--security-opt label=disable \
		-v $(REPO_ROOT):/repo \
		-w /repo/build \
		$(IMAGE) \
		bash scripts/run-pipeline.sh "$(CONFIG)" "$(DIRECTIVES_PROFILE)" "$(REMOTE_POLICY_URL)"

clean:
	command -v podman >/dev/null 2>&1 && podman unshare rm -rf output/ 2>/dev/null || rm -rf output/
