import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORTS_DIR = PROJECT_ROOT / "tests" / "reports"

INVENTORY_FILE = REPORTS_DIR / "function_inventory.csv"
MATRIX_FILE = REPORTS_DIR / "test_matrix.csv"


def classify_priority(row):
    """Assign initial testing priority based on complexity."""
    branches = int(row["branches"])
    exceptions = int(row["exceptions"])

    if exceptions > 0 or branches >= 15:
        return "critical"

    if branches >= 5:
        return "high"

    if branches >= 1:
        return "medium"

    return "normal"


def classify_category(row):
    """Assign broad testing categories."""
    file_name = row["file"]

    if file_name == "db.py":
        return "database"

    if file_name == "theme.py":
        return "utility"

    if file_name == "utils/export_utils.py":
        return "export"

    if file_name == "utils/time_input.py":
        return "input_validation"

    if file_name.startswith("screens/"):
        return "ui_logic"

    if file_name == "main.py":
        return "application"

    return "other"


def build_row(row):
    branches = int(row["branches"])
    exceptions = int(row["exceptions"])

    return {
        "file": row["file"],
        "class": row["class"],
        "function": row["function"],
        "line": row["line"],
        "arguments": row["arguments"],
        "branches": branches,
        "exceptions": exceptions,

        "test_category": classify_category(row),
        "priority": classify_priority(row),

        "happy_path": "yes",
        "boundary": "yes",
        "invalid_input": "yes" if row["arguments"] else "review",
        "exception_path": "yes" if exceptions > 0 else "not_applicable",
        "branch_cases": "yes" if branches > 0 else "not_applicable",

        "integration_required": "review",
        "scenario_required": "review",
        "stress_required": "review",

        "status": "planned",
    }


def main():
    if not INVENTORY_FILE.exists():
        raise FileNotFoundError(
            f"Inventory file not found: {INVENTORY_FILE}"
        )

    rows = []

    with INVENTORY_FILE.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        for row in reader:
            rows.append(build_row(row))

    fieldnames = [
        "file",
        "class",
        "function",
        "line",
        "arguments",
        "branches",
        "exceptions",
        "test_category",
        "priority",
        "happy_path",
        "boundary",
        "invalid_input",
        "exception_path",
        "branch_cases",
        "integration_required",
        "scenario_required",
        "stress_required",
        "status",
    ]

    with MATRIX_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Test matrix written to: {MATRIX_FILE}"
    )

    print(
        f"Functions included: {len(rows)}"
    )


if __name__ == "__main__":
    main()
