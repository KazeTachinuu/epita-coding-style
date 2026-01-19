#!/usr/bin/env python3
"""EPITA C Coding Style Checker - uses tree-sitter for robust parsing."""

import argparse
import os
import sys
from dataclasses import dataclass
from enum import Enum
from tree_sitter import Language, Parser
import tree_sitter_c as tsc

# Tree-sitter parser (singleton)
_parser = Parser(Language(tsc.language()))


class Severity(Enum):
    MAJOR = "MAJOR"
    MINOR = "MINOR"


@dataclass
class Violation:
    file: str
    line: int
    rule: str
    message: str
    severity: Severity = Severity.MAJOR


def parse(content: bytes):
    """Parse C code and return AST root."""
    return _parser.parse(content).root_node


def find_nodes(node, *types):
    """Yield all descendant nodes matching given types."""
    if node.type in types:
        yield node
    for child in node.children:
        yield from find_nodes(child, *types)


def text(node, content: bytes) -> str:
    """Get text content of a node."""
    return content[node.start_byte:node.end_byte].decode()


def find_id(node, content: bytes) -> str | None:
    """Recursively find first identifier in a node."""
    if node.type == 'identifier':
        return text(node, content)
    for child in node.children:
        if name := find_id(child, content):
            return name
    return None


# =============================================================================
# Checks
# =============================================================================

def check_file_format(path: str, content: str, lines: list[str]) -> list[Violation]:
    """Check file formatting rules."""
    v = []

    if '\r\n' in content:
        v.append(Violation(path, 1, "file.dos", "Use Unix LF, not DOS CRLF"))

    if content and not content.endswith('\n'):
        v.append(Violation(path, len(lines), "file.terminate", "File must end with newline"))

    if lines and not lines[0].strip():
        v.append(Violation(path, 1, "file.spurious", "No blank lines at start of file"))

    # Check end (ignoring final empty line from trailing newline)
    end_idx = len(lines) - 2 if lines and lines[-1] == '' else len(lines) - 1
    if end_idx >= 0 and not lines[end_idx].strip():
        v.append(Violation(path, end_idx + 1, "file.spurious", "No blank lines at end of file"))

    # Consecutive empty lines
    for i, line in enumerate(lines[1:], 2):
        if not line.strip() and not lines[i-2].strip():
            v.append(Violation(path, i, "lines.empty", "No consecutive empty lines"))

    # Trailing whitespace
    for i, line in enumerate(lines, 1):
        if line != line.rstrip():
            v.append(Violation(path, i, "file.trailing", "Trailing whitespace", Severity.MINOR))

    return v


def check_braces(path: str, lines: list[str]) -> list[Violation]:
    """Check Allman brace style."""
    v = []
    in_comment = False

    for i, line in enumerate(lines, 1):
        s = line.strip()

        # Track block comments
        if '/*' in s and '*/' not in s:
            in_comment = True
            continue
        if in_comment:
            if '*/' in s:
                in_comment = False
            continue

        if not s or s.startswith(('#', '//')):
            continue

        # Remove char literals to avoid '{'/'}'
        import re
        clean = re.sub(r"'(?:\\.|[^'\\])'", "   ", s)

        # Opening brace
        if '{' in clean:
            pos = clean.find('{')
            before = clean[:pos].strip()
            # Check for assignment = (not == != <= >=)
            is_init = False
            if '=' in before:
                temp = before.replace('==', '').replace('!=', '').replace('<=', '').replace('>=', '')
                is_init = '=' in temp
            # Allow: initializers (=), empty braces, do blocks, macros
            if before and not is_init and clean.strip() not in ('{}', '{ }') and before != 'do':
                if not line.rstrip().endswith('\\'):  # macro continuation
                    v.append(Violation(path, i, "braces", "Opening brace must be on its own line"))

        # Closing brace
        if '}' in clean and not line.rstrip().endswith('\\'):
            pos = clean.find('}')
            after = clean[pos+1:].strip()
            # Allow: while (do-while), semicolon, comma, comments
            if after and not after.startswith(('while', '//', '/*')) and after not in (';', ',', ');'):
                v.append(Violation(path, i, "braces", "Closing brace must be on its own line"))

    return v


def check_functions(path: str, tree, content: bytes, lines: list[str], max_args: int, max_lines: int) -> list[Violation]:
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

        # Empty params should be (void)
        if not params and ('()' in text(func, content) or '( )' in text(func, content)):
            v.append(Violation(path, line, "fun.proto.void", f"'{name}' should use (void) for empty params"))

        # Max arguments
        if len(params) > max_args:
            v.append(Violation(path, line, "fun.arg.count", f"'{name}' has {len(params)} args (max {max_args})"))

        # Max lines (count non-empty, non-brace, non-comment lines)
        if body:
            count = 0
            for ln in range(body.start_point[0], body.end_point[0] + 1):
                if ln < len(lines):
                    s = lines[ln].strip()
                    if s and s not in ('{', '}') and not s.startswith(('//', '/*', '*')):
                        count += 1
            if count > max_lines:
                v.append(Violation(path, line, "fun.length", f"Function has {count} lines (max {max_lines})"))

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
                        if not params and ('()' in decl_text or '( )' in decl_text):
                            v.append(Violation(path, line, "fun.proto.void", f"'{name}' should use (void)"))
                        if len(params) > max_args:
                            v.append(Violation(path, line, "fun.arg.count", f"'{name}' has {len(params)} args (max {max_args})"))

    return v


def check_exports(path: str, tree, content: bytes, max_funcs: int) -> list[Violation]:
    """Check exported symbols in .c files."""
    if not path.endswith('.c'):
        return []

    v = []

    # Exported functions (non-static)
    exported = []
    for func in find_nodes(tree, 'function_definition'):
        is_static = any(text(c, content) == 'static' for c in func.children if c.type == 'storage_class_specifier')
        if not is_static:
            for child in func.children:
                if child.type == 'function_declarator':
                    if name := find_id(child, content):
                        exported.append(name)

    if len(exported) > max_funcs:
        v.append(Violation(path, 1, "export.fun", f"{len(exported)} exported functions (max {max_funcs})"))

    # Exported global variables
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

    if len(globals_found) > 1:
        v.append(Violation(path, globals_found[1][1], "export.other",
                          f"{len(globals_found)} exported globals (max 1)"))

    return v


def check_preprocessor(path: str, lines: list[str]) -> list[Violation]:
    """Check preprocessor rules."""
    v = []

    # Header guard
    if path.endswith('.h'):
        guard = os.path.basename(path).upper().replace('.', '_').replace('-', '_')
        if not any('#ifndef' in l and guard in l for l in lines):
            v.append(Violation(path, 1, "cpp.guard", f"Missing include guard (#ifndef {guard})"))

    for i, line in enumerate(lines, 1):
        s = line.strip()

        # # must be column 1
        if s.startswith('#') and line[0] != '#':
            v.append(Violation(path, i, "cpp.mark", "# must be on first column"))

        # #endif needs comment
        if s.startswith('#endif') and '//' not in s and '/*' not in s:
            v.append(Violation(path, i, "cpp.if", "#endif should have comment", Severity.MINOR))

        # Digraphs/trigraphs
        for d in ['??=', '??/', "??'", '??(', '??)', '??!', '??<', '??>', '??-', '<%', '%>', '<:', ':>']:
            if d in line:
                v.append(Violation(path, i, "cpp.digraphs", f"Digraph '{d}' not allowed"))

    return v


def check_misc(path: str, lines: list[str]) -> list[Violation]:
    """Check misc rules (declarations, control structures)."""
    v = []
    brace_depth = 0

    for i, line in enumerate(lines, 1):
        s = line.strip()
        brace_depth += line.count('{') - line.count('}')

        # Multiple declarations: int a, b;
        if not s.startswith('for') and ',' in s and not s.endswith(')') and not s.endswith('){'):
            # Simple heuristic for "type var, var"
            import re
            if re.match(r'^\s*(?:int|char|short|long|float|double)\s+\*?\w+\s*,', s):
                v.append(Violation(path, i, "decl.single", "One declaration per line"))

        # VLA (check if inside any braces on this line or previous context)
        in_block = brace_depth > 0 or ('{' in s and '}' in s)
        if in_block:
            import re
            m = re.search(r'\b\w+\s+\w+\s*\[\s*([a-z_]\w*)\s*\]', s)
            if m and '=' not in s and not m.group(1).isupper():
                v.append(Violation(path, i, "decl.vla", "VLA not allowed"))

        # asm
        if any(kw in s for kw in ['asm(', '__asm__', '__asm']):
            v.append(Violation(path, i, "stat.asm", "asm not allowed"))

        # Empty loop body
        if s == ';' and i > 1:
            prev = lines[i-2].strip()
            if prev.startswith(('for', 'while')):
                v.append(Violation(path, i, "ctrl.empty", "Use 'continue' for empty loops"))

    return v


# =============================================================================
# Main
# =============================================================================

def check_file(path: str, max_args=4, max_lines=40, max_funcs=10) -> list[Violation]:
    """Run all checks on a file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
            content = f.read()
    except Exception as e:
        return [Violation(path, 0, "file.read", str(e))]

    lines = content.split('\n')
    content_bytes = content.encode()
    tree = parse(content_bytes)

    return (
        check_file_format(path, content, lines) +
        check_braces(path, lines) +
        check_functions(path, tree, content_bytes, lines, max_args, max_lines) +
        check_exports(path, tree, content_bytes, max_funcs) +
        check_preprocessor(path, lines) +
        check_misc(path, lines)
    )


def find_files(paths: list[str]) -> list[str]:
    """Find all .c and .h files."""
    files = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(('.c', '.h')):
            files.append(p)
        elif os.path.isdir(p):
            for root, _, names in os.walk(p):
                files.extend(os.path.join(root, n) for n in names if n.endswith(('.c', '.h')))
    return sorted(files)


def main():
    ap = argparse.ArgumentParser(description='EPITA C Style Checker')
    ap.add_argument('paths', nargs='*', default=['.'], help='Files/directories to check')
    ap.add_argument('--max-lines', type=int, default=40)
    ap.add_argument('--max-args', type=int, default=4)
    ap.add_argument('--max-funcs', type=int, default=10)
    ap.add_argument('-q', '--quiet', action='store_true')
    ap.add_argument('--no-color', action='store_true')
    args = ap.parse_args()

    # Colors
    R, Y, C, W, B, RST = ('\033[91m', '\033[93m', '\033[96m', '\033[97m', '\033[1m', '\033[0m')
    if args.no_color:
        R = Y = C = W = B = RST = ''

    files = find_files(args.paths)
    if not files:
        print(f"{R}No C files found{RST}", file=sys.stderr)
        return 1

    total_major = total_minor = 0

    for path in files:
        violations = check_file(path, args.max_args, args.max_lines, args.max_funcs)

        major = sum(1 for v in violations if v.severity == Severity.MAJOR)
        minor = sum(1 for v in violations if v.severity == Severity.MINOR)
        total_major += major
        total_minor += minor

        if not args.quiet and violations:
            print(f"\n{W}{B}{path}{RST}")
            for v in violations:
                color = R if v.severity == Severity.MAJOR else Y
                print(f"  {C}{v.line}{RST}: {color}[{v.severity.value}]{RST} {v.rule}: {v.message}")

    # Summary
    print(f"\n{W}Files: {len(files)}  Major: {R}{total_major}{RST}  Minor: {Y}{total_minor}{RST}")

    return 1 if total_major > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
