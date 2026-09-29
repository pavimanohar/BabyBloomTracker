import os
from pathlib import Path

import pytest


@pytest.fixture
def sample_text():
    """Simple fixture used to verify the test framework."""
    return "BabyBloomTracker"


@pytest.fixture
def isolated_test_environment(tmp_path, monkeypatch):
    """
    Provide an isolated filesystem environment for tests.

    Tests using this fixture must never touch the user's
    real BabyBloomTracker data.
    """

    test_data_dir = tmp_path / "babybloom_data"
    test_export_dir = tmp_path / "exports"

    test_data_dir.mkdir()
    test_export_dir.mkdir()

    monkeypatch.setenv(
        "BABYBLOOM_TEST_DATA_DIR",
        str(test_data_dir),
    )

    monkeypatch.setenv(
        "BABYBLOOM_TEST_EXPORT_DIR",
        str(test_export_dir),
    )

    return {
        "root": tmp_path,
        "data_dir": test_data_dir,
        "export_dir": test_export_dir,
    }


@pytest.fixture
def isolated_database(isolated_test_environment, monkeypatch):
    """
    Create a real SQLite Database instance inside pytest's
    temporary directory.

    The production database is never touched.
    """

    import db

    database_path = isolated_test_environment["data_dir"] / "bloom.db"

    def test_db_path():
        return str(database_path)

    monkeypatch.setattr(db, "get_db_path", test_db_path)

    # Every test gets a completely fresh singleton.
    db.Database._instance = None

    database = db.Database.instance()

    try:
        yield database
    finally:
        database.conn.close()

        # Critical: prevent this test's connection from leaking
        # into the next test.
        db.Database._instance = None


@pytest.fixture
def isolated_export_directory(isolated_test_environment):
    """Return the isolated export directory."""
    return isolated_test_environment["export_dir"]
