import pytest
import sqlite3


@pytest.mark.unit
def test_add_consultation_note_persists_record(isolated_database):
    """Verify that a consultation note is inserted and persisted."""

    database = isolated_database

    database.add_consultation_note(
        "2026-09-23",
        "Routine consultation notes",
    )

    records = database.get_all_consultation_notes()

    assert len(records) == 1

    record = records[0]

    assert record["log_date"] == "2026-09-23"
    assert record["notes"] == "Routine consultation notes"
    assert record["id"] > 0

@pytest.mark.unit
def test_get_consultation_notes_for_date_returns_only_matching_date(
    isolated_database,
):
    """Verify that notes are filtered by log date."""

    database = isolated_database

    database.add_consultation_note(
        "2026-09-23",
        "Note for September 23",
    )

    database.add_consultation_note(
        "2026-09-24",
        "Note for September 24",
    )

    database.add_consultation_note(
        "2026-09-23",
        "Second note for September 23",
    )

    records = database.get_consultation_notes_for_date("2026-09-23")

    assert len(records) == 2

    assert records[0]["log_date"] == "2026-09-23"
    assert records[0]["notes"] == "Note for September 23"

    assert records[1]["log_date"] == "2026-09-23"
    assert records[1]["notes"] == "Second note for September 23"

@pytest.mark.unit
def test_get_consultation_notes_for_date_returns_empty_list_when_no_match(
    isolated_database,
):
    """Verify that a date with no notes returns an empty list."""

    database = isolated_database

    database.add_consultation_note(
        "2026-09-23",
        "Existing note",
    )

    records = database.get_consultation_notes_for_date("2026-09-24")

    assert records == []

@pytest.mark.unit
def test_delete_consultation_note_removes_record(isolated_database):
    """Verify that deleting a consultation note removes it."""

    database = isolated_database

    database.add_consultation_note(
        "2026-09-23",
        "Note to be deleted",
    )

    records = database.get_all_consultation_notes()

    assert len(records) == 1

    note_id = records[0]["id"]

    database.delete_consultation_note(note_id)

    records_after_delete = database.get_all_consultation_notes()

    assert records_after_delete == []

@pytest.mark.unit
def test_get_all_consultation_notes_orders_by_date_then_id(
    isolated_database,
):
    """Verify that all consultation notes are ordered by date and ID."""

    database = isolated_database

    database.add_consultation_note(
        "2026-09-25",
        "September 25 note",
    )

    database.add_consultation_note(
        "2026-09-23",
        "September 23 first note",
    )

    database.add_consultation_note(
        "2026-09-24",
        "September 24 note",
    )

    database.add_consultation_note(
        "2026-09-23",
        "September 23 second note",
    )

    records = database.get_all_consultation_notes()

    assert len(records) == 4

    assert [record["log_date"] for record in records] == [
        "2026-09-23",
        "2026-09-23",
        "2026-09-24",
        "2026-09-25",
    ]

    assert [record["notes"] for record in records] == [
        "September 23 first note",
        "September 23 second note",
        "September 24 note",
        "September 25 note",
    ]

@pytest.mark.unit
def test_add_consultation_note_allows_empty_string_notes(isolated_database):
    """Verify the current behavior for an empty notes string."""

    database = isolated_database

    database.add_consultation_note(
        "2026-09-23",
        "",
    )

    records = database.get_all_consultation_notes()

    assert len(records) == 1
    assert records[0]["log_date"] == "2026-09-23"
    assert records[0]["notes"] == ""

@pytest.mark.unit
def test_add_consultation_note_rejects_null_notes(isolated_database):
    """Verify that NULL notes violate the database NOT NULL constraint."""

    database = isolated_database

    with pytest.raises(sqlite3.IntegrityError):
        database.add_consultation_note(
            "2026-09-23",
            None,
        )

@pytest.mark.unit
def test_multiple_notes_for_same_date_are_all_returned(isolated_database):
    """Verify that multiple notes for the same date are all returned."""

    database = isolated_database

    database.add_consultation_note("2026-09-23", "First note")
    database.add_consultation_note("2026-09-23", "Second note")
    database.add_consultation_note("2026-09-23", "Third note")

    records = database.get_consultation_notes_for_date("2026-09-23")

    assert len(records) == 3
    assert [record["notes"] for record in records] == [
        "First note",
        "Second note",
        "Third note",
    ]


@pytest.mark.unit
def test_same_date_notes_are_ordered_by_id(isolated_database):
    """Verify that same-date notes follow insertion/id order."""

    database = isolated_database

    database.add_consultation_note("2026-09-23", "First")
    database.add_consultation_note("2026-09-23", "Second")
    database.add_consultation_note("2026-09-23", "Third")

    records = database.get_consultation_notes_for_date("2026-09-23")

    ids = [record["id"] for record in records]

    assert ids == sorted(ids)


@pytest.mark.unit
def test_delete_one_of_multiple_notes_preserves_other_notes(
    isolated_database,
):
    """Verify that deleting one note does not delete other notes."""

    database = isolated_database

    database.add_consultation_note("2026-09-23", "Keep this")
    database.add_consultation_note("2026-09-23", "Delete this")
    database.add_consultation_note("2026-09-23", "Keep this too")

    records = database.get_all_consultation_notes()

    delete_id = records[1]["id"]

    database.delete_consultation_note(delete_id)

    remaining = database.get_all_consultation_notes()

    assert len(remaining) == 2
    assert [record["notes"] for record in remaining] == [
        "Keep this",
        "Keep this too",
    ]


@pytest.mark.unit
def test_delete_nonexistent_consultation_note_is_harmless(
    isolated_database,
):
    """Verify that deleting a nonexistent ID does not raise an error."""

    database = isolated_database

    database.delete_consultation_note(999999)

    assert database.get_all_consultation_notes() == []


@pytest.mark.unit
def test_delete_same_consultation_note_twice_is_harmless(
    isolated_database,
):
    """Verify that deleting the same note twice does not raise."""

    database = isolated_database

    database.add_consultation_note("2026-09-23", "Test note")

    records = database.get_all_consultation_notes()
    note_id = records[0]["id"]

    database.delete_consultation_note(note_id)
    database.delete_consultation_note(note_id)

    assert database.get_all_consultation_notes() == []


@pytest.mark.unit
def test_empty_string_log_date_is_stored(isolated_database):
    """Document current behavior for an empty date string."""

    database = isolated_database

    database.add_consultation_note("", "Empty date test")

    records = database.get_all_consultation_notes()

    assert len(records) == 1
    assert records[0]["log_date"] == ""
    assert records[0]["notes"] == "Empty date test"


@pytest.mark.unit
def test_none_log_date_is_rejected(isolated_database):
    """Verify that NULL log_date violates the NOT NULL constraint."""

    database = isolated_database

    with pytest.raises(sqlite3.IntegrityError):
        database.add_consultation_note(
            None,
            "Invalid date",
        )


@pytest.mark.unit
def test_very_long_notes_are_stored(isolated_database):
    """Verify that a large text value can be stored and retrieved."""

    database = isolated_database

    long_notes = "A" * 100_000

    database.add_consultation_note(
        "2026-09-23",
        long_notes,
    )

    records = database.get_all_consultation_notes()

    assert len(records) == 1
    assert records[0]["notes"] == long_notes


@pytest.mark.unit
def test_unicode_notes_are_stored(isolated_database):
    """Verify that Unicode text is preserved."""

    database = isolated_database

    unicode_notes = "மருத்துவர் ஆலோசனை — Baby ❤️ 😊"

    database.add_consultation_note(
        "2026-09-23",
        unicode_notes,
    )

    records = database.get_all_consultation_notes()

    assert len(records) == 1
    assert records[0]["notes"] == unicode_notes


@pytest.mark.unit
def test_special_characters_in_notes_are_stored_safely(
    isolated_database,
):
    """Verify that SQL-sensitive and multiline characters are preserved."""

    database = isolated_database

    notes = """Patient's note:
"Take medicine" at 10:00.
SQL-like text: '; DROP TABLE consultation_notes; --
New line."""

    database.add_consultation_note(
        "2026-09-23",
        notes,
    )

    records = database.get_all_consultation_notes()

    assert len(records) == 1
    assert records[0]["notes"] == notes

    # Confirm the table still exists.
    assert database.get_all_consultation_notes() == records


@pytest.mark.unit
def test_duplicate_consultation_notes_are_allowed(isolated_database):
    """Verify that identical notes can currently be stored multiple times."""

    database = isolated_database

    database.add_consultation_note(
        "2026-09-23",
        "Same note",
    )

    database.add_consultation_note(
        "2026-09-23",
        "Same note",
    )

    records = database.get_all_consultation_notes()

    assert len(records) == 2
    assert records[0]["notes"] == records[1]["notes"]
    assert records[0]["id"] != records[1]["id"]


@pytest.mark.unit
def test_consultation_note_commit_survives_connection_reopen(
    isolated_database,
):
    """Verify that committed data is visible after reopening SQLite."""

    database = isolated_database

    database.add_consultation_note(
        "2026-09-23",
        "Persistent note",
    )

    database_path = database.path

    database.conn.close()

    reopened = sqlite3.connect(database_path)

    try:
        rows = reopened.execute(
            """
            SELECT log_date, notes
            FROM consultation_notes
            ORDER BY id
            """
        ).fetchall()

        assert rows == [
            ("2026-09-23", "Persistent note"),
        ]
    finally:
        reopened.close()


@pytest.mark.unit
def test_consultation_note_records_have_expected_schema(
    isolated_database,
):
    """Verify the dictionary contract returned by the DB layer."""

    database = isolated_database

    database.add_consultation_note(
        "2026-09-23",
        "Schema test",
    )

    records = database.get_all_consultation_notes()

    assert len(records) == 1

    record = records[0]

    expected_columns = {
        "id",
        "log_date",
        "notes",
        "created_at",
    }

    assert set(record.keys()) == expected_columns
