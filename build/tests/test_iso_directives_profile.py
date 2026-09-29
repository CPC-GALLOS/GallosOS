"""Build-pipeline argument tests for selecting the ISO fallback directives."""

import subprocess
import tempfile
from pathlib import Path

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
