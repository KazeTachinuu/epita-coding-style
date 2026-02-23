"""Tests for CXX declaration rules."""

import pytest
from textwrap import dedent


# ── decl.ref ─────────────────────────────────────────────────────────────

REF_NEXT_TO_VAR = "void foo(int &x) {}\n"
REF_NEXT_TO_TYPE = "void foo(int& x) {}\n"


@pytest.mark.parametrize("code,should_fail", [
    (REF_NEXT_TO_TYPE, False),
    (REF_NEXT_TO_VAR, True),
], ids=["ref-left-ok", "ref-right-bad"])
def test_decl_ref(check_cxx, code, should_fail):
    assert check_cxx(code, "decl.ref") == should_fail


# ── decl.point ───────────────────────────────────────────────────────────

PTR_NEXT_TO_VAR = "void foo(int *x) {}\n"
PTR_NEXT_TO_TYPE = "void foo(int* x) {}\n"


@pytest.mark.parametrize("code,should_fail", [
    (PTR_NEXT_TO_TYPE, False),
    (PTR_NEXT_TO_VAR, True),
], ids=["ptr-left-ok", "ptr-right-bad"])
def test_decl_point(check_cxx, code, should_fail):
    assert check_cxx(code, "decl.point") == should_fail


# ── decl.ctor.explicit ──────────────────────────────────────────────────

CTOR_SINGLE_NOT_EXPLICIT = dedent("""\
    class Foo
    {
        Foo(int x);
    };
""")

CTOR_SINGLE_EXPLICIT = dedent("""\
    class Foo
    {
        explicit Foo(int x);
    };
""")

CTOR_MULTI_ARG = dedent("""\
    class Foo
    {
        Foo(int x, int y);
    };
""")

CTOR_ZERO_ARG = dedent("""\
    class Foo
    {
        Foo();
    };
""")


@pytest.mark.parametrize("code,should_fail", [
    (CTOR_SINGLE_EXPLICIT, False),
    (CTOR_MULTI_ARG, False),
    (CTOR_ZERO_ARG, False),
    (CTOR_SINGLE_NOT_EXPLICIT, True),
], ids=["explicit-ok", "multi-arg-ok", "zero-arg-ok", "single-not-explicit"])
def test_decl_ctor_explicit(check_cxx, code, should_fail):
    assert check_cxx(code, "decl.ctor.explicit") == should_fail


# ── decl.vla (C++) ──────────────────────────────────────────────────────

VLA_DETECTED = "void foo(int n) { int arr[n]; }\n"
FIXED_ARRAY = "void foo() { int arr[10]; }\n"


@pytest.mark.parametrize("code,should_fail", [
    (FIXED_ARRAY, False),
    (VLA_DETECTED, True),
], ids=["fixed-array-ok", "vla-detected"])
def test_decl_vla(check_cxx, code, should_fail):
    assert check_cxx(code, "decl.vla") == should_fail
