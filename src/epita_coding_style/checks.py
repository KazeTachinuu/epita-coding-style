"""Check functions for the coding style checker."""

from __future__ import annotations

import os
import re
import shutil
import subprocess

from .config import Config
from .core import Violation, Severity, find_nodes, text, find_id


def check_file_format(path: str, content: str, lines: list[str], cfg: Config) -> list[Violation]:
    """Check file formatting rules."""
    v = []

    if cfg.is_enabled("file.dos") and '\r\n' in content:
        v.append(Violation(path, 1, "file.dos", "Use Unix LF, not DOS CRLF"))

    if cfg.is_enabled("file.terminate") and content and not content.endswith('\n'):
        v.append(Violation(path, len(lines), "file.terminate", "File must end with newline"))

    if cfg.is_enabled("file.spurious"):
        if lines and not lines[0].strip():
            v.append(Violation(path, 1, "file.spurious", "No blank lines at start of file"))
        end_idx = len(lines) - 2 if lines and lines[-1] == '' else len(lines) - 1
        if end_idx >= 0 and not lines[end_idx].strip():
            v.append(Violation(path, end_idx + 1, "file.spurious", "No blank lines at end of file"))

    if cfg.is_enabled("lines.empty"):
        for i, line in enumerate(lines[1:], 2):
            if not line.strip() and not lines[i-2].strip():
                v.append(Violation(path, i, "lines.empty", "No consecutive empty lines"))

    if cfg.is_enabled("file.trailing"):
        for i, line in enumerate(lines, 1):
            if line != line.rstrip():
                v.append(Violation(path, i, "file.trailing", "Trailing whitespace", Severity.MINOR))

    return v


def check_braces(path: str, lines: list[str], cfg: Config) -> list[Violation]:
    """Check Allman brace style."""
    if not cfg.is_enabled("braces"):
        return []

    v = []
    in_comment = False

    for i, line in enumerate(lines, 1):
        s = line.strip()

        if '/*' in s and '*/' not in s:
            in_comment = True
            continue
        if in_comment:
            if '*/' in s:
                in_comment = False
            continue

        if not s or s.startswith(('#', '//')):
            continue

        clean = re.sub(r"'(?:\\.|[^'\\])'", "   ", s)

        if '{' in clean:
            pos = clean.find('{')
            before = clean[:pos].strip()
            is_init = False
            if '=' in before:
                temp = before.replace('==', '').replace('!=', '').replace('<=', '').replace('>=', '')
                is_init = '=' in temp
            if before and not is_init and clean.strip() not in ('{}', '{ }') and before != 'do':
                if not line.rstrip().endswith('\\'):
                    v.append(Violation(path, i, "braces", "Opening brace must be on its own line"))

        if '}' in clean and not line.rstrip().endswith('\\'):
            pos = clean.find('}')
            after = clean[pos+1:].strip()
            if after and not after.startswith(('while', '//', '/*')) and after not in (';', ',', ');'):
                v.append(Violation(path, i, "braces", "Closing brace must be on its own line"))

    return v


def check_functions(path: str, tree, content: bytes, lines: list[str], cfg: Config) -> list[Violation]:
    """Check function rules using AST."""
    v = []

    for func in find_nodes(tree, 'function_definition'):
        line = func.start_point[0] + 1
        name = None
        params = []
        body = None

        for child in func.children:
            if child.type == 'function_declarator':
                for c in child.children:
                    if c.type == 'identifier':
                        name = text(c, content)
                    elif c.type == 'parameter_list':
                        params = [p for p in c.children if p.type == 'parameter_declaration']
            elif child.type == 'compound_statement':
                body = child

        if not name:
            continue

        if cfg.is_enabled("fun.proto.void"):
            if not params and ('()' in text(func, content) or '( )' in text(func, content)):
                v.append(Violation(path, line, "fun.proto.void", f"'{name}' should use (void) for empty params"))

        if cfg.is_enabled("fun.arg.count") and len(params) > cfg.max_args:
            v.append(Violation(path, line, "fun.arg.count", f"'{name}' has {len(params)} args (max {cfg.max_args})"))

        if cfg.is_enabled("fun.length") and body:
            count = 0
            for ln in range(body.start_point[0], body.end_point[0] + 1):
                if ln < len(lines):
                    s = lines[ln].strip()
                    if s and s not in ('{', '}') and not s.startswith(('//', '/*', '*')):
                        count += 1
            if count > cfg.max_lines:
                v.append(Violation(path, line, "fun.length", f"Function has {count} lines (max {cfg.max_lines})"))

    # Header declarations
    if path.endswith('.h'):
        for decl in find_nodes(tree, 'declaration'):
            for child in decl.children:
                if child.type == 'function_declarator':
                    name = None
                    params = []
                    for c in child.children:
                        if c.type == 'identifier':
                            name = text(c, content)
                        elif c.type == 'parameter_list':
                            params = [p for p in c.children if p.type == 'parameter_declaration']

                    if name:
                        line = child.start_point[0] + 1
                        decl_text = text(child, content)
                        if cfg.is_enabled("fun.proto.void"):
                            if not params and ('()' in decl_text or '( )' in decl_text):
                                v.append(Violation(path, line, "fun.proto.void", f"'{name}' should use (void)"))
                        if cfg.is_enabled("fun.arg.count") and len(params) > cfg.max_args:
                            v.append(Violation(path, line, "fun.arg.count", f"'{name}' has {len(params)} args (max {cfg.max_args})"))

    return v


def check_exports(path: str, tree, content: bytes, cfg: Config) -> list[Violation]:
    """Check exported symbols in .c files."""
    if not path.endswith('.c'):
        return []

    v = []

    if cfg.is_enabled("export.fun"):
        exported = []
        for func in find_nodes(tree, 'function_definition'):
            is_static = any(text(c, content) == 'static' for c in func.children if c.type == 'storage_class_specifier')
            if not is_static:
                for child in func.children:
                    if child.type == 'function_declarator':
                        if name := find_id(child, content):
                            exported.append(name)

        if len(exported) > cfg.max_funcs:
            v.append(Violation(path, 1, "export.fun", f"{len(exported)} exported functions (max {cfg.max_funcs})"))

    if cfg.is_enabled("export.other"):
        globals_found = []
        for decl in tree.children:
            if decl.type != 'declaration':
                continue
            if any(c.type == 'function_declarator' for c in decl.children):
                continue

            is_static = any(text(c, content) == 'static' for c in decl.children if c.type == 'storage_class_specifier')
            is_extern = any(text(c, content) == 'extern' for c in decl.children if c.type == 'storage_class_specifier')

            if not is_static and not is_extern:
                if name := find_id(decl, content):
                    globals_found.append((name, decl.start_point[0] + 1))

        if len(globals_found) > cfg.max_globals:
            v.append(Violation(path, globals_found[1][1], "export.other",
                              f"{len(globals_found)} exported globals (max {cfg.max_globals})"))

    return v


def check_preprocessor(path: str, lines: list[str], cfg: Config) -> list[Violation]:
    """Check preprocessor rules."""
    v = []

    if cfg.is_enabled("cpp.guard") and path.endswith('.h'):
        guard = os.path.basename(path).upper().replace('.', '_').replace('-', '_')
        if not any('#ifndef' in l and guard in l for l in lines):
            v.append(Violation(path, 1, "cpp.guard", f"Missing include guard (#ifndef {guard})"))

    for i, line in enumerate(lines, 1):
        s = line.strip()

        if cfg.is_enabled("cpp.mark") and s.startswith('#') and line[0] != '#':
            v.append(Violation(path, i, "cpp.mark", "# must be on first column"))

        if cfg.is_enabled("cpp.if") and s.startswith('#endif') and '//' not in s and '/*' not in s:
            v.append(Violation(path, i, "cpp.if", "#endif should have comment", Severity.MINOR))

        if cfg.is_enabled("cpp.digraphs"):
            for d in ['??=', '??/', "??'", '??(', '??)', '??!', '??<', '??>', '??-', '<%', '%>', '<:', ':>']:
                if d in line:
                    v.append(Violation(path, i, "cpp.digraphs", f"Digraph '{d}' not allowed"))

    return v


def check_misc(path: str, tree, content: bytes, lines: list[str], cfg: Config) -> list[Violation]:
    """Check misc rules (declarations, control structures, goto, cast)."""
    v = []
    brace_depth = 0

    for i, line in enumerate(lines, 1):
        s = line.strip()
        brace_depth += line.count('{') - line.count('}')

        if cfg.is_enabled("decl.single"):
            if not s.startswith('for') and ',' in s and not s.endswith(')') and not s.endswith('){'):
                if re.match(r'^\s*(?:int|char|short|long|float|double)\s+\*?\w+\s*,', s):
                    v.append(Violation(path, i, "decl.single", "One declaration per line"))

        if cfg.is_enabled("decl.vla"):
            in_block = brace_depth > 0 or ('{' in s and '}' in s)
            if in_block:
                m = re.search(r'\b\w+\s+\w+\s*\[\s*([a-z_]\w*)\s*\]', s)
                if m and '=' not in s and not m.group(1).isupper():
                    v.append(Violation(path, i, "decl.vla", "VLA not allowed"))

        if cfg.is_enabled("stat.asm"):
            if any(kw in s for kw in ['asm(', '__asm__', '__asm']):
                v.append(Violation(path, i, "stat.asm", "asm not allowed"))

        if cfg.is_enabled("ctrl.empty"):
            if s == ';' and i > 1:
                prev = lines[i-2].strip()
                if prev.startswith(('for', 'while')):
                    v.append(Violation(path, i, "ctrl.empty", "Use 'continue' for empty loops"))

    # AST-based checks for goto and cast
    if cfg.is_enabled("keyword.goto"):
        for node in find_nodes(tree, 'goto_statement'):
            v.append(Violation(path, node.start_point[0] + 1, "keyword.goto", "goto not allowed"))

    if cfg.is_enabled("cast"):
        for node in find_nodes(tree, 'cast_expression'):
            v.append(Violation(path, node.start_point[0] + 1, "cast", "Explicit cast not allowed"))

    return v


def _find_clang_format_config(start_path: str) -> str | None:
    """Find .clang-format file by walking up from start_path."""
    path = os.path.abspath(start_path)
    if os.path.isfile(path):
        path = os.path.dirname(path)

    while path != os.path.dirname(path):  # Stop at root
        config = os.path.join(path, ".clang-format")
        if os.path.isfile(config):
            return config
        path = os.path.dirname(path)
    return None


def check_clang_format(path: str, cfg: Config) -> list[Violation]:
    """Check formatting using clang-format --dry-run --Werror."""
    if not cfg.is_enabled("format"):
        return []

    if not shutil.which("clang-format"):
        return []

    # Find .clang-format config
    config_file = _find_clang_format_config(path)
    if not config_file:
        pkg_config = os.path.join(os.path.dirname(__file__), ".clang-format")
        if os.path.isfile(pkg_config):
            config_file = pkg_config

    if not config_file:
        return []

    try:
        result = subprocess.run(
            ["clang-format", f"--style=file:{os.path.abspath(config_file)}",
             "--dry-run", "--Werror", path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return [Violation(path, 1, "format", "File needs formatting (run clang-format)", Severity.MINOR)]
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass

    return []
