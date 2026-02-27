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

CTOR_COPY = dedent("""\
    class Foo
    {
        Foo(const Foo& other);
    };
""")

CTOR_MOVE = dedent("""\
    class Foo
    {
        Foo(Foo&& other);
    };
""")

CTOR_COPY_TEMPLATE = dedent("""\
    template<typename T>
    class Bar
    {
        Bar(const Bar<T>& other);
    };
""")

CTOR_MOVE_TEMPLATE = dedent("""\
    template<typename T>
    class Bar
    {
        Bar(Bar<T>&& other);
    };
""")


@pytest.mark.parametrize("code,should_fail", [
    (CTOR_SINGLE_EXPLICIT, False),
    (CTOR_MULTI_ARG, False),
    (CTOR_ZERO_ARG, False),
    (CTOR_COPY, False),
    (CTOR_MOVE, False),
    (CTOR_COPY_TEMPLATE, False),
    (CTOR_MOVE_TEMPLATE, False),
    (CTOR_SINGLE_NOT_EXPLICIT, True),
], ids=["explicit-ok", "multi-arg-ok", "zero-arg-ok", "copy-ctor-ok", "move-ctor-ok",
        "copy-ctor-template-ok", "move-ctor-template-ok", "single-not-explicit"])
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
