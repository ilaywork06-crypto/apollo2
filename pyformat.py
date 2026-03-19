"""
pyformat.py — Custom Python formatter using libcst.

Conventions applied:
  1. ruff format + ruff check --fix runs first
  2. Reorders module to: Imports → Constants → Classes → Functions → Other
  3. Function/call parameters: one per line if count >= 3
  4. 2 blank lines before class/function (top-level)
  5. 1 blank line after import block
  6. Section headers: # ----- Imports ----- # etc.

Usage:
  python pyformat.py .          # format recursively
  python pyformat.py src/       # specific directory
  python pyformat.py file.py    # single file
  python pyformat.py . --dry-run
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
    """Expand params/args to one-per-line when count >= 3."""

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
        if total < 3:
            return updated_node

        indent = "    "
        newline_indent = cst.ParenthesizedWhitespace(
            first_line=cst.TrailingWhitespace(newline=cst.Newline()),
            indent=True,
            last_line=cst.SimpleWhitespace(indent),
        )

        def with_comma(param):
            return param.with_changes(comma=cst.Comma(whitespace_after=newline_indent))

        new_params = [with_comma(p) for p in params.params]
        new_star_arg = params.star_arg
        if isinstance(params.star_arg, cst.Param):
            new_star_arg = with_comma(params.star_arg)
        new_kwonly = [with_comma(p) for p in params.kwonly_params]
        new_star_kwarg = params.star_kwarg
        if params.star_kwarg:
            new_star_kwarg = with_comma(params.star_kwarg)
        elif new_kwonly:
            new_kwonly[-1] = with_comma(new_kwonly[-1])
        elif new_params:
            new_params[-1] = with_comma(new_params[-1])

        return updated_node.with_changes(
            params=params.with_changes(
                params=new_params,
                star_arg=new_star_arg,
                kwonly_params=new_kwonly,
                star_kwarg=new_star_kwarg,
            ),
            whitespace_before_params=cst.ParenthesizedWhitespace(
                first_line=cst.TrailingWhitespace(newline=cst.Newline()),
                indent=True,
                last_line=cst.SimpleWhitespace(indent),
            ),
        )

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.Call:
        args = updated_node.args
        if len(args) < 3:
            return updated_node

        # skip already multi-line calls
        for arg in args:
            if isinstance(arg.comma, cst.Comma) and isinstance(
                arg.comma.whitespace_after, cst.ParenthesizedWhitespace
            ):
                return updated_node

        indent = "    "
        newline_indent = cst.ParenthesizedWhitespace(
            first_line=cst.TrailingWhitespace(newline=cst.Newline()),
            indent=True,
            last_line=cst.SimpleWhitespace(indent),
        )
        closing_newline = cst.ParenthesizedWhitespace(
            first_line=cst.TrailingWhitespace(newline=cst.Newline()),
            indent=True,
            last_line=cst.SimpleWhitespace(indent),
        )

        new_args = []
        for i, arg in enumerate(args):
            is_last = i == len(args) - 1
            new_args.append(
                arg.with_changes(
                    comma=cst.Comma(
                        whitespace_after=closing_newline if is_last else newline_indent
                    )
                )
            )

        return updated_node.with_changes(
            args=new_args,
            whitespace_before_args=cst.ParenthesizedWhitespace(
                first_line=cst.TrailingWhitespace(newline=cst.Newline()),
                indent=True,
                last_line=cst.SimpleWhitespace(indent),
            ),
        )


class BlankLineFormatter(cst.CSTTransformer):
    """1 blank line after imports, 2 blank lines before top-level class/func."""

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        new_body = list(updated_node.body)
        result = []
        import_block_ended = False
        last_was_import = False
        has_imports = any(
            isinstance(s, cst.SimpleStatementLine)
            and any(isinstance(x, (cst.Import, cst.ImportFrom)) for x in s.body)
            for s in new_body
        )

        for i, stmt in enumerate(new_body):
            is_import = isinstance(stmt, cst.SimpleStatementLine) and any(
                isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body
            )
            is_class_or_func = isinstance(stmt, (cst.ClassDef, cst.FunctionDef))

            if last_was_import and not is_import and not import_block_ended:
                import_block_ended = True
                stmt = self._set_leading_lines(stmt, 1)
            elif is_class_or_func and i > 0:
                if not has_imports or (import_block_ended and not last_was_import):
                    stmt = self._set_leading_lines(stmt, 2)

            result.append(stmt)
            last_was_import = is_import

        return updated_node.with_changes(body=result)

    def _set_leading_lines(self, stmt, count: int):
        try:
            return stmt.with_changes(
                leading_lines=[cst.EmptyLine() for _ in range(count)]
            )
        except Exception:
            return stmt


# ----- Functions ----- #

_SECTION_RE = re.compile(
    r"^[ \t]*#[ \t]*(?:-----[^\n]*-----|[─\-]{3,}[^\n]*[─\-]{3,})[ \t]*(?:#[ \t]*)?\n",
    re.MULTILINE,
)
_CONST_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*\s*(?::[^=]+)?\s*=\s*(.+)")
_PRIMITIVE_RE = re.compile(
    r"""^(?:
    -?\d[\d_]*(?:\.\d+)?
    |"[^"]*"
    |'[^']*'
    |True|False|None
    |\(.*\)
    |\[.*\]
    |\{[^(]*\}
    |r"[^"]*"|r'[^']*'
    |f"[^"]*"|f'[^']*'
)\s*$""",
    re.VERBOSE,
)


def _section(title: str) -> str:
    return f"# ----- {title} ----- #"


def strip_existing_sections(source: str) -> str:
    return _SECTION_RE.sub("", source)


def _is_const_line(line: str) -> bool:
    """
    A constant is any top-level ALL_CAPS assignment — regardless of value.
    ALL_CAPS = os.getenv(...) is still a constant by convention.
    Rejects indented lines (inside functions/classes).
    """
    line = line.rstrip()
    if not line or line != line.lstrip():
        return False
    # ALL_CAPS: type = ... (annotated)
    if re.match(r"^[A-Z][A-Z0-9_]*[ 	]*:[^=]+=", line):
        return True
    # ALL_CAPS = anything
    if re.match(r"^[A-Z][A-Z0-9_]*[ 	]*=", line):
        return True
    return False



class ImportExtractor(cst.CSTTransformer):
    """
    Extracts import statements from inside functions/classes
    and collects them for hoisting to module level.
    """

    def __init__(self):
        self.extracted_imports = []
        self._depth = 0

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self._depth += 1
        return True

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        self._depth -= 1
        return updated_node

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self._depth += 1
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        self._depth -= 1
        return updated_node

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.SimpleStatementLine | cst.RemovalSentinel:
        if self._depth > 0 and any(
            isinstance(s, (cst.Import, cst.ImportFrom)) for s in updated_node.body
        ):
            # collect the import (strip indentation for module level)
            self.extracted_imports.append(
                updated_node.with_changes(leading_lines=[])
            )
            return cst.RemovalSentinel.REMOVE
        return updated_node


def reorder_module(source: str) -> str:
    """
    Physically reorder top-level statements into:
      Imports → Constants → Classes → Functions → Other

    Also hoists any imports found inside functions/classes to module level.
    Docstring (if present) always stays first.
    """
    try:
        tree = parse_module(source)
    except cst.ParserSyntaxError:
        return source

    # Step 1: extract imports from inside functions/classes
    extractor = ImportExtractor()
    tree = tree.visit(extractor)
    hoisted_imports = extractor.extracted_imports

    body = list(tree.body)

    imports = []
    constants = []
    classes = []
    functions = []
    other = []
    docstring = None

    # Check for module docstring (first statement is a string expression)
    start = 0
    if body and isinstance(body[0], cst.SimpleStatementLine):
        stmts = body[0].body
        if len(stmts) == 1 and isinstance(stmts[0], cst.Expr):
            val = stmts[0].value
            if isinstance(val, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                docstring = body[0]
                start = 1

    # Add hoisted imports first
    imports.extend(hoisted_imports)

    for stmt in body[start:]:
        # Imports
        if isinstance(stmt, cst.SimpleStatementLine) and any(
            isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body
        ):
            imports.append(stmt)

        # Constants — regular assignments AND annotated assignments (e.g. STORE: dict = {})
        elif isinstance(stmt, cst.SimpleStatementLine) and any(
            isinstance(s, (cst.Assign, cst.AnnAssign)) for s in stmt.body
        ):
            line_src = tree.code_for_node(stmt)
            if _is_const_line(line_src):
                constants.append(stmt)
            else:
                other.append(stmt)

        # Classes
        elif isinstance(stmt, cst.ClassDef):
            classes.append(stmt)

        # Functions
        elif isinstance(stmt, cst.FunctionDef):
            functions.append(stmt)

        # Everything else (if __name__, APP.add_middleware, etc.)
        else:
            other.append(stmt)

    def clean_leading(stmt):
        """Remove leading blank lines — BlankLineFormatter will re-add them."""
        try:
            return stmt.with_changes(leading_lines=[])
        except Exception:
            return stmt

    new_body = []

    if docstring:
        new_body.append(docstring)

    for stmt in imports:
        new_body.append(clean_leading(stmt))

    for stmt in constants:
        new_body.append(clean_leading(stmt))

    # "other" = top-level code that's not import/const/class/func
    # e.g. app = FastAPI(), app.add_middleware(...), logger = ...
    # placed AFTER constants, BEFORE classes and functions
    for stmt in other:
        new_body.append(clean_leading(stmt))

    for stmt in classes:
        new_body.append(clean_leading(stmt))

    for stmt in functions:
        new_body.append(clean_leading(stmt))

    new_tree = tree.with_changes(body=new_body)
    return new_tree.code


def _inject_header(result: list, header: str, line: str) -> None:
    """
    - 2 blank lines before header if last content is indented (end of class/func body)
    - 1 blank line before header otherwise
    - 2 blank lines after header (before class/def)
    """
    while result and result[-1].strip() == "":
        result.pop()

    last_content = next((r for r in reversed(result) if r.strip()), "")
    if last_content.startswith((" ", "\t")):
        result.append("\n")
        result.append("\n")
    else:
        result.append("\n")

    result.append(header + "\n")
    result.append("\n")
    result.append("\n")
    result.append(line)


def _inject_header_after_imports(result: list, header: str, line: str) -> None:
    """1 blank line before header (used right after import block), 2 blank lines after."""
    while result and result[-1].strip() == "":
        result.pop()
    result.append("\n")
    result.append(header + "\n")
    result.append("\n")
    result.append("\n")
    result.append(line)


def _find_section_indices(source: str) -> dict:
    """Use libcst to find accurate top-level line indices."""
    try:
        tree = parse_module(source)
    except cst.ParserSyntaxError:
        return {}

    wrapper = cst.metadata.MetadataWrapper(tree)
    positions = wrapper.resolve(cst.metadata.PositionProvider)
    lines = source.splitlines(keepends=True)

    result = {
        "first_import": None,
        "last_import": None,
        "first_const": None,
        "first_class": None,
        "first_func": None,
        "first_other": None,
    }

    for stmt in wrapper.module.body:
        pos = positions[stmt]
        start_line = pos.start.line - 1

        if isinstance(stmt, cst.SimpleStatementLine) and any(
            isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body
        ):
            if result["first_import"] is None:
                result["first_import"] = start_line
            result["last_import"] = start_line

        if isinstance(stmt, cst.SimpleStatementLine) and any(
            isinstance(s, cst.Assign) for s in stmt.body
        ):
            if _is_const_line(lines[start_line]) and result["first_const"] is None:
                result["first_const"] = start_line

        if isinstance(stmt, cst.ClassDef) and result["first_class"] is None:
            result["first_class"] = (
                positions[stmt.decorators[0]].start.line - 1
                if stmt.decorators
                else start_line
            )

        if isinstance(stmt, cst.FunctionDef) and result["first_func"] is None:
            result["first_func"] = (
                positions[stmt.decorators[0]].start.line - 1
                if stmt.decorators
                else start_line
            )

        # Other: not import, not const, not class, not func
        is_import = isinstance(stmt, cst.SimpleStatementLine) and any(
            isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body
        )
        is_const = isinstance(stmt, cst.SimpleStatementLine) and any(
            isinstance(s, cst.Assign) for s in stmt.body
        ) and _is_const_line(lines[start_line])
        is_class = isinstance(stmt, cst.ClassDef)
        is_func = isinstance(stmt, cst.FunctionDef)

        if not any([is_import, is_const, is_class, is_func]):
            if result["first_other"] is None:
                result["first_other"] = start_line

    return result


def add_section_comments(source: str) -> str:
    """Inject section dividers. Idempotent."""
    source = strip_existing_sections(source)
    indices = _find_section_indices(source)

    first_import_idx = indices.get("first_import")
    last_import_idx = indices.get("last_import")
    first_const_idx = indices.get("first_const")
    first_class_idx = indices.get("first_class")
    first_func_idx = indices.get("first_func")
    first_other_idx = indices.get("first_other")

    lines = source.splitlines(keepends=True)
    result = []
    consts_header_added = False
    classes_header_added = False
    functions_header_added = False
    other_header_added = False

    for idx, line in enumerate(lines):
        if idx == first_import_idx:
            while result and result[-1].strip() == "":
                result.pop()
            result.append(_section("Imports") + "\n")
            result.append("\n")

        if last_import_idx is not None and idx == last_import_idx + 1:
            while result and result[-1].strip() == "":
                result.pop()
            result.append("\n")

        if idx == first_const_idx and not consts_header_added:
            while result and result[-1].strip() == "":
                result.pop()
            result.append("\n")
            result.append(_section("Consts") + "\n")
            result.append("\n")
            result.append(line)
            consts_header_added = True
            continue

        if idx == first_class_idx and not classes_header_added:
            _inject_header(result, _section("Classes"), line)
            classes_header_added = True
            continue

        if idx == first_func_idx and not functions_header_added:
            _inject_header(result, _section("Functions"), line)
            functions_header_added = True
            continue

        if idx == first_other_idx and not other_header_added:
            while result and result[-1].strip() == "":
                result.pop()
            result.append("\n")
            result.append(_section("Other") + "\n")
            result.append("\n")
            result.append(line)
            other_header_added = True
            continue

        result.append(line)

    return "".join(result).lstrip("\n")


def strip_sections_from_file(path: Path) -> None:
    original = path.read_text(encoding="utf-8")
    cleaned = strip_existing_sections(original)
    if cleaned != original:
        path.write_text(cleaned, encoding="utf-8")


def run_ruff(target: str) -> None:
    try:
        subprocess.run(["ruff", "check", "--fix", target], capture_output=True)
        proc = subprocess.run(["ruff", "format", target], capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"  ⚠  ruff failed:\n{proc.stderr}")
        else:
            print("  ✓ ruff done")
    except FileNotFoundError:
        print("  ⚠  ruff not found (pip install ruff)")


def format_source(source: str) -> str:
    source = strip_existing_sections(source)

    # Step 1: reorder top-level statements (imports→consts→classes→funcs→other)
    source = reorder_module(source)

    try:
        tree = parse_module(source)
    except cst.ParserSyntaxError as e:
        raise ValueError(f"Syntax error: {e}") from e

    # Step 2: blank lines
    tree = tree.visit(BlankLineFormatter())

    # Step 3: expand params/args
    tree = tree.visit(ParameterFormatter())

    result = tree.code

    # Step 4: section headers
    result = add_section_comments(result)

    if not result.endswith("\n"):
        result += "\n"

    # Remove leading blank lines
    result = result.lstrip("\n")

    return result


def format_source_path(path: Path) -> str:
    """Read file, reorder, then return formatted source."""
    return format_source(path.read_text(encoding="utf-8"))


def format_file(path: Path, dry_run: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    try:
        formatted = format_source(original)
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


def format_target(target: str, dry_run: bool):
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

    if not dry_run:
        # Step 1: strip old headers so ruff doesn't choke
        for f in files:
            strip_sections_from_file(f)
        # Step 2: ruff cleans syntax, sorts imports within each existing block
        run_ruff(target)

    # Step 3: our formatter — reorder + blank lines + params + sections
    changed = 0
    for f in files:
        if format_file(f, dry_run):
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
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files",
    )
    args = parser.parse_args()
    format_target(args.target, args.dry_run)


if __name__ == "__main__":
    main()