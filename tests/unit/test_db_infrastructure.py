"""Unit tests for Database infrastructure and helper functions.

Scope:
- db.get_db_path()
- db.Database singleton and initialization
- db.Database._create_tables()
- db._rows_to_dicts()
- db.today_str()
- db.now_hhmm()

CRUD behavior for individual application domains is tested separately.
"""

import os
import re
import sqlite3
from datetime import datetime

import pytest


EXPECTED_TABLES = {
    "sugar_log",
    "medications",
    "calendar_events",
    "settings",
    "vitals_log",
    "consultation_notes",
}


# ---------------------------------------------------------------------------
# A. get_db_path()
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_db_path_without_running_app_uses_fallback(monkeypatch, tmp_path):
    import db

    monkeypatch.setattr(db, "App", None)
    monkeypatch.setattr(db.os.path, "expanduser", lambda path: str(tmp_path))

    result = db.get_db_path()

    assert result == str(tmp_path / ".babybloom" / "bloom.db")
    assert (tmp_path / ".babybloom").is_dir()


@pytest.mark.unit
def test_get_db_path_with_running_app_uses_user_data_dir(monkeypatch, tmp_path):
    import db

    class FakeAppInstance:
        user_data_dir = str(tmp_path / "app_data")

    class FakeApp:
        @staticmethod
        def get_running_app():
            return FakeAppInstance()

    monkeypatch.setattr(db, "App", FakeApp)

    result = db.get_db_path()

    assert result == str(tmp_path / "app_data" / "bloom.db")
    assert (tmp_path / "app_data").is_dir()


@pytest.mark.unit
def test_get_db_path_creates_missing_running_app_directory(monkeypatch, tmp_path):
    import db

    app_dir = tmp_path / "new_app_data"

    class FakeAppInstance:
        user_data_dir = str(app_dir)

    class FakeApp:
        @staticmethod
        def get_running_app():
            return FakeAppInstance()

    monkeypatch.setattr(db, "App", FakeApp)

    assert not app_dir.exists()

    result = db.get_db_path()

    assert app_dir.is_dir()
    assert result == str(app_dir / "bloom.db")


@pytest.mark.unit
def test_get_db_path_creates_missing_fallback_directory(monkeypatch, tmp_path):
    import db

    fallback_dir = tmp_path / ".babybloom"

    monkeypatch.setattr(db, "App", None)
    monkeypatch.setattr(db.os.path, "expanduser", lambda path: str(tmp_path))

    assert not fallback_dir.exists()

    result = db.get_db_path()

    assert fallback_dir.is_dir()
    assert result == str(fallback_dir / "bloom.db")

@pytest.mark.unit
def test_get_db_path_reuses_existing_directory(monkeypatch, tmp_path):
    import db

    fallback_dir = tmp_path / ".babybloom"
    fallback_dir.mkdir()

    monkeypatch.setattr(db, "App", None)
    monkeypatch.setattr(db.os.path, "expanduser", lambda path: str(tmp_path))

    result = db.get_db_path()

    assert result == str(fallback_dir / "bloom.db")
    assert fallback_dir.is_dir()

@pytest.mark.unit
def test_get_db_path_always_returns_bloom_db_filename(monkeypatch, tmp_path):
    import db

    monkeypatch.setattr(db, "App", None)
    monkeypatch.setattr(db.os.path, "expanduser", lambda path: str(tmp_path / "fallback"))

    result = db.get_db_path()

    assert os.path.basename(result) == "bloom.db"


@pytest.mark.unit
def test_get_db_path_handles_app_data_path_with_spaces(monkeypatch, tmp_path):
    import db

    app_dir = tmp_path / "Baby Bloom Tracker Data"

    class FakeAppInstance:
        user_data_dir = str(app_dir)

    class FakeApp:
        @staticmethod
        def get_running_app():
            return FakeAppInstance()

    monkeypatch.setattr(db, "App", FakeApp)

    result = db.get_db_path()

    assert result == str(app_dir / "bloom.db")
    assert app_dir.is_dir()


@pytest.mark.unit
def test_get_db_path_attempts_config_directory_for_running_app(
    monkeypatch,
    tmp_path,
):
    import db

    app_dir = tmp_path / "app_data"

    class FakeAppInstance:
        user_data_dir = str(app_dir)

    class FakeApp:
        @staticmethod
        def get_running_app():
            return FakeAppInstance()

    monkeypatch.setattr(db, "App", FakeApp)

    calls = []

    real_makedirs = db.os.makedirs

    def tracking_makedirs(path, exist_ok=False):
        calls.append((path, exist_ok))
        return real_makedirs(path, exist_ok=exist_ok)

    monkeypatch.setattr(db.os, "makedirs", tracking_makedirs)

    result = db.get_db_path()

    assert result == str(app_dir / "bloom.db")
    assert any(path == os.path.expanduser("~/.config") for path, _ in calls)


@pytest.mark.unit
def test_get_db_path_swallows_oserror_from_config_directory(monkeypatch, tmp_path):
    import db

    app_dir = tmp_path / "app_data"

    class FakeAppInstance:
        user_data_dir = str(app_dir)

    class FakeApp:
        @staticmethod
        def get_running_app():
            return FakeAppInstance()

    monkeypatch.setattr(db, "App", FakeApp)

    real_makedirs = db.os.makedirs

    def failing_config_makedirs(path, exist_ok=False):
        if path == os.path.expanduser("~/.config"):
            raise OSError("simulated config creation failure")
        return real_makedirs(path, exist_ok=exist_ok)

    monkeypatch.setattr(db.os, "makedirs", failing_config_makedirs)

    result = db.get_db_path()

    assert result == str(app_dir / "bloom.db")
    assert app_dir.is_dir()


# ---------------------------------------------------------------------------
# B. Database.instance()
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_database_instance_first_call_creates_database(isolated_database):
    import db

    assert isinstance(isolated_database, db.Database)


@pytest.mark.unit
def test_database_instance_second_call_returns_same_object(isolated_database):
    import db

    second = db.Database.instance()

    assert second is isolated_database


@pytest.mark.unit
def test_database_instance_after_reset_creates_new_object(
    isolated_test_environment,
    monkeypatch,
):
    import db

    database_path = isolated_test_environment["data_dir"] / "singleton_reset.db"

    monkeypatch.setattr(db, "get_db_path", lambda: str(database_path))

    db.Database._instance = None
    first = db.Database.instance()

    try:
        first.conn.close()
        db.Database._instance = None

        second = db.Database.instance()

        assert second is not first
    finally:
        second.conn.close()
        db.Database._instance = None


@pytest.mark.unit
def test_database_instance_connection_is_usable(isolated_database):
    result = isolated_database.conn.execute("SELECT 1").fetchone()

    assert result == (1,)


@pytest.mark.unit
def test_database_singleton_reset_allows_fresh_connection(
    isolated_test_environment,
    monkeypatch,
):
    import db

    database_path = isolated_test_environment["data_dir"] / "fresh_singleton.db"
    monkeypatch.setattr(db, "get_db_path", lambda: str(database_path))

    db.Database._instance = None
    first = db.Database.instance()

    try:
        first.set_setting("test_key", "test_value")
        first.conn.close()

        db.Database._instance = None
        second = db.Database.instance()

        assert second.get_setting("test_key") == "test_value"
    finally:
        second.conn.close()
        db.Database._instance = None


# ---------------------------------------------------------------------------
# C. Database.__init__() / database initialization
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_database_initialization_creates_sqlite_file(isolated_database):
    assert os.path.isfile(isolated_database.path)


@pytest.mark.unit
def test_database_initialization_establishes_connection(isolated_database):
    assert isinstance(isolated_database.conn, sqlite3.Connection)
    assert isolated_database.conn.execute("SELECT 1").fetchone() == (1,)


@pytest.mark.unit
def test_database_initialization_enables_foreign_keys(isolated_database):
    result = isolated_database.conn.execute("PRAGMA foreign_keys").fetchone()

    assert result == (1,)


@pytest.mark.unit
def test_database_initialization_creates_all_expected_tables(isolated_database):
    rows = isolated_database.conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    actual_tables = {row[0] for row in rows}

    assert EXPECTED_TABLES.issubset(actual_tables)


@pytest.mark.unit
def test_database_initialization_preserves_existing_data(
    isolated_test_environment,
    monkeypatch,
):
    import db

    database_path = isolated_test_environment["data_dir"] / "existing.db"
    monkeypatch.setattr(db, "get_db_path", lambda: str(database_path))

    db.Database._instance = None
    first = db.Database.instance()

    try:
        first.set_setting("existing_key", "existing_value")
        first.conn.close()
        db.Database._instance = None

        second = db.Database.instance()

        assert second.get_setting("existing_key") == "existing_value"
    finally:
        second.conn.close()
        db.Database._instance = None


# ---------------------------------------------------------------------------
# D. Database._create_tables()
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_create_tables_is_idempotent(isolated_database):
    isolated_database._create_tables()

    rows = isolated_database.conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    actual_tables = {row[0] for row in rows}

    assert EXPECTED_TABLES.issubset(actual_tables)


@pytest.mark.unit
def test_create_tables_preserves_existing_records(isolated_database):
    isolated_database.set_setting("before_recreate", "value")

    isolated_database._create_tables()

    assert isolated_database.get_setting("before_recreate") == "value"


@pytest.mark.unit
def test_create_tables_keeps_expected_schemas(isolated_database):
    for table in EXPECTED_TABLES:
        columns = isolated_database.conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        assert columns, f"Expected table {table!r} to have columns"


# ---------------------------------------------------------------------------
# E. _rows_to_dicts()
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_rows_to_dicts_empty_result_returns_empty_list(isolated_database):
    import db

    cursor = isolated_database.conn.execute(
        "SELECT key, value FROM settings WHERE 1 = 0"
    )

    assert db._rows_to_dicts(cursor) == []


@pytest.mark.unit
def test_rows_to_dicts_single_row_returns_dictionary(isolated_database):
    import db

    isolated_database.set_setting("theme", "dark")

    cursor = isolated_database.conn.execute(
        "SELECT key, value FROM settings WHERE key = ?",
        ("theme",),
    )

    result = db._rows_to_dicts(cursor)

    assert result == [{"key": "theme", "value": "dark"}]


@pytest.mark.unit
def test_rows_to_dicts_multiple_rows_preserves_order(isolated_database):
    import db

    isolated_database.set_setting("first", "one")
    isolated_database.set_setting("second", "two")
    isolated_database.set_setting("third", "three")

    cursor = isolated_database.conn.execute(
        "SELECT key, value FROM settings ORDER BY rowid"
    )

    result = db._rows_to_dicts(cursor)

    assert result == [
        {"key": "first", "value": "one"},
        {"key": "second", "value": "two"},
        {"key": "third", "value": "three"},
    ]


# ---------------------------------------------------------------------------
# F. Date/time helpers
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_today_str_returns_expected_date_format():
    import db

    result = db.today_str()

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", result)
    datetime.strptime(result, "%Y-%m-%d")


@pytest.mark.unit
def test_now_hhmm_returns_expected_time_format():
    import db

    result = db.now_hhmm()

    assert re.fullmatch(r"\d{2}:\d{2}", result)
    datetime.strptime(result, "%H:%M")

@pytest.mark.unit
def test_db_import_handles_missing_kivy_app(monkeypatch):
    import builtins
    import importlib
    import sys

    original_db = sys.modules.get("db")
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "kivy.app":
            raise ImportError("simulated missing kivy.app")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    sys.modules.pop("db", None)

    try:
        fallback_db = importlib.import_module("db")
        assert fallback_db.App is None
    finally:
        if original_db is not None:
            sys.modules["db"] = original_db
        else:
            sys.modules.pop("db", None)
