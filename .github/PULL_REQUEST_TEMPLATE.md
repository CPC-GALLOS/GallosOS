## What changed

<!-- Describe the problem and resulting behavior. Link the issue or specification, if available. -->

## Validation

<!-- List the commands run and their results. Explain any checks that were blocked or not run. -->

For runtime or hardware changes, identify the ISO / commit and test environment (VM or physical hardware). Record each relevant result as **PASS**, **FAIL**, **BLOCKED**, or **NOT TESTED**, with logs or screenshots where applicable. Repository checks alone do not establish boot, desktop, or physical hardware acceptance.

## Checklist

- [ ] `make check` (`./scripts/check.sh`) passes, or blocked checks are explained above.
- [ ] The PR title and commit messages follow Conventional Commits.
- [ ] Each commit is one independently reviewable logical change.
- [ ] Documentation, examples, and schemas match the changed behavior, where applicable.
