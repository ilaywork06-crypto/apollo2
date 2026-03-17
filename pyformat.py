"""
pyformat.py — Custom Python formatter using libcst.

Conventions applied:
  1. ruff format runs first
  2. Function parameters: one per line if more than 3 params (including *args, **kwargs, kwonly)
  3. 2 blank lines before class/function definitions (top-level)
  4. 1 blank line after the import block
  5. Optional section comments (--sections flag)
     Format:  # ----- Imports ----- #
     Order:   Imports → Classes → Functions
     Handles decorators correctly
     Idempotent: strips old headers before re-injecting

Usage:
  python pyformat.py .                         # format recursively
  python pyformat.py src/                      # specific directory
  python pyformat.py file.py                   # single file
  python pyformat.py . --sections              # with section dividers
  python pyformat.py . --dry-run               # preview only
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    import libcst as cst
    from libcst import parse_module
except ImportError:
    print("libcst not installed. Run: pip install libcst")
    sys.exit(1)


# ----- Classes ----- #


class ParameterFormatter(cst.CSTTransformer):
    """
    Expand ALL function parameters to one-per-line when total count > 3.
    Handles: regular params, *args, keyword-only, **kwargs, defaults, annotations.

    Before:  def foo(a, b, c, d, **kwargs):
    After:   def foo(
                 a,
                 b,
                 c,
                 d,
                 **kwargs,
             ):
    """

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        params = updated_node.params

        total = (
            len(params.params)
            + len(params.kwonly_params)
            + (1 if params.star_kwarg else 0)
            + (1 if isinstance(params.star_arg, cst.Param) else 0)
        )

        if total <= 3:
            return updated_node

        indent = "    "

        newline_then_indent = cst.ParenthesizedWhitespace(
            first_line=cst.TrailingWhitespace(newline=cst.Newline()),
            indent=True,
            last_line=cst.SimpleWhitespace(indent),
        )

        def with_trailing_comma(param):
            return param.with_changes(
                comma=cst.Comma(whitespace_after=newline_then_indent)
            )

        def without_comma(param):
            return param.with_changes(comma=cst.MaybeSentinel.DEFAULT)

        # Regular params
        new_params = [with_trailing_comma(p) for p in params.params]

        # *args
        new_star_arg = params.star_arg
        if isinstance(params.star_arg, cst.Param):
            new_star_arg = with_trailing_comma(params.star_arg)

        # keyword-only params
        new_kwonly = [with_trailing_comma(p) for p in params.kwonly_params]

        # Add trailing comma to last param so closing ) drops to its own line
        new_star_kwarg = params.star_kwarg
        if params.star_kwarg:
            new_star_kwarg = with_trailing_comma(params.star_kwarg)
        elif new_kwonly:
            new_kwonly[-1] = with_trailing_comma(new_kwonly[-1])
        elif new_params:
            new_params[-1] = with_trailing_comma(new_params[-1])

        new_parameters = params.with_changes(
            params=new_params,
            star_arg=new_star_arg,
            kwonly_params=new_kwonly,
            star_kwarg=new_star_kwarg,
        )

        return updated_node.with_changes(
            params=new_parameters,
            # Force first param onto next line after (
            whitespace_before_params=cst.ParenthesizedWhitespace(
                first_line=cst.TrailingWhitespace(newline=cst.Newline()),
                indent=True,
                last_line=cst.SimpleWhitespace(indent),
            ),

        )


class BlankLineFormatter(cst.CSTTransformer):
    """
    - 1 blank line after the import block
    - 2 blank lines before top-level class/function (not right after imports)
    """

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        new_body = list(updated_node.body)
        result = []
        import_block_ended = False
        last_was_import = False

        for i, stmt in enumerate(new_body):
            is_import = isinstance(stmt, cst.SimpleStatementLine) and any(
                isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body
            )
            is_class_or_func = isinstance(stmt, (cst.ClassDef, cst.FunctionDef))

            if last_was_import and not is_import and not import_block_ended:
                import_block_ended = True
                stmt = self._set_leading_lines(stmt, 1)
            elif is_class_or_func and i > 0 and import_block_ended:
                stmt = self._set_leading_lines(stmt, 2)

            result.append(stmt)
            last_was_import = is_import

        return updated_node.with_changes(body=result)

    def _set_leading_lines(self, stmt, count: int):
        empty_lines = [cst.EmptyLine() for _ in range(count)]
        try:
            return stmt.with_changes(leading_lines=empty_lines)
        except Exception:
            return stmt


# ----- Functions ----- #

_SECTION_RE = re.compile(
    r"^[ \t]*#[ \t]*(?:-----[^\n]*-----|[─\-]{3,}[^\n]*[─\-]{3,})[ \t]*(?:#[ \t]*)?\n",
    re.MULTILINE,
)


def _section(title: str) -> str:
    return f"# ----- {title} ----- #"


def strip_existing_sections(source: str) -> str:
    return _SECTION_RE.sub("", source)


def _inject_header(result: list, header: str, line: str) -> None:
    """Strip trailing blanks, write: blank + header + 2 blanks + line."""
    while result and result[-1].strip() == "":
        result.pop()
    result.append("\n")
    result.append(header + "\n")
    result.append("\n")
    result.append("\n")
    result.append(line)


# Constants = top-level (no indentation) ALL_CAPS assignments with primitive values.
# Excludes: indented lines (inside functions/classes), class instances, function calls.
_CONST_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*\s*(?::[^=]+)?\s*=\s*(.+)")
_PRIMITIVE_RE = re.compile(r"""^(?:
    -?\d[\d_]*(?:\.\d+)?        # int / float
    |"[^"]*"                    # double-quoted string
    |'[^']*'                 # single-quoted string
    |True|False|None            # builtins
    |\(.*\)                     # tuple
    |\[.*\]                     # list
    |r"[^"]*"|r'[^']*'       # raw strings
    |f"[^"]*"|f'[^']*'       # f-strings
)\s*$""", re.VERBOSE)


def _is_const_line(line: str) -> bool:
    # Must be at column 0 (top-level only — not inside a function or class)
    if line != line.lstrip():
        return False
    m = _CONST_NAME_RE.match(line)
    if not m:
        return False
    value = m.group(1).strip()
    return bool(_PRIMITIVE_RE.match(value))


def _find_section_indices(source: str) -> dict:
    """
    Use libcst to find the line numbers of the first import, last import,
    first const, first class, first function — all at module (top) level only.
    Returns a dict with keys: first_import, last_import, first_const, first_class, first_func.
    All values are line numbers (1-based from libcst) converted to 0-based for splitlines().
    """
    try:
        tree = parse_module(source)
    except cst.ParserSyntaxError:
        return {}

    wrapper = cst.metadata.MetadataWrapper(tree)
    positions = wrapper.resolve(cst.metadata.PositionProvider)

    result = {
        "first_import": None,
        "last_import": None,
        "first_const": None,
        "first_class": None,
        "first_func": None,
    }

    lines = source.splitlines(keepends=True)

    for stmt in wrapper.module.body:
        pos = positions[stmt]
        start_line = pos.start.line - 1

        # Imports
        if isinstance(stmt, cst.SimpleStatementLine) and any(
            isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body
        ):
            if result["first_import"] is None:
                result["first_import"] = start_line
            result["last_import"] = start_line

        # Constants: top-level ALL_CAPS with primitive value
        if isinstance(stmt, cst.SimpleStatementLine) and any(
            isinstance(s, cst.Assign) for s in stmt.body
        ):
            if _is_const_line(lines[start_line]):
                if result["first_const"] is None:
                    result["first_const"] = start_line

        # Classes — point at decorator if present
        if isinstance(stmt, cst.ClassDef):
            if result["first_class"] is None:
                if stmt.decorators:
                    result["first_class"] = positions[stmt.decorators[0]].start.line - 1
                else:
                    result["first_class"] = start_line

        # Functions — point at decorator if present
        if isinstance(stmt, cst.FunctionDef):
            if result["first_func"] is None:
                if stmt.decorators:
                    result["first_func"] = positions[stmt.decorators[0]].start.line - 1
                else:
                    result["first_func"] = start_line

    return result


def add_section_comments(source: str) -> str:
    """
    Inject section dividers — idempotent, decorator-aware.
    Order: Imports → Constants → Classes → Functions

    Uses libcst for accurate top-level detection (no false positives from
    indented code, decorators with multi-line bodies, etc.)
    """
    source = strip_existing_sections(source)
    indices = _find_section_indices(source)

    first_import_idx = indices.get("first_import")
    last_import_idx  = indices.get("last_import")
    first_const_idx  = indices.get("first_const")
    first_class_idx  = indices.get("first_class")
    first_func_idx   = indices.get("first_func")

    lines = source.splitlines(keepends=True)

    result = []
    consts_header_added = False
    classes_header_added = False
    functions_header_added = False

    for idx, line in enumerate(lines):
        # Imports header
        if idx == first_import_idx:
            while result and result[-1].strip() == "":
                result.pop()
            result.append(_section("Imports") + "\n")
            result.append("\n")

        # 1 blank line after last import
        if last_import_idx is not None and idx == last_import_idx + 1:
            while result and result[-1].strip() == "":
                result.pop()
            result.append("\n")

        # Constants header — 1 blank line before (not 2)
        if idx == first_const_idx and not consts_header_added:
            while result and result[-1].strip() == "":
                result.pop()
            result.append("\n")
            result.append(_section("Constants") + "\n")
            result.append("\n")
            result.append(line)
            consts_header_added = True
            continue

        # Classes header
        if idx == first_class_idx and not classes_header_added:
            _inject_header(result, _section("Classes"), line)
            classes_header_added = True
            continue

        # Functions header
        if idx == first_func_idx and not functions_header_added:
            _inject_header(result, _section("Functions"), line)
            functions_header_added = True
            continue

        result.append(line)

    return "".join(result)


def run_ruff(target: str) -> None:
    try:
        proc = subprocess.run(
            ["ruff", "format", target],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(f"  ⚠  ruff format failed:\n{proc.stderr}")
        else:
            print("  ✓ ruff format done")
    except FileNotFoundError:
        print("  ⚠  ruff not found — skipping (pip install ruff)")


def format_source(source: str, use_sections: bool = False) -> str:
    source = strip_existing_sections(source)

    try:
        tree = parse_module(source)
    except cst.ParserSyntaxError as e:
        raise ValueError(f"Syntax error: {e}") from e

    tree = tree.visit(BlankLineFormatter())
    tree = tree.visit(ParameterFormatter())
    result = tree.code

    if use_sections:
        result = add_section_comments(result)

    return result


def format_file(path: Path, use_sections: bool, dry_run: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    try:
        formatted = format_source(original, use_sections)
    except ValueError as e:
        print(f"  ⚠  Skipping {path}: {e}")
        return False

    if formatted == original:
        return False

    if dry_run:
        print(f"  ~ Would change: {path}")
    else:
        path.write_text(formatted, encoding="utf-8")
        print(f"  ✓ Formatted:    {path}")

    return True


def format_target(target: str, use_sections: bool, dry_run: bool):
    p = Path(target)

    if p.is_file():
        files = [p] if p.suffix == ".py" else []
    elif p.is_dir():
        files = sorted(p.rglob("*.py"))
    else:
        print(f"Error: '{target}' is not a valid file or directory.")
        sys.exit(1)

    if not files:
        print("No Python files found.")
        return

    # ruff first — cleans the base
    if not dry_run:
        run_ruff(target)

    changed = 0
    for f in files:
        if format_file(f, use_sections, dry_run):
            changed += 1

    label = "Would change" if dry_run else "Changed"
    print(f"\n{label} {changed}/{len(files)} files.")


def main():
    parser = argparse.ArgumentParser(
        description="Custom Python formatter — enforces project conventions."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="File or directory to format (default: current directory)",
    )
    parser.add_argument(
        "--sections",
        action="store_true",
        help="Inject section dividers: # ----- Imports ----- # etc.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files",
    )
    args = parser.parse_args()
    format_target(args.target, args.sections, args.dry_run)


if __name__ == "__main__":
    main()