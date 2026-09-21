# iname

CLI that renames files and directories to web-safe names. Zero runtime
dependencies, standard library only. Packaging, CI and publishing use Poetry.

## Layout

- `iname/rename.py` — all naming logic (`safe_stem`, `make_safe_path`, `rename_path`)
- `iname/cli.py` — argparse front end; reads a path argument or stdin
- `tests/` — pytest; `test_rename.py` for logic, `test_cli.py` for the CLI

## Development

```bash
poetry install                 # creates the venv and installs dev tools
poetry run pytest --cov=iname --cov-report=term-missing
poetry run ruff check .
poetry run ruff format .
```

CI runs ruff check, ruff format --check and pytest on Python 3.10–3.14
(Ubuntu) plus 3.12 on macOS and Windows. All must pass before merging.

Behaviour changes need a test first. Windows is in the matrix, so tests must
not assume `/` separators (use `Path(...).name`) and must skip anything that
creates a filename Windows forbids, such as one containing a newline.

## Version

The version lives only in `pyproject.toml`. `iname.__version__` reads it from
installed package metadata. Never edit a version string in `iname/__init__.py`
or in tests; tests compare against `iname.__version__`.

## Git workflow

Never commit directly to `main`. Every change, including docs and releases,
goes on a branch and lands through a pull request once CI is green:

```bash
git checkout main && git pull --rebase
git checkout -b <type>/<short-name>      # feat/, fix/, chore/, docs/, release/
# ... commit with Conventional Commits messages ...
git push -u origin <branch>
gh pr create --base main --fill
```

Merge with a merge commit so the branch history is preserved. Delete the
branch after merging.

## Release workflow

1. Start from an up-to-date `main` with a clean working tree.
2. Create a release branch: `git checkout -b release/vX.Y.Z`
3. Bump the version with Poetry, which edits `pyproject.toml`:
   `poetry version patch` | `minor` | `major`
4. In `CHANGELOG.md`, rename the `[Unreleased]` section to the new version
   with today's date, add a compare link at the bottom, and start a fresh
   empty `[Unreleased]` section above it. Format is Keep a Changelog.
5. Commit as `chore: release X.Y.Z`, push the branch, and open a PR.
6. Wait for CI to pass on every matrix job, then merge.
7. Tag the merge commit on `main`, not the branch, so the tag is reachable
   from `main` whatever the merge strategy:
   `git checkout main && git pull --rebase && git tag -a vX.Y.Z -m "iname X.Y.Z" && git push origin vX.Y.Z`
8. Create a GitHub Release from the tag using the changelog entry as notes:
   `gh release create vX.Y.Z --title "iname X.Y.Z" --notes-file <notes> --verify-tag`
9. Publishing the Release triggers `.github/workflows/publish.yml`, which builds
   with `poetry build` and uploads to PyPI via Trusted Publishing. No tokens
   are stored anywhere. To republish a tag manually:
   `gh workflow run publish.yml -f tag=vX.Y.Z`
10. Confirm on PyPI: `curl -s https://pypi.org/pypi/iname/json | python -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"`
    The JSON endpoint can lag a minute behind the upload.
11. Delete the release branch.

Semantic versioning applies. While the project is 0.x, a breaking change in
naming behaviour is a minor bump and is marked **Breaking:** in the changelog.
