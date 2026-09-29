from pathlib import Path
import re
import subprocess
import sys

ROOT = Path.cwd()

PRODUCTION_FILES = [
    "db.py",
    "main.py",
    "screens/calendar_screen.py",
    "screens/events_screen.py",
    "screens/export_screen.py",
    "screens/home_screen.py",
    "screens/medication_screen.py",
    "screens/notes_screen.py",
    "screens/sugar_screen.py",
    "screens/vitals_screen.py",
    "theme.py",
    "utils/export_utils.py",
    "utils/time_input.py",
]

TEST_FILES = [
    "tests/conftest.py",
    "tests/unit/conftest.py",
    "tests/unit/test_main.py",
    "tests/unit/test_calendar_screen.py",
    "tests/unit/test_events_screen.py",
    "tests/unit/test_export_screen.py",
    "tests/unit/test_home_screen.py",
    "tests/unit/test_medication_screen.py",
    "tests/unit/test_notes_screen.py",
    "tests/unit/test_sugar_screen.py",
    "tests/unit/test_vitals_screen.py",
    "tests/unit/test_time_input.py",
    "tests/unit/test_export_utils.py",
    "tests/unit/test_theme.py",
    "tests/unit/test_db_infrastructure.py",
]

OPTIONAL_FILES = [
    "tests/unit/test_db_consultation_notes.py",
    "tests/unit/test_db_sugar.py",
    "tests/unit/test_db_medications.py",
    "tests/unit/test_db_calendar_events.py",
    "tests/unit/test_db_vitals.py",
    "tests/unit/test_db_settings.py",
    "tests/unit/test_smoke.py",
]

OUTPUT = ROOT / "coverage_context.txt"


def read_file(path):
    path = ROOT / path
    if not path.exists():
        return f"[FILE NOT FOUND: {path}]\n"
    return path.read_text(encoding="utf-8", errors="replace")


def run_coverage():
    print("Running complete unit-test coverage...")
    result = subprocess.run(
        [
            "pytest",
            "-q",
            "tests/unit",
            "--cov=.",
            "--cov-report=term-missing",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    return result.returncode, result.stdout


def parse_missing_ranges(coverage_output):
    """
    Parse coverage lines such as:

    screens/home_screen.py 394 63 84% 438, 492, 667-672

    Returns:
        {
            "screens/home_screen.py": [(438, 438), (492, 492), ...]
        }
    """
    missing = {}

    pattern = re.compile(
        r"^(\S+\.py)\s+\d+\s+\d+\s+\d+%\s+(.+)$"
    )

    for line in coverage_output.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue

        filename = match.group(1)
        ranges = match.group(2).strip()

        if ranges in {"", "-"}:
            continue

        parsed = []

        for item in ranges.split(","):
            item = item.strip()

            if not item:
                continue

            if "-" in item:
                start, end = item.split("-", 1)
                parsed.append((int(start), int(end)))
            else:
                line_no = int(item)
                parsed.append((line_no, line_no))

        missing[filename] = parsed

    return missing


def expand_ranges(ranges, context=8):
    expanded = []

    for start, end in ranges:
        expanded.append(
            (
                max(1, start - context),
                end + context,
            )
        )

    # Merge overlapping ranges.
    expanded.sort()

    merged = []

    for start, end in expanded:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    return merged


def collect_source_context(filename, ranges):
    path = ROOT / filename

    if not path.exists():
        return f"\n[FILE NOT FOUND: {filename}]\n"

    lines = path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    output = []

    for start, end in expand_ranges(ranges, context=10):
        end = min(end, len(lines))

        output.append(
            f"\n--- {filename}: lines {start}-{end} ---\n"
        )

        for number in range(start, end + 1):
            output.append(
                f"{number:5}: {lines[number - 1]}"
            )

    return "\n".join(output)


def collect_full_file(filename):
    path = ROOT / filename

    if not path.exists():
        return f"\n[FILE NOT FOUND: {filename}]\n"

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lines = text.splitlines()

    output = [
        f"\n{'=' * 100}",
        f"FULL FILE: {filename}",
        f"LINES: {len(lines)}",
        f"{'=' * 100}",
    ]

    for number, line in enumerate(lines, 1):
        output.append(f"{number:5}: {line}")

    return "\n".join(output)


def main():
    coverage_return_code, coverage_output = run_coverage()

    missing = parse_missing_ranges(coverage_output)

    output = []

    output.append("=" * 100)
    output.append("BABYBLOOMTRACKER COVERAGE CONTEXT")
    output.append("=" * 100)
    output.append(f"Project root: {ROOT}")
    output.append("")

    output.append("=" * 100)
    output.append("CURRENT COVERAGE RUN")
    output.append("=" * 100)
    output.append(coverage_output)

    output.append("")
    output.append("=" * 100)
    output.append("PARSED UNCOVERED RANGES")
    output.append("=" * 100)

    if not missing:
        output.append("No uncovered ranges parsed.")
    else:
        for filename, ranges in missing.items():
            output.append(f"\n{filename}")
            for start, end in ranges:
                if start == end:
                    output.append(f"  {start}")
                else:
                    output.append(f"  {start}-{end}")

    output.append("")
    output.append("=" * 100)
    output.append("UNCOVERED SOURCE WITH CONTEXT")
    output.append("=" * 100)

    for filename, ranges in missing.items():
        output.append(
            collect_source_context(filename, ranges)
        )

    output.append("")
    output.append("=" * 100)
    output.append("COMPLETE PRODUCTION FILES")
    output.append("=" * 100)

    for filename in PRODUCTION_FILES:
        output.append(
            collect_full_file(filename)
        )

    output.append("")
    output.append("=" * 100)
    output.append("COMPLETE TEST FILES")
    output.append("=" * 100)

    all_test_files = TEST_FILES + OPTIONAL_FILES

    for filename in all_test_files:
        output.append(
            collect_full_file(filename)
        )

    output.append("")
    output.append("=" * 100)
    output.append("FUNCTION INVENTORY")
    output.append("=" * 100)

    inventory = ROOT / "tests/reports/function_inventory.csv"

    if inventory.exists():
        output.append(
            inventory.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    else:
        output.append(
            "[tests/reports/function_inventory.csv not found]"
        )

    output.append("")
    output.append("=" * 100)
    output.append("TEST MATRIX")
    output.append("=" * 100)

    matrix = ROOT / "tests/reports/test_matrix.csv"

    if matrix.exists():
        output.append(
            matrix.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    else:
        output.append(
            "[tests/reports/test_matrix.csv not found]"
        )

    OUTPUT.write_text(
        "\n".join(output),
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print("Collection complete")
    print("=" * 70)
    print(f"Coverage return code : {coverage_return_code}")
    print(f"Output file          : {OUTPUT}")
    print(f"Output size          : {OUTPUT.stat().st_size:,} bytes")
    print(f"Uncovered modules    : {len(missing)}")
    print()
    print("Next command:")
    print(f"  wc -l {OUTPUT}")
    print()
    print("Please send coverage_context.txt to me.")


if __name__ == "__main__":
    main()
