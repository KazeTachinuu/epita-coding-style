# EPITA C Coding Style Checker

A fast C linter for EPITA coding style rules. Uses [tree-sitter](https://tree-sitter.github.io/) for robust AST-based parsing.

## Installation

```bash
pipx install epita-coding-style
```

## Quick Start

```bash
epita-coding-style src/           # Check files/directories
epita-coding-style --list-rules   # List all rules with descriptions
epita-coding-style --show-config  # Show current configuration
epita-coding-style --help         # Full usage info
```

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

Or in `pyproject.toml`:

```toml
[tool.epita-coding-style]
max_lines = 40

[tool.epita-coding-style.rules]
"keyword.goto" = false
```

## clang-format

The `format` rule uses `clang-format` to check code formatting. Requires `clang-format` to be installed.

The checker looks for `.clang-format` in the file's directory (walking up to root), or uses the bundled EPITA config.

To disable: set `"format" = false` in your config, or use `--preset noformat`.

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/KazeTachinuu/epita-coding-style
    rev: v2.3.0
    hooks:
      - id: epita-coding-style
        args: [--preset, 42sh]  # optional
```

## License

MIT
