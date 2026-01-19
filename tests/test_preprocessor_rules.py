"""Tests for preprocessor rules."""

import pytest
from textwrap import dedent

GUARD_OK = dedent("""\
    #ifndef TEST_H
    #define TEST_H
    int x;
    #endif /* TEST_H */
""")

ENDIF_OK = dedent("""\
    #ifndef TEST_H
    #define TEST_H
    #endif /* TEST_H */
""")

ENDIF_NO_COMMENT = dedent("""\
    #ifndef TEST_H
    #define TEST_H
    #endif
""")


@pytest.mark.parametrize("code,should_fail", [
    (GUARD_OK, False),
    ("int x;\n", True),
])
def test_cpp_guard(check, code, should_fail):
    assert check(code, "cpp.guard", suffix=".h") == should_fail


@pytest.mark.parametrize("code,should_fail", [
    (ENDIF_OK, False),
    (ENDIF_NO_COMMENT, True),
])
def test_cpp_endif_comment(check, code, should_fail):
    assert check(code, "cpp.if", suffix=".h") == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ("#define X 1\n", False),
    ("  #define X 1\n", True),
    ("\t#define X 1\n", True),
])
def test_cpp_mark(check, code, should_fail):
    assert check(code, "cpp.mark") == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ("int arr[10];\n", False),
    ("int arr<:10:>;\n", True),
])
def test_cpp_digraphs(check, code, should_fail):
    assert check(code, "cpp.digraphs") == should_fail
