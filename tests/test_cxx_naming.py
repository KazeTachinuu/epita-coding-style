"""Tests for CXX naming rules."""


class TestNamingClass:
    """Tests for naming.class rule (CamelCase class/struct names)."""

    def test_lowercase_class_name(self, check_cxx):
        code = "class my_class {};\n"
        assert check_cxx(code, "naming.class")

    def test_snake_case_class(self, check_cxx):
        code = "class my_class_name {};\n"
        assert check_cxx(code, "naming.class")

    def test_camelcase_class_ok(self, check_cxx):
        code = "class MyClass {};\n"
        assert not check_cxx(code, "naming.class")

    def test_single_word_class_ok(self, check_cxx):
        code = "class Foo {};\n"
        assert not check_cxx(code, "naming.class")

    def test_struct_naming(self, check_cxx):
        code = "struct my_struct {};\n"
        assert check_cxx(code, "naming.class")

    def test_struct_camelcase_ok(self, check_cxx):
        code = "struct MyStruct {};\n"
        assert not check_cxx(code, "naming.class")


class TestNamingNamespace:
    """Tests for naming.namespace rule."""

    def test_uppercase_namespace(self, check_cxx):
        code = "namespace MyNamespace {\nvoid foo() {}\n} // namespace MyNamespace\n"
        assert check_cxx(code, "naming.namespace")

    def test_lowercase_namespace_ok(self, check_cxx):
        code = "namespace my_ns {\nvoid foo() {}\n} // namespace my_ns\n"
        assert not check_cxx(code, "naming.namespace")

    def test_missing_closing_comment(self, check_cxx):
        code = "namespace my_ns {\nvoid foo() {}\n}\n"
        assert check_cxx(code, "naming.namespace")

    def test_correct_closing_comment(self, check_cxx):
        code = "namespace my_ns {\nvoid foo() {}\n} // namespace my_ns\n"
        assert not check_cxx(code, "naming.namespace")
