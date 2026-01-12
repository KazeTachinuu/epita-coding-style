"""Tests for preprocessor rules."""

import pytest


# cpp.guard: header files need include guards
@pytest.mark.parametrize("code,should_fail", [
    ("#ifndef TEST_H\n#define TEST_H\nint x;\n#endif /* TEST_H */\n", False),
    ("int x;\n", True),
])
def test_cpp_guard(check, code, should_fail):
    assert check(code, "cpp.guard", suffix=".h") == should_fail


# cpp.if: #endif needs comment
@pytest.mark.parametrize("code,should_fail", [
    ("#ifndef TEST_H\n#define TEST_H\n#endif /* TEST_H */\n", False),
    ("#ifndef TEST_H\n#define TEST_H\n#endif\n", True),
])
def test_cpp_endif_comment(check, code, should_fail):
    assert check(code, "cpp.if", suffix=".h") == should_fail


# cpp.mark: # must be on first column
@pytest.mark.parametrize("code,should_fail", [
    ("#define X 1\n", False),
    ("  #define X 1\n", True),
    ("\t#define X 1\n", True),
])
def test_cpp_mark(check, code, should_fail):
    assert check(code, "cpp.mark") == should_fail


# cpp.digraphs: no digraphs/trigraphs
@pytest.mark.parametrize("code,should_fail", [
    ("int arr[10];\n", False),
    ("int arr<:10:>;\n", True),
])
def test_cpp_digraphs(check, code, should_fail):
    assert check(code, "cpp.digraphs") == should_fail
