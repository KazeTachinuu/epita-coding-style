"""Tests for file.ext rule (wrong C++ file extension)."""

import pytest
from epita_coding_style import Severity


# ── Test data ────────────────────────────────────────────────────────────

SOURCE_CODE = "void foo() {}\n"
HEADER_CODE = "#pragma once\nint x;\n"
SOURCE_WITH_NULLPTR = "void foo() { int* p = NULL; }\n"


# ── file.ext: positive (should pass) ────────────────────────────────────

@pytest.mark.parametrize("code,suffix", [
    (SOURCE_CODE, ".cc"),
    (HEADER_CODE, ".hh"),
    (HEADER_CODE, ".hxx"),
], ids=["cc-ok", "hh-ok", "hxx-ok"])
def test_file_ext_pass(check_cxx, code, suffix):
    assert not check_cxx(code, "file.ext", suffix=suffix)


# ── file.ext: negative (should fail) ────────────────────────────────────

@pytest.mark.parametrize("code,suffix", [
    (SOURCE_CODE, ".cpp"),
    (HEADER_CODE, ".hpp"),
], ids=["cpp-bad", "hpp-bad"])
def test_file_ext_fail(check_cxx, code, suffix):
    assert check_cxx(code, "file.ext", suffix=suffix)


# ── file.ext: metadata ──────────────────────────────────────────────────

def test_cpp_still_gets_checked(check_cxx_result):
    """A .cpp file should still get all CXX checks, not just the ext violation."""
    violations = check_cxx_result(SOURCE_WITH_NULLPTR, suffix=".cpp")
    rules = {v.rule for v in violations}
    assert "file.ext" in rules
    assert "global.nullptr" in rules


def test_cpp_ext_is_major(check_cxx_result):
    violations = check_cxx_result(SOURCE_CODE, rule="file.ext", suffix=".cpp")
    assert len(violations) == 1
    assert violations[0].severity == Severity.MAJOR


@pytest.mark.parametrize("suffix,expected", [
    (".cpp", "'.cc'"),
    (".hpp", "'.hh'"),
], ids=["cpp-suggests-cc", "hpp-suggests-hh"])
def test_file_ext_suggestion(check_cxx_result, suffix, expected):
    code = SOURCE_CODE if suffix == ".cpp" else HEADER_CODE
    violations = check_cxx_result(code, rule="file.ext", suffix=suffix)
    assert expected in violations[0].message
