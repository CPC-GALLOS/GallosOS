# GallosOS Dev Container

This directory provides a standardized development container environment for GallosOS, adhering to the open [Development Containers specification](https://containers.dev/).

It provides a ready-to-code workspace after the initial image build and dependency installation. Local use requires a working container runtime; GitHub Codespaces supplies one. Tool versions may change between rebuilds because image tags and dependency versions are not locked.

---

## 🚀 Quickstart

### Visual Studio Code / Cursor
1. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) in VS Code.
2. Open this repository folder in VS Code.
3. When prompted, click **"Reopen in Container"** (or press `Ctrl+Shift+P` / `Cmd+Shift+P` and choose `Dev Containers: Reopen in Container`).
4. The container will build, mount the repository, provision the `.venv`, install all tools, and install pre-commit hooks automatically.

### GitHub Codespaces
1. On GitHub, navigate to the GallosOS repository.
2. Click the green **Code** button, select the **Codespaces** tab, and click **Create codespace on main**.
3. A cloud-hosted VS Code environment will start up within a few minutes with everything pre-configured.

### DevPod / CLI
You can also launch this environment using DevPod or the devcontainer CLI:

```sh
# Using @devcontainers/cli
npx @devcontainers/cli up --workspace-folder .
npx @devcontainers/cli exec --workspace-folder . /bin/bash
```

---

## 🛠️ What's Included

| Component | Tool / Version | Purpose |
| :--- | :--- | :--- |
| **Base OS** | Ubuntu 24.04 LTS (Noble) | Mirrors the exact Live ISO build and target system environment |
| **Python** | Python 3.12 + `uv` | Fast package management and runtime daemon development |
| **Python QA** | `ruff`, `pytest`, `jsonschema` | Linting, formatting, schema validation, and unit tests |
| **Git Hooks** | `pre-commit` | Automatic Conventional Commits and formatting checks on commit |
| **Shell QA** | `shellcheck` | Static analysis for `build/scripts/*.sh` and helper scripts |
| **Docker-in-Docker** | Docker 27+ engine & CLI | Allows running `make -C build iso` directly within the container |
| **ISO Tools** | `squashfs-tools`, `xorriso`, `mtools`, `dosfstools` | Tools to inspect and debug Live ISO filesystem structures |

---

## ✅ Pre-Flight Verification

Once inside the container, verify your environment by running:

```sh
./scripts/check.sh
```

This runs Ruff, formatting checks, the Pytest suite (199+ tests), ShellCheck, TOML schema validation, and Conventional Commits checks.
