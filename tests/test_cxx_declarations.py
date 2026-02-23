"""Tests for CXX declaration rules."""


class TestDeclRef:
    """Tests for decl.ref rule (& next to type)."""

    def test_ref_next_to_var(self, check_cxx):
        code = "void foo(int &x) {}\n"
        assert check_cxx(code, "decl.ref")

    def test_ref_next_to_type_ok(self, check_cxx):
        code = "void foo(int& x) {}\n"
        assert not check_cxx(code, "decl.ref")


class TestDeclPoint:
    """Tests for decl.point rule (* next to type)."""

    def test_ptr_next_to_var(self, check_cxx):
        code = "void foo(int *x) {}\n"
        assert check_cxx(code, "decl.point")

    def test_ptr_next_to_type_ok(self, check_cxx):
        code = "void foo(int* x) {}\n"
        assert not check_cxx(code, "decl.point")


class TestCtorExplicit:
    """Tests for decl.ctor.explicit rule."""

    def test_single_arg_not_explicit(self, check_cxx):
        code = "class Foo {\n    Foo(int x);\n};\n"
        assert check_cxx(code, "decl.ctor.explicit")

    def test_single_arg_explicit_ok(self, check_cxx):
        code = "class Foo {\n    explicit Foo(int x);\n};\n"
        assert not check_cxx(code, "decl.ctor.explicit")

    def test_multi_arg_no_explicit_ok(self, check_cxx):
        code = "class Foo {\n    Foo(int x, int y);\n};\n"
        assert not check_cxx(code, "decl.ctor.explicit")

    def test_zero_arg_no_explicit_ok(self, check_cxx):
        code = "class Foo {\n    Foo();\n};\n"
        assert not check_cxx(code, "decl.ctor.explicit")


class TestDeclVla:
    """Tests for decl.vla rule in C++."""

    def test_vla_detected(self, check_cxx):
        code = "void foo(int n) { int arr[n]; }\n"
        assert check_cxx(code, "decl.vla")

    def test_fixed_array_ok(self, check_cxx):
        code = "void foo() { int arr[10]; }\n"
        assert not check_cxx(code, "decl.vla")
