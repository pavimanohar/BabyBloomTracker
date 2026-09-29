import ast
from pathlib import Path
import csv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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
    """Return application Python source files to analyze."""
    files = []

    for path in PROJECT_ROOT.rglob("*.py"):
        relative = path.relative_to(PROJECT_ROOT)

        if path.name in EXCLUDED_FILES:
            continue

        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue

        files.append(path)

    return sorted(files)


def count_branches(node):
    """Count major conditional/branch constructs."""
    count = 0

    for child in ast.walk(node):
        if isinstance(
            child,
            (
                ast.If,
                ast.IfExp,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.Try,
                ast.BoolOp,
                ast.Match,
            ),
        ):
            count += 1

    return count


def count_exceptions(node):
    """Count exception handlers."""
    return sum(
        1
        for child in ast.walk(node)
        if isinstance(child, ast.ExceptHandler)
    )


def get_arguments(node):
    """Return function argument names."""
    args = []

    for arg in node.args.posonlyargs:
        args.append(arg.arg)

    for arg in node.args.args:
        args.append(arg.arg)

    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}")

    for arg in node.args.kwonlyargs:
        args.append(arg.arg)

    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}")

    return args


def analyze_file(path):
    """Analyze one Python source file."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    relative_path = path.relative_to(PROJECT_ROOT)

    results = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            parent_class = None

            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    if any(
                        child is node
                        for child in parent.body
                    ):
                        parent_class = parent.name
                        break

            results.append(
                {
                    "file": str(relative_path),
                    "class": parent_class or "",
                    "function": node.name,
                    "line": node.lineno,
                    "arguments": get_arguments(node),
                    "branches": count_branches(node),
                    "exceptions": count_exceptions(node),
                }
            )

    return results


def main():
    all_functions = []

    for source_file in get_source_files():
        try:
            all_functions.extend(
                analyze_file(source_file)
            )
        except SyntaxError as exc:
            print(
                f"SYNTAX ERROR: {source_file}: "
                f"{exc}"
            )

    reports_dir = PROJECT_ROOT / "tests" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_path = reports_dir / "function_inventory.csv"

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "file",
                "class",
                "function",
                "line",
                "arguments",
                "branches",
                "exceptions",
            ],
        )

        writer.writeheader()

        for item in all_functions:
            row = item.copy()
            row["arguments"] = ", ".join(
                item["arguments"]
            )
            writer.writerow(row)

    print(
        f"Inventory CSV written to: {csv_path}"
    )


    print()
    print("=" * 100)
    print("BabyBloomTracker - Application Function Inventory")
    print("=" * 100)
    print()

    current_file = None

    for item in all_functions:
        if item["file"] != current_file:
            current_file = item["file"]

            print()
            print(f"FILE: {current_file}")
            print("-" * 100)

        class_name = (
            f"{item['class']}."
            if item["class"]
            else ""
        )

        args = ", ".join(item["arguments"])

        print(
            f"  Line {item['line']:4} | "
            f"{class_name}{item['function']}({args}) | "
            f"branches={item['branches']} | "
            f"exceptions={item['exceptions']}"
        )

    print()
    print("=" * 100)
    print(f"Total testable functions/methods: {len(all_functions)}")
    print("=" * 100)


if __name__ == "__main__":
    main()
