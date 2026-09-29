"""Unit tests for the Database settings API.

These tests intentionally exercise the public settings behavior exposed by
db.Database.get_setting() and db.Database.set_setting().

The isolated_database fixture from tests/conftest.py provides a fresh SQLite
database for every test, so the application's real database is never touched.
"""

import sqlite3

import pytest


# ---------------------------------------------------------------------------
# A. get_setting() - missing keys
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_get_missing_setting_returns_none(isolated_database):
    assert isolated_database.get_setting("missing_key") is None


@pytest.mark.unit
def test_get_missing_setting_returns_custom_default(isolated_database):
    assert isolated_database.get_setting("missing_key", "fallback") == "fallback"


@pytest.mark.unit
def test_get_missing_setting_returns_empty_string_default(isolated_database):
    assert isolated_database.get_setting("missing_key", "") == ""


@pytest.mark.unit
def test_get_missing_setting_returns_numeric_default(isolated_database):
    assert isolated_database.get_setting("missing_key", 12345) == 12345


@pytest.mark.unit
def test_get_missing_setting_explicit_none_default(isolated_database):
    assert isolated_database.get_setting("missing_key", None) is None


# ---------------------------------------------------------------------------
# B. set_setting() + get_setting() - basic behavior
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_set_and_get_normal_setting(isolated_database):
    isolated_database.set_setting("theme", "light")

    assert isolated_database.get_setting("theme") == "light"


@pytest.mark.unit
def test_set_empty_string_value(isolated_database):
    isolated_database.set_setting("empty_value", "")

    assert isolated_database.get_setting("empty_value") == ""


@pytest.mark.unit
def test_set_none_value(isolated_database):
    isolated_database.set_setting("nullable_value", None)

    assert isolated_database.get_setting("nullable_value") is None


@pytest.mark.unit
def test_set_unicode_key_and_value(isolated_database):
    key = "மொழி_🌸"
    value = "தமிழ் — BabyBloomTracker 🌸"

    isolated_database.set_setting(key, value)

    assert isolated_database.get_setting(key) == value


@pytest.mark.unit
def test_set_sql_like_key_and_value_is_stored_as_data(isolated_database):
    key = "key'; DROP TABLE settings; --"
    value = "' OR 1=1; --"

    isolated_database.set_setting(key, value)

    assert isolated_database.get_setting(key) == value

    # Confirm the settings table still exists and the stored value is intact.
    assert isolated_database.get_setting(key) == value


@pytest.mark.unit
def test_set_very_long_key_and_value(isolated_database):
    key = "k" * 10000
    value = "v" * 100000

    isolated_database.set_setting(key, value)

    assert isolated_database.get_setting(key) == value


@pytest.mark.unit
def test_set_empty_key(isolated_database):
    isolated_database.set_setting("", "empty-key-value")

    assert isolated_database.get_setting("") == "empty-key-value"


@pytest.mark.unit
def test_set_numeric_value_observes_sqlite_storage_behavior(isolated_database):
    isolated_database.set_setting("numeric_value", 12345)

    result = isolated_database.get_setting("numeric_value")

    # The column has TEXT affinity. Verify the actual persisted result rather
    # than assuming Python's original type is preserved.
    assert result == "12345"


@pytest.mark.unit
def test_set_boolean_value_observes_sqlite_storage_behavior(isolated_database):
    isolated_database.set_setting("boolean_value", True)

    result = isolated_database.get_setting("boolean_value")

    # SQLite TEXT affinity converts the bound integer representation to text.
    assert result == "1"


# ---------------------------------------------------------------------------
# C. Updating an existing setting
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_setting_same_key_updates_existing_value(isolated_database):
    isolated_database.set_setting("theme", "light")
    isolated_database.set_setting("theme", "dark")

    assert isolated_database.get_setting("theme") == "dark"


@pytest.mark.unit
def test_update_existing_setting_to_empty_string(isolated_database):
    isolated_database.set_setting("theme", "light")
    isolated_database.set_setting("theme", "")

    assert isolated_database.get_setting("theme") == ""


@pytest.mark.unit
def test_update_existing_setting_to_none(isolated_database):
    isolated_database.set_setting("theme", "light")
    isolated_database.set_setting("theme", None)

    assert isolated_database.get_setting("theme") is None


@pytest.mark.unit
def test_update_existing_setting_to_unicode(isolated_database):
    isolated_database.set_setting("language", "English")
    isolated_database.set_setting("language", "தமிழ் 🌸")

    assert isolated_database.get_setting("language") == "தமிழ் 🌸"


@pytest.mark.unit
def test_update_existing_setting_to_sql_like_text(isolated_database):
    isolated_database.set_setting("query_value", "normal")
    malicious_text = "'; DROP TABLE settings; --"

    isolated_database.set_setting("query_value", malicious_text)

    assert isolated_database.get_setting("query_value") == malicious_text


@pytest.mark.unit
def test_repeated_updates_keep_single_row(isolated_database):
    for value in ["one", "two", "three", "four", "five"]:
        isolated_database.set_setting("repeat", value)

    assert isolated_database.get_setting("repeat") == "five"

    row = isolated_database.conn.execute(
        "SELECT COUNT(*) FROM settings WHERE key = ?",
        ("repeat",),
    ).fetchone()

    assert row[0] == 1


# ---------------------------------------------------------------------------
# D. Key isolation / matching
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_different_keys_are_independent(isolated_database):
    isolated_database.set_setting("theme", "dark")
    isolated_database.set_setting("language", "English")

    assert isolated_database.get_setting("theme") == "dark"
    assert isolated_database.get_setting("language") == "English"


@pytest.mark.unit
def test_similar_keys_do_not_collide(isolated_database):
    isolated_database.set_setting("theme", "dark")
    isolated_database.set_setting("theme_mode", "system")

    assert isolated_database.get_setting("theme") == "dark"
    assert isolated_database.get_setting("theme_mode") == "system"


@pytest.mark.unit
def test_case_distinct_keys_are_independently_retrievable(isolated_database):
    isolated_database.set_setting("Theme", "uppercase")
    isolated_database.set_setting("theme", "lowercase")

    assert isolated_database.get_setting("Theme") == "uppercase"
    assert isolated_database.get_setting("theme") == "lowercase"


@pytest.mark.unit
def test_existing_null_value_does_not_use_default(isolated_database):
    isolated_database.set_setting("nullable_setting", None)

    assert isolated_database.get_setting("nullable_setting", "fallback") is None


# ---------------------------------------------------------------------------
# E. Persistence
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_setting_persists_after_database_reopen(
    isolated_test_environment,
    monkeypatch,
):
    import db

    database_path = isolated_test_environment["data_dir"] / "bloom.db"

    def test_db_path():
        return str(database_path)

    monkeypatch.setattr(db, "get_db_path", test_db_path)

    db.Database._instance = None
    first_database = db.Database.instance()

    try:
        first_database.set_setting("persistent_key", "persistent_value")
        assert first_database.get_setting("persistent_key") == "persistent_value"

        first_database.conn.close()
        db.Database._instance = None

        second_database = db.Database.instance()

        assert second_database.get_setting("persistent_key") == "persistent_value"
    finally:
        try:
            second_database.conn.close()
        except (NameError, AttributeError, sqlite3.ProgrammingError):
            pass

        db.Database._instance = None
