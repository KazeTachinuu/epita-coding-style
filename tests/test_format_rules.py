"""Tests for clang-format rule with separate C and C++ configs."""

import shutil
import pytest
from epita_coding_style.core import Severity


# Skip all tests if clang-format not installed
pytestmark = pytest.mark.skipif(
    not shutil.which("clang-format"),
    reason="clang-format not installed"
)


# ── General ──────────────────────────────────────────────────────────────


def test_format_disabled(check_result):
    """Format check should be skipped when disabled."""
    violations = check_result("#include <stdio.h>\nint main(void){int x=1;return x;}\n",
                              rule="format", preset="noformat")
    assert not violations


def test_format_is_minor(format_check):
    """Format violations should be MINOR severity."""
    _, fmt = format_check("int main(void){return 0;}\n", ".c")
    assert fmt
    assert all(v.severity == Severity.MINOR for v in fmt)


# ── C: positive (should pass) ───────────────────────────────────────────


C_GOOD_MAIN = """\
#include <stdio.h>

int main(void)
{
    int x = 1;
    return x;
}
"""

C_GOOD_POINTER_RIGHT = """\
void foo(void)
{
    int *x;
    char *y;
}
"""

C_GOOD_HEADER = """\
#ifndef GOOD_H
#define GOOD_H

int foo(void);
int *bar(int *x);

#endif /* GOOD_H */
"""

C_GOOD_ALLMAN = """\
void foo(void)
{
    if (1)
    {
        return;
    }
    else
    {
        return;
    }
}
"""


@pytest.mark.parametrize("code,suffix", [
    (C_GOOD_MAIN, ".c"),
    (C_GOOD_POINTER_RIGHT, ".c"),
    (C_GOOD_HEADER, ".h"),
    (C_GOOD_ALLMAN, ".c"),
], ids=["main", "pointer-right", "header", "allman-braces"])
def test_c_format_pass(format_passes, code, suffix):
    """C: well-formatted code should pass."""
    format_passes(code, suffix)


# ── C: negative (should fail) ───────────────────────────────────────────


C_BAD_KR_BRACES = """\
#include <stdio.h>

int main(void){
    int x = 1;
    return x;
}
"""

C_BAD_POINTER_LEFT = """\
void foo(void)
{
    int* x;
}
"""

C_BAD_HEADER = """\
#ifndef BAD_H
#define BAD_H

int foo(void) ;
int* bar(int* x);

#endif /* BAD_H */
"""

C_BAD_MISSING_SPACES = """\
void foo(void)
{
    int x=1;
}
"""


@pytest.mark.parametrize("code,suffix", [
    (C_BAD_KR_BRACES, ".c"),
    (C_BAD_POINTER_LEFT, ".c"),
    (C_BAD_HEADER, ".h"),
    (C_BAD_MISSING_SPACES, ".c"),
], ids=["kr-braces", "pointer-left", "header", "missing-spaces"])
def test_c_format_fail(format_fails, code, suffix):
    """C: badly formatted code should fail."""
    format_fails(code, suffix)


# ── C++: positive (should pass) ─────────────────────────────────────────


CXX_GOOD_MAIN = """\
#include <iostream>

int main()
{
    int x = 1;
    return x;
}
"""

CXX_GOOD_POINTER_LEFT = """\
void foo()
{
    int* x = nullptr;
    char* y = nullptr;
}
"""

CXX_GOOD_REFERENCE_LEFT = """\
void foo(int& x, const int& y)
{
    x = y;
}
"""

CXX_GOOD_HH_HEADER = """\
#pragma once

class Foo
{
public:
    int* get();
    void set(int& val);
};
"""

CXX_GOOD_HXX_HEADER = """\
#pragma once

template <typename T>
class Foo
{
public:
    T* get();
    void set(T& val);
};
"""

CXX_GOOD_ALLMAN = """\
void foo()
{
    if (true)
    {
        return;
    }
    else
    {
        return;
    }
}
"""


@pytest.mark.parametrize("code,suffix", [
    (CXX_GOOD_MAIN, ".cc"),
    (CXX_GOOD_POINTER_LEFT, ".cc"),
    (CXX_GOOD_REFERENCE_LEFT, ".cc"),
    (CXX_GOOD_HH_HEADER, ".hh"),
    (CXX_GOOD_HXX_HEADER, ".hxx"),
    (CXX_GOOD_ALLMAN, ".cc"),
], ids=["main", "pointer-left", "reference-left", "hh-header", "hxx-header", "allman-braces"])
def test_cxx_format_pass(format_passes, code, suffix):
    """C++: well-formatted code should pass."""
    format_passes(code, suffix)


# ── C++: negative (should fail) ─────────────────────────────────────────


CXX_BAD_KR_BRACES = """\
#include <iostream>

int main(){
    int x = 1;
    return x;
}
"""

CXX_BAD_POINTER_RIGHT = """\
void foo()
{
    int *x = nullptr;
}
"""

CXX_BAD_REFERENCE_RIGHT = """\
void foo(int &x)
{
    x = 1;
}
"""

CXX_BAD_HH_HEADER = """\
#pragma once

class Foo {
public:
    int *get();
    void set(int &val);
};
"""

CXX_BAD_MISSING_SPACES = """\
void foo()
{
    int x=1;
}
"""


@pytest.mark.parametrize("code,suffix", [
    (CXX_BAD_KR_BRACES, ".cc"),
    (CXX_BAD_POINTER_RIGHT, ".cc"),
    (CXX_BAD_REFERENCE_RIGHT, ".cc"),
    (CXX_BAD_HH_HEADER, ".hh"),
    (CXX_BAD_MISSING_SPACES, ".cc"),
], ids=["kr-braces", "pointer-right", "reference-right", "hh-header", "missing-spaces"])
def test_cxx_format_fail(format_fails, code, suffix):
    """C++: badly formatted code should fail."""
    format_fails(code, suffix)


# ── Cross-language: pointer alignment divergence ────────────────────────


def test_pointer_right_passes_c_fails_cxx(format_passes, format_fails):
    """int *x is correct in C but wrong in C++."""
    c_code = "void foo(void)\n{\n    int *x;\n}\n"
    cxx_code = "void foo()\n{\n    int *x = nullptr;\n}\n"
    format_passes(c_code, ".c", "int *x should pass in C")
    format_fails(cxx_code, ".cc", "int *x should fail in C++")


def test_pointer_left_passes_cxx_fails_c(format_passes, format_fails):
    """int* x is correct in C++ but wrong in C."""
    c_code = "void foo(void)\n{\n    int* x;\n}\n"
    cxx_code = "void foo()\n{\n    int* x = nullptr;\n}\n"
    format_fails(c_code, ".c", "int* x should fail in C")
    format_passes(cxx_code, ".cc", "int* x should pass in C++")
