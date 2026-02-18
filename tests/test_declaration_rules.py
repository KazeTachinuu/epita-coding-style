"""Tests for declaration rules."""

import pytest
from textwrap import dedent


@pytest.mark.parametrize("code,should_fail", [
    ("int x;\n", False),
    ("int x = 1;\n", False),
    ("int x, y;\n", True),
    ("int *x, *y;\n", True),
])
def test_decl_single(check, code, should_fail):
    assert check(code, "decl.single") == should_fail


VLA_MACRO_OK = dedent("""\
    #define SIZE 10
    void f(void) { int arr[SIZE]; }
""")

# Array access in return statement (not a VLA)
RETURN_ARRAY_ACCESS = dedent("""\
    struct sig { const char *name; int num; };
    int f(const char *name)
    {
        static const struct sig sigs[] = {
            { "HUP", 1 }, { NULL, -1 },
        };
        for (int i = 0; sigs[i].name; i++)
        {
            if (name)
                return sigs[i].num;
        }
        return -1;
    }
""")

# Array access in assignment (not a VLA)
ASSIGN_ARRAY_ACCESS = dedent("""\
    void f(int *arr, int n)
    {
        int x = arr[n];
    }
""")

# Array access in function call (not a VLA)
FUNCALL_ARRAY_ACCESS = dedent("""\
    void g(int x);
    void f(int *arr, int n)
    {
        g(arr[n]);
    }
""")

# Array access in condition (not a VLA)
COND_ARRAY_ACCESS = dedent("""\
    void f(int *arr, int n)
    {
        if (arr[n])
            return;
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    # Should NOT trigger (not VLAs)
    ("void f(void) { int arr[10]; }\n", False),
    (VLA_MACRO_OK, False),
    (RETURN_ARRAY_ACCESS, False),
    (ASSIGN_ARRAY_ACCESS, False),
    (FUNCALL_ARRAY_ACCESS, False),
    (COND_ARRAY_ACCESS, False),
    # Should trigger (actual VLAs)
    ("void f(int n) { int arr[n]; }\n", True),
    ("void f(int n) { char buf[n]; }\n", True),
    ("void f(int n) { int mat[n]; }\n", True),
])
def test_decl_vla(check, code, should_fail):
    assert check(code, "decl.vla") == should_fail
