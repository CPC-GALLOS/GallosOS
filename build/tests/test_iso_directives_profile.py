"""Build-pipeline argument tests for selecting the ISO fallback directives."""

import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def make_dry_run(*variables: str) -> str:
    result = subprocess.run(
        [
            "make",
            "-n",
            "-C",
            str(REPO_ROOT / "build"),
            "iso",
            "CONTAINER_ENGINE=echo",
            *variables,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_makefile_forwards_an_explicit_runtime_profile() -> None:
    output = make_dry_run("DIRECTIVES_PROFILE=examples/custom.gallos.toml")

    assert (
        'bash scripts/run-pipeline.sh "profiles/universal.build.toml" "examples/custom.gallos.toml"'
    ) in output


def test_makefile_leaves_runtime_profile_unset_by_default() -> None:
    output = make_dry_run()

    assert 'bash scripts/run-pipeline.sh "profiles/universal.build.toml" ""' in output


def test_makefile_forwards_build_time_remote_policy_url() -> None:
    output = make_dry_run("REMOTE_POLICY_URL=https://policies.example.org/gallos.toml")

    assert '"https://policies.example.org/gallos.toml"' in output


def test_makefile_forwards_grub_password_without_expanding_hash() -> None:
    output = make_dry_run("GALLOS_GRUB_PASSWORD_HASH=grub.pbkdf2.sha512.10000.AA.BB")
    assert "--env GALLOS_GRUB_PASSWORD_HASH" in output
    assert "grub.pbkdf2.sha512.10000.AA.BB" not in output


def test_bios_core_includes_password_authentication() -> None:
    script = (REPO_ROOT / "build/scripts/build-iso.sh").read_text()
    modules = script.split("grub-mkimage", 1)[1].split("# casper-md5check", 1)[0]
    assert "password_pbkdf2" in modules


@pytest.mark.parametrize(
    "value", ["", "grub.pbkdf2.sha512.bad", "grub.pbkdf2.sha512.1.AA.BB;reboot"]
)
def test_reject_malformed_grub_hash_before_build(value: str) -> None:
    helper = REPO_ROOT / "build/scripts/lib-grub.sh"
    result = subprocess.run(
        ["bash", "-c", 'source "$1"; require_grub_password_hash "$2"', "bash", str(helper), value],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "valid GRUB PBKDF2 hash" in result.stderr


def test_accept_valid_grub_hash() -> None:
    helper = REPO_ROOT / "build/scripts/lib-grub.sh"
    value = "grub.pbkdf2.sha512.10000." + "AA" * 64 + "." + "BB" * 64
    result = subprocess.run(
        ["bash", "-c", 'source "$1"; require_grub_password_hash "$2"', "bash", str(helper), value],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_copy_helper_uses_neutral_profile_when_no_override_is_selected() -> None:
    source_helper = REPO_ROOT / "build/scripts/lib-directives.sh"
    with tempfile.TemporaryDirectory() as temp_dir:
        staging_dir = Path(temp_dir) / "staging"
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; copy_directives_profile "$2" "$3"',
                "bash",
                str(source_helper),
                str(REPO_ROOT / "examples/neutral.gallos.toml"),
                str(staging_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (staging_dir / "gallos/config/baseline/baseline.gallos.toml").read_bytes() == (
            REPO_ROOT / "examples/neutral.gallos.toml"
        ).read_bytes()


def test_copy_helper_uses_selected_runtime_profile() -> None:
    source_helper = REPO_ROOT / "build/scripts/lib-directives.sh"
    custom_profile = REPO_ROOT / "examples/maratona-sbc.gallos.toml"
    with tempfile.TemporaryDirectory() as temp_dir:
        staging_dir = Path(temp_dir) / "staging"
        subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; copy_directives_profile "$2" "$3"',
                "bash",
                str(source_helper),
                str(custom_profile),
                str(staging_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        assert (
            staging_dir / "gallos/config/baseline/baseline.gallos.toml"
        ).read_bytes() == custom_profile.read_bytes()


def test_copy_helper_injects_https_policy_url() -> None:
    source_helper = REPO_ROOT / "build/scripts/lib-directives.sh"
    with tempfile.TemporaryDirectory() as temp_dir:
        staging_dir = Path(temp_dir) / "staging"
        subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; copy_remote_policy_url "$2" "$3"',
                "bash",
                str(source_helper),
                "https://policies.example.org/gallos.toml",
                str(staging_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        assert (staging_dir / "gallos/config/remote-policy-url.txt").read_text(
            encoding="utf-8"
        ) == "https://policies.example.org/gallos.toml\n"
