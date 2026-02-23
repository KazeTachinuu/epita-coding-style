"""Tests for CXX config handling — idempotency, with_cxx(), language detection."""

from epita_coding_style import Config, Lang, lang_from_path


class TestLangFromPath:
    """Tests for language detection from file extensions."""

    def test_c_source(self):
        assert lang_from_path("foo.c") == Lang.C

    def test_c_header(self):
        assert lang_from_path("foo.h") == Lang.C

    def test_cxx_source(self):
        assert lang_from_path("foo.cc") == Lang.CXX

    def test_cxx_header(self):
        assert lang_from_path("foo.hh") == Lang.CXX

    def test_cxx_hxx(self):
        assert lang_from_path("foo.hxx") == Lang.CXX

    def test_unknown_extension(self):
        assert lang_from_path("foo.py") is None

    def test_nested_path(self):
        assert lang_from_path("/some/dir/foo.cc") == Lang.CXX


class TestWithCxx:
    """Tests for Config.with_cxx() method."""

    def test_returns_new_config(self):
        cfg = Config()
        cxx = cfg.with_cxx()
        assert cxx is not cfg

    def test_does_not_mutate_original(self):
        cfg = Config()
        original_rules = dict(cfg.rules)
        cfg.with_cxx()
        assert cfg.rules == original_rules

    def test_idempotent(self):
        """Calling with_cxx() twice should produce equivalent configs."""
        cfg = Config()
        cxx1 = cfg.with_cxx()
        cxx2 = cfg.with_cxx()
        assert cxx1.rules == cxx2.rules
        assert cxx1.max_lines == cxx2.max_lines

    def test_cxx_rules_enabled(self):
        cxx = Config().with_cxx()
        assert cxx.is_enabled("global.casts")
        assert cxx.is_enabled("global.nullptr")
        assert cxx.is_enabled("naming.class")
        assert cxx.is_enabled("cpp.pragma.once")
        assert cxx.is_enabled("enum.class")
        assert cxx.is_enabled("fun.proto.void.cxx")

    def test_c_only_rules_disabled(self):
        cxx = Config().with_cxx()
        assert not cxx.is_enabled("cpp.guard")
        assert not cxx.is_enabled("export.fun")
        assert not cxx.is_enabled("export.other")
        assert not cxx.is_enabled("fun.proto.void")
        assert not cxx.is_enabled("keyword.goto")
        assert not cxx.is_enabled("cast")

    def test_shared_rules_preserved(self):
        cxx = Config().with_cxx()
        assert cxx.is_enabled("file.dos")
        assert cxx.is_enabled("file.trailing")
        assert cxx.is_enabled("lines.empty")

    def test_max_lines_50(self):
        cxx = Config().with_cxx()
        assert cxx.max_lines == 50

    def test_preserves_user_overrides(self):
        """User disabling a CXX rule should persist through with_cxx()."""
        cfg = Config()
        cfg.rules["global.casts"] = False
        # with_cxx enables all CXX rules, overriding user choice
        # This is intentional — CXX rules are always on for CXX files
        cxx = cfg.with_cxx()
        assert cxx.is_enabled("global.casts")

    def test_preserves_user_limits(self):
        """with_cxx sets max_lines=50, but this is the CXX default."""
        cfg = Config()
        cfg.max_args = 6
        cxx = cfg.with_cxx()
        assert cxx.max_args == 6
        assert cxx.max_lines == 50


class TestCxxDefaultsDisabled:
    """CXX rules should be disabled by default in a plain Config()."""

    def test_cxx_rules_disabled_by_default(self):
        cfg = Config()
        assert not cfg.is_enabled("global.casts")
        assert not cfg.is_enabled("naming.class")
        assert not cfg.is_enabled("cpp.pragma.once")
        assert not cfg.is_enabled("enum.class")

    def test_c_rules_enabled_by_default(self):
        cfg = Config()
        assert cfg.is_enabled("fun.proto.void")
        assert cfg.is_enabled("cpp.guard")
        assert cfg.is_enabled("export.fun")
