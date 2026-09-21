# Release process

## Versioning

Versions are derived from git tags by [hatch-vcs](https://github.com/ofek/hatch-vcs)
(`dynamic = ["version"]`, `local_scheme = "no-local-version"`). There is no version
to edit in `pyproject.toml`:

- A release tag `vX.Y.Z` produces version `X.Y.Z`.
- Commits after the latest tag produce `X.Y.(Z+1).devN` automatically.

## Continuous dev releases (Test PyPI)

Every push to `main` with a green CI run triggers `release.yaml`
(`workflow_run`), which builds the package and uploads the current dev
version to <https://test.pypi.org/project/sqlastack-core/>. Nothing to do
manually.

## Cutting a release

1. Make sure `main` is green (CI badge / `gh run list`).
2. Create a GitHub release with a new tag (this triggers the PyPI upload):

       gh release create vX.Y.Z --generate-notes

3. Watch the "Build & upload PyPI package" workflow; verify the version
   appears on <https://pypi.org/project/sqlastack-core/>.

## One-time setup (already done? check before first release)

- pypi.org and test.pypi.org: project registered with a *Trusted Publisher*
  (GitHub repo `bluedynamics/sqlastack-core`, workflow `release.yaml`,
  environments `release-pypi` / `release-test-pypi`).
- GitHub repo settings → Environments: `release-pypi` and `release-test-pypi`
  exist (no secrets needed — Trusted Publishing uses OIDC).

## Troubleshooting

- Upload skipped/failed: re-run via `gh workflow run release.yaml` (the
  `workflow_dispatch` trigger publishes the current main state to Test PyPI).
- `workflow_run` did not fire: the CI workflow name must be exactly `CI`.
