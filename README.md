# EPITA C/C++ Coding Style Checker

A fast C (.c/.h) and C++ (.cc/.hh/.hxx) linter for EPITA coding style rules: AST-based checks via [tree-sitter](https://tree-sitter.github.io/), `clang-format` integration with language-specific configs, TOML/preset/CLI configuration, and pre-commit support.

## Installation

```bash
pipx install epita-coding-style
```

Requires Python >= 3.10, and `clang-format` on PATH for the format check
(skipped with a warning otherwise).

## Quick Start

```bash
epita-coding-style src/           # Check files/directories
epita-coding-style --list-rules   # List all rules with descriptions
epita-coding-style --show-config  # Show current configuration
epita-coding-style --help         # Full usage info
```

## Example Output

```
$ epita-coding-style src/
src/rbtree.c:1:1: error: No blank lines at start of file [epita-file.spurious]

src/rbtree.c:307:1: error: 'rb_delete_cases' has 5 args (max 4) [epita-fun.arg.count]
static void rb_delete_cases(struct rb_node **node, struct rb_node **tmp,
src/rbtree.c:12:1: error: 2 exported globals (max 1) [epita-export.other]
src/rbtree.c:1:1: error: 36 lines need formatting [epita-format]

Files: 1  Major: 4  Minor: 0

Fix formatting: clang-format -i src/rbtree.c
```

## Supported File Extensions

| Language | Source | Header |
|----------|--------|--------|
| C        | `.c`   | `.h`   |
| C++      | `.cc`  | `.hh`, `.hxx` |

C++ files using `.cpp` / `.hpp` will be checked but flagged with a `file.ext` violation.

## Configuration

Configuration is auto-detected from (in order):
- `.epita-style`
- `.epita-style.toml`
- `epita-style.toml`
- `[tool.epita-coding-style]` in `pyproject.toml`

**Priority:** CLI flags > config file > preset > defaults

### Generate a Config File

```bash
epita-coding-style --show-config --no-color > .epita-style.toml
```

This outputs a complete, commented TOML config you can customize.

### Presets

```bash
epita-coding-style --preset 42sh src/      # 40 lines, goto/cast allowed
epita-coding-style --preset noformat src/  # Same + skip clang-format
```

### Example Config

```toml
# .epita-style.toml
max_lines = 40

[rules]
"keyword.goto" = false  # Allow goto
"cast" = false          # Allow casts
```

The same keys work under `[tool.epita-coding-style]` in `pyproject.toml`.

### Limits

| Setting | Default (C) | Default (C++) | Description |
|---------|-------------|---------------|-------------|
| `max_lines` | 30 | 50 | Max lines per function body |
| `max_args` | 4 | 4 | Max arguments per function |
| `max_funcs` | 10 | n/a | Max exported functions per file (C only) |
| `max_globals` | 1 | n/a | Max exported globals per file (C only) |

## clang-format

The `format` rule uses `clang-format` to check code formatting. Requires `clang-format` to be installed.

The checker uses language-specific configs:
- **C**: looks for `.clang-format-c`, then `.clang-format`
- **C++**: looks for `.clang-format-cxx`, then `.clang-format`

It searches from the file's directory up to root, falling back to the bundled EPITA configs.

To disable: set `"format" = false` in your config, or use `--preset noformat`.

## Editor Integration

Neovim: [epita-nvim-lint](https://github.com/KazeTachinuu/epita-nvim-lint)
lints on save via nvim-lint.

Any editor that parses GCC-style diagnostics (`file:line:col: error: ...`)
works out of the box, e.g. Vim's `:make` with `makeprg=epita-coding-style\ %`.

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/KazeTachinuu/epita-coding-style
    rev: v3.4.0
    hooks:
      - id: epita-coding-style
        args: [--preset, 42sh]  # optional
```

Update the pinned `rev` with `pre-commit autoupdate`.

With the tool already installed, `./setup-hooks.sh` sets up a local hook instead.
