"""Command-line interface for iname."""

import argparse
import sys
from pathlib import Path

from iname import __version__
from iname.rename import Style, rename_file


def _process_file(filepath: str, args) -> int:
    """Process a single file. Returns 0 on success, 1 on error."""
    filepath = filepath.strip()
    if not filepath:
        return 0

    path = Path(filepath)
    try:
        new_path = rename_file(path, dry_run=args.dry_run, style=Style(args.style))
        print(new_path)
        if args.verbose:
            if str(new_path) != str(path):
                print(f"{path} → {new_path}", file=sys.stderr)
            else:
                print(f"{path} (unchanged)", file=sys.stderr)
        return 0
    except (FileNotFoundError, OSError, ValueError) as e:
        print(f"iname: {e}", file=sys.stderr)
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="iname",
        description="Make filenames safe and consistent for the web.",
        epilog="Reads from stdin when no FILE is given: find . -name '*.jpg' | iname",
    )
    parser.add_argument("file", nargs="?", help="file to rename")
    parser.add_argument(
        "--style",
        choices=["web", "snake", "kebab", "camel"],
        default="web",
        help="naming style (default: web)",
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

    # Single file argument
    if args.file:
        return _process_file(args.file, args)

    # Piped stdin
    if not sys.stdin.isatty():
        exit_code = 0
        for line in sys.stdin:
            result = _process_file(line, args)
            if result != 0:
                exit_code = 1
        return exit_code

    # No file and no stdin — show help
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
