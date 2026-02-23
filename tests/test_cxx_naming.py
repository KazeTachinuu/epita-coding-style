"""Tests for CXX naming rules."""

import pytest
from textwrap import dedent


# ── naming.class ─────────────────────────────────────────────────────────

CLASS_LOWERCASE = "class my_class {};\n"
CLASS_SNAKE_CASE = "class my_class_name {};\n"
CLASS_CAMELCASE = "class MyClass {};\n"
CLASS_SINGLE_WORD = "class Foo {};\n"
STRUCT_SNAKE_CASE = "struct my_struct {};\n"
STRUCT_CAMELCASE = "struct MyStruct {};\n"


@pytest.mark.parametrize("code,should_fail", [
    (CLASS_CAMELCASE, False),
    (CLASS_SINGLE_WORD, False),
    (STRUCT_CAMELCASE, False),
    (CLASS_LOWERCASE, True),
    (CLASS_SNAKE_CASE, True),
    (STRUCT_SNAKE_CASE, True),
], ids=[
    "class-camelcase-ok", "class-single-word-ok", "struct-camelcase-ok",
    "class-lowercase-bad", "class-snake-bad", "struct-snake-bad",
])
def test_naming_class(check_cxx, code, should_fail):
    assert check_cxx(code, "naming.class") == should_fail


# ── naming.namespace ─────────────────────────────────────────────────────

NS_UPPERCASE = dedent("""\
    namespace MyNamespace
    {
        void foo() {}
    } // namespace MyNamespace
""")

NS_LOWERCASE_OK = dedent("""\
    namespace my_ns
    {
        void foo() {}
    } // namespace my_ns
""")

NS_MISSING_COMMENT = dedent("""\
    namespace my_ns
    {
        void foo() {}
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    (NS_LOWERCASE_OK, False),
    (NS_UPPERCASE, True),
    (NS_MISSING_COMMENT, True),
], ids=["lowercase-ok", "uppercase-bad", "missing-comment-bad"])
def test_naming_namespace(check_cxx, code, should_fail):
    assert check_cxx(code, "naming.namespace") == should_fail
