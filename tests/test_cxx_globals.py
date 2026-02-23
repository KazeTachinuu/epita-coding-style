"""Tests for CXX global rules."""

import pytest


# ── global.casts ─────────────────────────────────────────────────────────

C_STYLE_CAST = "void foo() { auto x = (int)3.14; }\n"
STATIC_CAST = "void foo() { auto x = static_cast<int>(3.14); }\n"
REINTERPRET_CAST = "void foo() { auto x = reinterpret_cast<char*>(ptr); }\n"


@pytest.mark.parametrize("code,should_fail", [
    (STATIC_CAST, False),
    (REINTERPRET_CAST, False),
    (C_STYLE_CAST, True),
], ids=["static-cast-ok", "reinterpret-cast-ok", "c-style-cast-bad"])
def test_global_casts(check_cxx, code, should_fail):
    assert check_cxx(code, "global.casts") == should_fail


# ── global.memory.no_malloc ──────────────────────────────────────────────

MALLOC_CALL = "void foo() { int* p = malloc(sizeof(int)); }\n"
CALLOC_CALL = "void foo() { int* p = calloc(10, sizeof(int)); }\n"
FREE_CALL = "void foo() { free(ptr); }\n"
NEW_CALL = "void foo() { int* p = new int(42); }\n"


@pytest.mark.parametrize("code,should_fail", [
    (NEW_CALL, False),
    (MALLOC_CALL, True),
    (CALLOC_CALL, True),
    (FREE_CALL, True),
], ids=["new-ok", "malloc-bad", "calloc-bad", "free-bad"])
def test_global_memory(check_cxx, code, should_fail):
    assert check_cxx(code, "global.memory.no_malloc") == should_fail


# ── global.nullptr ───────────────────────────────────────────────────────

NULL_USED = "void foo() { int* p = NULL; }\n"
NULLPTR_USED = "void foo() { int* p = nullptr; }\n"


@pytest.mark.parametrize("code,should_fail", [
    (NULLPTR_USED, False),
    (NULL_USED, True),
], ids=["nullptr-ok", "null-bad"])
def test_global_nullptr(check_cxx, code, should_fail):
    assert check_cxx(code, "global.nullptr") == should_fail


# ── c.extern ─────────────────────────────────────────────────────────────

EXTERN_C_SINGLE = 'extern "C" void cfunc();\n'
EXTERN_C_BLOCK = 'extern "C" {\nvoid cfunc();\n}\n'
NO_EXTERN_C = "void foo() {}\n"


@pytest.mark.parametrize("code,should_fail", [
    (NO_EXTERN_C, False),
    (EXTERN_C_SINGLE, True),
    (EXTERN_C_BLOCK, True),
], ids=["no-extern-ok", "extern-c-single", "extern-c-block"])
def test_c_extern(check_cxx, code, should_fail):
    assert check_cxx(code, "c.extern") == should_fail


# ── c.headers ────────────────────────────────────────────────────────────

INCLUDE_STDIO_H = "#include <stdio.h>\nint main() { return 0; }\n"
INCLUDE_STDLIB_H = "#include <stdlib.h>\nint main() { return 0; }\n"
INCLUDE_CSTDIO = "#include <cstdio>\nint main() { return 0; }\n"
INCLUDE_IOSTREAM = "#include <iostream>\nint main() { return 0; }\n"


@pytest.mark.parametrize("code,should_fail", [
    (INCLUDE_CSTDIO, False),
    (INCLUDE_IOSTREAM, False),
    (INCLUDE_STDIO_H, True),
    (INCLUDE_STDLIB_H, True),
], ids=["cstdio-ok", "iostream-ok", "stdio.h-bad", "stdlib.h-bad"])
def test_c_headers(check_cxx, code, should_fail):
    assert check_cxx(code, "c.headers") == should_fail


# ── c.std_functions ──────────────────────────────────────────────────────

BARE_PRINTF = '#include <cstdio>\nvoid foo() { printf("hello"); }\n'
BARE_STRLEN = '#include <cstring>\nvoid foo() { strlen("hello"); }\n'
STD_COUT = '#include <iostream>\nvoid foo() { std::cout << "hello"; }\n'


@pytest.mark.parametrize("code,should_fail", [
    (STD_COUT, False),
    (BARE_PRINTF, True),
    (BARE_STRLEN, True),
], ids=["std-cout-ok", "printf-bad", "strlen-bad"])
def test_c_std_functions(check_cxx, code, should_fail):
    assert check_cxx(code, "c.std_functions") == should_fail
