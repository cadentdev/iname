# iname — Internet Name

[![CI](https://github.com/cadentdev/iname/actions/workflows/ci.yml/badge.svg)](https://github.com/cadentdev/iname/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/iname)](https://pypi.org/project/iname/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Make filenames safe and consistent for the web. One file at a time, composable with Unix pipes.

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

## Behavior

- **Stdout**: always prints the new path (enables piping and chaining)
- **Stderr**: `--verbose` prints `old → new` mappings (doesn't interfere with pipes)
- **Collisions**: auto-dedup with `-01`, `-02`, ... `-99` suffix
- **Already safe**: prints path unchanged, exits 0
- **Exit codes**: 0 = success, 1 = error, 2 = usage error

## Safety

- Rejects symlinks
- Strips null bytes
- Normalizes Unicode whitespace (no-break spaces, narrow spaces)
- Truncates to filesystem NAME_MAX (255 bytes)
- Case-insensitive filesystem aware

## Zero dependencies

iname uses only the Python standard library. No runtime dependencies.

## Development

```bash
pip install -e '.[dev]'
pytest --cov=iname --cov-report=term-missing
```

## Origin

Extracted from [xplat](https://github.com/cadentdev/xplat) — the proven rename logic, distilled into a single-purpose Unix tool.
