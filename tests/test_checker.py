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
