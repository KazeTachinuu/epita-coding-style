# EPITA C Coding Style Checker

A fast C linter for EPITA coding style rules. Uses [tree-sitter](https://tree-sitter.github.io/) for robust AST-based parsing.

## Installation

```bash
pipx install epita-coding-style
```

## Usage

```bash
epita-coding-style <path>              # Check files/directories
epita-coding-style src/ --preset 42sh  # Use relaxed preset
epita-coding-style src/ --config style.toml  # Use config file
epita-coding-style --list-rules        # List all rules
```

## Configuration

**Default:** Strict EPITA rules (30 lines max, goto/cast banned).

Settings are applied in order of priority (highest wins):

```
CLI flags > Config file > Preset > Defaults
```

This means you can start with a preset and override specific settings in your config file or via CLI.

### Presets

```bash
epita-coding-style --preset 42sh src/  # Relaxed: 40 lines, goto/cast allowed
```

### Config File

Create `.epita-style` (or `.epita-style.toml`) in your project root:

```toml
max_lines = 40

[rules]
"keyword.goto" = false
"cast" = false
```

Auto-detection order: `.epita-style` → `.epita-style.toml` → `pyproject.toml`

In `pyproject.toml`:

```toml
[tool.epita-coding-style]
max_lines = 40

[tool.epita-coding-style.rules]
"keyword.goto" = false
```

### Combining Preset + Config

Use a preset as a base and customize specific settings:

```toml
# .epita-style.toml
preset = "42sh"      # Start with 42sh (40 lines, goto/cast allowed)
max_lines = 50       # Override: bump to 50 lines

[rules]
"cast" = true        # Override: re-enable cast checking
```

### CLI Options

```
--preset NAME   Use preset (42sh)
--config FILE   Use config file
--max-lines N   Max lines per function
--max-args N    Max args per function
--max-funcs N   Max exported functions
-q, --quiet     Summary only
--no-color      Disable colors
--list-rules    List all rules
```

## Rules

| Rule | Description | Default |
|------|-------------|---------|
| `fun.length` | Max lines per function body | 30 |
| `fun.arg.count` | Max arguments per function | 4 |
| `fun.proto.void` | Empty params should use `void` | on |
| `export.fun` | Max exported functions per file | 10 |
| `export.other` | Max exported globals per file | 1 |
| `braces` | Allman brace style | on |
| `decl.single` | One declaration per line | on |
| `decl.vla` | No variable-length arrays | on |
| `keyword.goto` | No goto statements | on |
| `cast` | No explicit casts | on |
| `stat.asm` | No asm declarations | on |
| `ctrl.empty` | Empty loops use `continue` | on |
| `file.trailing` | No trailing whitespace | on |
| `file.dos` | No CRLF line endings | on |
| `file.terminate` | File ends with newline | on |
| `file.spurious` | No blank lines at file start/end | on |
| `lines.empty` | No consecutive empty lines | on |
| `cpp.guard` | Headers need include guards | on |
| `cpp.mark` | `#` on first column | on |
| `cpp.if` | `#endif` needs comment | on |
| `cpp.digraphs` | No digraphs/trigraphs | on |
| `format` | clang-format compliance | on |

## clang-format

The `format` rule uses `clang-format` to check code formatting. Requires `clang-format` to be installed.

The checker looks for `.clang-format` in the file's directory (walking up to root), or uses the bundled EPITA config.

To disable: set `"format" = false` in your config.

## Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/KazeTachinuu/epita-coding-style
    rev: v2.1.0
    hooks:
      - id: epita-coding-style
        args: [--preset, 42sh]  # optional
```

## License

MIT
