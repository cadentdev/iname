# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Switched packaging to Poetry: `poetry-core` is the build backend, dev
  dependencies live in a Poetry group with a committed `poetry.lock`, and CI
  and the publish workflow build with Poetry. Project metadata stays in the
  standard `[project]` table. The package still has no runtime dependencies.
- The version is now single-sourced from `pyproject.toml`: `iname.__version__`
  reads it from the installed package metadata instead of duplicating it.

## [0.2.0] - 2026-09-21

### Removed

- **Breaking:** dropped support for Python 3.9, which reached end of life in
  October 2025. The minimum supported version is now Python 3.10.

### Added

- Directories can be renamed, not just files. `rename_file` is now an alias of
  `rename_path`.
- `-0` / `--null`: NUL-separated paths on stdin and stdout, so filenames
  containing newlines work with `find -print0` and `xargs -0`.
- Python 3.14 to the supported versions and the CI test matrix.
- Python 3.10 to the CI test matrix. It was listed as supported but never
  actually tested.

### Changed

- **Breaking:** dots inside a name are now kept in every style instead of
  being converted to the delimiter, so `archive.tar.gz`, `example.com.zip` and
  `app.min.js` are left alone and `My Photo.v2.JPG` becomes `my-photo.v2.jpg`
  (previously `my-photo-v2.jpg`). A dot outranks adjacent separators:
  `My Photo .v2` → `my-photo.v2`.
- **Breaking:** names are NFKD-normalized before sanitizing, so accented
  letters consistently fold to ASCII (`Café.png` → `cafe.png`) and ligatures
  and fullwidth characters fold to their plain forms. Previously the result
  depended on whether the filesystem stored the name as NFC or NFD.
- The extension is kept verbatim apart from lowercasing (`photo.C++` →
  `photo.c++`). Only an extension containing whitespace is folded into the
  stem and sanitized (`photo.JPG (1)` → `photo.jpg-1`).
- Running with no argument and no piped stdin now prints usage and an error to
  stderr, following the argparse convention, instead of help to stdout. The
  exit code is still 2.
- `.` and `..` are refused with a clear error instead of failing with a
  confusing "empty stem" message.
- Bumped `actions/checkout` to v7 and `actions/setup-python` to v7. Both now run
  on Node 24, clearing the Node 20 deprecation warning in CI.
- Pinned development dependencies to compatible release ranges
  (`pytest>=9.1,<10`, `pytest-cov>=7.1,<8`, `ruff>=0.16,<0.17`). Previously
  unpinned, which let a new ruff release turn CI red with no change to the code.
- `[tool.ruff] target-version` raised to `py310`.
- Internal refactor of the rename module: the style table now states which
  characters are converted and which are kept, truncation is a single byte
  slice instead of a character-by-character loop, and `NAME_MAX` is a named
  constant.

### Fixed

- Filenames with leading or trailing whitespace could not be renamed: the CLI
  stripped whitespace from the path before looking it up. Only the line ending
  is now removed from stdin input, and arguments are used verbatim.
- An extension containing whitespace was passed through untouched, so
  `photo.JPG (1)` became `photo.jpg (1)`. It is now folded into the stem and
  sanitized.
- Hidden files lost their leading dot (`.htaccess` → `htaccess`). The dot is
  now preserved.
- `camel` style capitalized letters after digits inside a word
  (`file 2nd edition` → `file2NdEdition`). Now `file2ndEdition`.
- The dedup suffix could push a name past 255 bytes, which crashed with
  "File name too long". The stem is now trimmed to make room.
- `web` style stripped a trailing underscore but kept a leading one
  (`_foo_` → `_foo`). Separators are now stripped from both ends.
- An empty string argument (`iname ""`) fell through to reading stdin instead
  of reporting an error.
- A file created at the target path by another process between the collision
  check and the rename was silently overwritten on POSIX. Files are now moved
  with an atomic hard link and unlink, which fails instead of clobbering.
  Directories, Windows and filesystems without hard links use a plain rename
  (Windows already refuses to overwrite).
- Two ruff violations that were failing CI on every job: a `subprocess.run` call
  without an explicit `check` argument (`PLW1510`) and an unsorted import block
  (`I001`).
- Version assertions in the CLI tests now compare against `iname.__version__`
  instead of a hardcoded literal, so a release no longer requires editing tests.

## [0.1.0] - 2026-03-01

Initial release. Extracted from [xplat](https://github.com/cadentdev/xplat) —
the proven rename logic, distilled into a single-purpose Unix tool.

### Added

- `iname` CLI that renames a file to a web-safe name and prints the new path to
  stdout, so it composes with pipes and `xargs`.
- Reads paths from arguments or stdin, for batch use with `find`.
- Four naming styles: `web` (default), `snake`, `kebab`, and `camel`.
- `--dry-run` to preview without renaming, and `--verbose` to print
  `old → new` mappings to stderr.
- Collision handling with an auto-dedup `-01` through `-99` suffix.
- Safety behaviors: rejects symlinks, strips null bytes, normalizes Unicode
  whitespace, truncates to the filesystem `NAME_MAX` of 255 bytes, and accounts
  for case-insensitive filesystems.
- Exit codes: `0` success, `1` error, `2` usage error.
- Zero runtime dependencies — standard library only.

[Unreleased]: https://github.com/cadentdev/iname/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/cadentdev/iname/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cadentdev/iname/releases/tag/v0.1.0
