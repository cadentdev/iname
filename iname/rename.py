"""Core rename logic — make filenames safe for the web.

Supports multiple naming styles:
* web (default): lowercase, hyphens — URL-safe
* snake: lowercase, underscores — Python/filesystem-friendly
* kebab: lowercase, hyphens — converts underscores too
* camel: camelCase — no separators

Ported from xplat (github.com/cadentdev/xplat).
"""

import re
from enum import Enum
from pathlib import Path

DEDUP_MAX = 99


class Style(str, Enum):
    """Naming style for safe filenames."""

    web = "web"
    snake = "snake"
    kebab = "kebab"
    camel = "camel"


def _normalize_whitespace(name: str) -> str:
    """Normalize all Unicode whitespace to ASCII space, strip null bytes."""
    name = name.replace("\x00", " ")
    return re.sub(r"\s", " ", name).strip()


def _apply_delimiter_style(name: str, delim: str, convert_chars: str) -> str:
    """Apply a delimiter-based style: replace chars, filter, collapse, strip."""
    result = name.lower()
    for ch in convert_chars:
        result = result.replace(ch, delim)
    allowed = {delim} | ({"_"} if delim == "-" and "_" not in convert_chars else set())
    result = "".join(c for c in result if c.isalnum() or c in allowed)
    double = delim + delim
    while double in result:
        result = result.replace(double, delim)
    return result.strip(delim)


def _apply_camel(name: str) -> str:
    """Camel style: remove separators, produce camelCase."""
    parts = re.split(r"[ .\-_]+", name)
    clean_parts = [
        cleaned
        for part in parts
        if (cleaned := "".join(c for c in part if c.isalnum()))
    ]
    if not clean_parts:
        return ""
    return clean_parts[0].lower() + "".join(p.title() for p in clean_parts[1:])


_STYLE_CONFIG = {
    Style.web: ("-", " ."),
    Style.snake: ("_", " .-"),
    Style.kebab: ("-", " ._"),
}


def safe_stem(name: str, style: Style = Style.web, *, max_bytes: int = 255) -> str:
    """Transform a filename stem to be safe for the web.

    Returns the transformed stem, or empty string if input is all special chars.
    """
    normalized = _normalize_whitespace(name)
    if not normalized:
        return ""
    if style == Style.camel:
        result = _apply_camel(normalized)
    else:
        delim, convert_chars = _STYLE_CONFIG[style]
        result = _apply_delimiter_style(normalized, delim, convert_chars)
    while len(result.encode("utf-8")) > max_bytes:
        result = result[:-1]
    return result.rstrip("-_")


def make_safe_path(orig_path: Path, style: Style = Style.web) -> Path:
    """Create a new Path with safe filename in the same directory.

    Raises ValueError if the filename produces an empty stem.
    """
    suffix = orig_path.suffix.lower()
    suffix_bytes = len(suffix.encode("utf-8"))
    stem = safe_stem(orig_path.stem, style, max_bytes=255 - suffix_bytes)
    if not stem:
        raise ValueError(
            f"Filename produces empty stem after sanitization: {orig_path.name}"
        )
    return orig_path.with_name(stem + suffix)


def _dedup_path(path: Path) -> Path:
    """Find an available path by appending -01, -02, ... -99."""
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for i in range(1, DEDUP_MAX + 1):
        candidate = parent / f"{stem}-{i:02d}{suffix}"
        if not candidate.exists():
            return candidate
    raise OSError(f"Cannot find available name after {DEDUP_MAX} attempts: {path}")


def rename_file(
    orig_path: Path,
    dry_run: bool = False,
    style: Style = Style.web,
) -> Path:
    """Rename a single file to be web-safe.

    Returns the new path (or original if already safe).
    Handles collisions with zero-padded dedup suffix (-01 to -99).

    Raises:
        FileNotFoundError: If original path is not a file
        OSError: If original path is a symlink, or dedup exhausted
        ValueError: If filename produces empty stem
    """
    if orig_path.is_symlink():
        raise OSError(f"Refusing to operate on symlink: {orig_path}")
    if not orig_path.is_file():
        raise FileNotFoundError(f"Not a file: {orig_path}")

    new_path = make_safe_path(orig_path, style)

    # Already safe — no rename needed
    if str(new_path) == str(orig_path):
        return orig_path

    # Handle collisions with dedup
    if new_path.exists() and not orig_path.samefile(new_path):
        new_path = _dedup_path(new_path)

    if not dry_run:
        orig_path.rename(new_path)

    return new_path
