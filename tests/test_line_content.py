"""Tests for line content and column display in violations."""


def test_decl_single_line_content(lint):
    [v] = [v for v in lint("int x, y;\n") if v.rule == "decl.single"]
    assert v.line_content == "int x, y;"
    assert v.column == 0  # Points to start of declaration


def test_braces_line_content(lint):
    # Use noformat preset to test braces independently from clang-format
    [v] = [v for v in lint("void f(void) {\n    return;\n}\n", preset="noformat") if v.rule == "braces"]
    assert v.line_content == "void f(void) {"
    assert v.column == 13  # Position of the opening brace


def test_fun_arg_count_line_content(lint):
    code = "int f(int a, int b, int c, int d, int e) { return 0; }\n"
    [v] = [v for v in lint(code) if v.rule == "fun.arg.count"]
    assert v.line_content is not None
    assert "int f" in v.line_content


def test_trailing_whitespace_line_content(lint):
    [v] = [v for v in lint("int x = 1;   \n") if v.rule == "file.trailing"]
    assert v.line_content == "int x = 1;   "
    assert v.column == 10  # Position where trailing whitespace starts


def test_vla_line_content(lint):
    [v] = [v for v in lint("void f(int n) { int arr[n]; }\n") if v.rule == "decl.vla"]
    assert v.line_content is not None
    assert "[n]" in v.line_content
    assert v.column is not None  # Should point to the bracket


def test_cpp_mark_line_content(lint):
    [v] = [v for v in lint("  #define X 1\n") if v.rule == "cpp.mark"]
    assert v.line_content == "  #define X 1"
    assert v.column == 0
