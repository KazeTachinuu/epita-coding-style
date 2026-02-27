"""C++ (CXX) specific check functions for the EPITA coding style checker."""

from __future__ import annotations

import os
import re

from .config import Config
from .core import Violation, Severity, NodeCache, text, find_id, find_nodes, line_at
from .checks import check_vla, check_ctrl_empty, count_function_lines

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

# Memory allocation functions forbidden in C++
_MALLOC_FUNCS = {"malloc", "calloc", "realloc", "free"}

# Forbidden operator overloads
_FORBIDDEN_OPS = {"operator,", "operator||", "operator&&"}

_CAMEL_CASE = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
_LOWER_NS = re.compile(r'^[a-z_][a-z0-9_]*$')
_REF_PATTERN = re.compile(r'(\w)\s+&(\w)')
_PTR_PATTERN = re.compile(r'(\w)\s+\*(\w)')

_LITERAL_TYPES = frozenset(('number_literal', 'string_literal', 'char_literal',
                            'true', 'false', 'null', 'nullptr'))
_STMT_TYPES = frozenset(('expression_statement', 'return_statement', 'break_statement',
                         'continue_statement', 'throw_statement'))
_DECL_TYPES = frozenset(('declaration', 'field_declaration', 'function_definition'))


def check_cxx_preprocessor(path: str, lines: list[str], content_bytes: bytes,
                           nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX preprocessor rules: pragma.once, include.filetype, include.order, constexpr."""
    v = []

    if cfg.is_enabled("cpp.pragma.once") and path.endswith(('.hh', '.hxx')):
        has_pragma = any(line.strip() == '#pragma once' for line in lines)
        if not has_pragma:
            v.append(Violation(path, 1, "cpp.pragma.once",
                               "Use #pragma once instead of include guards",
                               line_content=lines[0] if lines else None))

    if cfg.is_enabled("cpp.include.filetype"):
        for inc in nodes.get('preproc_include'):
            for child in inc.children:
                if child.type == 'string_literal':
                    fname = text(child, content_bytes).strip('"')
                    if not fname.endswith(('.hh', '.hxx')):
                        line_num = inc.start_point[0] + 1
                        v.append(Violation(path, line_num, "cpp.include.filetype",
                                           f"Included file '{fname}' should have .hh or .hxx extension",
                                           line_content=line_at(lines, inc.start_point[0])))

    if cfg.is_enabled("cpp.include.order"):
        v.extend(_check_include_order(path, lines, nodes, content_bytes))

    if cfg.is_enabled("cpp.constexpr"):
        for decl in nodes.root.children:
            if decl.type != 'declaration':
                continue
            has_const = any(text(c, content_bytes) == 'const'
                           for c in decl.children if c.type == 'type_qualifier')
            if not has_const:
                continue
            # Check if it's a simple literal init that could be constexpr
            for child in decl.children:
                if child.type == 'init_declarator':
                    for c in child.children:
                        if c.type in ('number_literal', 'string_literal', 'true', 'false', 'char_literal'):
                            line_num = decl.start_point[0] + 1
                            v.append(Violation(path, line_num, "cpp.constexpr",
                                               "Consider using constexpr for compile-time constant",
                                               Severity.MINOR,
                                               line_content=line_at(lines, decl.start_point[0])))
                            break

    return v


def _check_include_order(path: str, lines: list[str], nodes: NodeCache,
                         content_bytes: bytes) -> list[Violation]:
    """Check that includes are ordered: same-name header, system, local."""
    base = os.path.splitext(os.path.basename(path))[0]
    v = []

    includes = []
    for inc in nodes.get('preproc_include'):
        line_num = inc.start_point[0] + 1
        for child in inc.children:
            if child.type == 'system_lib_string':
                includes.append((line_num, 'system', text(child, content_bytes)))
            elif child.type == 'string_literal':
                fname = text(child, content_bytes).strip('"')
                fname_base = os.path.splitext(fname)[0]
                if fname_base == base:
                    includes.append((line_num, 'self', fname))
                else:
                    includes.append((line_num, 'local', fname))

    if not includes:
        return v

    # Check self-include is first (skip for .hh including .hxx at the end)
    self_incs = [i for i in includes if i[1] == 'self']
    if self_incs:
        is_header_with_hxx = path.endswith('.hh') and self_incs[0][2].endswith('.hxx')
        first_non_self = next((i for i in includes if i[1] != 'self'), None)
        if not is_header_with_hxx and first_non_self and self_incs[0][0] > first_non_self[0]:
            v.append(Violation(path, self_incs[0][0], "cpp.include.order",
                               "Same-name header should be included first",
                               line_content=lines[self_incs[0][0] - 1] if self_incs[0][0] <= len(lines) else None))

    # Find first local that comes before a system include
    found_order_violation = False
    for i, (line_num, kind, _) in enumerate(includes):
        if kind == 'local':
            for _, kind2, _ in includes[i + 1:]:
                if kind2 == 'system':
                    v.append(Violation(path, line_num, "cpp.include.order",
                                       "System includes should come before local includes",
                                       line_content=lines[line_num - 1] if line_num <= len(lines) else None))
                    found_order_violation = True
                    break
            if found_order_violation:
                break

    # Check alphabetical order within each group
    groups: dict[str, list[tuple[int, str]]] = {}
    for line_num, kind, fname in includes:
        groups.setdefault(kind, []).append((line_num, fname))
    for kind, items in groups.items():
        for j in range(1, len(items)):
            prev_name = items[j - 1][1].lower()
            curr_name = items[j][1].lower()
            if curr_name < prev_name:
                v.append(Violation(path, items[j][0], "cpp.include.order",
                                   f"Includes not in alphabetical order: '{items[j][1]}' before '{items[j - 1][1]}'",
                                   Severity.MINOR,
                                   line_content=lines[items[j][0] - 1] if items[j][0] <= len(lines) else None))
                break  # one per group

    # Check blank line between groups
    prev_kind = None
    prev_line = None
    for line_num, kind, _ in includes:
        if prev_kind is not None and kind != prev_kind:
            # Check there's a blank line between prev_line and line_num (both 1-indexed)
            has_blank = False
            for idx in range(prev_line, line_num - 1):  # 0-indexed: prev_line..line_num-2
                if idx < len(lines) and not lines[idx].strip():
                    has_blank = True
                    break
            if not has_blank:
                v.append(Violation(path, line_num, "cpp.include.order",
                                   "Include groups should be separated by a blank line",
                                   Severity.MINOR,
                                   line_content=lines[line_num - 1] if line_num <= len(lines) else None))
        prev_kind = kind
        prev_line = line_num

    return v


def check_cxx_globals(path: str, lines: list[str], content_bytes: bytes,
                      nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX global rules: casts, memory, nullptr, extern C, C headers, C functions."""
    v = []

    if cfg.is_enabled("global.casts"):
        for node in nodes.get('cast_expression'):
            line_num = node.start_point[0] + 1
            line_content = line_at(lines, node.start_point[0])
            v.append(Violation(path, line_num, "global.casts",
                               "Use C++ casts (static_cast, etc.) instead of C-style casts",
                               line_content=line_content, column=node.start_point[1]))

    # global.memory.no_malloc + c.std_functions: combined pass over call_expression
    _check_malloc = cfg.is_enabled("global.memory.no_malloc")
    _check_std = cfg.is_enabled("c.std_functions")
    if _check_malloc or _check_std:
        for node in nodes.get('call_expression'):
            func_node = node.children[0] if node.children else None
            if not func_node or func_node.type != 'identifier':
                continue
            fname = text(func_node, content_bytes)
            line_num = node.start_point[0] + 1
            lc = line_at(lines, node.start_point[0])
            col = node.start_point[1]
            if _check_malloc and fname in _MALLOC_FUNCS:
                v.append(Violation(path, line_num, "global.memory.no_malloc",
                                   f"Don't use {fname}(), use new/delete or smart pointers",
                                   line_content=lc, column=col))
            elif _check_std and fname in _C_FUNCTIONS and fname not in _MALLOC_FUNCS:
                v.append(Violation(path, line_num, "c.std_functions",
                                   f"Use std::{fname} instead of {fname}",
                                   line_content=lc, column=col))

    # global.nullptr: use nullptr, not NULL
    if cfg.is_enabled("global.nullptr"):
        for node in nodes.get('null'):
            if text(node, content_bytes) == 'NULL':
                v.append(Violation(path, node.start_point[0] + 1, "global.nullptr",
                                   "Use nullptr instead of NULL",
                                   line_content=line_at(lines, node.start_point[0]),
                                   column=node.start_point[1]))

    # c.extern: no extern "C"
    if cfg.is_enabled("c.extern"):
        for node in nodes.get('linkage_specification'):
            v.append(Violation(path, node.start_point[0] + 1, "c.extern",
                               'No extern "C" in C++ code',
                               line_content=line_at(lines, node.start_point[0]),
                               column=node.start_point[1]))

    # c.headers: no C headers
    if cfg.is_enabled("c.headers"):
        for inc in nodes.get('preproc_include'):
            for child in inc.children:
                if child.type == 'system_lib_string':
                    header = text(child, content_bytes).strip('<>')
                    if header in _C_HEADERS:
                        v.append(Violation(path, inc.start_point[0] + 1, "c.headers",
                                           f"Use <c{header.replace('.h', '')}> instead of <{header}>",
                                           line_content=line_at(lines, inc.start_point[0])))

    return v


def check_cxx_naming(path: str, lines: list[str], content_bytes: bytes,
                     nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX naming rules: class/struct names (CamelCase), namespace (lowercase + closing comment)."""
    v = []

    if cfg.is_enabled("naming.class"):
        for node in nodes.get('class_specifier', 'struct_specifier'):
            for child in node.children:
                if child.type == 'type_identifier':
                    name = text(child, content_bytes)
                    if not _CAMEL_CASE.match(name):
                        line_num = child.start_point[0] + 1
                        line_content = line_at(lines, child.start_point[0])
                        v.append(Violation(path, line_num, "naming.class",
                                           f"Class/struct '{name}' should be CamelCase",
                                           line_content=line_content, column=child.start_point[1]))
                    break

    if cfg.is_enabled("naming.namespace"):
        for node in nodes.get('namespace_definition'):
            ns_name = None
            for child in node.children:
                if child.type == 'namespace_identifier':
                    ns_name = text(child, content_bytes)
                    if not _LOWER_NS.match(ns_name):
                        v.append(Violation(path, child.start_point[0] + 1, "naming.namespace",
                                           f"Namespace '{ns_name}' should be lowercase",
                                           line_content=line_at(lines, child.start_point[0]),
                                           column=child.start_point[1]))
                    break

            end_line = node.end_point[0]
            if ns_name and end_line < len(lines):
                closing = lines[end_line].strip()
                if closing.startswith('}') and f'// namespace {ns_name}' not in closing:
                    v.append(Violation(path, end_line + 1, "naming.namespace",
                                       f"Closing brace should have comment '// namespace {ns_name}'",
                                       Severity.MINOR, line_content=lines[end_line]))

    return v


def check_cxx_declarations(path: str, lines: list[str], content_bytes: bytes,
                           nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX declaration rules: ref/pointer placement, explicit constructors, VLA."""
    v = []

    # decl.ref / decl.point: & and * should be next to type, not variable
    if cfg.is_enabled("decl.ref") or cfg.is_enabled("decl.point"):
        v.extend(_check_ref_pointer_placement(path, lines, content_bytes, nodes, cfg))

    # decl.ctor.explicit: single-arg constructors should be explicit
    if cfg.is_enabled("decl.ctor.explicit"):
        v.extend(_check_explicit_ctors(path, lines, content_bytes, nodes))

    # decl.vla: no variable-length arrays (shared helper)
    v.extend(check_vla(path, nodes, content_bytes, lines, cfg))

    return v


def _check_ref_pointer_placement(path: str, lines: list[str], content_bytes: bytes,
                                 nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check that & and * are next to type, not variable name."""
    v = []

    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith(('#', '//', '/*', '*')):
            continue

        if cfg.is_enabled("decl.ref"):
            for m in _REF_PATTERN.finditer(line):
                # Avoid matching && (logical and) or &= etc.
                pos = m.start(0)
                # Check it's not inside a string or preceded by another &
                amp_pos = line.index('&', pos)
                if amp_pos + 1 < len(line) and line[amp_pos + 1] == '&':
                    continue  # It's && operator
                # Check context: should be in a declaration context
                if _is_declaration_context(line):
                    v.append(Violation(path, i, "decl.ref",
                                       "& should be next to type, not variable",
                                       line_content=line, column=amp_pos))

        if cfg.is_enabled("decl.point"):
            for m in _PTR_PATTERN.finditer(line):
                pos = m.start(0)
                star_pos = line.index('*', pos)
                # Skip if inside a comment or multiplication
                if _is_declaration_context(line):
                    v.append(Violation(path, i, "decl.point",
                                       "* should be next to type, not variable",
                                       line_content=line, column=star_pos))

    return v


_TYPE_KEYWORDS = frozenset({
    'int', 'char', 'float', 'double', 'long', 'short', 'unsigned',
    'signed', 'void', 'bool', 'auto', 'const', 'static', 'volatile',
    'extern', 'virtual', 'inline', 'explicit', 'mutable',
})


def _is_declaration_context(line: str) -> bool:
    """Heuristic: check if a line looks like a declaration (has a type)."""
    words = line.split()
    if not words:
        return False
    first = words[0]
    if any(w in _TYPE_KEYWORDS for w in words[:3]):
        return True
    if first[0].isupper() and first.isalpha():
        return True
    return first.startswith('std::')


def _check_explicit_ctors(path: str, lines: list[str], content_bytes: bytes,
                          nodes: NodeCache) -> list[Violation]:
    """Check that single-argument constructors are marked explicit."""
    v = []
    for cls in nodes.get('class_specifier', 'struct_specifier'):
        class_name = None
        for child in cls.children:
            if child.type == 'type_identifier':
                class_name = text(child, content_bytes)
                break
        if not class_name:
            continue

        for child in cls.children:
            if child.type != 'field_declaration_list':
                continue
            for decl in child.children:
                if decl.type not in _DECL_TYPES:
                    continue
                func_decl = None
                is_explicit = False
                for c in decl.children:
                    if c.type == 'function_declarator':
                        func_decl = c
                    elif c.type == 'explicit_function_specifier':
                        is_explicit = True
                if not func_decl or is_explicit:
                    continue
                if find_id(func_decl, content_bytes) != class_name:
                    continue

                params = []
                for c in func_decl.children:
                    if c.type == 'parameter_list':
                        params = [p for p in c.children if p.type == 'parameter_declaration']
                if len(params) != 1:
                    continue

                # Skip copy/move constructors
                param = params[0]
                has_ref = any(c.type == 'reference_declarator' for c in param.children)
                if has_ref and _param_has_type(param, class_name, content_bytes):
                    continue

                v.append(Violation(path, decl.start_point[0] + 1, "decl.ctor.explicit",
                                   f"Single-argument constructor '{class_name}' should be explicit",
                                   Severity.MINOR,
                                   line_content=line_at(lines, decl.start_point[0])))

    return v


def _param_has_type(param, class_name: str, content_bytes: bytes) -> bool:
    """Check if a parameter references the given class type (for copy/move detection)."""
    for c in param.children:
        if c.type == 'type_identifier' and text(c, content_bytes) == class_name:
            return True
        if c.type == 'template_type':
            if any(gc.type == 'type_identifier' and text(gc, content_bytes) == class_name
                   for gc in c.children):
                return True
    return False


def check_cxx_control(path: str, lines: list[str], content_bytes: bytes,
                      nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX control flow rules: switch/default, label padding, empty bodies."""
    v = []

    # ctrl.switch: default case must be present
    if cfg.is_enabled("ctrl.switch"):
        for sw in nodes.get('switch_statement'):
            has_default = False
            # Only check direct case_statement children of the switch's body,
            # not recursing into nested switches.
            body = None
            for child in sw.children:
                if child.type == 'compound_statement':
                    body = child
                    break
            if body:
                for child in body.children:
                    if child.type == 'case_statement':
                        case_text = text(child.children[0], content_bytes) if child.children else ''
                        if case_text == 'default':
                            has_default = True
                            break
            if not has_default:
                line_num = sw.start_point[0] + 1
                line_content = line_at(lines, sw.start_point[0])
                v.append(Violation(path, line_num, "ctrl.switch",
                                   "Switch statement should have a default case",
                                   line_content=line_content))

    # ctrl.switch.padding: no space before colon in case/default labels
    if cfg.is_enabled("ctrl.switch.padding"):
        for node in nodes.get('case_statement'):
            # Find the colon
            for child in node.children:
                if child.type == ':':
                    col = child.start_point[1]
                    line_idx = child.start_point[0]
                    if line_idx < len(lines) and col > 0 and lines[line_idx][col - 1].isspace():
                        v.append(Violation(path, line_idx + 1, "ctrl.switch.padding",
                                           "No space before colon in case/default label",
                                           line_content=lines[line_idx], column=col))
                    break

    # ctrl.empty: empty loop bodies should use continue (shared helper)
    v.extend(check_ctrl_empty(path, lines, cfg, nodes=nodes))

    return v


def check_cxx_writing(path: str, lines: list[str], content_bytes: bytes,
                      nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX writing rules: braces, throw, operators, enum class, etc."""
    v = []

    if cfg.is_enabled("braces.empty"):
        v.extend(_check_empty_braces(path, lines, content_bytes, nodes))

    if cfg.is_enabled("braces.single_exp"):
        v.extend(_check_single_exp_braces(path, lines, content_bytes, nodes))

    # err.throw + err.throw.paren: combined pass
    _check_throw = cfg.is_enabled("err.throw")
    _check_throw_paren = cfg.is_enabled("err.throw.paren")
    if _check_throw or _check_throw_paren:
        for node in nodes.get('throw_statement'):
            line_num = node.start_point[0] + 1
            line_content = line_at(lines, node.start_point[0])
            col = node.start_point[1]
            for child in node.children:
                if _check_throw and child.type in _LITERAL_TYPES:
                    v.append(Violation(path, line_num, "err.throw",
                                       "Don't throw literals, throw exception objects",
                                       line_content=line_content, column=col))
                elif _check_throw and child.type == 'new_expression':
                    v.append(Violation(path, line_num, "err.throw",
                                       "Don't throw with new, throw by value",
                                       line_content=line_content, column=col))
                elif _check_throw_paren and child.type == 'parenthesized_expression':
                    v.append(Violation(path, line_num, "err.throw.paren",
                                       "No parentheses after throw",
                                       line_content=line_content, column=col))

    if cfg.is_enabled("err.throw.catch"):
        for node in nodes.get('catch_clause'):
            for child in node.children:
                if child.type == 'parameter_list':
                    for param in child.children:
                        if param.type == 'parameter_declaration':
                            param_text = text(param, content_bytes)
                            if '&' not in param_text and param_text != '...':
                                v.append(Violation(path, param.start_point[0] + 1,
                                                   "err.throw.catch",
                                                   "Catch exceptions by reference",
                                                   Severity.MINOR,
                                                   line_content=line_at(lines, param.start_point[0])))

    if cfg.is_enabled("exp.padding"):
        v.extend(_check_operator_padding(path, lines, content_bytes, nodes))

    if cfg.is_enabled("exp.linebreak"):
        v.extend(_check_linebreak_operators(path, lines, root=nodes.root))

    if cfg.is_enabled("fun.proto.void.cxx"):
        v.extend(_check_no_void_params(path, lines, content_bytes, nodes))

    if cfg.is_enabled("fun.length"):
        max_lines = cfg.max_lines
        for func in nodes.get('function_definition'):
            body = next((c for c in func.children if c.type == 'compound_statement'), None)
            if body:
                count = count_function_lines(body, lines)
                if count > max_lines:
                    v.append(Violation(path, func.start_point[0] + 1, "fun.length",
                                       f"Function has {count} lines (max {max_lines})",
                                       line_content=line_at(lines, func.start_point[0])))

    if cfg.is_enabled("op.assign"):
        v.extend(_check_op_assign(path, lines, content_bytes, nodes))

    # op.overload + op.overload.binand
    _check_overload = cfg.is_enabled("op.overload")
    _check_binand = cfg.is_enabled("op.overload.binand")
    if _check_overload or _check_binand:
        for node in nodes.get('operator_name'):
            op = text(node, content_bytes).replace(' ', '')
            line_num = node.start_point[0] + 1
            lc = line_at(lines, node.start_point[0])
            if _check_overload and op in _FORBIDDEN_OPS:
                v.append(Violation(path, line_num, "op.overload",
                                   f"Don't overload {op}", line_content=lc))
            elif _check_binand and op == "operator&":
                v.append(Violation(path, line_num, "op.overload.binand",
                                   f"Don't overload {op}", Severity.MINOR, line_content=lc))

    if cfg.is_enabled("enum.class"):
        for node in nodes.get('enum_specifier'):
            has_class = any(child.type == 'class' for child in node.children)
            if not has_class:
                line_num = node.start_point[0] + 1
                line_content = line_at(lines, node.start_point[0])
                v.append(Violation(path, line_num, "enum.class",
                                   "Prefer 'enum class' over plain 'enum'",
                                   Severity.MINOR,
                                   line_content=line_content))

    return v


def _check_empty_braces(path: str, lines: list[str], content_bytes: bytes,
                        nodes: NodeCache) -> list[Violation]:
    """Check that empty bodies use {} on the same line (no space inside)."""
    v = []
    for node in nodes.get('compound_statement'):
        # Empty body: only { and } children, no statements
        real_children = [c for c in node.children if c.type not in ('{', '}', 'comment')]
        if not real_children:
            if node.start_point[0] != node.end_point[0]:
                # Multi-line empty body
                line_num = node.start_point[0] + 1
                line_content = line_at(lines, node.start_point[0])
                v.append(Violation(path, line_num, "braces.empty",
                                   "Empty body should use {} on the same line",
                                   line_content=line_content))
            else:
                # Same line — must be exactly `{}`, not `{ }` or `{ /* comment */ }`
                body_text = text(node, content_bytes)
                if body_text != '{}':
                    line_num = node.start_point[0] + 1
                    line_content = line_at(lines, node.start_point[0])
                    v.append(Violation(path, line_num, "braces.empty",
                                       "Empty body should be {} with no space",
                                       line_content=line_content))
    return v


def _check_single_exp_braces(path: str, lines: list[str], content_bytes: bytes,
                             nodes: NodeCache) -> list[Violation]:
    """Check that single-expression blocks have braces."""
    v = []
    for node in nodes.get('if_statement', 'while_statement', 'for_statement', 'do_statement'):
        body = None
        for child in node.children:
            if child.type in _STMT_TYPES:
                body = child

        if body:
            line_num = body.start_point[0] + 1
            line_content = line_at(lines, body.start_point[0])
            v.append(Violation(path, line_num, "braces.single_exp",
                               "Single-expression block should have braces",
                               Severity.MINOR,
                               line_content=line_content))

    # else clauses: skip `else if` (child is if_statement, not a bare statement)
    for node in nodes.get('else_clause'):
        for child in node.children:
            if child.type in _STMT_TYPES:
                line_num = child.start_point[0] + 1
                line_content = line_at(lines, child.start_point[0])
                v.append(Violation(path, line_num, "braces.single_exp",
                                   "Single-expression block should have braces",
                                   Severity.MINOR,
                                   line_content=line_content))

    return v


def _check_operator_padding(path: str, lines: list[str],
                            content_bytes: bytes,
                            nodes: NodeCache) -> list[Violation]:
    """Check no space in operator keyword (operator++ not operator ++)."""
    v = []
    for node in nodes.get('operator_name'):
        op_text = text(node, content_bytes)
        # Check if there's a space between 'operator' and the symbol
        if ' ' in op_text[len('operator'):]:
            line_num = node.start_point[0] + 1
            v.append(Violation(path, line_num, "exp.padding",
                               "No space between 'operator' and the operator symbol",
                               line_content=line_at(lines, node.start_point[0]),
                               column=node.start_point[1]))
    return v


_TEMPLATE_TYPES = frozenset(('template_parameter_list', 'template_argument_list'))
_REF_TYPES = frozenset(('reference_declarator', 'abstract_reference_declarator', 'type_descriptor'))
_PTR_TYPES = frozenset(('pointer_declarator', 'abstract_pointer_declarator'))


def _collect_non_binary_op_lines(root) -> set[tuple[int, str]]:
    """Find lines where >, >>, &, or * are NOT binary operators (AST-based)."""
    excluded = set()
    stack = [root]
    while stack:
        node = stack.pop()
        ntype = node.type
        if ntype in _TEMPLATE_TYPES:
            end_line = node.end_point[0]
            excluded.add((end_line, '>'))
            excluded.add((end_line, '>>'))
        elif ntype in _REF_TYPES:
            for child in node.children:
                if child.type in ('&', '&&'):
                    excluded.add((child.start_point[0], child.type))
        elif ntype in _PTR_TYPES:
            for child in node.children:
                if child.type == '*':
                    excluded.add((child.start_point[0], '*'))
        elif ntype == 'trailing_return_type':
            end_line = node.end_point[0]
            excluded.update(((end_line, '&'), (end_line, '*'),
                             (end_line, '>'), (end_line, '>>')))
        stack.extend(node.children)
    return excluded


# Pre-sorted by length (longest first) for greedy matching
_BIN_OPS = ('&&', '||', '<<', '>>', '==', '!=', '<=', '>=',
            '+', '-', '*', '/', '%', '&', '|', '^', '<', '>')


def _check_linebreak_operators(path: str, lines: list[str],
                               root=None) -> list[Violation]:
    """Check that line breaks come before binary operators, not after."""
    v = []
    excluded = _collect_non_binary_op_lines(root) if root else set()

    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith(('#', '//', '/*', '*')):
            continue
        for op in _BIN_OPS:
            if s.endswith(op) and not s.endswith(f'//{op}'):
                before = s[:-len(op)].rstrip()
                if before and not before.endswith(('(', ',', '=')):
                    if (i - 1, op) in excluded:
                        break
                    v.append(Violation(path, i, "exp.linebreak",
                                       f"Line break should come before '{op}', not after",
                                       line_content=line))
                    break

    return v


def _check_no_void_params(path: str, lines: list[str], content_bytes: bytes,
                          nodes: NodeCache) -> list[Violation]:
    """In C++, empty parameter lists should use () not (void)."""
    v = []
    seen = set()
    for node in nodes.get('function_definition', 'declaration', 'field_declaration'):
        for fd in find_nodes(node, 'function_declarator'):
            key = (fd.start_point, fd.end_point)
            if key in seen:
                continue
            seen.add(key)
            for child in fd.children:
                if child.type == 'parameter_list':
                    params = [p for p in child.children if p.type == 'parameter_declaration']
                    if len(params) == 1 and text(params[0], content_bytes).strip() == 'void':
                        name = find_id(fd, content_bytes)
                        v.append(Violation(path, fd.start_point[0] + 1, "fun.proto.void.cxx",
                                           f"'{name or '?'}' should use () not (void) in C++",
                                           line_content=line_at(lines, fd.start_point[0])))
    return v


def _check_op_assign(path: str, lines: list[str], content_bytes: bytes,
                     nodes: NodeCache) -> list[Violation]:
    """Check that assignment operators return Class& and *this."""
    v = []
    for func in nodes.get('function_definition'):
        if not any(text(n, content_bytes) == 'operator=' for n in find_nodes(func, 'operator_name')):
            continue

        line_num = func.start_point[0] + 1
        lc = line_at(lines, func.start_point[0])

        if not any(c.type == 'reference_declarator' for c in func.children):
            v.append(Violation(path, line_num, "op.assign",
                               "Assignment operator should return Class&", line_content=lc))
            continue

        body = next((c for c in func.children if c.type == 'compound_statement'), None)
        if body and 'return *this' not in text(body, content_bytes):
            v.append(Violation(path, line_num, "op.assign",
                               "Assignment operator should return *this", line_content=lc))

    return v


