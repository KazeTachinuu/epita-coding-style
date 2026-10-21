"""C++-only checks."""

from __future__ import annotations

import os
import re
from itertools import pairwise
from pathlib import Path

from ..config import Config
from ..model import Severity, Source, Violation, child, find_nodes
from .common import params

_C_HEADERS = {
    "assert.h", "complex.h", "ctype.h", "errno.h", "fenv.h", "float.h",
    "inttypes.h", "iso646.h", "limits.h", "locale.h", "math.h", "setjmp.h",
    "signal.h", "stdalign.h", "stdarg.h", "stdatomic.h", "stdbool.h",
    "stddef.h", "stdint.h", "stdio.h", "stdlib.h", "stdnoreturn.h",
    "string.h", "tgmath.h", "threads.h", "time.h", "uchar.h", "wchar.h",
    "wctype.h",
}

# C functions that have std:: equivalents
_C_FUNCTIONS = {"printf", "scanf", "malloc", "calloc", "realloc", "free",
                "memcpy", "memset", "memmove", "strlen", "strcmp", "strncmp",
                "strcpy", "strncpy", "strcat", "strncat", "atoi", "atof",
                "atol", "strtol", "strtoul", "strtod", "abs", "exit",
                "qsort", "bsearch"}
_MALLOC_FUNCS = {"malloc", "calloc", "realloc", "free"}
_FORBIDDEN_OPS = {"operator,", "operator||", "operator&&"}

_CAMEL_CASE = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
_LOWER_NS = re.compile(r'^[a-z_][a-z0-9_]*$')
_REF_PATTERN = re.compile(r'(\w)\s+&(\w)')
_PTR_PATTERN = re.compile(r'(\w)\s+\*(\w)')

_CONSTEXPR_LITERALS = frozenset(('number_literal', 'string_literal', 'true', 'false', 'char_literal'))
_LITERAL_TYPES = frozenset(('number_literal', 'string_literal', 'char_literal',
                            'true', 'false', 'null', 'nullptr'))
_STMT_TYPES = frozenset(('expression_statement', 'return_statement', 'break_statement',
                         'continue_statement', 'throw_statement'))
_DECL_TYPES = frozenset(('declaration', 'field_declaration', 'function_definition'))


def check_file_ext(src: Source, cfg: Config) -> list[Violation]:
    """C++ files use .cc/.hh, not .cpp/.hpp."""
    ext = Path(src.path).suffix
    expected = {'.cpp': '.cc', '.hpp': '.hh'}.get(ext)
    if expected is None or not cfg.is_enabled("file.ext"):
        return []
    return [src.violation("file.ext", f"Use '{expected}' extension instead of '{ext}'")]


def check_cxx_preprocessor(src: Source, cfg: Config) -> list[Violation]:
    """Check CXX preprocessor rules: pragma.once, include.filetype, include.order, constexpr."""
    v = []

    if cfg.is_enabled("cpp.pragma.once") and src.path.endswith(('.hh', '.hxx')) \
            and not any(line.strip() == '#pragma once' for line in src.lines):
        v.append(src.violation("cpp.pragma.once", "Use #pragma once instead of include guards",
                               show_line=True))

    if cfg.is_enabled("cpp.include.filetype"):
        for inc in src.nodes.get('preproc_include'):
            for part in inc.children:
                if part.type == 'string_literal':
                    fname = src.text_of(part).strip('"')
                    if not fname.endswith(('.hh', '.hxx')):
                        v.append(src.at(inc, "cpp.include.filetype",
                                        f"Included file '{fname}' should have .hh or .hxx extension",
                                        column=False))

    if cfg.is_enabled("cpp.include.order"):
        v.extend(_check_include_order(src))

    if cfg.is_enabled("cpp.constexpr"):
        for decl in src.nodes.root.children:
            if decl.type != 'declaration' or not any(
                    src.text_of(c) == 'const' for c in decl.children if c.type == 'type_qualifier'):
                continue
            for part in decl.children:
                if part.type == 'init_declarator' and child(part, *_CONSTEXPR_LITERALS):
                    v.append(src.at(decl, "cpp.constexpr",
                                    "Consider using constexpr for compile-time constant",
                                    severity=Severity.MINOR, column=False))

    return v


def _check_include_order(src: Source) -> list[Violation]:
    """Check that includes are ordered: same-name header, system, local."""
    base = os.path.splitext(os.path.basename(src.path))[0]
    includes = []
    v = []
    for inc in src.nodes.get('preproc_include'):
        line = inc.start_point[0] + 1
        for part in inc.children:
            if part.type == 'system_lib_string':
                includes.append((line, 'system', src.text_of(part)))
            elif part.type == 'string_literal':
                fname = src.text_of(part).strip('"')
                kind = 'self' if os.path.splitext(fname)[0] == base else 'local'
                includes.append((line, kind, fname))

    def flag(line, message, severity=Severity.MAJOR):
        v.append(src.violation("cpp.include.order", message, line, severity=severity,
                               show_line=True))

    # A .hh may include its own .hxx at the end
    self_inc = next((i for i in includes if i[1] == 'self'), None)
    if self_inc and not (src.path.endswith('.hh') and self_inc[2].endswith('.hxx')):
        first_other = next((i for i in includes if i[1] != 'self'), None)
        if first_other and self_inc[0] > first_other[0]:
            flag(self_inc[0], "Same-name header should be included first")

    for i, (line, kind, _) in enumerate(includes):
        if kind == 'local' and any(k == 'system' for _, k, _ in includes[i + 1:]):
            flag(line, "System includes should come before local includes")
            break

    groups: dict[str, list[tuple[int, str]]] = {}
    for line, kind, fname in includes:
        groups.setdefault(kind, []).append((line, fname))
    for items in groups.values():
        for (_, prev), (line, name) in pairwise(items):
            if name.lower() < prev.lower():
                flag(line, f"Includes not in alphabetical order: '{name}' before '{prev}'",
                     Severity.MINOR)
                break

    for (prev_line, prev_kind, _), (line, kind, _) in pairwise(includes):
        between = src.lines[prev_line:line - 1]
        if kind != prev_kind and all(s.strip() for s in between):
            flag(line, "Include groups should be separated by a blank line", Severity.MINOR)

    return v


def check_cxx_globals(src: Source, cfg: Config) -> list[Violation]:
    """Check CXX global rules: casts, memory, nullptr, extern C, C headers, C functions."""
    v = []

    if cfg.is_enabled("global.casts"):
        for node in src.nodes.get('cast_expression'):
            v.append(src.at(node, "global.casts",
                            "Use C++ casts (static_cast, etc.) instead of C-style casts"))

    check_malloc = cfg.is_enabled("global.memory.no_malloc")
    check_std = cfg.is_enabled("c.std_functions")
    if check_malloc or check_std:
        for node in src.nodes.get('call_expression'):
            func = node.children[0] if node.children else None
            if not func or func.type != 'identifier':
                continue
            fname = src.text_of(func)
            if fname in _MALLOC_FUNCS:
                if check_malloc:
                    v.append(src.at(node, "global.memory.no_malloc",
                                    f"Don't use {fname}(), use new/delete or smart pointers"))
            elif check_std and fname in _C_FUNCTIONS:
                v.append(src.at(node, "c.std_functions", f"Use std::{fname} instead of {fname}"))

    if cfg.is_enabled("global.nullptr"):
        for node in src.nodes.get('null'):
            if src.text_of(node) == 'NULL':
                v.append(src.at(node, "global.nullptr", "Use nullptr instead of NULL"))

    if cfg.is_enabled("c.extern"):
        for node in src.nodes.get('linkage_specification'):
            v.append(src.at(node, "c.extern", 'No extern "C" in C++ code'))

    if cfg.is_enabled("c.headers"):
        for inc in src.nodes.get('preproc_include'):
            for part in inc.children:
                if part.type == 'system_lib_string':
                    header = src.text_of(part).strip('<>')
                    if header in _C_HEADERS:
                        v.append(src.at(inc, "c.headers",
                                        f"Use <c{header.replace('.h', '')}> instead of <{header}>",
                                        column=False))

    return v


def check_cxx_naming(src: Source, cfg: Config) -> list[Violation]:
    """Check CXX naming rules: class/struct names (CamelCase), namespace (lowercase + closing comment)."""
    v = []

    if cfg.is_enabled("naming.class"):
        for node in src.nodes.get('class_specifier', 'struct_specifier'):
            ident = child(node, 'type_identifier')
            if ident and not _CAMEL_CASE.match(name := src.text_of(ident)):
                v.append(src.at(ident, "naming.class", f"Class/struct '{name}' should be CamelCase"))

    if cfg.is_enabled("naming.namespace"):
        for node in src.nodes.get('namespace_definition'):
            ident = child(node, 'namespace_identifier')
            if not ident:
                continue
            name = src.text_of(ident)
            if not _LOWER_NS.match(name):
                v.append(src.at(ident, "naming.namespace", f"Namespace '{name}' should be lowercase"))
            end = node.end_point[0]
            closing = (src.line(end) or '').strip()
            if closing.startswith('}') and f'// namespace {name}' not in closing:
                v.append(src.violation("naming.namespace",
                                       f"Closing brace should have comment '// namespace {name}'",
                                       end + 1, severity=Severity.MINOR, show_line=True))

    return v


def _scrub_comments(src: Source) -> list[str]:
    """Lines with comment text blanked out."""
    out = list(src.lines)
    for c in src.nodes.get('comment'):
        (sr, sc), (er, ec) = c.start_point, c.end_point
        for r in range(sr, min(er + 1, len(out))):
            line = out[r]
            a = sc if r == sr else 0
            b = ec if r == er else len(line)
            out[r] = line[:a] + ' ' * (b - a) + line[b:]
    return out


_TYPE_KEYWORDS = frozenset({
    'int', 'char', 'float', 'double', 'long', 'short', 'unsigned',
    'signed', 'void', 'bool', 'auto', 'const', 'static', 'volatile',
    'extern', 'virtual', 'inline', 'explicit', 'mutable',
})


def _is_declaration_context(line: str) -> bool:
    """Heuristic: the line looks like a declaration (has a type)."""
    words = line.split()
    if not words:
        return False
    first = words[0]
    if any(w in _TYPE_KEYWORDS for w in words[:3]):
        return True
    if first[0].isupper() and first.isalpha():
        return True
    return first.startswith('std::')


def check_cxx_declarations(src: Source, cfg: Config) -> list[Violation]:
    """Check CXX declaration rules: ref/pointer placement, explicit constructors."""
    v = []
    placements = [(rule, pattern, sym) for rule, pattern, sym in
                  (("decl.ref", _REF_PATTERN, '&'), ("decl.point", _PTR_PATTERN, '*'))
                  if cfg.is_enabled(rule)]
    if placements:
        for i, line in enumerate(_scrub_comments(src), 1):
            if line.strip().startswith('#') or not _is_declaration_context(line):
                continue
            for rule, pattern, sym in placements:
                for m in pattern.finditer(line):
                    v.append(Violation(src.path, i, rule, f"{sym} should be next to type, not variable",
                                       line_content=line, column=line.index(sym, m.start())))

    if cfg.is_enabled("decl.ctor.explicit"):
        v.extend(_check_explicit_ctors(src))

    return v


def _is_type(src: Source, node, name: str) -> bool:
    return node.type == 'type_identifier' and src.text_of(node) == name


def _check_explicit_ctors(src: Source) -> list[Violation]:
    """Check that single-argument constructors are marked explicit."""
    v = []
    for cls in src.nodes.get('class_specifier', 'struct_specifier'):
        ident = child(cls, 'type_identifier')
        if not ident:
            continue
        name = src.text_of(ident)
        for body in cls.children:
            if body.type != 'field_declaration_list':
                continue
            for decl in body.children:
                if decl.type not in _DECL_TYPES or child(decl, 'explicit_function_specifier'):
                    continue
                func = next((c for c in reversed(decl.children) if c.type == 'function_declarator'), None)
                if not func or src.id_of(func) != name:
                    continue
                plist = params(func)
                if plist is None or len(plist) != 1:
                    continue
                param = plist[0]
                is_copy_or_move = child(param, 'reference_declarator') and any(
                    _is_type(src, c, name)
                    or c.type == 'template_type' and any(_is_type(src, gc, name) for gc in c.children)
                    for c in param.children)
                if not is_copy_or_move:
                    v.append(src.at(decl, "decl.ctor.explicit",
                                    f"Single-argument constructor '{name}' should be explicit",
                                    severity=Severity.MINOR, column=False))
    return v


def check_cxx_control(src: Source, cfg: Config) -> list[Violation]:
    """Check CXX control flow rules: switch/default, label padding."""
    v = []

    if cfg.is_enabled("ctrl.switch"):
        for sw in src.nodes.get('switch_statement'):
            # Direct cases only, not those of nested switches
            body = child(sw, 'compound_statement')
            if not body or not any(c.type == 'case_statement' and c.children
                                   and src.text_of(c.children[0]) == 'default'
                                   for c in body.children):
                v.append(src.at(sw, "ctrl.switch", "Switch statement should have a default case",
                                column=False))

    if cfg.is_enabled("ctrl.switch.padding"):
        for node in src.nodes.get('case_statement'):
            colon = child(node, ':')
            if not colon:
                continue
            row, col = colon.start_point
            line = src.line(row)
            if line is not None and col > 0 and line[col - 1].isspace():
                v.append(src.violation("ctrl.switch.padding",
                                       "No space before colon in case/default label",
                                       row + 1, column=col, show_line=True))

    return v


def check_cxx_writing(src: Source, cfg: Config) -> list[Violation]:
    """Check CXX writing rules: braces, throw, operators, enum class, etc."""
    v = []

    if cfg.is_enabled("braces.empty"):
        for node in src.nodes.get('compound_statement'):
            if any(c.type not in ('{', '}', 'comment') for c in node.children):
                continue
            if node.start_point[0] != node.end_point[0]:
                v.append(src.at(node, "braces.empty", "Empty body should use {} on the same line",
                                column=False))
            elif src.text_of(node) != '{}':
                v.append(src.at(node, "braces.empty", "Empty body should be {} with no space",
                                column=False))

    if cfg.is_enabled("braces.single_exp"):
        bodies = []
        for node in src.nodes.get('if_statement', 'while_statement', 'for_statement', 'do_statement'):
            stmts = [c for c in node.children if c.type in _STMT_TYPES]
            if stmts:
                bodies.append(stmts[-1])
        # else if: the child is an if_statement, not a bare statement
        for node in src.nodes.get('else_clause'):
            bodies.extend(c for c in node.children if c.type in _STMT_TYPES)
        for body in bodies:
            v.append(src.at(body, "braces.single_exp", "Single-expression block should have braces",
                            severity=Severity.MINOR, column=False))

    check_throw = cfg.is_enabled("err.throw")
    check_paren = cfg.is_enabled("err.throw.paren")
    if check_throw or check_paren:
        for node in src.nodes.get('throw_statement'):
            for part in node.children:
                if check_throw and part.type in _LITERAL_TYPES:
                    v.append(src.at(node, "err.throw", "Don't throw literals, throw exception objects"))
                elif check_throw and part.type == 'new_expression':
                    v.append(src.at(node, "err.throw", "Don't throw with new, throw by value"))
                elif check_paren and part.type == 'parenthesized_expression':
                    v.append(src.at(node, "err.throw.paren", "No parentheses after throw"))

    if cfg.is_enabled("err.throw.catch"):
        for node in src.nodes.get('catch_clause'):
            for part in node.children:
                if part.type != 'parameter_list':
                    continue
                for param in part.children:
                    if param.type == 'parameter_declaration' \
                            and '&' not in (t := src.text_of(param)) and t != '...':
                        v.append(src.at(param, "err.throw.catch", "Catch exceptions by reference",
                                        severity=Severity.MINOR, column=False))

    if cfg.is_enabled("exp.padding"):
        for node in src.nodes.get('operator_name'):
            if ' ' in src.text_of(node)[len('operator'):]:
                v.append(src.at(node, "exp.padding",
                                "No space between 'operator' and the operator symbol"))

    if cfg.is_enabled("exp.linebreak"):
        v.extend(_check_linebreak_operators(src))

    if cfg.is_enabled("fun.proto.void.cxx"):
        for fd in src.nodes.get('function_declarator'):
            plist = params(fd)
            if plist and len(plist) == 1 and src.text_of(plist[0]).strip() == 'void':
                v.append(src.at(fd, "fun.proto.void.cxx",
                                f"'{src.id_of(fd) or '?'}' should use () not (void) in C++",
                                column=False))

    if cfg.is_enabled("op.assign"):
        for func in src.nodes.get('function_definition'):
            if not any(src.text_of(n) == 'operator=' for n in find_nodes(func, 'operator_name')):
                continue
            if not child(func, 'reference_declarator'):
                msg = "Assignment operator should return Class&"
            elif (body := child(func, 'compound_statement')) and 'return *this' not in src.text_of(body):
                msg = "Assignment operator should return *this"
            else:
                continue
            v.append(src.at(func, "op.assign", msg, column=False))

    check_overload = cfg.is_enabled("op.overload")
    check_binand = cfg.is_enabled("op.overload.binand")
    if check_overload or check_binand:
        for node in src.nodes.get('operator_name'):
            op = src.text_of(node).replace(' ', '')
            if check_overload and op in _FORBIDDEN_OPS:
                v.append(src.at(node, "op.overload", f"Don't overload {op}", column=False))
            elif check_binand and op == "operator&":
                v.append(src.at(node, "op.overload.binand", f"Don't overload {op}",
                                severity=Severity.MINOR, column=False))

    if cfg.is_enabled("enum.class"):
        for node in src.nodes.get('enum_specifier'):
            if not child(node, 'class', 'struct'):
                v.append(src.at(node, "enum.class", "Prefer 'enum class' over plain 'enum'",
                                severity=Severity.MINOR, column=False))

    return v


_TEMPLATE_TYPES = frozenset(('template_parameter_list', 'template_argument_list'))
_REF_TYPES = frozenset(('reference_declarator', 'abstract_reference_declarator', 'type_descriptor'))
_PTR_TYPES = frozenset(('pointer_declarator', 'abstract_pointer_declarator'))


def _non_binary_ops(src: Source) -> set[tuple[int, str]]:
    """(row, op) pairs where >, >>, &, or * are NOT binary operators."""
    excluded = set()
    for node in src.nodes.get(*_TEMPLATE_TYPES, *_REF_TYPES, *_PTR_TYPES, 'trailing_return_type'):
        end = node.end_point[0]
        if node.type in _TEMPLATE_TYPES:
            excluded.update(((end, '>'), (end, '>>')))
        elif node.type in _REF_TYPES:
            excluded.update((c.start_point[0], c.type) for c in node.children if c.type in ('&', '&&'))
        elif node.type in _PTR_TYPES:
            excluded.update((c.start_point[0], '*') for c in node.children if c.type == '*')
        else:
            excluded.update(((end, '&'), (end, '*'), (end, '>'), (end, '>>')))
    return excluded


# Longest first for greedy matching
_BIN_OPS = ('&&', '||', '<<', '>>', '==', '!=', '<=', '>=',
            '+', '-', '*', '/', '%', '&', '|', '^', '<', '>')


def _check_linebreak_operators(src: Source) -> list[Violation]:
    """Check that line breaks come before binary operators, not after."""
    v = []
    excluded = _non_binary_ops(src)
    for i, line in enumerate(_scrub_comments(src), 1):
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        for op in _BIN_OPS:
            before = s[:-len(op)].rstrip()
            if s.endswith(op) and before and not before.endswith(('(', ',', '=')):
                if (i - 1, op) not in excluded:
                    v.append(Violation(src.path, i, "exp.linebreak",
                                       f"Line break should come before '{op}', not after",
                                       line_content=line))
                break
    return v


CHECKS = (check_cxx_preprocessor, check_cxx_globals, check_cxx_naming,
          check_cxx_declarations, check_cxx_control, check_cxx_writing)
