"""Tests for file.ext rule (wrong C++ file extension)."""


class TestFileExt:
    """Tests for file.ext rule — .cpp/.hpp should be flagged."""

    def test_cpp_extension_flagged(self, check_cxx):
        code = "void foo() {}\n"
        assert check_cxx(code, "file.ext", suffix=".cpp")

    def test_hpp_extension_flagged(self, check_cxx):
        code = "#pragma once\nint x;\n"
        assert check_cxx(code, "file.ext", suffix=".hpp")

    def test_cc_extension_ok(self, check_cxx):
        code = "void foo() {}\n"
        assert not check_cxx(code, "file.ext", suffix=".cc")

    def test_hh_extension_ok(self, check_cxx):
        code = "#pragma once\nint x;\n"
        assert not check_cxx(code, "file.ext", suffix=".hh")

    def test_hxx_extension_ok(self, check_cxx):
        code = "#pragma once\nint x;\n"
        assert not check_cxx(code, "file.ext", suffix=".hxx")

    def test_cpp_still_gets_checked(self, check_cxx_result):
        """A .cpp file should still get all CXX checks, not just the ext violation."""
        code = "void foo() { int* p = NULL; }\n"
        violations = check_cxx_result(code, suffix=".cpp")
        rules = {v.rule for v in violations}
        assert "file.ext" in rules
        assert "global.nullptr" in rules

    def test_cpp_ext_is_major(self, check_cxx_result):
        code = "void foo() {}\n"
        violations = check_cxx_result(code, rule="file.ext", suffix=".cpp")
        assert len(violations) == 1
        from epita_coding_style import Severity
        assert violations[0].severity == Severity.MAJOR

    def test_cpp_suggests_cc(self, check_cxx_result):
        code = "void foo() {}\n"
        violations = check_cxx_result(code, rule="file.ext", suffix=".cpp")
        assert "'.cc'" in violations[0].message

    def test_hpp_suggests_hh(self, check_cxx_result):
        code = "#pragma once\nint x;\n"
        violations = check_cxx_result(code, rule="file.ext", suffix=".hpp")
        assert "'.hh'" in violations[0].message
