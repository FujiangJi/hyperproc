"""The netCDF rc-file check: a last line without a newline is the whole bug."""
from pathlib import Path

import pytest

from hyperproc._ncrc import (NC_RC_NAMES, rc_warning, terminate_rc_file,
                             unterminated_rc_files)


def write(d: Path, name: str, text: str) -> Path:
    p = d / name
    p.write_text(text)
    return p


def test_a_last_line_without_a_newline_is_found(tmp_path):
    write(tmp_path, ".dodsrc", "HTTP.COOKIEJAR=/x\nHTTP.NETRC=/y")
    assert unterminated_rc_files(tmp_path) == [tmp_path / ".dodsrc"]


def test_a_file_that_ends_in_a_newline_is_not_reported(tmp_path):
    write(tmp_path, ".dodsrc", "HTTP.COOKIEJAR=/x\nHTTP.NETRC=/y\n")
    assert unterminated_rc_files(tmp_path) == []


def test_an_empty_file_has_no_last_line_to_run_off(tmp_path):
    write(tmp_path, ".dodsrc", "")
    assert unterminated_rc_files(tmp_path) == []


def test_a_directory_with_no_rc_files_is_quiet(tmp_path):
    assert unterminated_rc_files(tmp_path) == []


def test_every_name_netcdf_reads_is_checked(tmp_path):
    for name in NC_RC_NAMES:
        write(tmp_path, name, "KEY=value")
    found = {p.name for p in unterminated_rc_files(tmp_path)}
    assert found == set(NC_RC_NAMES)


def test_several_directories_are_checked_in_order(tmp_path):
    home, work = tmp_path / "home", tmp_path / "work"
    home.mkdir(); work.mkdir()
    write(home, ".dodsrc", "a=1")
    write(work, ".daprc", "b=2")
    assert unterminated_rc_files(home, work) == [home / ".dodsrc", work / ".daprc"]


def test_fixing_appends_one_byte_and_changes_nothing_else(tmp_path):
    p = write(tmp_path, ".dodsrc", "HTTP.COOKIEJAR=/x\nHTTP.NETRC=/y")
    before = p.read_bytes()
    assert terminate_rc_file(p) is True
    assert p.read_bytes() == before + b"\n"
    assert unterminated_rc_files(tmp_path) == []


def test_fixing_an_already_terminated_file_does_nothing(tmp_path):
    p = write(tmp_path, ".dodsrc", "KEY=value\n")
    before = p.read_bytes()
    assert terminate_rc_file(p) is False
    assert p.read_bytes() == before


def test_the_warning_names_the_file_and_the_command_that_fixes_it(tmp_path):
    p = write(tmp_path, ".dodsrc", "KEY=value")
    text = rc_warning(unterminated_rc_files(tmp_path))
    assert str(p) in text
    assert f"printf '\\n' >> {p}" in text
    assert "NCRCENV_RC" in text


def test_an_unreadable_path_is_skipped_rather_than_raising(tmp_path, monkeypatch):
    write(tmp_path, ".dodsrc", "KEY=value")

    def boom(self, *a, **k):
        raise PermissionError(str(self))

    monkeypatch.setattr(Path, "read_bytes", boom)
    assert unterminated_rc_files(tmp_path) == []
