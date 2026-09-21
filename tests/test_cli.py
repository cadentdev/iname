"""Tests for the CLI interface."""

import io
import subprocess
import sys
from pathlib import Path

import pytest

from iname import __version__
from iname.cli import main


class TestCliArgs:
    def test_no_args_no_stdin_returns_2(self, monkeypatch, capsys):
        """No file + interactive terminal → usage error on stderr (exit 2)."""
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        assert main([]) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err.startswith("usage:")
        assert "iname: error:" in captured.err

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        assert __version__ in capsys.readouterr().out

    def test_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "iname" in output
        assert "--style" in output
        assert "--dry-run" in output

    def test_invalid_style(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--style", "invalid", "file.txt"])
        assert exc_info.value.code == 2


class TestCliSingleFile:
    def test_rename(self, tmp_path, capsys):
        f = tmp_path / "My Photo.jpg"
        f.write_text("content")
        result = main([str(f)])
        assert result == 0
        out = capsys.readouterr().out.strip()
        assert out.endswith("my-photo.jpg")
        assert (tmp_path / "my-photo.jpg").exists()

    def test_dry_run(self, tmp_path, capsys):
        f = tmp_path / "My Photo.jpg"
        f.write_text("content")
        result = main(["--dry-run", str(f)])
        assert result == 0
        out = capsys.readouterr().out.strip()
        assert out.endswith("my-photo.jpg")
        assert f.exists()  # original unchanged

    def test_verbose(self, tmp_path, capsys):
        f = tmp_path / "My Photo.jpg"
        f.write_text("content")
        result = main(["--verbose", str(f)])
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip().endswith("my-photo.jpg")
        assert "→" in captured.err

    def test_verbose_unchanged(self, tmp_path, capsys):
        f = tmp_path / "already-safe.txt"
        f.write_text("content")
        result = main(["--verbose", str(f)])
        assert result == 0
        captured = capsys.readouterr()
        assert "unchanged" in captured.err

    def test_already_safe_prints_path(self, tmp_path, capsys):
        f = tmp_path / "clean-name.txt"
        f.write_text("content")
        result = main([str(f)])
        assert result == 0
        assert capsys.readouterr().out.strip().endswith("clean-name.txt")

    def test_not_found(self, tmp_path, capsys):
        result = main([str(tmp_path / "nope.txt")])
        assert result == 1
        assert "Not a file" in capsys.readouterr().err

    def test_style_snake(self, tmp_path, capsys):
        f = tmp_path / "My Photo.jpg"
        f.write_text("content")
        result = main(["--style", "snake", str(f)])
        assert result == 0
        assert capsys.readouterr().out.strip().endswith("my_photo.jpg")

    def test_collision_dedup(self, tmp_path, capsys):
        (tmp_path / "my-photo.jpg").write_text("existing")
        f = tmp_path / "My Photo.jpg"
        f.write_text("new")
        result = main([str(f)])
        assert result == 0
        assert capsys.readouterr().out.strip().endswith("my-photo-01.jpg")


class TestCliStdin:
    def test_piped_input(self, tmp_path, capsys, monkeypatch):
        f1 = tmp_path / "File One.txt"
        f2 = tmp_path / "File Two.txt"
        f1.write_text("1")
        f2.write_text("2")
        stdin_data = f"{f1}\n{f2}\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        result = main([])
        assert result == 0
        lines = capsys.readouterr().out.strip().split("\n")
        assert len(lines) == 2
        assert lines[0].endswith("file-one.txt")
        assert lines[1].endswith("file-two.txt")

    def test_piped_with_style(self, tmp_path, capsys, monkeypatch):
        f = tmp_path / "My File.txt"
        f.write_text("content")
        monkeypatch.setattr("sys.stdin", io.StringIO(f"{f}\n"))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        result = main(["--style", "snake"])
        assert result == 0
        assert capsys.readouterr().out.strip().endswith("my_file.txt")

    def test_piped_empty_lines_skipped(self, tmp_path, capsys, monkeypatch):
        f = tmp_path / "My File.txt"
        f.write_text("content")
        monkeypatch.setattr("sys.stdin", io.StringIO(f"\n{f}\n\n"))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        result = main([])
        assert result == 0
        lines = [x for x in capsys.readouterr().out.strip().split("\n") if x]
        assert len(lines) == 1

    def test_piped_partial_error(self, tmp_path, capsys, monkeypatch):
        f = tmp_path / "Good File.txt"
        f.write_text("content")
        stdin_data = f"/nonexistent/bad.txt\n{f}\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        result = main([])
        assert result == 1  # one error → exit 1
        out = capsys.readouterr().out.strip()
        assert "good-file.txt" in out  # good file still processed


class TestCliEntryPoint:
    def test_module_execution(self):
        """iname -m invocation works."""
        result = subprocess.run(
            [sys.executable, "-m", "iname.cli", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert __version__ in result.stdout


class TestCliWhitespaceInPaths:
    """Leading/trailing whitespace is part of the filename, not noise."""

    def test_relative_path_with_leading_space(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / " Leading.txt").write_text("content")
        assert main([" Leading.txt"]) == 0
        assert (tmp_path / "leading.txt").exists()

    def test_name_with_trailing_space(self, tmp_path, capsys):
        f = tmp_path / "Trailing.txt "
        f.write_text("content")
        assert main([str(f)]) == 0
        assert (tmp_path / "trailing.txt").exists()

    def test_piped_name_with_trailing_space(self, tmp_path, capsys, monkeypatch):
        f = tmp_path / "Trailing.txt "
        f.write_text("content")
        monkeypatch.setattr("sys.stdin", io.StringIO(f"{f}\n"))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        assert main([]) == 0
        assert (tmp_path / "trailing.txt").exists()

    def test_piped_whitespace_only_lines_skipped(self, tmp_path, capsys, monkeypatch):
        f = tmp_path / "My File.txt"
        f.write_text("content")
        monkeypatch.setattr("sys.stdin", io.StringIO(f"   \n{f}\n\t\n"))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        assert main([]) == 0
        lines = [x for x in capsys.readouterr().out.split("\n") if x]
        assert len(lines) == 1

    def test_empty_argument_is_an_error(self, capsys):
        assert main([""]) == 1
        assert "Refusing to rename" in capsys.readouterr().err


class TestCliNullSeparated:
    """-0 / --null: NUL-separated input and output, for find -print0 / xargs -0."""

    @staticmethod
    def _null_stdin(monkeypatch, data: bytes):
        monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(data)))

    def test_reads_nul_separated_paths(self, tmp_path, capsys, monkeypatch):
        f1 = tmp_path / "File One.txt"
        f2 = tmp_path / "File Two.txt"
        f1.write_text("1")
        f2.write_text("2")
        self._null_stdin(monkeypatch, f"{f1}\0{f2}\0".encode())
        assert main(["-0"]) == 0
        out = capsys.readouterr().out
        assert out.endswith("\0")
        names = [Path(x).name for x in out.split("\0") if x]
        assert names == ["file-one.txt", "file-two.txt"]

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Windows forbids newlines in filenames"
    )
    def test_newline_in_filename(self, tmp_path, capsys, monkeypatch):
        f = tmp_path / "Line\nBreak.txt"
        f.write_text("content")
        self._null_stdin(monkeypatch, f"{f}\0".encode())
        assert main(["--null"]) == 0
        assert (tmp_path / "line-break.txt").exists()
        assert capsys.readouterr().out.rstrip("\0").endswith("line-break.txt")

    def test_missing_trailing_nul_is_tolerated(self, tmp_path, capsys, monkeypatch):
        f = tmp_path / "My File.txt"
        f.write_text("content")
        self._null_stdin(monkeypatch, f"{f}".encode())
        assert main(["-0"]) == 0
        assert (tmp_path / "my-file.txt").exists()

    def test_single_argument_output_is_nul_terminated(self, tmp_path, capsys):
        f = tmp_path / "My File.txt"
        f.write_text("content")
        assert main(["-0", str(f)]) == 0
        out = capsys.readouterr().out
        assert out.endswith("my-file.txt\0")
        assert "\n" not in out


class TestCliDirectory:
    def test_rename_directory(self, tmp_path, capsys):
        d = tmp_path / "My Folder"
        d.mkdir()
        assert main([str(d)]) == 0
        assert capsys.readouterr().out.strip().endswith("my-folder")
        assert (tmp_path / "my-folder").is_dir()

    def test_missing_path_message(self, tmp_path, capsys):
        assert main([str(tmp_path / "nope")]) == 1
        assert "Not a file or directory" in capsys.readouterr().err
