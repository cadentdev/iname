"""Core rename logic — make filenames safe for the web.

Supports multiple naming styles:
* web (default): lowercase, hyphens — URL-safe
* snake: lowercase, underscores — Python/filesystem-friendly
* kebab: lowercase, hyphens — converts underscores too
* camel: camelCase — no separators

Ported from xplat (github.com/cadentdev/xplat).
"""

import re
import unicodedata
from enum import Enum
from pathlib import Path

NAME_MAX = 255  # bytes; the filename limit on every mainstream filesystem
DEDUP_MAX = 99

_SEPARATORS = "-_"


class Style(str, Enum):
    """Naming style for safe filenames."""

    web = "web"
    snake = "snake"
    kebab = "kebab"
    camel = "camel"


# delimiter, characters converted to the delimiter, other characters kept as-is
_DELIMITER_STYLES = {
    Style.web: ("-", " .", "_"),
    Style.snake: ("_", " .-", ""),
    Style.kebab: ("-", " ._", ""),
}


def _normalize(name: str) -> str:
    """Canonicalize a name before any transformation.

    NFKD decomposition makes a name read the same whether it came from a
    filesystem that stores NFC (Linux) or NFD (macOS), and folds compatibility
    forms such as ligatures and fullwidth digits to their plain equivalents.
    The combining marks it leaves behind are dropped by the alphanumeric
    filters, so accented letters end up as plain ASCII. Null bytes and all
    Unicode whitespace become a single ASCII space.
    """
    name = unicodedata.normalize("NFKD", name).replace("\x00", " ")
    return re.sub(r"\s", " ", name).strip()


def _apply_delimiter_style(
    name: str, delim: str, convert_chars: str, keep_chars: str
) -> str:
    """Lowercase, turn convert_chars into delim, drop the rest, collapse runs."""
    chars = []
    for c in name.lower():
        if c in convert_chars:
            chars.append(delim)
        elif c.isalnum() or c == delim or c in keep_chars:
            chars.append(c)
    return re.sub(re.escape(delim) + "+", delim, "".join(chars))


def _apply_camel(name: str) -> str:
    """Camel style: remove separators, produce camelCase."""
    words = [
        word
        for part in re.split(r"[ .\-_]+", name)
        if (word := "".join(c for c in part if c.isalnum()))
    ]
    if not words:
        return ""
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


def _truncate(name: str, max_bytes: int) -> str:
    """Cut to max_bytes of UTF-8 on a character boundary; strip end separators."""
    cut = name.encode("utf-8")[: max(max_bytes, 0)].decode("utf-8", "ignore")
    return cut.strip(_SEPARATORS)


def safe_stem(name: str, style: Style = Style.web, *, max_bytes: int = NAME_MAX) -> str:
    """Transform a filename stem to be safe for the web.

    Returns the transformed stem, or empty string if input is all special chars.
    """
    normalized = _normalize(name)
    if style == Style.camel:
        result = _apply_camel(normalized)
    else:
        result = _apply_delimiter_style(normalized, *_DELIMITER_STYLES[style])
    return _truncate(result, max_bytes)


def _split_extension(name: str) -> tuple[str, str]:
    """Split "stem.ext" into ("stem", ".ext").

    The extension is only recognised when it is purely alphanumeric. Anything
    else ("photo.JPG (1)", "file.") is treated as part of the stem so that it
    gets sanitized rather than passed through.
    """
    stem, dot, ext = name.rpartition(".")
    if dot and ext.isalnum():
        return stem, "." + ext.lower()
    return name, ""


def make_safe_path(orig_path: Path, style: Style = Style.web) -> Path:
    """Create a new Path with safe filename in the same directory.

    A leading dot is preserved so hidden files stay hidden.

    Raises ValueError if the filename produces an empty stem.
    """
    name = _normalize(orig_path.name)
    prefix = "." if name.startswith(".") else ""
    stem, suffix = _split_extension(name.lstrip("."))
    budget = NAME_MAX - len(prefix) - len(suffix.encode("utf-8"))
    stem = safe_stem(stem, style, max_bytes=budget)
    if not stem:
        raise ValueError(
            f"Filename produces empty stem after sanitization: {orig_path.name}"
        )
    return orig_path.with_name(prefix + stem + suffix)


def _dedup_path(path: Path) -> Path:
    """Find an available path by appending -01, -02, ... -99.

    The stem is trimmed if needed so the result still fits in NAME_MAX.
    """
    suffix = path.suffix
    tag_bytes = len("-00")
    stem = _truncate(path.stem, NAME_MAX - tag_bytes - len(suffix.encode("utf-8")))
    for i in range(1, DEDUP_MAX + 1):
        candidate = path.with_name(f"{stem}-{i:02d}{suffix}")
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

    # Compare as strings: WindowsPath equality ignores case, which would make
    # "Photo.JPG" -> "photo.jpg" look like a no-op.
    if str(new_path) == str(orig_path):
        return orig_path

    # A case-only change on a case-insensitive filesystem "exists" but is the
    # same file, so it needs no dedup.
    if new_path.exists() and not orig_path.samefile(new_path):
        new_path = _dedup_path(new_path)

    if not dry_run:
        orig_path.rename(new_path)

    return new_path
