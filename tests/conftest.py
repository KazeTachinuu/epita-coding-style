"""
Pytest fixtures for EPITA C Coding Style Checker tests.
"""

import os
import sys
import tempfile

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from check import CodingStyleChecker


# =============================================================================
# Checker Fixtures
# =============================================================================

@pytest.fixture
def checker():
    """Default checker (40 lines, 4 args)."""
    return CodingStyleChecker(max_func_lines=40, max_func_args=4)


# =============================================================================
# File Management
# =============================================================================

class TempCFile:
    """Manages temporary C/H files for testing."""

    def __init__(self):
        self._files = []

    def create(self, content: str, suffix: str = ".c", name: str = None) -> str:
        # Use binary mode if content contains CRLF to preserve it
        binary = '\r' in content
        mode = 'wb' if binary else 'w'
        data = content.encode() if binary else content

        if name:
            path = f"/tmp/{name}"
            with open(path, mode) as f:
                f.write(data)
        else:
            fd, path = tempfile.mkstemp(suffix=suffix)
            with os.fdopen(fd, mode) as f:
                f.write(data)
        self._files.append(path)
        return path

    def cleanup(self):
        for path in self._files:
            if os.path.exists(path):
                os.unlink(path)


@pytest.fixture
def temp_file():
    """Factory for creating temp files."""
    manager = TempCFile()
    yield manager.create
    manager.cleanup()


# =============================================================================
# Sample Code Fixtures - Valid Code
# =============================================================================

@pytest.fixture
def valid_function_4_args():
    return "int add(int a, int b, int c, int d) { return a+b+c+d; }\n"


@pytest.fixture
def valid_short_function():
    return "void f(void) {\n    int x = 1;\n    return;\n}\n"


@pytest.fixture
def valid_function_40_lines():
    body = "\n".join(["    x++;"] * 37)
    return f"void f(void)\n{{\n    int x = 0;\n{body}\n    return;\n}}\n"


@pytest.fixture
def valid_function_with_comments():
    comments = "\n".join(["    // comment"] * 50)
    return f"void f(void) {{\n    int x = 1;\n{comments}\n    return;\n}}\n"


@pytest.fixture
def valid_function_with_blanks():
    blanks = "\n" * 50
    return f"void f(void) {{\n    int x = 1;{blanks}    return;\n}}\n"


@pytest.fixture
def valid_function_with_braces():
    return """void f(void)
{
    if (1)
    {
        int x = 1;
    }
}
"""


@pytest.fixture
def valid_single_decl():
    return "int a;\nint b;\n"


@pytest.fixture
def valid_for_multi_decl():
    return "void f(void) { for (int i = 0, j = 0; i < 10; i++) {} }\n"


@pytest.fixture
def valid_func_params_multiline():
    """Function parameters spanning multiple lines should NOT trigger decl.single."""
    return """static int handle_fi_node(struct Ast_node *tmp_root, struct Ast_node **root,
                          int *count_if, int *res)
{
    return 0;
}
"""


@pytest.fixture
def valid_func_params_typed_after_comma():
    """Function params with type after comma should NOT trigger decl.single."""
    return "void foo(int a, int b, char c)\n{\n    return;\n}\n"


@pytest.fixture
def valid_fixed_array():
    return "void f(void) { int arr[10]; }\n"


@pytest.fixture
def valid_macro_size_array():
    return "#define SIZE 10\nvoid f(void) { int arr[SIZE]; }\n"


@pytest.fixture
def valid_no_trailing():
    return "int main(void)\n{\n    return 0;\n}\n"


@pytest.fixture
def valid_with_newline():
    return "int x = 1;\n"


@pytest.fixture
def valid_single_blank():
    return "int a;\n\nint b;\n"


@pytest.fixture
def valid_big_enum():
    values = ",\n    ".join([f"VAL_{i}" for i in range(50)])
    return f"enum big {{\n    {values},\n}};\n"


@pytest.fixture
def valid_big_struct():
    fields = "\n    ".join([f"int f{i};" for i in range(50)])
    return f"struct big {{\n    {fields}\n}};\n"


@pytest.fixture
def valid_static_array():
    values = ", ".join(["0"] * 100)
    return f"static int arr[] = {{ {values} }};\n"


@pytest.fixture
def valid_typedef_fn_ptr():
    return "typedef void (*fn)(int, void *);\n"


# =============================================================================
# Sample Code Fixtures - Invalid Code
# =============================================================================

@pytest.fixture
def invalid_function_5_args():
    return "int add(int a, int b, int c, int d, int e) { return 0; }\n"


@pytest.fixture
def invalid_function_41_lines():
    body = "\n".join(["    x++;"] * 39)
    return f"void f(void) {{\n    int x = 0;\n{body}\n    return;\n}}\n"


@pytest.fixture
def invalid_multi_decl():
    return "int a, b;\n"


@pytest.fixture
def invalid_vla():
    return "void f(int n) { int arr[n]; }\n"


@pytest.fixture
def invalid_trailing_space():
    return "int main(void)   \n{\n    return 0;\n}\n"


@pytest.fixture
def invalid_no_newline():
    return "int x = 1;"


@pytest.fixture
def invalid_double_blank():
    return "int a;\n\n\nint b;\n"


@pytest.fixture
def invalid_blank_at_start():
    return "\nint x = 1;\n"


@pytest.fixture
def invalid_indented_hash():
    return "void f(void) {\n    #define X 1\n}\n"


# =============================================================================
# Header File Fixtures
# =============================================================================

@pytest.fixture
def valid_header_with_guard():
    return "#ifndef MY_H\n#define MY_H\nint x;\n#endif /* MY_H */\n"


@pytest.fixture
def valid_header_void_proto():
    return "#ifndef T_H\n#define T_H\nvoid f(void);\n#endif /* T_H */\n"


@pytest.fixture
def valid_header_endif_comment():
    return "#ifndef T_H\n#define T_H\n#endif /* T_H */\n"


@pytest.fixture
def invalid_header_no_guard():
    return "int x;\n"


@pytest.fixture
def invalid_header_empty_proto():
    return "#ifndef T_H\n#define T_H\nvoid f();\n#endif /* T_H */\n"


@pytest.fixture
def invalid_header_no_endif_comment():
    return "#ifndef T_H\n#define T_H\n#endif\n"


# =============================================================================
# Additional Invalid Code Fixtures
# =============================================================================

@pytest.fixture
def invalid_crlf():
    return "int x = 1;\r\nint y = 2;\r\n"


@pytest.fixture
def invalid_blank_at_end():
    return "int x = 1;\n\n"


@pytest.fixture
def invalid_asm():
    return "void f(void) {\n    asm(\"nop\");\n}\n"


@pytest.fixture
def invalid_digraph():
    return "int arr<:10:> = {0};\n"


@pytest.fixture
def invalid_empty_loop():
    return "void f(void) {\n    while (1)\n    ;\n}\n"
