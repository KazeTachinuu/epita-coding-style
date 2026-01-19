# EPITA C Coding Style Checker

A fast C code linter that validates against EPITA coding style rules. Uses [tree-sitter](https://tree-sitter.github.io/) for robust parsing.

## Installation

```bash
pipx install epita-coding-style
```

Or with pip:
```bash
pip install epita-coding-style
```

## Usage

```bash
epita-coding-style <path> [options]

# Examples
epita-coding-style .                 # Check current directory
epita-coding-style src/              # Check a directory recursively
epita-coding-style main.c utils.h    # Check specific files

# Options
epita-coding-style src/ --max-lines 30   # Max 30 lines per function
epita-coding-style src/ --max-args 5     # Max 5 args per function
epita-coding-style src/ --no-color       # Disable colored output
epita-coding-style src/ -q               # Quiet mode (summary only)
```

## Pre-commit Hook

### Using pre-commit framework

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/KazeTachinuu/epita-coding-style
    rev: v2.0.2
    hooks:
      - id: epita-coding-style
```

Then run:
```bash
pre-commit install
```

### Manual git hook

If you don't want to use the pre-commit framework, create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
files=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(c|h)$')
if [ -n "$files" ]; then
    epita-coding-style $files
fi
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Rules Checked

| Rule | Description |
|------|-------------|
| `fun.length` | Max 40 lines per function body |
| `fun.arg.count` | Max 4 arguments per function |
| `fun.proto.void` | Empty params should use `void` |
| `export.fun` | Max 10 exported functions per file |
| `export.other` | Max 1 exported global variable |
| `braces` | Allman brace style (braces on own line) |
| `decl.single` | One declaration per line |
| `decl.vla` | No variable-length arrays |
| `file.trailing` | No trailing whitespace |
| `file.dos` | No CRLF line endings |
| `file.terminate` | File must end with newline |
| `file.spurious` | No blank lines at start/end |
| `lines.empty` | No consecutive empty lines |
| `cpp.guard` | Header files need include guards |
| `cpp.mark` | Preprocessor `#` on first column |
| `cpp.if` | `#endif` needs comment |
| `cpp.digraphs` | No digraphs/trigraphs |
| `stat.asm` | No asm declarations |
| `ctrl.empty` | Empty loops should use `continue` |

## Example Output

```
src/parser.c
  42: [MAJOR] fun.arg.count: 'parse_node' has 5 args (max 4)
  156: [MAJOR] fun.length: Function has 45 lines (max 40)

src/utils.c
  12: [MINOR] file.trailing: Trailing whitespace

Files: 2  Major: 2  Minor: 1
```

## Development

```bash
# Clone and setup
git clone https://github.com/KazeTachinuu/epita-coding-style
cd epita-coding-style
uv sync --dev

# Run tests
uv run pytest

# Build
python -m build
```

## License

MIT
