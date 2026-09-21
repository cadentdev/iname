# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Filenames with leading or trailing whitespace could not be renamed: the CLI
  stripped whitespace from the path before looking it up. Only the line ending
  is now removed from stdin input, and arguments are used verbatim.
- An extension containing unsafe characters was passed through untouched, so
  `photo.JPG (1)` became `photo.jpg (1)`. Only a purely alphanumeric extension
  is now kept; anything else is folded into the stem and sanitized.
- Hidden files lost their leading dot (`.htaccess` → `htaccess`). The dot is
  now preserved.
- The same name produced different results depending on the filesystem's
  Unicode normalization form: NFD input (macOS) had its accents stripped while
  NFC input (Linux) kept them. Names are now NFKD-normalized first, so accented
  letters consistently fold to ASCII and ligatures and fullwidth characters
  fold to their plain forms.
- `camel` style capitalized letters after digits inside a word
  (`file 2nd edition` → `file2NdEdition`). Now `file2ndEdition`.
- The dedup suffix could push a name past 255 bytes, which crashed with
  "File name too long". The stem is now trimmed to make room.
- `web` style stripped a trailing underscore but kept a leading one
  (`_foo_` → `_foo`). Separators are now stripped from both ends.
- An empty string argument (`iname ""`) fell through to reading stdin instead
  of reporting an error.

### Changed

- Internal refactor of the rename module: the style table now states which
  characters are converted and which are kept, truncation is a single byte
  slice instead of a character-by-character loop, and `NAME_MAX` is a named
  constant.

## [0.2.0] - 2026-09-21

### Removed

- **Breaking:** dropped support for Python 3.9, which reached end of life in
  October 2025. The minimum supported version is now Python 3.10.

### Added

- Python 3.14 to the supported versions and the CI test matrix.
- Python 3.10 to the CI test matrix. It was listed as supported but never
  actually tested.

### Changed

- Bumped `actions/checkout` to v7 and `actions/setup-python` to v7. Both now run
  on Node 24, clearing the Node 20 deprecation warning in CI.
- Pinned development dependencies to compatible release ranges
  (`pytest>=9.1,<10`, `pytest-cov>=7.1,<8`, `ruff>=0.16,<0.17`). Previously
  unpinned, which let a new ruff release turn CI red with no change to the code.
- `[tool.ruff] target-version` raised to `py310`.

### Fixed

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
