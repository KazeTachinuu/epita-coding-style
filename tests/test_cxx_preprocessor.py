"""Tests for CXX preprocessor rules."""

import pytest
from textwrap import dedent


# ── cpp.pragma.once ──────────────────────────────────────────────────────

HEADER_WITH_GUARD = "#ifndef FOO_HH\n#define FOO_HH\nint x;\n#endif\n"
HEADER_WITH_PRAGMA = "#pragma once\nint x;\n"
SOURCE_NO_PRAGMA = "int x;\n"


@pytest.mark.parametrize("code,suffix,should_fail", [
    (HEADER_WITH_PRAGMA, ".hh", False),
    (SOURCE_NO_PRAGMA, ".cc", False),
    (HEADER_WITH_GUARD, ".hh", True),
], ids=["pragma-once-ok", "source-file-ok", "guard-instead-of-pragma"])
def test_cpp_pragma_once(check_cxx, code, suffix, should_fail):
    assert check_cxx(code, "cpp.pragma.once", suffix=suffix) == should_fail


# ── cpp.include.filetype ────────────────────────────────────────────────

INCLUDE_SOURCE_CC = '#include "foo.cc"\nint x;\n'
INCLUDE_SOURCE_C = '#include "foo.c"\nint x;\n'
INCLUDE_HEADER_HH = '#include "foo.hh"\nint x;\n'
INCLUDE_HEADER_HXX = '#include "foo.hxx"\nint x;\n'
INCLUDE_HEADER_H = '#include "foo.h"\nint x;\n'
INCLUDE_SYSTEM = "#include <iostream>\nint x;\n"


@pytest.mark.parametrize("code,should_fail", [
    (INCLUDE_HEADER_HH, False),
    (INCLUDE_HEADER_HXX, False),
    (INCLUDE_SYSTEM, False),
    (INCLUDE_SOURCE_CC, True),
    (INCLUDE_SOURCE_C, True),
    (INCLUDE_HEADER_H, True),
], ids=["header-hh-ok", "header-hxx-ok", "system-ok",
        "source-cc-bad", "source-c-bad", "header-h-bad"])
def test_cpp_include_filetype(check_cxx, code, should_fail):
    assert check_cxx(code, "cpp.include.filetype") == should_fail


# ── cpp.include.order ───────────────────────────────────────────────────

# test.cc: same-name header first, then system, then local (with blank lines between groups)
INCLUDE_ORDER_CORRECT = '#include "test.hh"\n\n#include <iostream>\n\n#include "other.hh"\n\nint x;\n'
INCLUDE_SYSTEM_BEFORE_SELF = '#include <iostream>\n\n#include "test.hh"\n\nint x;\n'
INCLUDE_LOCAL_BEFORE_SYSTEM = '#include "other.hh"\n\n#include <iostream>\n\nint x;\n'


@pytest.mark.parametrize("code,should_fail", [
    (INCLUDE_ORDER_CORRECT, False),
    (INCLUDE_SYSTEM_BEFORE_SELF, True),
    (INCLUDE_LOCAL_BEFORE_SYSTEM, True),
], ids=["correct-order", "system-before-self", "local-before-system"])
def test_cpp_include_order(check_cxx, code, should_fail):
    assert check_cxx(code, "cpp.include.order") == should_fail


# .hh file including same-name .hxx at the end is the standard template pattern
HEADER_WITH_HXX_AT_END = '#pragma once\n\n#include <map>\n\nclass Foo {};\n\n#include "test.hxx"\n'


def test_cpp_include_order_hh_hxx_at_end(check_cxx):
    assert check_cxx(HEADER_WITH_HXX_AT_END, "cpp.include.order", suffix=".hh") == False


# ── cpp.include.order (alphabetical) ────────────────────────────────────

INCLUDES_ALPHA_OK = '#include <algorithm>\n#include <vector>\n\n#include "bar.hh"\n#include "foo.hh"\n\nint x;\n'
INCLUDES_ALPHA_BAD = '#include <vector>\n#include <algorithm>\nint x;\n'


@pytest.mark.parametrize("code,should_fail", [
    (INCLUDES_ALPHA_OK, False),
    (INCLUDES_ALPHA_BAD, True),
], ids=["alphabetical-ok", "alphabetical-bad"])
def test_cpp_include_order_alphabetical(check_cxx, code, should_fail):
    assert check_cxx(code, "cpp.include.order") == should_fail


# ── cpp.include.order (blank line between groups) ───────────────────────

INCLUDES_BLANK_LINE_OK = dedent("""\
    #include "test.hh"

    #include <iostream>

    #include "other.hh"

    int x;
""")

INCLUDES_NO_BLANK_LINE = '#include "test.hh"\n#include <iostream>\n#include "other.hh"\nint x;\n'


def test_cpp_include_order_blank_line(check_cxx_result):
    vs = check_cxx_result(INCLUDES_BLANK_LINE_OK, "cpp.include.order")
    blank_line_vs = [v for v in vs if "blank line" in v.message]
    assert blank_line_vs == []

    vs = check_cxx_result(INCLUDES_NO_BLANK_LINE, "cpp.include.order")
    blank_line_vs = [v for v in vs if "blank line" in v.message]
    assert len(blank_line_vs) > 0


# ── cpp.constexpr ───────────────────────────────────────────────────────

CONST_LITERAL = "const int x = 42;\nint main() { return 0; }\n"
CONSTEXPR_LITERAL = "constexpr int x = 42;\nint main() { return 0; }\n"


@pytest.mark.parametrize("code,should_fail", [
    (CONSTEXPR_LITERAL, False),
    (CONST_LITERAL, True),
], ids=["constexpr-ok", "const-should-be-constexpr"])
def test_cpp_constexpr(check_cxx, code, should_fail):
    assert check_cxx(code, "cpp.constexpr") == should_fail
