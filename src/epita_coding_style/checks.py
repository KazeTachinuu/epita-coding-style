"""Check functions for the coding style checker."""

from __future__ import annotations

import os
import re
import shutil
import subprocess

from .config import Config
from .core import Violation, Severity, NodeCache, text, find_id, find_nodes, line_at, Lang, lang_from_path

# Pre-compiled regex patterns
_CHAR_LITERAL = re.compile(r"'(?:\\.|[^'\\])'")
_INIT_ASSIGN = re.compile(r'(?<![!=<>])=(?!=)')
_CLANG_ERROR = re.compile(r'^.*:(\d+):\d+: (?:error|warning):')
_DIGRAPHS = ('??=', '??/', "??'", '??(', '??)', '??!', '??<', '??>', '??-', '<%', '%>', '<:', ':>')
_ASM_KEYWORDS = ('asm(', '__asm__', '__asm')


def check_file_format(path: str, content: str, lines: list[str], cfg: Config) -> list[Violation]:
    """Check file formatting rules."""
    v = []

    if cfg.is_enabled("file.dos") and '\r\n' in content:
        v.append(Violation(path, 1, "file.dos", "Use Unix LF, not DOS CRLF",
                          line_content=lines[0] if lines else None))

    if cfg.is_enabled("file.terminate") and content and not content.endswith('\n'):
        v.append(Violation(path, len(lines), "file.terminate", "File must end with newline",
                          line_content=lines[-1] if lines else None))

    if cfg.is_enabled("file.spurious"):
        if lines and not lines[0].strip():
            v.append(Violation(path, 1, "file.spurious", "No blank lines at start of file",
                              line_content=lines[0]))
        end_idx = len(lines) - 2 if lines and lines[-1] == '' else len(lines) - 1
        if end_idx >= 0 and not lines[end_idx].strip():
            v.append(Violation(path, end_idx + 1, "file.spurious", "No blank lines at end of file",
                              line_content=lines[end_idx]))

    if cfg.is_enabled("lines.empty"):
        for i, line in enumerate(lines[1:], 2):
            if not line.strip() and not lines[i-2].strip():
                v.append(Violation(path, i, "lines.empty", "No consecutive empty lines",
                                  line_content=line))

    if cfg.is_enabled("file.trailing"):
        for i, line in enumerate(lines, 1):
            if line != line.rstrip():
                trailing_start = len(line.rstrip())
                v.append(Violation(path, i, "file.trailing", "Trailing whitespace", Severity.MINOR,
                                  line_content=line, column=trailing_start))

    return v


def check_braces(path: str, lines: list[str], cfg: Config) -> list[Violation]:
    """Check Allman brace style."""
    if not cfg.is_enabled("braces"):
        return []
    # Skip if format check is enabled - clang-format handles braces
    if cfg.is_enabled("format"):
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

        clean = _CHAR_LITERAL.sub("   ", s)

        if '{' in clean:
            pos = clean.find('{')
            before = clean[:pos].strip()
            is_init = bool(_INIT_ASSIGN.search(before))
            if before and not is_init and clean.strip() not in ('{}', '{ }') and before != 'do':
                if not line.rstrip().endswith('\\'):
                    col = line.find('{')
                    v.append(Violation(path, i, "braces", "Opening brace must be on its own line",
                                      line_content=line, column=col))

        if '}' in clean and not line.rstrip().endswith('\\'):
            pos = clean.find('}')
            after = clean[pos+1:].strip()
            if after and not after.startswith(('while', '//', '/*')) and after not in (';', ',', ');'):
                col = line.find('}')
                v.append(Violation(path, i, "braces", "Closing brace must be on its own line",
                                  line_content=line, column=col))

    return v


def _find_function_declarator(node):
    """Find innermost function_declarator (the one defining the actual function).

    For complex return types like function pointers:
    - int (*f(void))(int) has nested function_declarators
    - We need the innermost one containing the actual function name
    """
    if node.type == 'function_declarator':
        # Check for nested function_declarator inside (for function pointer returns)
        for child in node.children:
            if inner := _find_function_declarator(child):
                return inner
        return node
    # Handle wrapped declarators (pointers, arrays, parenthesized)
    if node.type in ('pointer_declarator', 'array_declarator', 'parenthesized_declarator'):
        for child in node.children:
            if result := _find_function_declarator(child):
                return result
    return None


def check_functions(path: str, nodes: NodeCache, content: bytes, lines: list[str], cfg: Config) -> list[Violation]:
    """Check function rules using AST."""
    v = []
    chk_void = cfg.is_enabled("fun.proto.void")
    chk_args = cfg.is_enabled("fun.arg.count")
    chk_len = cfg.is_enabled("fun.length")
    max_args = cfg.max_args
    max_lines = cfg.max_lines

    for func in nodes.get('function_definition'):
        line_num = func.start_point[0] + 1
        line_content = line_at(lines, func.start_point[0])
        name = None
        params = []
        body = None

        for child in func.children:
            func_decl = _find_function_declarator(child)
            if func_decl:
                name = find_id(func_decl, content)
                for c in func_decl.children:
                    if c.type == 'parameter_list':
                        params = [p for p in c.children if p.type == 'parameter_declaration']
            elif child.type == 'compound_statement':
                body = child

        if not name:
            continue

        if chk_void and not params and ('()' in text(func, content) or '( )' in text(func, content)):
            v.append(Violation(path, line_num, "fun.proto.void", f"'{name}' should use (void) for empty params",
                              line_content=line_content))

        if chk_args and len(params) > max_args:
            v.append(Violation(path, line_num, "fun.arg.count", f"'{name}' has {len(params)} args (max {max_args})",
                              line_content=line_content))

        if chk_len and body:
            count = count_function_lines(body, lines)
            if count > max_lines:
                v.append(Violation(path, line_num, "fun.length", f"Function has {count} lines (max {max_lines})",
                                  line_content=line_content))

    # Header declarations
    if path.endswith('.h'):
        for decl in nodes.get('declaration'):
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
                        line_num = child.start_point[0] + 1
                        line_content = line_at(lines, child.start_point[0])
                        decl_text = text(child, content)
                        if cfg.is_enabled("fun.proto.void"):
                            if not params and ('()' in decl_text or '( )' in decl_text):
                                v.append(Violation(path, line_num, "fun.proto.void", f"'{name}' should use (void)",
                                                  line_content=line_content))
                        if cfg.is_enabled("fun.arg.count") and len(params) > cfg.max_args:
                            v.append(Violation(path, line_num, "fun.arg.count", f"'{name}' has {len(params)} args (max {cfg.max_args})",
                                              line_content=line_content))

    return v


def check_exports(path: str, nodes: NodeCache, content: bytes, cfg: Config) -> list[Violation]:
    """Check exported symbols in .c files."""
    if not path.endswith('.c'):
        return []

    v = []

    if cfg.is_enabled("export.fun"):
        count = 0
        for func in nodes.get('function_definition'):
            if any(text(c, content) == 'static' for c in func.children if c.type == 'storage_class_specifier'):
                continue
            for child in func.children:
                func_decl = _find_function_declarator(child)
                if func_decl and find_id(func_decl, content):
                    count += 1
                    break
        if count > cfg.max_funcs:
            v.append(Violation(path, 1, "export.fun", f"{count} exported functions (max {cfg.max_funcs})"))

    if cfg.is_enabled("export.other"):
        globals_found = []
        for decl in nodes.root.children:
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
            first_excess = globals_found[cfg.max_globals]
            v.append(Violation(path, first_excess[1], "export.other",
                              f"{len(globals_found)} exported globals (max {cfg.max_globals})"))

    return v


def check_preprocessor(path: str, lines: list[str], cfg: Config) -> list[Violation]:
    """Check preprocessor rules."""
    v = []

    if cfg.is_enabled("cpp.guard") and path.endswith('.h'):
        guard = os.path.basename(path).upper().replace('.', '_').replace('-', '_')
        if not any('#ifndef' in l and guard in l for l in lines):
            v.append(Violation(path, 1, "cpp.guard", f"Missing include guard (#ifndef {guard})",
                              line_content=lines[0] if lines else None))

    check_mark = cfg.is_enabled("cpp.mark")
    check_if = cfg.is_enabled("cpp.if")
    check_digraphs = cfg.is_enabled("cpp.digraphs")
    if not (check_mark or check_if or check_digraphs):
        return v

    for i, line in enumerate(lines, 1):
        s = line.strip()

        if check_mark and s.startswith('#') and line[0] != '#':
            v.append(Violation(path, i, "cpp.mark", "# must be on first column",
                              line_content=line, column=0))

        if check_if and (s.startswith('#endif') or s.startswith('#else')) \
                and '//' not in s and '/*' not in s:
            directive = '#else' if s.startswith('#else') else '#endif'
            v.append(Violation(path, i, "cpp.if", f"{directive} should have comment", Severity.MINOR,
                              line_content=line))

        if check_digraphs:
            for d in _DIGRAPHS:
                if d in line:
                    v.append(Violation(path, i, "cpp.digraphs", f"Digraph '{d}' not allowed",
                                      line_content=line, column=line.find(d)))

    return v


def check_vla(path: str, nodes: NodeCache, content: bytes, lines: list[str], cfg: Config) -> list[Violation]:
    """Check for variable-length arrays. Shared between C and C++."""
    if not cfg.is_enabled("decl.vla"):
        return []
    v = []
    for decl in nodes.get('declaration'):
        for arr in find_nodes(decl, 'array_declarator'):
            # Find the size expression between [ and ]
            size = None
            for child in arr.children:
                if child.type == '[':
                    size = None
                elif child.type == ']':
                    break
                else:
                    size = child
            if size and size.type == 'identifier' and not text(size, content).isupper():
                v.append(Violation(path, arr.start_point[0] + 1, "decl.vla",
                                  "VLA not allowed",
                                  line_content=line_at(lines, arr.start_point[0]),
                                  column=arr.start_point[1]))
    return v


def check_ctrl_empty(path: str, lines: list[str], cfg: Config,
                     nodes: NodeCache | None = None) -> list[Violation]:
    """Check for empty loop bodies. Shared between C and C++."""
    if not cfg.is_enabled("ctrl.empty"):
        return []
    v = []
    if nodes is not None:
        for node in nodes.get('for_statement', 'while_statement'):
            for child in node.children:
                if child.type == 'expression_statement' \
                        and all(c.type == ';' for c in child.children):
                    v.append(Violation(path, child.start_point[0] + 1, "ctrl.empty",
                                      "Use 'continue' for empty loops",
                                      line_content=line_at(lines, child.start_point[0])))
        return v
    # Line-based fallback
    for i, line in enumerate(lines, 1):
        if line.strip() == ';' and i > 1 and lines[i - 2].strip().startswith(('for', 'while')):
            v.append(Violation(path, i, "ctrl.empty", "Use 'continue' for empty loops",
                              line_content=line))
    return v


def count_function_lines(body, lines: list[str]) -> int:
    """Count non-trivial lines in a function body. Shared between C and C++."""
    count = 0
    for ln in range(body.start_point[0], body.end_point[0] + 1):
        if ln < len(lines):
            s = lines[ln].strip()
            if s and s not in ('{', '}') and not s.startswith(('//', '/*', '*')):
                count += 1
    return count


_CLANG_FORMAT_CANDIDATES = {
    Lang.C: (".clang-format-c", ".clang-format"),
    Lang.CXX: (".clang-format-cxx", ".clang-format"),
}
_CLANG_FORMAT_DEFAULT = (".clang-format",)


def _clang_format_candidates(lang: Lang | None) -> tuple[str, ...]:
    """Return ordered clang-format config filenames for a language."""
    return _CLANG_FORMAT_CANDIDATES.get(lang, _CLANG_FORMAT_DEFAULT)


def check_misc(path: str, nodes: NodeCache, content: bytes, lines: list[str], cfg: Config) -> list[Violation]:
    """Check misc rules (declarations, control structures, goto, cast)."""
    v = []

    # AST-based check for multiple declarations on one line
    if cfg.is_enabled("decl.single"):
        for decl in nodes.get('declaration'):
            # Skip function declarations
            if any(c.type == 'function_declarator' for c in decl.children):
                continue
            # Count init_declarators (each variable in the declaration)
            declarators = [c for c in decl.children
                         if c.type in ('init_declarator', 'pointer_declarator', 'identifier', 'array_declarator')]
            if len(declarators) > 1:
                line_num = decl.start_point[0] + 1
                line_content = line_at(lines, decl.start_point[0])
                # Find the comma within the declaration span, not the whole line
                col = decl.start_point[1]  # Point to start of declaration
                v.append(Violation(path, line_num, "decl.single", "One declaration per line",
                                  line_content=line_content, column=col))

    if cfg.is_enabled("stat.asm"):
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if any(kw in s for kw in _ASM_KEYWORDS):
                v.append(Violation(path, i, "stat.asm", "asm not allowed",
                                  line_content=line))

    # AST-based checks for goto and cast
    if cfg.is_enabled("keyword.goto"):
        for node in nodes.get('goto_statement'):
            line_num = node.start_point[0] + 1
            v.append(Violation(path, line_num, "keyword.goto", "goto not allowed",
                              line_content=line_at(lines, node.start_point[0]), column=node.start_point[1]))

    if cfg.is_enabled("cast"):
        for node in nodes.get('cast_expression'):
            line_num = node.start_point[0] + 1
            v.append(Violation(path, line_num, "cast", "Explicit cast not allowed",
                              line_content=line_at(lines, node.start_point[0]), column=node.start_point[1]))

    return v


def _find_clang_format_config(start_path: str, lang: Lang | None = None) -> str | None:
    """Find .clang-format config file by walking up from start_path.

    Looks for language-specific configs first (.clang-format-c / .clang-format-cxx),
    then falls back to the generic .clang-format.
    """
    suffixes = _clang_format_candidates(lang)

    path = os.path.abspath(start_path)
    if os.path.isfile(path):
        path = os.path.dirname(path)

    while path != os.path.dirname(path):  # Stop at root
        for suffix in suffixes:
            config = os.path.join(path, suffix)
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

    lang = lang_from_path(path)

    # Find language-specific .clang-format config
    config_file = _find_clang_format_config(path, lang)
    if not config_file:
        # Fallback to bundled package configs
        pkg_dir = os.path.dirname(__file__)
        for name in _clang_format_candidates(lang):
            pkg_config = os.path.join(pkg_dir, name)
            if os.path.isfile(pkg_config):
                config_file = pkg_config
                break

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
            # Count unique lines with formatting issues
            error_lines = set()
            for line in result.stderr.splitlines():
                if m := _CLANG_ERROR.match(line):
                    error_lines.add(int(m.group(1)))
            count = len(error_lines)
            if count > 0:
                msg = f"{count} line{'s' if count > 1 else ''} need{'s' if count == 1 else ''} formatting"
            else:
                msg = "Needs formatting"
            return [Violation(path, 1, "format", msg, Severity.MAJOR)]
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass

    return []
