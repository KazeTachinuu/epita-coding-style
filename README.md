# EPITA C Coding Style Checker

A Python script to check C code against EPITA coding style rules.

## Usage

```bash
# Check current directory (recursive)
./check.py

# Check specific files or directories
./check.py src/
./check.py main.c utils.h

# Options
./check.py --help
./check.py --max-lines 30    # Custom max function lines
./check.py --no-color        # Disable colored output
./check.py -q                # Quiet mode (summary only)
```

## Rules Checked

- `fun.length` - Max 40 lines per function body
- `fun.arg.count` - Max 4 arguments per function
- `fun.proto.void` - Empty params should use `void`
- `decl.single` - One declaration per line
- `decl.vla` - No variable-length arrays
- `file.trailing` - No trailing whitespace
- `file.dos` - No CRLF line endings
- `file.terminate` - File must end with newline
- `file.spurious` - No blank lines at start/end
- `lines.empty` - No consecutive empty lines
- `cpp.guard` - Header files need include guards
- `cpp.mark` - Preprocessor `#` on first column
- `cpp.if` - `#endif` needs comment
- `cpp.digraphs` - No digraphs/trigraphs
- `stat.asm` - No asm declarations
- `ctrl.empty` - Empty loops should use `continue`

## Development

```bash
# Setup
uv sync --dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=check
```
