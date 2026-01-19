"""Tests for clang-format rule."""

import shutil
import pytest
from epita_coding_style import check_file
from epita_coding_style.config import Config


# Skip all tests if clang-format not installed
pytestmark = pytest.mark.skipif(
    not shutil.which("clang-format"),
    reason="clang-format not installed"
)


@pytest.fixture
def cfg():
    return Config()


@pytest.fixture
def cfg_no_format():
    cfg = Config()
    cfg.rules["format"] = False
    return cfg


def test_format_good(tmp_path, cfg):
    """Properly formatted file should pass."""
    f = tmp_path / "good.c"
    f.write_text("""\
#include <stdio.h>

int main(void)
{
    int x = 1;
    return x;
}
""")
    violations = check_file(str(f), cfg)
    assert not any(v.rule == "format" for v in violations)


def test_format_bad(tmp_path, cfg):
    """Badly formatted file should fail."""
    f = tmp_path / "bad.c"
    f.write_text("""\
#include <stdio.h>
int main(void){
    int x=1;
    return x;
}
""")
    violations = check_file(str(f), cfg)
    assert any(v.rule == "format" for v in violations)


def test_format_disabled(tmp_path, cfg_no_format):
    """Format check should be skipped when disabled."""
    f = tmp_path / "bad.c"
    f.write_text("""\
#include <stdio.h>
int main(void){int x=1;return x;}
""")
    violations = check_file(str(f), cfg_no_format)
    assert not any(v.rule == "format" for v in violations)


def test_format_is_minor(tmp_path, cfg):
    """Format violations should be MINOR severity."""
    from epita_coding_style.core import Severity
    f = tmp_path / "bad.c"
    f.write_text("int main(void){return 0;}\n")
    violations = check_file(str(f), cfg)
    format_violations = [v for v in violations if v.rule == "format"]
    assert all(v.severity == Severity.MINOR for v in format_violations)
