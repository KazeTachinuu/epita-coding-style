"""Hostile input handling: the checker must never crash on garbage."""

import pytest

from epita_coding_style import Config, check_file


@pytest.mark.parametrize("data", [
    b"\x7fELF\x02\x01\x01\x00" + bytes(range(256)) * 16,
    b"\xc3\x28\xa0\xa1invalid utf8",
    b"int main(void)\x00{\x00return 0;\x00}\n",
    b"\xef\xbb\xbfint x;\n",
    b"",
    b"\r\n\r\n\r\n",
    b"A" * 100_000 + b"\n",
    b"/*" + b"x" * 1000,
    b'"' + b"y" * 1000,
    b"(" * 500 + b")" * 500,
], ids=["elf-binary", "invalid-utf8", "null-bytes", "bom", "empty",
        "crlf-only", "long-line", "unterminated-comment",
        "unterminated-string", "paren-bomb"])
def test_garbage_never_crashes(tmp_path, data):
    p = tmp_path / "hostile.c"
    p.write_bytes(data)
    assert isinstance(check_file(str(p), Config()), list)


def test_deeply_nested_declarator(tmp_path):
    depth = 200
    code = "int " + "(" * depth + "f" + ")" * depth + "(void)\n{\n    return 0;\n}\n"
    p = tmp_path / "deep.c"
    p.write_text(code)
    assert isinstance(check_file(str(p), Config()), list)


def test_check_file_ignores_non_source(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello\n")
    assert check_file(str(path), Config()) == []
