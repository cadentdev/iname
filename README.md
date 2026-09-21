# iname — Internet Name

[![CI](https://github.com/cadentdev/iname/actions/workflows/ci.yml/badge.svg)](https://github.com/cadentdev/iname/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/iname)](https://pypi.org/project/iname/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Make file and directory names safe and consistent for the web. One path at a time, composable with Unix pipes.

## Install

```bash
pip install iname
```

## Usage

```bash
# Rename a single file (default: web style with hyphens)
iname "My Photo (2).jpeg"           # → my-photo-2.jpeg

# Preview without renaming
iname "My Photo (2).jpeg" --dry-run

# Different naming styles
iname "My Photo.jpeg" --style snake  # → my_photo.jpeg
iname "My Photo.jpeg" --style kebab  # → my-photo.jpeg
iname "My Photo.jpeg" --style camel  # → myPhoto.jpeg

# Batch rename with find
find . -name "*.jpeg" | iname

# Filenames with newlines or other odd characters: NUL-separated in and out
find . -name "*.jpeg" -print0 | iname -0 | xargs -0 ls -la

# Directories too (-depth renames children before their parents)
find . -depth -type d | iname

# Chain with other tools
iname "My Photo.jpeg" | xargs ls -la

# Preview a batch
find . -name "*.JPEG" | iname --dry-run --verbose
```

## Styles

| Style | Input | Output |
|-------|-------|--------|
| `web` (default) | `My Photo (2).jpeg` | `my-photo-2.jpeg` |
| `snake` | `My Photo (2).jpeg` | `my_photo_2.jpeg` |
| `kebab` | `My_Photo (2).jpeg` | `my-photo-2.jpeg` |
| `camel` | `My Photo (2).jpeg` | `myPhoto2.jpeg` |

Dots are kept in every style, so `archive.tar.gz`, `example.com.zip` and
`app.min.js` are left alone and `My Photo.v2.JPG` becomes `my-photo.v2.jpg`.
A dot outranks the separators next to it: `My Photo .v2` → `my-photo.v2`.
The extension is kept verbatim apart from lowercasing (`photo.C++` → `photo.c++`),
unless it contains whitespace, in which case the whole name is sanitized.

## Behavior

- **Stdout**: always prints the new path (enables piping and chaining)
- **Stderr**: `--verbose` prints `old → new` mappings (doesn't interfere with pipes)
- **`-0` / `--null`**: NUL-separated paths on stdin and stdout, for `find -print0` and `xargs -0`
- **Directories**: renamed like files; rename children before parents (`find -depth`)
- **Collisions**: auto-dedup with `-01`, `-02`, ... `-99` suffix
- **Already safe**: prints path unchanged, exits 0
- **Exit codes**: 0 = success, 1 = error, 2 = usage error

## Safety

- Rejects symlinks, and refuses to rename `.` or `..`
- Never overwrites: files are moved with an atomic hard link, so a target that
  appears between the collision check and the move is reported, not clobbered
  (directories and filesystems without hard links fall back to a plain rename)
- Strips null bytes
- Normalizes Unicode whitespace (no-break spaces, narrow spaces)
- Folds accented letters to ASCII (`Café.png` → `cafe.png`), so a name comes out
  the same whether the filesystem stores it as NFC (Linux) or NFD (macOS)
- Sanitizes an extension containing whitespace: `photo.JPG (1)` → `photo.jpg-1`
- Keeps hidden files hidden (`.DS_Store` → `.ds_store`)
- Truncates to filesystem NAME_MAX (255 bytes), including any dedup suffix
- Case-insensitive filesystem aware

## Zero dependencies

iname uses only the Python standard library. No runtime dependencies.

## Development

Requires [Poetry](https://python-poetry.org/).

```bash
poetry install
poetry run pytest --cov=iname --cov-report=term-missing
poetry run ruff check .
```

## Origin

Extracted from [xplat](https://github.com/cadentdev/xplat) — the proven rename logic, distilled into a single-purpose Unix tool.
