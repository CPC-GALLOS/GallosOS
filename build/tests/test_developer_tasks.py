"""Root task orchestration, argument forwarding, and cleanup boundaries."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_make(directory: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "--no-print-directory", "-C", str(directory), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def copy_runner(directory: Path) -> None:
    shutil.copyfile(REPO_ROOT / "Makefile", directory / "Makefile")


def test_default_help_does_not_require_a_container_engine() -> None:
    result = run_make(REPO_ROOT, "CONTAINER_ENGINE=")

    assert result.returncode == 0, result.stderr
    for target in ("check", "test", "lint", "format", "iso", "qemu-test", "clean-build"):
        assert target in result.stdout


@pytest.mark.parametrize("exit_code", [0, 7])
def test_check_propagates_quality_gate_failure(tmp_path: Path, exit_code: int) -> None:
    copy_runner(tmp_path)
    (tmp_path / "scripts").mkdir()
    script = tmp_path / "scripts/check.sh"
    script.write_text(f"#!/bin/sh\nexit {exit_code}\n")
    script.chmod(0o755)

    result = run_make(tmp_path, "check", "CONTAINER_ENGINE=")

    assert (result.returncode == 0) == (exit_code == 0), result.stderr


def test_iso_forwards_existing_build_variables_without_exposing_grub_hash() -> None:
    result = run_make(
        REPO_ROOT,
        "-n",
        "iso",
        "CONTAINER_ENGINE=echo",
        "CONFIG=profiles/custom.build.toml",
        "DIRECTIVES_PROFILE=examples/club.gallos.toml",
        "GALLOS_GRUB_PASSWORD_HASH=grub.pbkdf2.sha512.10000.AA.BB",
    )

    assert result.returncode == 0, result.stderr
    assert '"profiles/custom.build.toml" "examples/club.gallos.toml"' in result.stdout
    assert "--env GALLOS_GRUB_PASSWORD_HASH" in result.stdout
    assert "grub.pbkdf2.sha512.10000.AA.BB" not in result.stdout


def test_qemu_preserves_iso_path_and_firmware_options(tmp_path: Path) -> None:
    copy_runner(tmp_path)
    scripts = tmp_path / "build/scripts"
    scripts.mkdir(parents=True)
    (scripts / "test-iso-qemu.sh").write_text('#!/bin/sh\nprintf "<%s>\\n" "$@"\n')

    result = run_make(
        tmp_path,
        "qemu-test",
        "ISO=build/output/test image.iso",
        "QEMU_ARGS=--secure-boot --smoke",
    )

    assert result.returncode == 0, result.stderr
    assert "<--iso>\n<build/output/test image.iso>\n<--secure-boot>\n<--smoke>" in result.stdout


def test_clean_preserves_virtualenv_reference_trees_and_build_output(tmp_path: Path) -> None:
    copy_runner(tmp_path)
    caches = [
        ".pytest_cache/state",
        ".ruff_cache/state",
        "daemon/src/__pycache__/module.pyc",
        "scripts/__pycache__/module.pyc",
        "build/tests/__pycache__/module.pyc",
    ]
    preserved = [
        ".venv/lib/__pycache__/module.pyc",
        "HuronOS/__pycache__/module.pyc",
        "build/output/rootfs/usr/__pycache__/module.pyc",
        "build/output/test.iso",
        "daemon/src/main.py",
    ]
    for relative in caches + preserved:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("keep or remove as specified\n")
    (tmp_path / "daemon/reference-link").symlink_to(tmp_path / "HuronOS", target_is_directory=True)

    result = run_make(tmp_path, "clean", "CONTAINER_ENGINE=")

    assert result.returncode == 0, result.stderr
    assert all(not (tmp_path / relative).exists() for relative in caches)
    assert all((tmp_path / relative).is_file() for relative in preserved)


def test_clean_build_delegates_to_the_existing_build_target(tmp_path: Path) -> None:
    copy_runner(tmp_path)
    (tmp_path / "build").mkdir()
    (tmp_path / "build/Makefile").write_text("clean:\n\t@printf 'build-clean-called\\n'\n")

    result = run_make(tmp_path, "clean-build")

    assert result.returncode == 0, result.stderr
    assert "build-clean-called" in result.stdout
