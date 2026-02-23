# EPITA C/C++ Coding Style Checker

A fast C and C++ linter for EPITA coding style rules. Uses [tree-sitter](https://tree-sitter.github.io/) for robust AST-based parsing.

## Features

- **C** (.c, .h) and **C++** (.cc, .hh, .hxx) support
- 58 rules across file formatting, functions, exports, preprocessor, declarations, control flow, naming, and more
- AST-based checks via tree-sitter (no regex hacks for structure)
- `clang-format` integration with language-specific configs (C vs C++)
- Configurable via TOML, presets, or CLI flags
- Pre-commit hook support

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

Or in `pyproject.toml`:

```toml
[tool.epita-coding-style]
max_lines = 40

[tool.epita-coding-style.rules]
"keyword.goto" = false
```

### Limits

| Setting | Default (C) | Default (C++) | Description |
|---------|-------------|---------------|-------------|
| `max_lines` | 30 | 50 | Max lines per function body |
| `max_args` | 4 | 4 | Max arguments per function |
| `max_funcs` | 10 | — | Max exported functions per file (C only) |
| `max_globals` | 1 | — | Max exported globals per file (C only) |

## Rules Overview

Use `epita-coding-style --list-rules` for the full list. Key categories:

**C rules** (enabled by default):
- **File** — line endings, trailing whitespace, blank lines, file termination
- **Style** — Allman brace style
- **Functions** — length, argument count, `(void)` for empty params
- **Exports** — max exported functions/globals per `.c` file
- **Preprocessor** — include guards, `#` column, `#endif` comments, digraphs
- **Declarations** — one per line, no VLAs
- **Control** — no empty loop bodies
- **Strict** — no `goto`, no explicit casts
- **Formatting** — clang-format compliance

**C++ rules** (auto-enabled for .cc/.hh/.hxx files):
- **File** — correct extensions (.cc/.hh/.hxx, not .cpp/.hpp)
- **Preprocessor** — `#pragma once`, include order, no source includes, `constexpr`
- **Global** — C++ casts, no malloc, `nullptr`, no `extern "C"`, C++ headers, `std::` functions
- **Naming** — CamelCase classes/structs, lowercase namespaces with closing comments
- **Declarations** — `&`/`*` next to type, `explicit` constructors, no VLAs
- **Control** — switch default case, label padding, no empty loops
- **Writing** — empty braces, single-expression braces, throw/catch rules, operator overloads, `enum class`, function length

## clang-format

The `format` rule uses `clang-format` to check code formatting. Requires `clang-format` to be installed.

The checker uses language-specific configs:
- **C**: looks for `.clang-format-c`, then `.clang-format`
- **C++**: looks for `.clang-format-cxx`, then `.clang-format`

It searches from the file's directory up to root, falling back to the bundled EPITA configs.

To disable: set `"format" = false` in your config, or use `--preset noformat`.

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/KazeTachinuu/epita-coding-style
    rev: v3.1.0
    hooks:
      - id: epita-coding-style
        args: [--preset, 42sh]  # optional
```

## License

MIT
