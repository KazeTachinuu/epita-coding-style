"""Tests for CXX preprocessor rules."""


class TestPragmaOnce:
    """Tests for cpp.pragma.once rule."""

    def test_missing_pragma_once_in_header(self, check_cxx):
        code = "#ifndef FOO_HH\n#define FOO_HH\nint x;\n#endif\n"
        assert check_cxx(code, "cpp.pragma.once", suffix=".hh")

    def test_has_pragma_once(self, check_cxx):
        code = "#pragma once\nint x;\n"
        assert not check_cxx(code, "cpp.pragma.once", suffix=".hh")

    def test_not_checked_for_source_files(self, check_cxx):
        code = "int x;\n"
        assert not check_cxx(code, "cpp.pragma.once", suffix=".cc")


class TestIncludeFiletype:
    """Tests for cpp.include.filetype rule."""

    def test_include_source_file(self, check_cxx):
        code = '#include "foo.cc"\nint x;\n'
        assert check_cxx(code, "cpp.include.filetype")

    def test_include_c_file(self, check_cxx):
        code = '#include "foo.c"\nint x;\n'
        assert check_cxx(code, "cpp.include.filetype")

    def test_include_header_ok(self, check_cxx):
        code = '#include "foo.hh"\nint x;\n'
        assert not check_cxx(code, "cpp.include.filetype")

    def test_include_system_header_ok(self, check_cxx):
        code = "#include <iostream>\nint x;\n"
        assert not check_cxx(code, "cpp.include.filetype")


class TestIncludeOrder:
    """Tests for cpp.include.order rule."""

    def test_correct_order(self, check_cxx):
        # test.cc: same-name header first, then system, then local
        code = '#include "test.hh"\n#include <iostream>\n#include "other.hh"\nint x;\n'
        assert not check_cxx(code, "cpp.include.order")

    def test_system_before_self(self, check_cxx):
        code = '#include <iostream>\n#include "test.hh"\nint x;\n'
        assert check_cxx(code, "cpp.include.order")

    def test_local_before_system(self, check_cxx):
        code = '#include "other.hh"\n#include <iostream>\nint x;\n'
        assert check_cxx(code, "cpp.include.order")


class TestConstexpr:
    """Tests for cpp.constexpr rule."""

    def test_const_literal_should_be_constexpr(self, check_cxx):
        code = "const int x = 42;\nint main() { return 0; }\n"
        assert check_cxx(code, "cpp.constexpr")

    def test_constexpr_is_ok(self, check_cxx):
        code = "constexpr int x = 42;\nint main() { return 0; }\n"
        assert not check_cxx(code, "cpp.constexpr")
