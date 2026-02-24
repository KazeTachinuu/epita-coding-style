"""Tests for CXX preprocessor rules."""

import pytest


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
INCLUDE_SYSTEM = "#include <iostream>\nint x;\n"


@pytest.mark.parametrize("code,should_fail", [
    (INCLUDE_HEADER_HH, False),
    (INCLUDE_SYSTEM, False),
    (INCLUDE_SOURCE_CC, True),
    (INCLUDE_SOURCE_C, True),
], ids=["header-ok", "system-ok", "source-cc-bad", "source-c-bad"])
def test_cpp_include_filetype(check_cxx, code, should_fail):
    assert check_cxx(code, "cpp.include.filetype") == should_fail


# ── cpp.include.order ───────────────────────────────────────────────────

# test.cc: same-name header first, then system, then local
INCLUDE_ORDER_CORRECT = '#include "test.hh"\n#include <iostream>\n#include "other.hh"\nint x;\n'
INCLUDE_SYSTEM_BEFORE_SELF = '#include <iostream>\n#include "test.hh"\nint x;\n'
INCLUDE_LOCAL_BEFORE_SYSTEM = '#include "other.hh"\n#include <iostream>\nint x;\n'


@pytest.mark.parametrize("code,should_fail", [
    (INCLUDE_ORDER_CORRECT, False),
    (INCLUDE_SYSTEM_BEFORE_SELF, True),
    (INCLUDE_LOCAL_BEFORE_SYSTEM, True),
], ids=["correct-order", "system-before-self", "local-before-system"])
def test_cpp_include_order(check_cxx, code, should_fail):
    assert check_cxx(code, "cpp.include.order") == should_fail


# .hh file including same-name .hxx at the end is the standard template pattern
HEADER_WITH_HXX_AT_END = '#pragma once\n#include <map>\nclass Foo {};\n#include "test.hxx"\n'


def test_cpp_include_order_hh_hxx_at_end(check_cxx):
    assert check_cxx(HEADER_WITH_HXX_AT_END, "cpp.include.order", suffix=".hh") == False


# ── cpp.constexpr ───────────────────────────────────────────────────────

CONST_LITERAL = "const int x = 42;\nint main() { return 0; }\n"
CONSTEXPR_LITERAL = "constexpr int x = 42;\nint main() { return 0; }\n"


@pytest.mark.parametrize("code,should_fail", [
    (CONSTEXPR_LITERAL, False),
    (CONST_LITERAL, True),
], ids=["constexpr-ok", "const-should-be-constexpr"])
def test_cpp_constexpr(check_cxx, code, should_fail):
    assert check_cxx(code, "cpp.constexpr") == should_fail
