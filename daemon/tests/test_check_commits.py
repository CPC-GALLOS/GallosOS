"""Unit tests for Conventional Commits verification logic in scripts/check_commits.py."""

import pytest
from scripts.check_commits import ALLOWED_TYPES, validate_commit_message


@pytest.mark.parametrize("commit_type", sorted(ALLOWED_TYPES))
def test_valid_commit_types(commit_type: str) -> None:
    msg = f"{commit_type}: add something useful"
    valid, reason = validate_commit_message(msg)
    assert valid is True
    assert reason == ""


@pytest.mark.parametrize(
    "msg",
    [
        "feat(daemon): implement dynamic reload",
        "fix(ci): quote ShellCheck arguments",
        "docs(anti-cheat): document network filtering",
        "build(deps): bump ruff to 0.9.9",
        "refactor(desktop,daemon): split session gate",
        "feat(storage/casper): add overlayfs persistent partition",
    ],
)
def test_valid_scoped_commits(msg: str) -> None:
    valid, reason = validate_commit_message(msg)
    assert valid is True
    assert reason == ""


def test_valid_breaking_change_syntax() -> None:
    msg = "feat(daemon)!: remove legacy IPC command protocol"
    valid, reason = validate_commit_message(msg)
    assert valid is True
    assert reason == ""


def test_valid_multiline_commit() -> None:
    msg = (
        "feat(network): configure nftables rules\n"
        "\n"
        "Detailed explanation of why nftables rules are configured\n"
        "with specific port isolation.\n"
        "\n"
        "BREAKING CHANGE: closed legacy ports 8080-8088."
    )
    valid, reason = validate_commit_message(msg)
    assert valid is True
    assert reason == ""


def test_invalid_missing_blank_line_between_header_and_body() -> None:
    msg = "feat(network): configure nftables rules\nDirectly following body without empty line."
    valid, reason = validate_commit_message(msg)
    assert valid is False
    assert "Missing blank line" in reason


@pytest.mark.parametrize(
    ("msg", "expected_err_substring"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("WIP: not finished", "Invalid commit type"),
        ("update: several files", "Invalid commit type"),
        ("feat:", "Expected format"),
        ("feat: ", "Expected format"),
        ("random commit without prefix", "Expected format"),
        ("feat (daemon): space between type and scope", "Expected format"),
    ],
)
def test_invalid_commit_headers(msg: str, expected_err_substring: str) -> None:
    valid, reason = validate_commit_message(msg)
    assert valid is False
    assert expected_err_substring.lower() in reason.lower()


def test_merge_and_revert_commits_handled() -> None:
    merge_msg = "Merge branch 'main' into feature/network"
    valid, reason = validate_commit_message(merge_msg, strict=False)
    assert valid is True
    assert reason == ""

    # In strict mode, merge commits are disallowed
    valid_strict, _ = validate_commit_message(merge_msg, strict=True)
    assert valid_strict is False
