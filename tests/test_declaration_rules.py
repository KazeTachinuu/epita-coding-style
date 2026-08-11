"""Tests for declaration rules."""

import pytest
from textwrap import dedent


@pytest.mark.parametrize("code,should_fail", [
    ("int x;\n", False),
    ("int x = 1;\n", False),
    ("int x, y;\n", True),
    ("int *x, *y;\n", True),
], ids=["single-decl", "single-init", "multi-decl", "multi-ptr-decl"])
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
], ids=[
    "fixed-size", "macro-size", "return-access", "assign-access",
    "funcall-access", "cond-access", "vla-int", "vla-char", "vla-mat",
])
def test_decl_vla(check, code, should_fail):
    assert check(code, "decl.vla") == should_fail


STAT_SEP_FOR_OK = dedent("""\
    void f(void)
    {
        for (int i = 0; i < 8; i++, i++)
        {
            continue;
        }
    }
""")

STAT_SEP_STMT_BAD = dedent("""\
    void f(int x, int y)
    {
        x = 3, y = 4;
    }
""")

STAT_SEP_FOR_INIT_OK = dedent("""\
    void f(int i, int j)
    {
        for (i = 0, j = 0; i < 5; i++)
        {
            continue;
        }
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    (STAT_SEP_FOR_OK, False),
    (STAT_SEP_FOR_INIT_OK, False),
    (STAT_SEP_STMT_BAD, True),
], ids=["for-update", "for-init", "statement"])
def test_stat_sep(check, code, should_fail):
    assert check(code, "stat.sep") == should_fail


STAT_SEP_CALL_OK = dedent("""\
    void g(int a, int b);
    void f(int x, int y)
    {
        g(x, y);
    }
""")

STAT_SEP_WHILE_BAD = dedent("""\
    void f(int x, int y)
    {
        while ((x--, y))
        {
            continue;
        }
    }
""")

NESTED_COMMA_BAD = dedent("""\
    void f(int x, int y, int z)
    {
        x = 1, y = 2, z = 3;
    }
""")


def test_stat_sep_call_args_not_flagged(check):
    assert not check(STAT_SEP_CALL_OK, "stat.sep")


def test_stat_sep_while_condition_flagged(check):
    assert check(STAT_SEP_WHILE_BAD, "stat.sep")


def test_stat_sep_nested_comma_reported_once(check_result):
    assert len(check_result(NESTED_COMMA_BAD, "stat.sep")) == 1
