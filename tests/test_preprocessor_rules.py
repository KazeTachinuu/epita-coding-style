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

ELSE_WITH_COMMENT = dedent("""\
    #ifndef TEST_H
    #define TEST_H
    #ifdef FOO
    int x;
    #else /* !FOO */
    int y;
    #endif /* FOO */
    #endif /* TEST_H */
""")

ELSE_NO_COMMENT = dedent("""\
    #ifndef TEST_H
    #define TEST_H
    #ifdef FOO
    int x;
    #else
    int y;
    #endif /* FOO */
    #endif /* TEST_H */
""")


@pytest.mark.parametrize("code,should_fail", [
    (GUARD_OK, False),
    ("int x;\n", True),
], ids=["guard-ok", "no-guard"])
def test_cpp_guard(check, code, should_fail):
    assert check(code, "cpp.guard", suffix=".h") == should_fail


@pytest.mark.parametrize("code,should_fail", [
    (ENDIF_OK, False),
    (ENDIF_NO_COMMENT, True),
    (ELSE_WITH_COMMENT, False),
    (ELSE_NO_COMMENT, True),
], ids=["endif-comment-ok", "endif-no-comment", "else-comment-ok", "else-no-comment"])
def test_cpp_endif_comment(check, code, should_fail):
    assert check(code, "cpp.if", suffix=".h") == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ("#define X 1\n", False),
    ("  #define X 1\n", True),
    ("\t#define X 1\n", True),
], ids=["col0-ok", "indented-spaces", "indented-tab"])
def test_cpp_mark(check, code, should_fail):
    assert check(code, "cpp.mark") == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ("int arr[10];\n", False),
    ("int arr<:10:>;\n", True),
], ids=["brackets-ok", "digraph-fail"])
def test_cpp_digraphs(check, code, should_fail):
    assert check(code, "cpp.digraphs") == should_fail
