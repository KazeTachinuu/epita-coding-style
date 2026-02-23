"""Tests for CXX global rules."""


class TestGlobalCasts:
    """Tests for global.casts rule (no C-style casts)."""

    def test_c_style_cast_detected(self, check_cxx):
        code = "void foo() { auto x = (int)3.14; }\n"
        assert check_cxx(code, "global.casts")

    def test_static_cast_ok(self, check_cxx):
        code = "void foo() { auto x = static_cast<int>(3.14); }\n"
        assert not check_cxx(code, "global.casts")

    def test_reinterpret_cast_ok(self, check_cxx):
        code = "void foo() { auto x = reinterpret_cast<char*>(ptr); }\n"
        assert not check_cxx(code, "global.casts")


class TestNoMalloc:
    """Tests for global.memory.no_malloc rule."""

    def test_malloc_detected(self, check_cxx):
        code = "void foo() { int* p = malloc(sizeof(int)); }\n"
        assert check_cxx(code, "global.memory.no_malloc")

    def test_calloc_detected(self, check_cxx):
        code = "void foo() { int* p = calloc(10, sizeof(int)); }\n"
        assert check_cxx(code, "global.memory.no_malloc")

    def test_free_detected(self, check_cxx):
        code = "void foo() { free(ptr); }\n"
        assert check_cxx(code, "global.memory.no_malloc")

    def test_new_ok(self, check_cxx):
        code = "void foo() { int* p = new int(42); }\n"
        assert not check_cxx(code, "global.memory.no_malloc")


class TestNullptr:
    """Tests for global.nullptr rule."""

    def test_null_detected(self, check_cxx):
        code = "void foo() { int* p = NULL; }\n"
        assert check_cxx(code, "global.nullptr")

    def test_nullptr_ok(self, check_cxx):
        code = "void foo() { int* p = nullptr; }\n"
        assert not check_cxx(code, "global.nullptr")


class TestExternC:
    """Tests for c.extern rule."""

    def test_extern_c_detected(self, check_cxx):
        code = 'extern "C" void cfunc();\n'
        assert check_cxx(code, "c.extern")

    def test_extern_c_block_detected(self, check_cxx):
        code = 'extern "C" {\nvoid cfunc();\n}\n'
        assert check_cxx(code, "c.extern")

    def test_no_extern_c_ok(self, check_cxx):
        code = "void foo() {}\n"
        assert not check_cxx(code, "c.extern")


class TestCHeaders:
    """Tests for c.headers rule."""

    def test_c_header_detected(self, check_cxx):
        code = "#include <stdio.h>\nint main() { return 0; }\n"
        assert check_cxx(code, "c.headers")

    def test_c_header_stdlib(self, check_cxx):
        code = "#include <stdlib.h>\nint main() { return 0; }\n"
        assert check_cxx(code, "c.headers")

    def test_cxx_header_ok(self, check_cxx):
        code = "#include <cstdio>\nint main() { return 0; }\n"
        assert not check_cxx(code, "c.headers")

    def test_cpp_header_ok(self, check_cxx):
        code = "#include <iostream>\nint main() { return 0; }\n"
        assert not check_cxx(code, "c.headers")


class TestCStdFunctions:
    """Tests for c.std_functions rule."""

    def test_printf_detected(self, check_cxx):
        code = '#include <cstdio>\nvoid foo() { printf("hello"); }\n'
        assert check_cxx(code, "c.std_functions")

    def test_strlen_detected(self, check_cxx):
        code = '#include <cstring>\nvoid foo() { strlen("hello"); }\n'
        assert check_cxx(code, "c.std_functions")

    def test_std_cout_ok(self, check_cxx):
        code = '#include <iostream>\nvoid foo() { std::cout << "hello"; }\n'
        assert not check_cxx(code, "c.std_functions")
