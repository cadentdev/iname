"""Tests for the rename module."""

import errno
import os
from pathlib import Path

import pytest

from iname.rename import Style, make_safe_path, rename_file, rename_path, safe_stem

# --- safe_stem: style tests ---


class TestSafeStemStyles:
    def test_web_default(self):
        assert safe_stem("My File.v2") == "my-file.v2"

    def test_web_preserves_hyphens(self):
        assert safe_stem("my-file", style=Style.web) == "my-file"

    def test_web_preserves_underscores(self):
        assert safe_stem("my_file", style=Style.web) == "my_file"

    def test_snake(self):
        assert safe_stem("My File.v2", style=Style.snake) == "my_file.v2"

    def test_snake_converts_hyphens(self):
        assert safe_stem("my-file", style=Style.snake) == "my_file"

    def test_kebab(self):
        assert safe_stem("My_File.v2", style=Style.kebab) == "my-file.v2"

    def test_kebab_converts_underscores(self):
        assert safe_stem("my_file", style=Style.kebab) == "my-file"

    def test_camel(self):
        assert safe_stem("My File.v2", style=Style.camel) == "myFile.v2"

    def test_camel_single_word(self):
        assert safe_stem("Hello", style=Style.camel) == "hello"

    def test_camel_all_special_chars(self):
        assert safe_stem("!!!", style=Style.camel) == ""


# --- safe_stem: edge cases ---


class TestSafeStemEdgeCases:
    def test_empty_string(self):
        assert safe_stem("") == ""

    def test_all_special_chars(self):
        assert safe_stem("!!!") == ""

    def test_only_whitespace(self):
        assert safe_stem("   \t\n  ") == ""

    def test_leading_trailing_whitespace(self):
        assert safe_stem("  hello  ") == "hello"

    def test_consecutive_delims_collapsed(self):
        assert safe_stem("a---b") == "a-b"

    def test_multiple_dots(self):
        assert safe_stem("This..Has...Lots.Of..Dots") == "this.has.lots.of.dots"

    def test_dot_wins_over_adjacent_separators(self):
        assert safe_stem("My Photo .v2") == "my-photo.v2"
        assert safe_stem("a_.b", style=Style.web) == "a.b"
        assert safe_stem("a - . - b", style=Style.snake) == "a.b"

    def test_dots_stripped_from_ends(self):
        assert safe_stem(".foo.") == "foo"
        assert safe_stem("foo.-") == "foo"

    def test_camel_keeps_dots(self):
        assert safe_stem("example.com", style=Style.camel) == "example.com"
        assert safe_stem("My Photo .v2", style=Style.camel) == "myPhoto.v2"

    def test_numeric_only(self):
        assert safe_stem("12345") == "12345"

    def test_single_char(self):
        assert safe_stem("a") == "a"

    def test_already_safe(self):
        assert safe_stem("already-safe") == "already-safe"

    def test_null_bytes(self):
        assert safe_stem("hello\x00world") == "hello-world"
        assert safe_stem("\x00\x00\x00") == ""

    def test_unicode_nbsp(self):
        assert safe_stem("hello\u00a0world") == "hello-world"

    def test_unicode_narrow_nbsp(self):
        assert safe_stem("Screenshot\u202f2024-01-15") == "screenshot-2024-01-15"

    def test_mixed_unicode_whitespace(self):
        assert safe_stem("a\tb\u00a0c\u202fd") == "a-b-c-d"

    def test_tabs(self):
        assert safe_stem("hello\tworld") == "hello-world"

    def test_very_long_name(self):
        result = safe_stem("a" * 300)
        assert len(result) <= 255
        assert len(result) > 0


# --- make_safe_path ---


class TestMakeSafePath:
    def test_basic(self, tmp_path):
        orig = tmp_path / "Test File.TXT"
        safe = make_safe_path(orig)
        assert safe.name == "test-file.txt"
        assert safe.parent == tmp_path

    def test_with_style(self, tmp_path):
        orig = tmp_path / "Test File.TXT"
        assert make_safe_path(orig, style=Style.snake).name == "test_file.txt"
        assert make_safe_path(orig, style=Style.kebab).name == "test-file.txt"
        assert make_safe_path(orig, style=Style.camel).name == "testFile.txt"

    def test_no_extension(self, tmp_path):
        orig = tmp_path / "Makefile"
        assert make_safe_path(orig).name == "makefile"

    def test_empty_stem_raises(self, tmp_path):
        orig = tmp_path / "!!!.txt"
        with pytest.raises(ValueError, match="empty stem"):
            make_safe_path(orig)

    def test_long_stem_with_extension(self, tmp_path):
        orig = tmp_path / ("a" * 300 + ".jpeg")
        safe = make_safe_path(orig)
        assert len(safe.name.encode("utf-8")) <= 255


# --- rename_file ---


class TestRenameFile:
    def test_success(self, tmp_path):
        f = tmp_path / "My Photo.TXT"
        f.write_text("content")
        result = rename_file(f)
        assert result.name == "my-photo.txt"
        assert result.exists()
        assert not f.exists()

    def test_already_safe(self, tmp_path):
        f = tmp_path / "already-safe.txt"
        f.write_text("content")
        result = rename_file(f)
        assert result == f
        assert f.exists()

    def test_uppercase_extension(self, tmp_path):
        f = tmp_path / "safe-stem.TXT"
        f.write_text("content")
        result = rename_file(f)
        assert result.name == "safe-stem.txt"
        assert result.exists()

    def test_dry_run(self, tmp_path):
        f = tmp_path / "My Photo.TXT"
        f.write_text("content")
        result = rename_file(f, dry_run=True)
        assert result.name == "my-photo.txt"
        assert f.exists()  # original still exists
        assert not result.exists()  # new name not created

    def test_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            rename_file(tmp_path / "nonexistent.txt")

    def test_rejects_symlink(self, tmp_path):
        real = tmp_path / "real.txt"
        real.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(real)
        with pytest.raises(OSError, match="symlink"):
            rename_file(link)

    def test_empty_stem_raises(self, tmp_path):
        f = tmp_path / "!!!.txt"
        f.write_text("content")
        with pytest.raises(ValueError, match="empty stem"):
            rename_file(f)

    def test_style_propagates(self, tmp_path):
        f = tmp_path / "My File.txt"
        f.write_text("content")
        result = rename_file(f, style=Style.snake)
        assert result.name == "my_file.txt"


# --- dedup ---


class TestDedup:
    def test_collision_gets_suffix_01(self, tmp_path):
        existing = tmp_path / "my-photo.txt"
        existing.write_text("existing")
        f = tmp_path / "My Photo.txt"
        f.write_text("new")
        result = rename_file(f)
        assert result.name == "my-photo-01.txt"
        assert result.exists()

    def test_multiple_collisions(self, tmp_path):
        (tmp_path / "my-photo.txt").write_text("0")
        (tmp_path / "my-photo-01.txt").write_text("1")
        (tmp_path / "my-photo-02.txt").write_text("2")
        f = tmp_path / "My Photo.txt"
        f.write_text("new")
        result = rename_file(f)
        assert result.name == "my-photo-03.txt"

    def test_dedup_dry_run(self, tmp_path):
        existing = tmp_path / "my-photo.txt"
        existing.write_text("existing")
        f = tmp_path / "My Photo.txt"
        f.write_text("new")
        result = rename_file(f, dry_run=True)
        assert result.name == "my-photo-01.txt"
        assert f.exists()  # original unchanged

    def test_dedup_exhausted(self, tmp_path):
        # Use a name that sanitizes to "test" but is distinct from "test.txt"
        # to avoid case-insensitive samefile() on macOS/Windows
        (tmp_path / "test.txt").write_text("base")
        for i in range(1, 100):
            (tmp_path / f"test-{i:02d}.txt").write_text(str(i))
        f = tmp_path / "TEST!.txt"
        f.write_text("overflow")
        with pytest.raises(OSError, match="99 attempts"):
            rename_file(f)


# --- Unicode normalization ---


class TestUnicodeNormalization:
    def test_nfc_and_nfd_input_agree(self):
        # macOS stores names as NFD, Linux as NFC — both must give the same result
        assert safe_stem("café") == safe_stem("café")

    def test_accents_folded_to_ascii(self):
        assert safe_stem("Café Crème") == "cafe-creme"

    def test_compatibility_forms_folded(self):
        # "fi" ligature and fullwidth digit 2
        assert safe_stem("ﬁle ２") == "file-2"

    def test_non_latin_letters_preserved(self):
        assert safe_stem("写真 2024") == "写真-2024"


# --- camel: word capitalization ---


class TestCamelCapitalization:
    def test_digit_led_word_not_retitled(self):
        assert safe_stem("file 2nd edition", style=Style.camel) == "file2ndEdition"

    def test_inner_digits_not_retitled(self):
        assert safe_stem("x abc123def", style=Style.camel) == "xAbc123def"


# --- separators at the ends ---


class TestEdgeSeparators:
    def test_web_strips_underscores_at_both_ends(self):
        assert safe_stem("_foo_") == "foo"

    def test_web_strips_hyphens_at_both_ends(self):
        assert safe_stem("-foo-") == "foo"


# --- make_safe_path: extension handling ---


class TestMakeSafePathExtension:
    def test_suffix_with_whitespace_is_folded_into_stem(self, tmp_path):
        assert make_safe_path(tmp_path / "photo.JPG (1)").name == "photo.jpg-1"

    def test_suffix_with_whitespace_with_style(self, tmp_path):
        orig = tmp_path / "photo.JPG (1)"
        assert make_safe_path(orig, style=Style.snake).name == "photo.jpg_1"
        assert make_safe_path(orig, style=Style.camel).name == "photo.jpg1"

    def test_non_alphanumeric_suffix_kept_verbatim(self, tmp_path):
        assert make_safe_path(tmp_path / "Photo.C++").name == "photo.c++"

    def test_compound_extensions_unchanged(self, tmp_path):
        for name in ["archive.tar.gz", "example.com.zip", "app.min.js", "types.d.ts"]:
            assert make_safe_path(tmp_path / name).name == name

    def test_dotted_stem_kept(self, tmp_path):
        orig = tmp_path / "Screenshot 2024.01.15.PNG"
        assert make_safe_path(orig).name == "screenshot-2024.01.15.png"
        assert (
            make_safe_path(orig, style=Style.camel).name == "screenshot2024.01.15.png"
        )

    def test_trailing_whitespace_after_suffix(self, tmp_path):
        assert make_safe_path(tmp_path / "file.TXT ").name == "file.txt"

    def test_trailing_dot_dropped(self, tmp_path):
        assert make_safe_path(tmp_path / "file.").name == "file"


# --- make_safe_path: hidden files ---


class TestMakeSafePathDotfiles:
    def test_leading_dot_preserved(self, tmp_path):
        assert make_safe_path(tmp_path / ".DS_Store").name == ".ds_store"

    def test_dotfile_with_extension(self, tmp_path):
        assert make_safe_path(tmp_path / ".env.Local").name == ".env.local"

    def test_dotfile_with_spaces(self, tmp_path):
        assert make_safe_path(tmp_path / ".Hidden File.txt").name == ".hidden-file.txt"

    def test_dots_only_raises(self, tmp_path):
        with pytest.raises(ValueError, match="empty stem"):
            make_safe_path(tmp_path / "...")

    def test_dotfile_counts_toward_name_max(self, tmp_path):
        safe = make_safe_path(tmp_path / ("." + "a" * 300 + ".txt"))
        assert safe.name.startswith(".")
        assert len(safe.name.encode("utf-8")) <= 255


# --- dedup respects NAME_MAX ---


class TestDedupNameMax:
    def test_dedup_suffix_does_not_exceed_name_max(self, tmp_path):
        (tmp_path / ("a" * 250 + ".txt")).write_text("existing")
        f = tmp_path / (
            "a" * 250 + "!.txt"
        )  # 255 bytes; sanitizes to the existing name
        f.write_text("new")
        result = rename_file(f)
        assert result.name == "a" * 248 + "-01.txt"
        assert len(result.name.encode("utf-8")) <= 255
        assert result.exists()


# --- directories ---


class TestRenameDirectory:
    def test_directory_renamed(self, tmp_path):
        d = tmp_path / "My Folder"
        d.mkdir()
        (d / "child.txt").write_text("content")
        result = rename_path(d)
        assert result.name == "my-folder"
        assert (result / "child.txt").exists()
        assert not d.exists()

    def test_directory_with_dots(self, tmp_path):
        d = tmp_path / "Example.COM"
        d.mkdir()
        assert rename_path(d).name == "example.com"

    def test_directory_dry_run(self, tmp_path):
        d = tmp_path / "My Folder"
        d.mkdir()
        assert rename_path(d, dry_run=True).name == "my-folder"
        assert d.exists()

    def test_directory_collision_dedup(self, tmp_path):
        (tmp_path / "my-folder").mkdir()
        d = tmp_path / "My Folder"
        d.mkdir()
        assert rename_path(d).name == "my-folder-01"

    @pytest.mark.parametrize("name", [".", ".."])
    def test_refuses_dot_and_dotdot(self, tmp_path, name, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Refusing to rename"):
            rename_path(Path(name))
        assert tmp_path.exists()

    def test_rejects_directory_symlink(self, tmp_path):
        real = tmp_path / "real"
        real.mkdir()
        link = tmp_path / "Link Dir"
        link.symlink_to(real, target_is_directory=True)
        with pytest.raises(OSError, match="symlink"):
            rename_path(link)

    def test_rename_file_is_an_alias(self):
        assert rename_file is rename_path


# --- no-clobber move ---


class TestNoClobber:
    def test_target_appearing_after_check_is_not_overwritten(
        self, tmp_path, monkeypatch
    ):
        target = tmp_path / "my-photo.txt"
        target.write_text("precious")
        f = tmp_path / "My Photo.txt"
        f.write_text("new")
        # Simulate the race: the existence check misses the target.
        monkeypatch.setattr(Path, "exists", lambda self: False)
        with pytest.raises(FileExistsError):
            rename_path(f)
        assert target.read_text() == "precious"
        assert f.read_text() == "new"

    def test_falls_back_to_rename_when_links_unsupported(self, tmp_path, monkeypatch):
        def no_links(*args, **kwargs):
            raise OSError(errno.ENOTSUP, "Operation not supported")

        monkeypatch.setattr(os, "link", no_links)
        f = tmp_path / "My Photo.txt"
        f.write_text("content")
        result = rename_path(f)
        assert result.name == "my-photo.txt"
        assert result.read_text() == "content"
        assert not f.exists()

    def test_case_only_rename_on_same_file(self, tmp_path):
        f = tmp_path / "PHOTO.txt"
        f.write_text("content")
        result = rename_path(f)
        assert result.name == "photo.txt"
        assert result.read_text() == "content"
        assert [p.name for p in tmp_path.iterdir()] == ["photo.txt"]
