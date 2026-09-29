import ast
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORTS_DIR = PROJECT_ROOT / "tests" / "reports"

INVENTORY_FILE = REPORTS_DIR / "function_inventory.csv"
OUTPUT_FILE = REPORTS_DIR / "source_analysis.csv"


EXCLUDED_FILES = {
    "build_apk.py",
}

EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".buildozer",
    "build",
    "dist",
    "bin",
    "tests",
    "assets",
}


def get_source_files():
    """Return application Python source files."""
    files = []

    for path in PROJECT_ROOT.rglob("*.py"):
        relative = path.relative_to(PROJECT_ROOT)

        if path.name in EXCLUDED_FILES:
            continue

        if any(
            part in EXCLUDED_DIRS
            for part in relative.parts
        ):
            continue

        files.append(path)

    return sorted(files)


def get_function_nodes(tree):
    """Return all function and method AST nodes."""
    nodes = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            nodes.append(node)

    return nodes


def source_text(node):
    """Return normalized source code for a function."""
    lines = []

    for line in ast.get_source_segment(
        CURRENT_SOURCE,
        node
    ).splitlines():
        lines.append(line.strip())

    return " ".join(lines)


def get_call_names(node):
    """Return function/method names called inside a function."""
    calls = set()

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue

        function = child.func

        if isinstance(function, ast.Name):
            calls.add(function.id)

        elif isinstance(function, ast.Attribute):
            calls.add(function.attr)

    return sorted(calls)


def get_imported_modules(tree):
    """Return imported module names."""
    modules = set()

    for node in tree.body:

        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)

    return sorted(modules)


def get_control_features(node):
    """Identify important control-flow constructs."""
    features = set()

    for child in ast.walk(node):

        if isinstance(child, ast.If):
            features.add("if")

        elif isinstance(child, ast.For):
            features.add("for")

        elif isinstance(child, ast.While):
            features.add("while")

        elif isinstance(child, ast.Try):
            features.add("try")

        elif isinstance(child, ast.With):
            features.add("with")

        elif isinstance(child, ast.Match):
            features.add("match")

        elif isinstance(child, ast.comprehension):
            features.add("comprehension")

    return sorted(features)


def get_io_features(node):
    """Identify common I/O and external-operation patterns."""
    features = set()

    for child in ast.walk(node):

        if isinstance(child, ast.Call):

            if isinstance(child.func, ast.Name):
                name = child.func.id

            elif isinstance(child.func, ast.Attribute):
                name = child.func.attr

            else:
                continue

            name = name.lower()

            if name in {
                "open",
                "write",
                "read",
                "unlink",
                "remove",
                "exists",
                "mkdir",
                "makedirs",
            }:
                features.add("filesystem")

            if name in {
                "execute",
                "executemany",
                "fetchone",
                "fetchall",
                "commit",
                "rollback",
            }:
                features.add("database")

            if name in {
                "sleep",
                "subprocess",
                "run",
                "popen",
            }:
                features.add("system")

    return sorted(features)


def get_exception_types(node):
    """Return explicitly handled exception types."""
    exceptions = set()

    for child in ast.walk(node):

        if not isinstance(child, ast.ExceptHandler):
            continue

        if child.type is None:
            exceptions.add("Exception")

        elif isinstance(child.type, ast.Name):
            exceptions.add(child.type.id)

        elif isinstance(child.type, ast.Attribute):
            exceptions.add(child.type.attr)

        else:
            exceptions.add("unknown")

    return sorted(exceptions)


def analyze_file(path):
    global CURRENT_SOURCE

    CURRENT_SOURCE = path.read_text(
        encoding="utf-8",
        errors="strict",
    )

    tree = ast.parse(
        CURRENT_SOURCE,
        filename=str(path),
    )

    imported_modules = get_imported_modules(tree)

    results = []

    for node in get_function_nodes(tree):

        class_name = ""

        parent_candidates = [
            parent
            for parent in ast.walk(tree)
            if isinstance(parent, ast.ClassDef)
            and node in parent.body
        ]

        if parent_candidates:
            class_name = parent_candidates[0].name

        results.append(
            {
                "file": str(
                    path.relative_to(PROJECT_ROOT)
                ),
                "class": class_name,
                "function": node.name,
                "line": node.lineno,
                "arguments": ", ".join(
                    arg.arg
                    for arg in node.args.args
                ),
                "source_lines": len(
                    ast.get_source_segment(
                        CURRENT_SOURCE,
                        node
                    ).splitlines()
                ),
                "calls": ", ".join(
                    get_call_names(node)
                ),
                "control_features": ", ".join(
                    get_control_features(node)
                ),
                "io_features": ", ".join(
                    get_io_features(node)
                ),
                "handled_exceptions": ", ".join(
                    get_exception_types(node)
                ),
                "imports": ", ".join(
                    imported_modules
                ),
            }
        )

    return results


def main():
    all_results = []

    for source_file in get_source_files():

        try:
            all_results.extend(
                analyze_file(source_file)
            )

        except (
            SyntaxError,
            UnicodeDecodeError,
        ) as exc:

            print(
                f"ERROR: {source_file}: {exc}"
            )

    fieldnames = [
        "file",
        "class",
        "function",
        "line",
        "arguments",
        "source_lines",
        "calls",
        "control_features",
        "io_features",
        "handled_exceptions",
        "imports",
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(all_results)

    print(
        f"Source analysis written to: {OUTPUT_FILE}"
    )

    print(
        f"Functions analyzed: {len(all_results)}"
    )


if __name__ == "__main__":
    main()
