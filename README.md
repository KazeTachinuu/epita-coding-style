# epita-coding-style

Linter for the EPITA C and C++ coding style: tree-sitter checks plus `clang-format`.

## Install

```bash
pipx install epita-coding-style
```

Requires Python >= 3.10. The format check needs `clang-format` on `PATH`;
without it the check is skipped with a warning.

## Usage

```bash
epita-coding-style src/                      # check a directory recursively
epita-coding-style main.c list.h             # check specific files
epita-coding-style --preset 42sh src/        # use a preset
git ls-files '*.c' | epita-coding-style -   # read paths from stdin
epita-coding-style --list-rules              # list every rule
```

```
$ epita-coding-style src/
src/list.c:5:1: error: 'list_sum' has 5 args (max 4) [epita-fun.arg.count]
int list_sum(int *values, int len, int start, int step, int max)
src/list.c:7:5: error: One declaration per line [epita-decl.single]
    int sum = 0, i;
    ^
src/list.c:8:1: error: 1 line needs formatting [epita-format]

Files: 1  Major: 3  Minor: 0

Fix formatting:
  clang-format --style=file:.../epita_coding_style/.clang-format-c -i src/list.c
```

## What gets scanned

| Language | Extensions |
|----------|------------|
| C        | `.c`, `.h` |
| C++      | `.cc`, `.hh`, `.hxx` (`.cpp`/`.hpp` are checked but flagged by `file.ext`) |

Directories are scanned recursively. Hidden files and directories are skipped,
and inside a git repo so is everything git ignores (`.gitignore`,
`.git/info/exclude`, global excludes). Files named explicitly are always checked.

## Configuration

The first config found in the current directory or any parent is used:
`.epita-style`, `.epita-style.toml`, `epita-style.toml`, or the
`[tool.epita-coding-style]` table of `pyproject.toml`. `--config FILE` picks one explicitly.

```toml
preset = "42sh"
max_lines = 40

[rules]
"keyword.goto" = false
"cast" = false
```

Priority: CLI flags > config file > preset > defaults.

| Preset     | Effect |
|------------|--------|
| `ppex1`    | `max_casts = 5` |
| `42sh`     | `max_lines = 40`, disables `keyword.goto`, `cast` |
| `noformat` | same as `42sh`, also disables `format` |

| Limit         | C  | C++ | Flag            |
|---------------|----|-----|-----------------|
| `max_lines`   | 30 | 50  | `--max-lines`   |
| `max_args`    | 4  | 4   | `--max-args`    |
| `max_funcs`   | 10 | -   | `--max-funcs`   |
| `max_globals` | 1  | -   | `--max-globals` |
| `max_casts`   | 0  | -   | `--max-casts`   |

`max_casts` is a budget shared by all C files checked in one run, so run it on
the whole project (`epita-coding-style .`). Over budget, every cast is reported.
`"cast" = false` allows any number of casts.

`--show-config` prints the effective configuration as loadable TOML: settings
you changed are live lines, everything else is a commented-out default.

```bash
epita-coding-style --show-config --no-color > .epita-style.toml
```

## clang-format

For each file, the nearest config from the file's directory up to the root is
used: `.clang-format-c` (C) or `.clang-format-cxx` (C++), then `.clang-format`.
If none is found, the bundled EPITA config for that language is used.
Disable with `"format" = false` or `--preset noformat`.

## Pre-commit

```yaml
repos:
  - repo: https://github.com/KazeTachinuu/epita-coding-style
    rev: v3.4.0
    hooks:
      - id: epita-coding-style
        args: [--preset, 42sh]  # optional
```

A commit only checks the staged files, so `max_casts` counts the casts in those
files alone. To enforce the budget on the whole project, check it all:

```yaml
      - id: epita-coding-style
        args: [--preset, ppex1, .]
        pass_filenames: false
```

## Editor integration

Neovim: [epita-nvim-lint](https://github.com/KazeTachinuu/epita-nvim-lint).
Diagnostics are GCC-style (`file:line:col: error: ...`), so any editor that
parses them works, e.g. Vim with `makeprg=epita-coding-style\ %`.
Checked one file at a time, `max_casts` only counts that file's casts.

## Exit codes

| Code | Meaning |
|------|---------|
| 0    | no major violations |
| 1    | major violations found |
| 2    | usage, config or file error |

## Environment

| Variable | Effect |
|----------|--------|
| `NO_COLOR` | disable colors |
| `FORCE_COLOR` | force colors when not a terminal |
| `EPITA_STYLE_NO_UPDATE_CHECK` | disable the daily PyPI version check (only runs in a terminal, never in CI) |
