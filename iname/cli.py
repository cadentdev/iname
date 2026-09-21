"""Command-line interface for iname."""

import argparse
import sys
from collections.abc import Iterator
from pathlib import Path

from iname import __version__
from iname.rename import Style, rename_file


def _process_file(path: Path, *, style: Style, dry_run: bool, verbose: bool) -> int:
    """Process a single file. Returns 0 on success, 1 on error."""
    try:
        new_path = rename_file(path, dry_run=dry_run, style=style)
    except (OSError, ValueError) as e:
        print(f"iname: {e}", file=sys.stderr)
        return 1
    print(new_path)
    if verbose:
        if str(new_path) != str(path):
            print(f"{path} → {new_path}", file=sys.stderr)
        else:
            print(f"{path} (unchanged)", file=sys.stderr)
    return 0


def _stdin_paths() -> Iterator[str]:
    """Yield one path per non-blank stdin line.

    Only the line ending is removed: other leading or trailing whitespace may
    be part of the filename, which is exactly what iname exists to fix.
    """
    for line in sys.stdin:
        line = line.rstrip("\r\n")
        if line.strip():
            yield line


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="iname",
        description="Make filenames safe and consistent for the web.",
        epilog="Reads from stdin when no FILE is given: find . -name '*.jpg' | iname",
    )
    parser.add_argument("file", nargs="?", help="file to rename")
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
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args(argv)
    opts = {
        "style": Style(args.style),
        "dry_run": args.dry_run,
        "verbose": args.verbose,
    }

    # Single file argument
    if args.file is not None:
        return _process_file(Path(args.file), **opts)

    # Piped stdin
    if not sys.stdin.isatty():
        codes = [_process_file(Path(p), **opts) for p in _stdin_paths()]
        return max(codes, default=0)

    # No file and no stdin — show help
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
