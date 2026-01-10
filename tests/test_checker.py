#!/usr/bin/env python3
"""
Test suite for EPITA C Coding Style Checker.

Run from project root:
    pytest tests/ -v
    pytest tests/ --cov=coding_style_checker --cov-report=term-missing
"""

import os
import sys

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from check import Severity


def has_violation(result, rule: str) -> bool:
    """Check if result contains a specific rule violation."""
    return any(v.rule == rule for v in result.violations)


# =============================================================================
# Function Rules
# =============================================================================

class TestFunctionArgCount:
    """fun.arg.count: max 4 arguments."""

    def test_passes_with_4_args(self, checker, temp_file, valid_function_4_args):
        path = temp_file(valid_function_4_args)
        assert not has_violation(checker.check_file(path), "fun.arg.count")

    def test_fails_with_5_args(self, checker, temp_file, invalid_function_5_args):
        path = temp_file(invalid_function_5_args)
        assert has_violation(checker.check_file(path), "fun.arg.count")


class TestFunctionLength:
    """fun.length: max 40 lines (excluding comments, blanks, braces)."""

    def test_passes_short_function(self, checker, temp_file, valid_short_function):
        path = temp_file(valid_short_function)
        assert not has_violation(checker.check_file(path), "fun.length")

    def test_passes_40_lines(self, checker, temp_file, valid_function_40_lines):
        path = temp_file(valid_function_40_lines)
        assert not has_violation(checker.check_file(path), "fun.length")

    def test_fails_41_lines(self, checker, temp_file, invalid_function_41_lines):
        path = temp_file(invalid_function_41_lines)
        assert has_violation(checker.check_file(path), "fun.length")

    def test_comments_not_counted(self, checker, temp_file, valid_function_with_comments):
        path = temp_file(valid_function_with_comments)
        assert not has_violation(checker.check_file(path), "fun.length")

    def test_blanks_not_counted(self, checker, temp_file, valid_function_with_blanks):
        path = temp_file(valid_function_with_blanks)
        assert not has_violation(checker.check_file(path), "fun.length")

    def test_braces_not_counted(self, checker, temp_file, valid_function_with_braces):
        path = temp_file(valid_function_with_braces)
        assert not has_violation(checker.check_file(path), "fun.length")


class TestFunctionProtoVoid:
    """fun.proto.void: empty params should be 'void'."""

    def test_passes_with_void(self, checker, temp_file, valid_header_void_proto):
        path = temp_file(valid_header_void_proto, suffix=".h", name="t.h")
        assert not has_violation(checker.check_file(path), "fun.proto.void")

    def test_fails_empty_params(self, checker, temp_file, invalid_header_empty_proto):
        path = temp_file(invalid_header_empty_proto, suffix=".h", name="t.h")
        assert has_violation(checker.check_file(path), "fun.proto.void")


# =============================================================================
# File Rules
# =============================================================================

class TestFileTrailing:
    """file.trailing: no trailing whitespace."""

    def test_passes_clean(self, checker, temp_file, valid_no_trailing):
        path = temp_file(valid_no_trailing)
        assert not has_violation(checker.check_file(path), "file.trailing")

    def test_fails_with_spaces(self, checker, temp_file, invalid_trailing_space):
        path = temp_file(invalid_trailing_space)
        assert has_violation(checker.check_file(path), "file.trailing")


class TestFileTerminate:
    """file.terminate: must end with newline."""

    def test_passes_with_newline(self, checker, temp_file, valid_with_newline):
        path = temp_file(valid_with_newline)
        assert not has_violation(checker.check_file(path), "file.terminate")

    def test_fails_without_newline(self, checker, temp_file, invalid_no_newline):
        path = temp_file(invalid_no_newline)
        assert has_violation(checker.check_file(path), "file.terminate")


class TestLinesEmpty:
    """lines.empty: no consecutive empty lines."""

    def test_passes_single_blank(self, checker, temp_file, valid_single_blank):
        path = temp_file(valid_single_blank)
        assert not has_violation(checker.check_file(path), "lines.empty")

    def test_fails_double_blank(self, checker, temp_file, invalid_double_blank):
        path = temp_file(invalid_double_blank)
        assert has_violation(checker.check_file(path), "lines.empty")


class TestFileDos:
    """file.dos: no CRLF line endings."""

    def test_fails_with_crlf(self, checker, temp_file, invalid_crlf):
        path = temp_file(invalid_crlf)
        assert has_violation(checker.check_file(path), "file.dos")


class TestFileSpurious:
    """file.spurious: no blank lines at start/end."""

    def test_passes_clean(self, checker, temp_file, valid_with_newline):
        path = temp_file(valid_with_newline)
        assert not has_violation(checker.check_file(path), "file.spurious")

    def test_fails_blank_at_start(self, checker, temp_file, invalid_blank_at_start):
        path = temp_file(invalid_blank_at_start)
        assert has_violation(checker.check_file(path), "file.spurious")

    def test_fails_blank_at_end(self, checker, temp_file, invalid_blank_at_end):
        path = temp_file(invalid_blank_at_end)
        assert has_violation(checker.check_file(path), "file.spurious")


# =============================================================================
# Declaration Rules
# =============================================================================

class TestDeclSingle:
    """decl.single: one declaration per line."""

    def test_passes_single_decl(self, checker, temp_file, valid_single_decl):
        path = temp_file(valid_single_decl)
        assert not has_violation(checker.check_file(path), "decl.single")

    def test_fails_multi_decl(self, checker, temp_file, invalid_multi_decl):
        path = temp_file(invalid_multi_decl)
        assert has_violation(checker.check_file(path), "decl.single")

    def test_for_loop_exception(self, checker, temp_file, valid_for_multi_decl):
        path = temp_file(valid_for_multi_decl)
        assert not has_violation(checker.check_file(path), "decl.single")

    def test_func_params_multiline_not_flagged(self, checker, temp_file, valid_func_params_multiline):
        """Function parameters on multiple lines should NOT trigger decl.single."""
        path = temp_file(valid_func_params_multiline)
        assert not has_violation(checker.check_file(path), "decl.single")

    def test_func_params_typed_after_comma_not_flagged(self, checker, temp_file, valid_func_params_typed_after_comma):
        """Function params with types after comma should NOT trigger decl.single."""
        path = temp_file(valid_func_params_typed_after_comma)
        assert not has_violation(checker.check_file(path), "decl.single")


class TestDeclVla:
    """decl.vla: no variable-length arrays."""

    def test_passes_fixed_array(self, checker, temp_file, valid_fixed_array):
        path = temp_file(valid_fixed_array)
        assert not has_violation(checker.check_file(path), "decl.vla")

    def test_passes_macro_constant_array(self, checker, temp_file, valid_macro_size_array):
        """Macro constants (UPPER_CASE) should NOT be flagged as VLA."""
        path = temp_file(valid_macro_size_array)
        assert not has_violation(checker.check_file(path), "decl.vla")

    def test_fails_vla(self, checker, temp_file, invalid_vla):
        path = temp_file(invalid_vla)
        assert has_violation(checker.check_file(path), "decl.vla")


# =============================================================================
# Preprocessor Rules
# =============================================================================

class TestCppGuard:
    """cpp.guard: header files need include guards."""

    def test_passes_with_guard(self, checker, temp_file, valid_header_with_guard):
        path = temp_file(valid_header_with_guard, suffix=".h", name="my.h")
        assert not has_violation(checker.check_file(path), "cpp.guard")

    def test_fails_no_guard(self, checker, temp_file, invalid_header_no_guard):
        path = temp_file(invalid_header_no_guard, suffix=".h", name="test.h")
        assert has_violation(checker.check_file(path), "cpp.guard")


class TestCppEndif:
    """cpp.if: #endif needs comment."""

    def test_passes_with_comment(self, checker, temp_file, valid_header_endif_comment):
        path = temp_file(valid_header_endif_comment, suffix=".h", name="t.h")
        assert not has_violation(checker.check_file(path), "cpp.if")

    def test_fails_no_comment(self, checker, temp_file, invalid_header_no_endif_comment):
        path = temp_file(invalid_header_no_endif_comment, suffix=".h", name="t.h")
        assert has_violation(checker.check_file(path), "cpp.if")


class TestCppMark:
    """cpp.mark: # must be on first column."""

    def test_passes_first_column(self, checker, temp_file):
        path = temp_file("#include <stdio.h>\n")
        assert not has_violation(checker.check_file(path), "cpp.mark")

    def test_fails_indented(self, checker, temp_file, invalid_indented_hash):
        path = temp_file(invalid_indented_hash)
        assert has_violation(checker.check_file(path), "cpp.mark")


class TestCppDigraphs:
    """cpp.digraphs: no digraphs/trigraphs."""

    def test_fails_with_digraph(self, checker, temp_file, invalid_digraph):
        path = temp_file(invalid_digraph)
        assert has_violation(checker.check_file(path), "cpp.digraphs")


# =============================================================================
# Export Rules
# =============================================================================

class TestExportFun:
    """export.fun: max 10 exported (non-static) functions per .c file."""

    def test_passes_with_10_exported(self, checker, temp_file, valid_10_exported_functions):
        """Exactly 10 exported functions should pass."""
        path = temp_file(valid_10_exported_functions)
        assert not has_violation(checker.check_file(path), "export.fun")

    def test_passes_mixed_static_exported(self, checker, temp_file, valid_mixed_static_exported):
        """Static functions don't count toward the limit."""
        path = temp_file(valid_mixed_static_exported)
        assert not has_violation(checker.check_file(path), "export.fun")

    def test_passes_all_static(self, checker, temp_file, valid_all_static_functions):
        """All static functions should pass (0 exported)."""
        path = temp_file(valid_all_static_functions)
        assert not has_violation(checker.check_file(path), "export.fun")

    def test_fails_with_11_exported(self, checker, temp_file, invalid_11_exported_functions):
        """11 exported functions should fail."""
        path = temp_file(invalid_11_exported_functions)
        assert has_violation(checker.check_file(path), "export.fun")

    def test_fails_with_many_exported(self, checker, temp_file, invalid_many_exported_functions):
        """15 exported functions should fail."""
        path = temp_file(invalid_many_exported_functions)
        assert has_violation(checker.check_file(path), "export.fun")

    def test_header_file_not_checked(self, checker, temp_file, invalid_11_exported_functions):
        """Header files should NOT be checked for export.fun."""
        # Use .h suffix - should pass even with 11 functions
        path = temp_file(invalid_11_exported_functions, suffix=".h", name="many.h")
        assert not has_violation(checker.check_file(path), "export.fun")

    def test_is_major_severity(self, checker, temp_file, invalid_11_exported_functions):
        """export.fun violation should be MAJOR severity."""
        path = temp_file(invalid_11_exported_functions)
        result = checker.check_file(path)
        violations = [v for v in result.violations if v.rule == "export.fun"]
        assert len(violations) > 0
        assert all(v.severity == Severity.MAJOR for v in violations)


class TestExportOther:
    """export.other: max 1 non-function exported symbol per .c file."""

    def test_passes_with_one_exported_global(self, checker, temp_file, valid_one_exported_global):
        """One exported global should pass."""
        path = temp_file(valid_one_exported_global)
        assert not has_violation(checker.check_file(path), "export.other")

    def test_passes_with_static_globals(self, checker, temp_file, valid_static_globals):
        """Static globals don't count as exported."""
        path = temp_file(valid_static_globals)
        assert not has_violation(checker.check_file(path), "export.other")

    def test_fails_with_two_exported_globals(self, checker, temp_file, invalid_two_exported_globals):
        """Two exported globals should fail."""
        path = temp_file(invalid_two_exported_globals)
        assert has_violation(checker.check_file(path), "export.other")

    def test_fails_with_many_exported_globals(self, checker, temp_file, invalid_many_exported_globals):
        """Three exported globals should fail."""
        path = temp_file(invalid_many_exported_globals)
        assert has_violation(checker.check_file(path), "export.other")


# =============================================================================
# Braces Rules
# =============================================================================

class TestBraces:
    """braces: Braces must be on their own line (Allman style)."""

    def test_passes_allman_style(self, checker, temp_file, valid_allman_braces):
        """Correct Allman style should pass."""
        path = temp_file(valid_allman_braces)
        assert not has_violation(checker.check_file(path), "braces")

    def test_passes_initializer_exception(self, checker, temp_file, valid_allman_with_initializer):
        """Array initializers are an exception."""
        path = temp_file(valid_allman_with_initializer)
        assert not has_violation(checker.check_file(path), "braces")

    def test_passes_do_while_exception(self, checker, temp_file, valid_allman_do_while):
        """do-while } while is an exception."""
        path = temp_file(valid_allman_do_while)
        assert not has_violation(checker.check_file(path), "braces")

    def test_fails_kr_function_braces(self, checker, temp_file, invalid_kr_braces):
        """K&R style function braces should fail."""
        path = temp_file(invalid_kr_braces)
        assert has_violation(checker.check_file(path), "braces")

    def test_fails_kr_if_braces(self, checker, temp_file, invalid_kr_if_braces):
        """K&R style if braces should fail."""
        path = temp_file(invalid_kr_if_braces)
        assert has_violation(checker.check_file(path), "braces")

    def test_fails_else_same_line(self, checker, temp_file, invalid_else_same_line):
        """Else on same line as } should fail."""
        path = temp_file(invalid_else_same_line)
        assert has_violation(checker.check_file(path), "braces")


class TestBracesIndent:
    """braces.indent: 4-space indentation, no tabs."""

    def test_passes_4space_indent(self, checker, temp_file, valid_4space_indent):
        """4-space indentation should pass."""
        path = temp_file(valid_4space_indent)
        assert not has_violation(checker.check_file(path), "braces.indent")

    def test_fails_tab_indent(self, checker, temp_file, invalid_tab_indent):
        """Tab indentation should fail."""
        path = temp_file(invalid_tab_indent)
        assert has_violation(checker.check_file(path), "braces.indent")

    def test_fails_2space_indent(self, checker, temp_file, invalid_2space_indent):
        """2-space indentation should fail."""
        path = temp_file(invalid_2space_indent)
        assert has_violation(checker.check_file(path), "braces.indent")

    def test_fails_3space_indent(self, checker, temp_file, invalid_3space_indent):
        """3-space indentation should fail."""
        path = temp_file(invalid_3space_indent)
        assert has_violation(checker.check_file(path), "braces.indent")

    def test_passes_wrapped_condition_and(self, checker, temp_file, valid_wrapped_condition_and):
        """Wrapped condition starting with && should pass."""
        path = temp_file(valid_wrapped_condition_and)
        assert not has_violation(checker.check_file(path), "braces.indent")

    def test_passes_wrapped_condition_or(self, checker, temp_file, valid_wrapped_condition_or):
        """Wrapped condition starting with || should pass."""
        path = temp_file(valid_wrapped_condition_or)
        assert not has_violation(checker.check_file(path), "braces.indent")

    def test_passes_wrapped_else_if_condition(self, checker, temp_file, valid_wrapped_else_if_condition):
        """Wrapped else if condition should pass."""
        path = temp_file(valid_wrapped_else_if_condition)
        assert not has_violation(checker.check_file(path), "braces.indent")


# =============================================================================
# Control Rules
# =============================================================================

class TestControlAsm:
    """stat.asm: no asm declarations."""

    def test_fails_with_asm(self, checker, temp_file, invalid_asm):
        path = temp_file(invalid_asm)
        assert has_violation(checker.check_file(path), "stat.asm")


class TestControlEmpty:
    """ctrl.empty: empty loops should use continue."""

    def test_fails_empty_loop(self, checker, temp_file, invalid_empty_loop):
        path = temp_file(invalid_empty_loop)
        assert has_violation(checker.check_file(path), "ctrl.empty")


# =============================================================================
# Edge Cases (should NOT trigger violations)
# =============================================================================

class TestEdgeCases:
    """Edge cases that should pass."""

    def test_big_enum_passes(self, checker, temp_file, valid_big_enum):
        path = temp_file(valid_big_enum)
        assert not has_violation(checker.check_file(path), "fun.length")

    def test_big_struct_passes(self, checker, temp_file, valid_big_struct):
        path = temp_file(valid_big_struct)
        assert not has_violation(checker.check_file(path), "fun.length")

    def test_static_array_passes(self, checker, temp_file, valid_static_array):
        path = temp_file(valid_static_array)
        assert not has_violation(checker.check_file(path), "fun.length")

    def test_typedef_fn_ptr_passes(self, checker, temp_file, valid_typedef_fn_ptr):
        path = temp_file(valid_typedef_fn_ptr)
        result = checker.check_file(path)
        assert result.major_count == 0


# =============================================================================
# Severity
# =============================================================================

class TestSeverity:
    """Violation severity levels."""

    def test_arg_count_is_major(self, checker, temp_file, invalid_function_5_args):
        path = temp_file(invalid_function_5_args)
        result = checker.check_file(path)
        violations = [v for v in result.violations if v.rule == "fun.arg.count"]
        assert all(v.severity == Severity.MAJOR for v in violations)

    def test_trailing_is_minor(self, checker, temp_file, invalid_trailing_space):
        path = temp_file(invalid_trailing_space)
        result = checker.check_file(path)
        violations = [v for v in result.violations if v.rule == "file.trailing"]
        assert all(v.severity == Severity.MINOR for v in violations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
