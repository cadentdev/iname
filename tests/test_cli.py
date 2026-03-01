"""Tests for the CLI interface."""

import subprocess
import sys

import pytest

from iname.cli import main


class TestCliArgs:
    def test_no_args_no_stdin_returns_2(self, monkeypatch):
        """No file + interactive terminal → usage error (exit 2)."""
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        assert main([]) == 2

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        assert "0.1.0" in capsys.readouterr().out

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
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(stdin_data))
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
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(f"{f}\n"))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        result = main(["--style", "snake"])
        assert result == 0
        assert capsys.readouterr().out.strip().endswith("my_file.txt")

    def test_piped_empty_lines_skipped(self, tmp_path, capsys, monkeypatch):
        f = tmp_path / "My File.txt"
        f.write_text("content")
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(f"\n{f}\n\n"))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        result = main([])
        assert result == 0
        lines = [x for x in capsys.readouterr().out.strip().split("\n") if x]
        assert len(lines) == 1

    def test_piped_partial_error(self, tmp_path, capsys, monkeypatch):
        f = tmp_path / "Good File.txt"
        f.write_text("content")
        stdin_data = f"/nonexistent/bad.txt\n{f}\n"
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(stdin_data))
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
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout
