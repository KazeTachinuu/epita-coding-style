"""Tests for CXX writing rules."""


class TestBracesEmpty:
    """Tests for braces.empty rule ({} on same line for empty bodies)."""

    def test_empty_body_multiline(self, check_cxx):
        code = "void foo()\n{\n}\n"
        assert check_cxx(code, "braces.empty")

    def test_empty_body_same_line_ok(self, check_cxx):
        code = "void foo() {}\n"
        assert not check_cxx(code, "braces.empty")


class TestBracesSingleExp:
    """Tests for braces.single_exp rule."""

    def test_if_without_braces(self, check_cxx):
        code = "void foo() {\n    if (true)\n        return;\n}\n"
        assert check_cxx(code, "braces.single_exp")

    def test_if_with_braces_ok(self, check_cxx):
        code = "void foo() {\n    if (true) {\n        return;\n    }\n}\n"
        assert not check_cxx(code, "braces.single_exp")


class TestErrThrow:
    """Tests for err.throw rule (don't throw literals)."""

    def test_throw_integer(self, check_cxx):
        code = "void foo() { throw 42; }\n"
        assert check_cxx(code, "err.throw")

    def test_throw_string(self, check_cxx):
        code = 'void foo() { throw "error"; }\n'
        assert check_cxx(code, "err.throw")

    def test_throw_exception_ok(self, check_cxx):
        code = '#include <stdexcept>\nvoid foo() { throw std::runtime_error("err"); }\n'
        assert not check_cxx(code, "err.throw")


class TestErrThrowCatch:
    """Tests for err.throw.catch rule (catch by reference)."""

    def test_catch_by_value(self, check_cxx):
        code = "void foo() {\n    try { throw 1; }\n    catch (int x) {}\n}\n"
        assert check_cxx(code, "err.throw.catch")

    def test_catch_by_reference_ok(self, check_cxx):
        code = "void foo() {\n    try { throw 1; }\n    catch (const int& x) {}\n}\n"
        assert not check_cxx(code, "err.throw.catch")

    def test_catch_ellipsis_ok(self, check_cxx):
        code = "void foo() {\n    try { throw 1; }\n    catch (...) {}\n}\n"
        assert not check_cxx(code, "err.throw.catch")


class TestErrThrowParen:
    """Tests for err.throw.paren rule."""

    def test_throw_with_parens(self, check_cxx):
        code = '#include <stdexcept>\nvoid foo() { throw(std::runtime_error("err")); }\n'
        assert check_cxx(code, "err.throw.paren")

    def test_throw_without_parens_ok(self, check_cxx):
        code = '#include <stdexcept>\nvoid foo() { throw std::runtime_error("err"); }\n'
        assert not check_cxx(code, "err.throw.paren")


class TestExpPadding:
    """Tests for exp.padding rule (no space in operator keyword)."""

    def test_operator_with_space(self, check_cxx):
        code = "class Foo {\n    bool operator ==(const Foo& o);\n};\n"
        assert check_cxx(code, "exp.padding")

    def test_operator_no_space_ok(self, check_cxx):
        code = "class Foo {\n    bool operator==(const Foo& o);\n};\n"
        assert not check_cxx(code, "exp.padding")


class TestFunProtoVoidCxx:
    """Tests for fun.proto.void.cxx rule (no void in empty params)."""

    def test_void_params_in_cxx(self, check_cxx):
        code = "void foo(void) {}\n"
        assert check_cxx(code, "fun.proto.void.cxx")

    def test_empty_params_ok(self, check_cxx):
        code = "void foo() {}\n"
        assert not check_cxx(code, "fun.proto.void.cxx")

    def test_void_in_declaration(self, check_cxx):
        code = "void foo(void);\n"
        assert check_cxx(code, "fun.proto.void.cxx")


class TestOpAssign:
    """Tests for op.assign rule."""

    def test_assign_no_ref_return(self, check_cxx):
        code = "class Foo {\n    Foo operator=(const Foo& o) { return *this; }\n};\n"
        assert check_cxx(code, "op.assign")

    def test_assign_correct_ok(self, check_cxx):
        code = "class Foo {\n    Foo& operator=(const Foo& o) { return *this; }\n};\n"
        assert not check_cxx(code, "op.assign")

    def test_assign_missing_this(self, check_cxx):
        code = "class Foo {\n    Foo& operator=(const Foo& o) { return o; }\n};\n"
        assert check_cxx(code, "op.assign")


class TestOpOverload:
    """Tests for op.overload rule (forbidden overloads)."""

    def test_overload_comma(self, check_cxx):
        code = "class Foo {\n    Foo operator,(const Foo& o);\n};\n"
        assert check_cxx(code, "op.overload")

    def test_overload_logical_or(self, check_cxx):
        code = "class Foo {\n    bool operator||(const Foo& o);\n};\n"
        assert check_cxx(code, "op.overload")

    def test_overload_logical_and(self, check_cxx):
        code = "class Foo {\n    bool operator&&(const Foo& o);\n};\n"
        assert check_cxx(code, "op.overload")

    def test_overload_plus_ok(self, check_cxx):
        code = "class Foo {\n    Foo operator+(const Foo& o);\n};\n"
        assert not check_cxx(code, "op.overload")


class TestOpOverloadBinand:
    """Tests for op.overload.binand rule."""

    def test_overload_address_of(self, check_cxx):
        code = "class Foo {\n    Foo* operator&();\n};\n"
        assert check_cxx(code, "op.overload.binand")


class TestEnumClass:
    """Tests for enum.class rule."""

    def test_plain_enum(self, check_cxx):
        code = "enum Color { Red, Green, Blue };\n"
        assert check_cxx(code, "enum.class")

    def test_enum_class_ok(self, check_cxx):
        code = "enum class Color { Red, Green, Blue };\n"
        assert not check_cxx(code, "enum.class")


class TestExpLinebreak:
    """Tests for exp.linebreak rule."""

    def test_operator_at_end_of_line(self, check_cxx):
        code = "void foo() {\n    int x = 1 +\n        2;\n}\n"
        assert check_cxx(code, "exp.linebreak")

    def test_operator_at_start_of_next_line_ok(self, check_cxx):
        code = "void foo() {\n    int x = 1\n        + 2;\n}\n"
        assert not check_cxx(code, "exp.linebreak")
