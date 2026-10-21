"""Every rule can be turned off: a disabled rule never reaches the output."""

import shutil
from pathlib import Path

import pytest

from epita_coding_style import RULES, Config
from epita_coding_style.lint import lint_files

CORPUS = Path(__file__).parent / "snapshots" / "corpus"

# Rules the snapshot corpus leaves out
EXPORTS = "".join(f"int f{i}(void)\n{{\n  return 0;\n}}\n" for i in range(11))
LONG_FUNCTION = "void long_one(void)\n{\n" + "  f0();\n" * 31 + "}\n"
EXTRA = {
    "extra.c": EXPORTS + LONG_FUNCTION,
    "extra.cc": """#include "other.c"

const int k = 3;

struct Foo
{
  Foo operator ,(Foo);
  Foo operator&(Foo);
};

int Foo::operator=(const Foo& o)
{
  if (k)
    return 1;
  int b = k +
    2;
  throw (b);
}
""",
}

# clang-format owns brace layout when installed, so only one of the two can fire
UNTRIGGERED = {"braces" if shutil.which("clang-format") else "format"}


def triggered(tmp_path, cfg):
    shutil.copytree(CORPUS, tmp_path, dirs_exist_ok=True)
    for name, code in EXTRA.items():
        (tmp_path / name).write_text(code)
    files = [str(p) for p in sorted(tmp_path.rglob("*.*")) if p.name != ".epita-style.toml"]
    return {v.rule for vs in lint_files(files, cfg).values() for v in vs}


def test_corpus_triggers_every_rule(tmp_path):
    assert triggered(tmp_path, Config()) == set(RULES) - UNTRIGGERED


@pytest.mark.parametrize("rule", sorted(set(RULES) - UNTRIGGERED))
def test_disabled_rule_is_not_reported(tmp_path, rule):
    cfg = Config()
    cfg.rules[rule] = False
    cfg.user_rules.add(rule)
    assert rule not in triggered(tmp_path, cfg)
