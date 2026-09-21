"""Command-line interface for iname."""

import argparse
import sys
from collections.abc import Iterator
from pathlib import Path

from iname import __version__
from iname.rename import Style, rename_path


def _process_file(
    path: Path, *, style: Style, dry_run: bool, verbose: bool, end: str
) -> int:
    """Process a single path. Returns 0 on success, 1 on error."""
    try:
        new_path = rename_path(path, dry_run=dry_run, style=style)
    except (OSError, ValueError) as e:
        print(f"iname: {e}", file=sys.stderr)
        return 1
    print(new_path, end=end)
    if verbose:
        if str(new_path) != str(path):
            print(f"{path} → {new_path}", file=sys.stderr)
        else:
            print(f"{path} (unchanged)", file=sys.stderr)
    return 0


def _stdin_paths(null_separated: bool) -> Iterator[str]:
    """Yield one path per non-blank stdin record.

    Records are lines, or NUL-separated when null_separated (find -print0).
    Only the separator is removed: other leading or trailing whitespace may
    be part of the filename, which is exactly what iname exists to fix.
    """
    if null_separated:
        data = sys.stdin.buffer.read().decode(
            sys.getfilesystemencoding(), "surrogateescape"
        )
        records = data.split("\0")
    else:
        records = (line.rstrip("\r\n") for line in sys.stdin)
    for record in records:
        if record.strip():
            yield record


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="iname",
        description="Make file and directory names safe and consistent for the web.",
        epilog="Reads from stdin when no FILE is given: find . -name '*.jpg' | iname",
    )
    parser.add_argument("file", nargs="?", help="file or directory to rename")
    parser.add_argument(
        "--style",
        choices=[s.value for s in Style],
        default=Style.web.value,
        help="naming style (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print new name without renaming",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print old → new mapping to stderr",
    )
    parser.add_argument(
        "-0",
        "--null",
        action="store_true",
        help="separate paths with NUL instead of newline, on stdin and stdout "
        "(for find -print0 and xargs -0)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args(argv)
    opts = {
        "style": Style(args.style),
        "dry_run": args.dry_run,
        "verbose": args.verbose,
        "end": "\0" if args.null else "\n",
    }

    # Single file argument
    if args.file is not None:
        return _process_file(Path(args.file), **opts)

    # Piped stdin
    if not sys.stdin.isatty():
        codes = [_process_file(Path(p), **opts) for p in _stdin_paths(args.null)]
        return max(codes, default=0)

    # No file and no stdin — usage error
    parser.print_usage(sys.stderr)
    print("iname: error: no FILE given and stdin is a terminal", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
