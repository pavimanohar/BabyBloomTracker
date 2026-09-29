import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORTS_DIR = PROJECT_ROOT / "tests" / "reports"

INVENTORY_FILE = REPORTS_DIR / "function_inventory.csv"
ANALYSIS_FILE = REPORTS_DIR / "source_analysis.csv"
OUTPUT_FILE = REPORTS_DIR / "test_requirements.csv"


def yes_no(condition):
    return "yes" if condition else "no"


def requirement_for(row):
    branches = int(row["branches"])
    exceptions = int(row["exceptions"])
    source_lines = int(row["source_lines"])

    arguments = row["arguments"].strip()
    calls = row["calls"].lower()
    control = row["control_features"].lower()
    io_features = row["io_features"].lower()
    handled_exceptions = row["handled_exceptions"].strip()
    file_name = row["file"]
    function = row["function"]

    requirements = {
        "happy_path": "yes",
        "boundary_values": "yes",
        "invalid_inputs": "yes" if arguments else "review",
        "branch_testing": yes_no(branches > 0),
        "exception_testing": yes_no(exceptions > 0),
        "return_value_testing": "yes",
        "state_change_testing": "review",
        "dependency_mocking": "no",
        "database_testing": "no",
        "filesystem_testing": "no",
        "ui_testing": "no",
        "integration_testing": "no",
        "scenario_testing": "no",
        "stress_testing": "no",
        "randomized_testing": "no",
        "priority": "normal",
        "notes": "",
    }

    # ---------------------------------------------------------
    # Priority
    # ---------------------------------------------------------

    if exceptions > 0 or branches >= 15:
        requirements["priority"] = "critical"

    elif branches >= 5:
        requirements["priority"] = "high"

    elif branches >= 1:
        requirements["priority"] = "medium"

    # ---------------------------------------------------------
    # Branches
    # ---------------------------------------------------------

    if branches > 0:
        requirements["notes"] += (
            "Every branch requires positive and negative coverage. "
        )

    # ---------------------------------------------------------
    # Exceptions
    # ---------------------------------------------------------

    if exceptions > 0:
        requirements["exception_testing"] = "yes"
        requirements["dependency_mocking"] = "yes"

        requirements["notes"] += (
            "Explicit exception path must be tested. "
        )

        if handled_exceptions:
            requirements["notes"] += (
                f"Handled exceptions: {handled_exceptions}. "
            )

    # ---------------------------------------------------------
    # Database
    # ---------------------------------------------------------

    if file_name == "db.py":
        requirements["database_testing"] = "yes"
        requirements["integration_testing"] = "yes"
        requirements["state_change_testing"] = "yes"

        requirements["notes"] += (
            "Validate persisted database state independently. "
        )

    elif "database" in io_features:
        requirements["database_testing"] = "yes"
        requirements["dependency_mocking"] = "yes"

    # ---------------------------------------------------------
    # Filesystem
    # ---------------------------------------------------------

    if "filesystem" in io_features:
        requirements["filesystem_testing"] = "yes"
        requirements["dependency_mocking"] = "yes"

        requirements["notes"] += (
            "Test filesystem success and failure paths. "
        )

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    if file_name.startswith("screens/"):
        requirements["ui_testing"] = "yes"
        requirements["integration_testing"] = "yes"

        requirements["notes"] += (
            "UI-dependent behavior should be tested separately "
            "from pure business logic. "
        )

    # ---------------------------------------------------------
    # Calls / external dependencies
    # ---------------------------------------------------------

    external_call_keywords = (
        "get_running_app",
        "popup",
        "dialog",
        "toast",
        "share",
        "open",
        "calendar",
        "filechooser",
    )

    if any(
        keyword in calls
        for keyword in external_call_keywords
    ):
        requirements["dependency_mocking"] = "yes"

    # ---------------------------------------------------------
    # Control flow
    # ---------------------------------------------------------

    if "for" in control or "while" in control:
        requirements["boundary_values"] = "yes"
        requirements["randomized_testing"] = "yes"

        requirements["notes"] += (
            "Loop boundaries and empty/non-empty collections "
            "should be tested. "
        )

    if "try" in control:
        requirements["exception_testing"] = "yes"

    # ---------------------------------------------------------
    # Export functionality
    # ---------------------------------------------------------

    if (
        file_name == "utils/export_utils.py"
        or file_name == "utils/export_screen.py"
        or file_name == "screens/export_screen.py"
    ):
        requirements["integration_testing"] = "yes"
        requirements["scenario_testing"] = "yes"
        requirements["stress_testing"] = "yes"

        requirements["notes"] += (
            "Validate generated output independently "
            "and test repeated exports. "
        )

    # ---------------------------------------------------------
    # Input validation
    # ---------------------------------------------------------

    if file_name == "utils/time_input.py":
        requirements["boundary_values"] = "yes"
        requirements["invalid_inputs"] = "yes"
        requirements["randomized_testing"] = "yes"

    # ---------------------------------------------------------
    # High-complexity functions
    # ---------------------------------------------------------

    if branches >= 10:
        requirements["scenario_testing"] = "yes"
        requirements["stress_testing"] = "yes"

        requirements["notes"] += (
            "High branch complexity requires scenario coverage. "
        )

    if source_lines >= 50:
        requirements["scenario_testing"] = "yes"

    # ---------------------------------------------------------
    # Functions that modify state
    # ---------------------------------------------------------

    state_keywords = (
        "add_",
        "update_",
        "delete_",
        "set_",
        "save",
        "toggle",
        "remove",
        "clear",
    )

    if function.startswith(state_keywords):
        requirements["state_change_testing"] = "yes"

    # ---------------------------------------------------------
    # Scenario candidates
    # ---------------------------------------------------------

    if (
        requirements["database_testing"] == "yes"
        or requirements["state_change_testing"] == "yes"
    ):
        requirements["scenario_testing"] = "yes"

    # ---------------------------------------------------------
    # Stress candidates
    # ---------------------------------------------------------

    if (
        requirements["database_testing"] == "yes"
        or requirements["filesystem_testing"] == "yes"
        or branches >= 10
    ):
        requirements["stress_testing"] = "yes"

    return requirements


def main():
    if not INVENTORY_FILE.exists():
        raise FileNotFoundError(
            f"Missing inventory: {INVENTORY_FILE}"
        )

    if not ANALYSIS_FILE.exists():
        raise FileNotFoundError(
            f"Missing source analysis: {ANALYSIS_FILE}"
        )

    with INVENTORY_FILE.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as inventory_file:

        inventory_rows = list(
            csv.DictReader(inventory_file)
        )

    with ANALYSIS_FILE.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as analysis_file:

        analysis_rows = list(
            csv.DictReader(analysis_file)
        )

    analysis_map = {
        (
            row["file"],
            row["class"],
            row["function"],
            row["line"],
        ): row
        for row in analysis_rows
    }

    results = []

    for inventory_row in inventory_rows:

        key = (
            inventory_row["file"],
            inventory_row["class"],
            inventory_row["function"],
            inventory_row["line"],
        )

        analysis_row = analysis_map.get(key)

        if analysis_row is None:
            raise RuntimeError(
                "No source-analysis entry found for "
                f"{key}"
            )

        requirements = requirement_for(
            {
                **inventory_row,
                **analysis_row,
            }
        )

        results.append(
            {
                **inventory_row,
                **analysis_row,
                **requirements,
            }
        )

    fieldnames = [
        "file",
        "class",
        "function",
        "line",
        "arguments",
        "branches",
        "exceptions",
        "source_lines",
        "calls",
        "control_features",
        "io_features",
        "handled_exceptions",
        "happy_path",
        "boundary_values",
        "invalid_inputs",
        "branch_testing",
        "exception_testing",
        "return_value_testing",
        "state_change_testing",
        "dependency_mocking",
        "database_testing",
        "filesystem_testing",
        "ui_testing",
        "integration_testing",
        "scenario_testing",
        "stress_testing",
        "randomized_testing",
        "priority",
        "notes",
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output_file:

        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    field: result.get(field, "")
                    for field in fieldnames
                }
            )

    print(
        f"Test requirements written to: {OUTPUT_FILE}"
    )

    print(
        f"Functions analyzed: {len(results)}"
    )


if __name__ == "__main__":
    main()
