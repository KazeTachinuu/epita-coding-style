"""Tests for CXX writing rules."""

import pytest
from textwrap import dedent


# ── braces.empty ─────────────────────────────────────────────────────────

EMPTY_BODY_MULTILINE = "void foo()\n{\n}\n"
EMPTY_BODY_SAME_LINE = "void foo() {}\n"
EMPTY_BODY_SPACE = "void foo() { }\n"


@pytest.mark.parametrize("code,should_fail", [
    (EMPTY_BODY_SAME_LINE, False),
    (EMPTY_BODY_MULTILINE, True),
    (EMPTY_BODY_SPACE, True),
], ids=["same-line-ok", "multiline-bad", "space-inside-bad"])
def test_braces_empty(check_cxx, code, should_fail):
    assert check_cxx(code, "braces.empty") == should_fail


# ── braces.single_exp ───────────────────────────────────────────────────

IF_WITHOUT_BRACES = dedent("""\
    void foo()
    {
        if (true)
            return;
    }
""")

IF_WITH_BRACES = dedent("""\
    void foo()
    {
        if (true)
        {
            return;
        }
    }
""")

ELSE_WITHOUT_BRACES = dedent("""\
    void foo()
    {
        if (true)
        {
            return;
        }
        else
            return;
    }
""")

ELSE_WITH_BRACES = dedent("""\
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
""")

DO_WITHOUT_BRACES = dedent("""\
    void foo()
    {
        do
            continue;
        while (true);
    }
""")

DO_WITH_BRACES = dedent("""\
    void foo()
    {
        do
        {
            continue;
        }
        while (true);
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    (IF_WITH_BRACES, False),
    (IF_WITHOUT_BRACES, True),
    (ELSE_WITH_BRACES, False),
    (ELSE_WITHOUT_BRACES, True),
    (DO_WITH_BRACES, False),
    (DO_WITHOUT_BRACES, True),
], ids=["if-with-braces-ok", "if-without-braces-bad",
        "else-with-braces-ok", "else-without-braces-bad",
        "do-with-braces-ok", "do-without-braces-bad"])
def test_braces_single_exp(check_cxx, code, should_fail):
    assert check_cxx(code, "braces.single_exp") == should_fail


# ── err.throw ────────────────────────────────────────────────────────────

THROW_INTEGER = "void foo() { throw 42; }\n"
THROW_STRING = 'void foo() { throw "error"; }\n'
THROW_EXCEPTION = '#include <stdexcept>\nvoid foo() { throw std::runtime_error("err"); }\n'
THROW_NEW = '#include <stdexcept>\nvoid foo() { throw new std::runtime_error("err"); }\n'


@pytest.mark.parametrize("code,should_fail", [
    (THROW_EXCEPTION, False),
    (THROW_INTEGER, True),
    (THROW_STRING, True),
    (THROW_NEW, True),
], ids=["exception-ok", "integer-bad", "string-bad", "throw-new-bad"])
def test_err_throw(check_cxx, code, should_fail):
    assert check_cxx(code, "err.throw") == should_fail


# ── err.throw.catch ──────────────────────────────────────────────────────

CATCH_BY_VALUE = dedent("""\
    void foo()
    {
        try { throw 1; }
        catch (int x) {}
    }
""")

CATCH_BY_REF = dedent("""\
    void foo()
    {
        try { throw 1; }
        catch (const int& x) {}
    }
""")

CATCH_ELLIPSIS = dedent("""\
    void foo()
    {
        try { throw 1; }
        catch (...) {}
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    (CATCH_BY_REF, False),
    (CATCH_ELLIPSIS, False),
    (CATCH_BY_VALUE, True),
], ids=["by-ref-ok", "ellipsis-ok", "by-value-bad"])
def test_err_throw_catch(check_cxx, code, should_fail):
    assert check_cxx(code, "err.throw.catch") == should_fail


# ── err.throw.paren ─────────────────────────────────────────────────────

THROW_WITH_PARENS = '#include <stdexcept>\nvoid foo() { throw(std::runtime_error("err")); }\n'
THROW_WITHOUT_PARENS = '#include <stdexcept>\nvoid foo() { throw std::runtime_error("err"); }\n'


@pytest.mark.parametrize("code,should_fail", [
    (THROW_WITHOUT_PARENS, False),
    (THROW_WITH_PARENS, True),
], ids=["no-parens-ok", "parens-bad"])
def test_err_throw_paren(check_cxx, code, should_fail):
    assert check_cxx(code, "err.throw.paren") == should_fail


# ── exp.padding ──────────────────────────────────────────────────────────

OPERATOR_WITH_SPACE = dedent("""\
    class Foo
    {
        bool operator ==(const Foo& o);
    };
""")

OPERATOR_NO_SPACE = dedent("""\
    class Foo
    {
        bool operator==(const Foo& o);
    };
""")

OPERATOR_CAST_BOOL = dedent("""\
    class Foo
    {
        operator bool() const;
    };
""")

OPERATOR_CAST_INT = dedent("""\
    class Foo
    {
        operator int() const;
    };
""")


@pytest.mark.parametrize("code,should_fail", [
    (OPERATOR_NO_SPACE, False),
    (OPERATOR_WITH_SPACE, True),
    (OPERATOR_CAST_BOOL, False),
    (OPERATOR_CAST_INT, False),
], ids=["no-space-ok", "space-bad", "cast-bool-ok", "cast-int-ok"])
def test_exp_padding(check_cxx, code, should_fail):
    assert check_cxx(code, "exp.padding") == should_fail


# ── fun.proto.void.cxx ──────────────────────────────────────────────────

VOID_PARAMS = "void foo(void) {}\n"
EMPTY_PARAMS = "void foo() {}\n"
VOID_IN_DECL = "void foo(void);\n"


@pytest.mark.parametrize("code,should_fail", [
    (EMPTY_PARAMS, False),
    (VOID_PARAMS, True),
    (VOID_IN_DECL, True),
], ids=["empty-params-ok", "void-params-bad", "void-in-decl-bad"])
def test_fun_proto_void_cxx(check_cxx, code, should_fail):
    assert check_cxx(code, "fun.proto.void.cxx") == should_fail


# ── op.assign ────────────────────────────────────────────────────────────

ASSIGN_NO_REF_RETURN = dedent("""\
    class Foo
    {
        Foo operator=(const Foo& o) { return *this; }
    };
""")

ASSIGN_CORRECT = dedent("""\
    class Foo
    {
        Foo& operator=(const Foo& o) { return *this; }
    };
""")

ASSIGN_MISSING_THIS = dedent("""\
    class Foo
    {
        Foo& operator=(const Foo& o) { return o; }
    };
""")

ASSIGN_EQUALITY_NOT_ASSIGN = dedent("""\
    class Foo
    {
        bool operator==(const Foo& o) const { return true; }
    };
""")

ASSIGN_COMPOUND_NOT_ASSIGN = dedent("""\
    class Foo
    {
        Foo& operator+=(const Foo& o) { return *this; }
    };
""")


@pytest.mark.parametrize("code,should_fail", [
    (ASSIGN_CORRECT, False),
    (ASSIGN_NO_REF_RETURN, True),
    (ASSIGN_MISSING_THIS, True),
    (ASSIGN_EQUALITY_NOT_ASSIGN, False),
    (ASSIGN_COMPOUND_NOT_ASSIGN, False),
], ids=["correct-ok", "no-ref-return-bad", "missing-this-bad",
        "equality-not-assign-ok", "compound-not-assign-ok"])
def test_op_assign(check_cxx, code, should_fail):
    assert check_cxx(code, "op.assign") == should_fail


# ── op.overload ──────────────────────────────────────────────────────────

OVERLOAD_COMMA = dedent("""\
    class Foo
    {
        Foo operator,(const Foo& o);
    };
""")

OVERLOAD_LOGICAL_OR = dedent("""\
    class Foo
    {
        bool operator||(const Foo& o);
    };
""")

OVERLOAD_LOGICAL_AND = dedent("""\
    class Foo
    {
        bool operator&&(const Foo& o);
    };
""")

OVERLOAD_PLUS = dedent("""\
    class Foo
    {
        Foo operator+(const Foo& o);
    };
""")


@pytest.mark.parametrize("code,should_fail", [
    (OVERLOAD_PLUS, False),
    (OVERLOAD_COMMA, True),
    (OVERLOAD_LOGICAL_OR, True),
    (OVERLOAD_LOGICAL_AND, True),
], ids=["plus-ok", "comma-bad", "logical-or-bad", "logical-and-bad"])
def test_op_overload(check_cxx, code, should_fail):
    assert check_cxx(code, "op.overload") == should_fail


# ── op.overload.binand ──────────────────────────────────────────────────

OVERLOAD_ADDRESS_OF = dedent("""\
    class Foo
    {
        Foo* operator&();
    };
""")


def test_op_overload_binand(check_cxx):
    assert check_cxx(OVERLOAD_ADDRESS_OF, "op.overload.binand")


# ── enum.class ───────────────────────────────────────────────────────────

PLAIN_ENUM = "enum Color { Red, Green, Blue };\n"
ENUM_CLASS = "enum class Color { Red, Green, Blue };\n"


@pytest.mark.parametrize("code,should_fail", [
    (ENUM_CLASS, False),
    (PLAIN_ENUM, True),
], ids=["enum-class-ok", "plain-enum-bad"])
def test_enum_class(check_cxx, code, should_fail):
    assert check_cxx(code, "enum.class") == should_fail


# ── exp.linebreak ───────────────────────────────────────────────────────

OPERATOR_END_OF_LINE = dedent("""\
    void foo()
    {
        int x = 1 +
            2;
    }
""")

OPERATOR_START_OF_NEXT = dedent("""\
    void foo()
    {
        int x = 1
            + 2;
    }
""")


TEMPLATE_CLOSING_ANGLE = dedent("""\
    template <typename Lhs, typename Rhs>
    class Bimap
    {};
""")

TEMPLATE_FUNCTION = dedent("""\
    template <typename Lhs, typename Rhs>
    auto foo(const Lhs& a, const Rhs& b) -> bool
    {
        return true;
    }
""")

REFERENCE_RETURN_TYPE = dedent("""\
    template <typename T>
    auto get() const -> const std::map<int, T>&
    {
        return m_;
    }
""")

REFERENCE_PARAM = dedent("""\
    void foo(const std::string& s)
    {}
""")

NESTED_TEMPLATE = dedent("""\
    std::map<int, std::map<int, int>> m;
""")

POINTER_RETURN_TYPE = dedent("""\
    int* get()
    {
        return nullptr;
    }
""")

REAL_BINARY_OP_AT_EOL = dedent("""\
    void foo()
    {
        bool x = a &&
            b;
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    (OPERATOR_START_OF_NEXT, False),
    (OPERATOR_END_OF_LINE, True),
    (TEMPLATE_CLOSING_ANGLE, False),
    (TEMPLATE_FUNCTION, False),
    (REFERENCE_RETURN_TYPE, False),
    (REFERENCE_PARAM, False),
    (NESTED_TEMPLATE, False),
    (POINTER_RETURN_TYPE, False),
    (REAL_BINARY_OP_AT_EOL, True),
], ids=[
    "start-of-next-ok",
    "end-of-line-bad",
    "template-closing-angle-ok",
    "template-function-ok",
    "reference-return-type-ok",
    "reference-param-ok",
    "nested-template-ok",
    "pointer-return-type-ok",
    "real-binary-op-at-eol-bad",
])
def test_exp_linebreak(check_cxx, code, should_fail):
    assert check_cxx(code, "exp.linebreak") == should_fail
