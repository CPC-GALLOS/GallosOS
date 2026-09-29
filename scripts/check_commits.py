#!/usr/bin/env python3
"""Validates git commit messages according to the Conventional Commits specification.

Specification: https://www.conventionalcommits.org/
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ALLOWED_TYPES = {
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "revert",
    "style",
    "test",
}

HEADER_RE = re.compile(
    r"^(?P<type>[a-zA-Z0-9]+)"
    r"(?:\((?P<scope>[^()\r\n]+)\))?"
    r"(?P<breaking>!)?"
    r": (?P<subject>\S.*)$"
)


def is_merge_or_revert(line: str) -> bool:
    """Check if header matches git automated merge or revert commit formatting."""
    lower = line.lower()
    return lower.startswith("merge ") or line.startswith('Revert "')


def validate_commit_message(msg: str, strict: bool = False) -> tuple[bool, str]:
    """Validate a commit message against Conventional Commits 1.0.0.

    Returns:
        tuple of (is_valid, error_reason).
    """
    clean_msg = msg.strip()
    if not clean_msg:
        return False, "Commit message cannot be empty."

    lines = clean_msg.splitlines()
    header = lines[0].strip()

    if not strict and is_merge_or_revert(header):
        return True, ""

    match = HEADER_RE.match(header)
    if not match:
        return False, (
            f"Header '{header}' does not match Conventional Commits format.\n"
            "Expected format: '<type>(<optional-scope>): <subject>' (e.g. 'feat: add feature')."
        )

    commit_type = match.group("type").lower()
    if commit_type not in ALLOWED_TYPES:
        allowed_list = ", ".join(sorted(ALLOWED_TYPES))
        return False, (f"Invalid commit type '{commit_type}'.\nAllowed types are: {allowed_list}")

    if len(lines) > 1 and lines[1].strip() != "":
        return False, (
            "Missing blank line between commit header and body (Conventional Commits rule 6)."
        )

    return True, ""


def get_commits_from_range(rev_range: str) -> list[tuple[str, str]]:
    """Retrieve commits in a given revision range using git log."""
    cmd = ["git", "log", rev_range, "--format=%H%x00%B%x00"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []

    parts = result.stdout.split("\x00")
    commits = []
    for i in range(0, len(parts) - 1, 2):
        sha = parts[i].strip()
        body = parts[i + 1]
        if sha and body:
            commits.append((sha, body))
    return commits


def get_last_commits(count: int = 1) -> list[tuple[str, str]]:
    """Retrieve the last N commits from HEAD."""
    cmd = ["git", "log", f"-n{count}", "--format=%H%x00%B%x00"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []

    parts = result.stdout.split("\x00")
    commits = []
    for i in range(0, len(parts) - 1, 2):
        sha = parts[i].strip()
        body = parts[i + 1]
        if sha and body:
            commits.append((sha, body))
    return commits


def resolve_ci_range() -> str | None:
    """Determine the commit range to inspect within a CI/CD environment."""
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    base_ref = os.environ.get("GITHUB_BASE_REF", "")

    if event_name == "pull_request" and base_ref:
        check_ref = subprocess.run(
            ["git", "rev-parse", "--verify", f"origin/{base_ref}"],
            capture_output=True,
            check=False,
        )
        target = f"origin/{base_ref}" if check_ref.returncode == 0 else base_ref
        return f"{target}..HEAD"

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and Path(event_path).is_file():
        try:
            with open(event_path, encoding="utf-8") as f:
                event_data = json.load(f)
            before = event_data.get("before")
            after = event_data.get("after")
            if before and after and not before.startswith("00000000"):
                return f"{before}..{after}"
        except (json.JSONDecodeError, OSError):
            return None

    return None


def get_default_commits() -> list[tuple[str, str]]:
    """Retrieve commits ahead of upstream, or fallback to the last commit."""
    upstream_check = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if upstream_check.returncode == 0:
        upstream = upstream_check.stdout.strip()
        diff_commits = get_commits_from_range(f"{upstream}..HEAD")
        if diff_commits:
            return diff_commits

    return get_last_commits(1)


def resolve_commits(args: argparse.Namespace) -> list[tuple[str, str]]:
    """Determine the list of (sha, commit_message) pairs to validate."""
    if args.msg:
        return [("CLI", args.msg)]

    if args.file:
        file_path = Path(args.file)
        if not file_path.is_file():
            print(f"[commit-check] Error: File '{args.file}' not found.", file=sys.stderr)
            return []
        return [("FILE", file_path.read_text(encoding="utf-8"))]

    if args.ci:
        ci_range = resolve_ci_range()
        if ci_range:
            commits = get_commits_from_range(ci_range)
            if commits:
                return commits
        return get_last_commits(1)

    if args.range:
        return get_commits_from_range(args.range)

    if args.last:
        return get_last_commits(args.last)

    return get_default_commits()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate git commit messages against Conventional Commits 1.0.0."
    )
    parser.add_argument("--msg", type=str, help="Commit message string to validate.")
    parser.add_argument("--file", type=str, help="Path to commit message file.")
    parser.add_argument(
        "--range", type=str, help="Git revision range to validate (e.g. 'origin/main..HEAD')."
    )
    parser.add_argument(
        "--last", type=int, default=0, help="Validate the last N commits from HEAD."
    )
    parser.add_argument(
        "--ci", action="store_true", help="Auto-detect commit range in GitHub Actions CI."
    )
    parser.add_argument(
        "--strict", action="store_true", help="Strict mode (disallow merge/revert headers)."
    )
    return parser.parse_args()


def main() -> int:
    """Main CLI entrypoint."""
    args = parse_args()
    commits = resolve_commits(args)

    if not commits:
        print("[commit-check] No commits found to validate.")
        return 0

    failed = False
    for sha, msg in commits:
        valid, reason = validate_commit_message(msg, strict=args.strict)
        first_line = msg.strip().splitlines()[0] if msg.strip() else "<empty>"
        prefix = f"[{sha[:7]}]" if len(sha) >= 7 and sha not in ("CLI", "FILE") else f"[{sha}]"

        if valid:
            print(f"[commit-check] ✓ {prefix} {first_line}")
        else:
            print(f"[commit-check] ✗ {prefix} {first_line}", file=sys.stderr)
            print(f"               Error: {reason}", file=sys.stderr)
            failed = True

    if failed:
        print(
            "\n[commit-check] ❌ One or more commit messages violate Conventional Commits.\n"
            "See https://www.conventionalcommits.org/ for details.",
            file=sys.stderr,
        )
        return 1

    print(f"\n[commit-check] ✓ All {len(commits)} evaluated commit(s) follow Conventional Commits.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(130)
