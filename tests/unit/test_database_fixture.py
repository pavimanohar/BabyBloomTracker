from pathlib import Path

import pytest


@pytest.mark.unit
def test_database_fixture_uses_isolated_database(isolated_database):
    """Verify that the database fixture uses pytest's temporary directory."""

    database = isolated_database

    database_path = Path(database.path)

    assert database_path.name == "bloom.db"
    assert database_path.exists()
    assert database_path.parent.name == "babybloom_data"


@pytest.mark.unit
def test_database_fixture_creates_expected_tables(isolated_database):
    """Verify that the isolated database initializes the application schema."""

    database = isolated_database

    rows = database.conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    tables = {row[0] for row in rows}

    expected_tables = {
        "sugar_log",
        "medications",
        "calendar_events",
        "settings",
        "vitals_log",
        "consultation_notes",
    }

    assert expected_tables.issubset(tables)

@pytest.mark.unit
def test_database_fixture_resets_singleton(isolated_database):
    """Verify that the fixture provides a fresh Database singleton."""

    import db

    first_database = isolated_database

    first_database.add_consultation_note(
        "2026-01-01",
        "Test data",
    )

    assert len(
        first_database.get_all_consultation_notes()
    ) == 1

    # The fixture owns the singleton during this test.
    assert db.Database._instance is first_database
