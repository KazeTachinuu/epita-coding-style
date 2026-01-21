"""Tests for line content and column display in violations."""

import pytest


def test_decl_single_line_content(check_result):
    """Test that decl.single violation includes line content and column."""
    code = "int x, y;\n"
    violations = check_result(code)
    v = next((v for v in violations if v.rule == "decl.single"), None)
    assert v is not None
    assert v.line_content == "int x, y;"
    assert v.column == 0  # Points to start of declaration


def test_braces_line_content(check_result):
    """Test that braces violation includes line content and column."""
    code = "void f(void) {\n    return;\n}\n"
    # Use noformat preset to test braces independently from clang-format
    violations = check_result(code, preset="noformat")
    v = next((v for v in violations if v.rule == "braces"), None)
    assert v is not None
    assert v.line_content == "void f(void) {"
    assert v.column == 13  # Position of the opening brace


def test_fun_arg_count_line_content(check_result):
    """Test that fun.arg.count violation includes line content."""
    code = "int f(int a, int b, int c, int d, int e) { return 0; }\n"
    violations = check_result(code)
    v = next((v for v in violations if v.rule == "fun.arg.count"), None)
    assert v is not None
    assert v.line_content is not None
    assert "int f" in v.line_content


def test_trailing_whitespace_line_content(check_result):
    """Test that file.trailing violation includes line content and column."""
    code = "int x = 1;   \n"
    violations = check_result(code)
    v = next((v for v in violations if v.rule == "file.trailing"), None)
    assert v is not None
    assert v.line_content == "int x = 1;   "
    assert v.column == 10  # Position where trailing whitespace starts


def test_vla_line_content(check_result):
    """Test that decl.vla violation includes line content and column."""
    code = "void f(int n) { int arr[n]; }\n"
    violations = check_result(code)
    v = next((v for v in violations if v.rule == "decl.vla"), None)
    assert v is not None
    assert v.line_content is not None
    assert "[n]" in v.line_content
    assert v.column is not None  # Should point to the bracket


def test_cpp_mark_line_content(check_result):
    """Test that cpp.mark violation includes line content."""
    code = "  #define X 1\n"
    violations = check_result(code, suffix=".c")
    v = next((v for v in violations if v.rule == "cpp.mark"), None)
    assert v is not None
    assert v.line_content == "  #define X 1"
    assert v.column == 0
