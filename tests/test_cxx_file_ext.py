"""Tests for file.ext rule (wrong C++ file extension)."""

import pytest

from epita_coding_style import Severity

# Test data

SOURCE_CODE = "void foo() {}\n"
HEADER_CODE = "#pragma once\nint x;\n"
SOURCE_WITH_NULLPTR = "void foo() { int* p = NULL; }\n"


# file.ext: positive (should pass)

@pytest.mark.parametrize("code,suffix", [
    (SOURCE_CODE, ".cc"),
    (HEADER_CODE, ".hh"),
    (HEADER_CODE, ".hxx"),
], ids=["cc-ok", "hh-ok", "hxx-ok"])
def test_file_ext_pass(rules, code, suffix):
    assert "file.ext" not in rules(code, suffix)


# file.ext: negative (should fail)

@pytest.mark.parametrize("code,suffix", [
    (SOURCE_CODE, ".cpp"),
    (HEADER_CODE, ".hpp"),
], ids=["cpp-bad", "hpp-bad"])
def test_file_ext_fail(rules, code, suffix):
    assert "file.ext" in rules(code, suffix)


# file.ext: metadata

def test_cpp_still_gets_checked(rules):
    """A .cpp file should still get all CXX checks, not just the ext violation."""
    assert {"file.ext", "global.nullptr"} <= rules(SOURCE_WITH_NULLPTR, ".cpp")


def test_cpp_ext_is_major(lint):
    violations = [v for v in lint(SOURCE_CODE, ".cpp") if v.rule == "file.ext"]
    assert len(violations) == 1
    assert violations[0].severity == Severity.MAJOR


@pytest.mark.parametrize("suffix,expected", [
    (".cpp", "'.cc'"),
    (".hpp", "'.hh'"),
], ids=["cpp-suggests-cc", "hpp-suggests-hh"])
def test_file_ext_suggestion(lint, suffix, expected):
    code = SOURCE_CODE if suffix == ".cpp" else HEADER_CODE
    violations = [v for v in lint(code, suffix) if v.rule == "file.ext"]
    assert expected in violations[0].message
