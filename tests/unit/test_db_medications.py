import sqlite3

import pytest


def add_medication(
    database,
    log_date="2026-09-23",
    name="Folic Acid",
    dosage="5 mg",
    scheduled_time="08:00",
    notes="Morning dose",
):
    database.add_medication(
        log_date,
        name,
        dosage,
        scheduled_time,
        notes,
    )


# ============================================================
# add_medication()
# ============================================================


@pytest.mark.unit
def test_add_medication_persists_record(isolated_database):
    add_medication(isolated_database)

    records = isolated_database.get_medications_for_date("2026-09-23")

    assert len(records) == 1
    record = records[0]

    assert record["log_date"] == "2026-09-23"
    assert record["name"] == "Folic Acid"
    assert record["dosage"] == "5 mg"
    assert record["scheduled_time"] == "08:00"
    assert record["taken"] == 0
    assert record["notes"] == "Morning dose"
    assert record["id"] > 0


@pytest.mark.unit
def test_add_medication_stores_all_supplied_fields(isolated_database):
    add_medication(
        isolated_database,
        log_date="2026-09-24",
        name="Iron",
        dosage="100 mg",
        scheduled_time="13:30",
        notes="After lunch",
    )

    record = isolated_database.get_medications_for_date("2026-09-24")[0]

    assert record["log_date"] == "2026-09-24"
    assert record["name"] == "Iron"
    assert record["dosage"] == "100 mg"
    assert record["scheduled_time"] == "13:30"
    assert record["taken"] == 0
    assert record["notes"] == "After lunch"


@pytest.mark.unit
def test_add_medication_default_notes_is_empty_string(isolated_database):
    isolated_database.add_medication(
        "2026-09-23",
        "Folic Acid",
        "5 mg",
        "08:00",
    )

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["notes"] == ""


@pytest.mark.unit
def test_add_medication_empty_notes(isolated_database):
    add_medication(isolated_database, notes="")

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["notes"] == ""


@pytest.mark.unit
def test_add_medication_none_notes(isolated_database):
    add_medication(isolated_database, notes=None)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["notes"] is None


@pytest.mark.unit
def test_add_medication_none_dosage(isolated_database):
    add_medication(isolated_database, dosage=None)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["dosage"] is None


@pytest.mark.unit
def test_add_medication_none_scheduled_time(isolated_database):
    add_medication(isolated_database, scheduled_time=None)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["scheduled_time"] is None


@pytest.mark.unit
def test_add_medication_empty_name_is_stored(isolated_database):
    add_medication(isolated_database, name="")

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["name"] == ""


@pytest.mark.unit
def test_add_medication_very_long_name(isolated_database):
    name = "Medication " + ("A" * 100_000)

    add_medication(isolated_database, name=name)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["name"] == name


@pytest.mark.unit
def test_add_medication_very_long_dosage(isolated_database):
    dosage = "Dose " + ("A" * 100_000)

    add_medication(isolated_database, dosage=dosage)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["dosage"] == dosage


@pytest.mark.unit
def test_add_medication_very_long_notes(isolated_database):
    notes = "N" * 100_000

    add_medication(isolated_database, notes=notes)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["notes"] == notes


@pytest.mark.unit
def test_add_medication_unicode_name(isolated_database):
    name = "ஃபோலிக் ஆசிட் ❤️"

    add_medication(isolated_database, name=name)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["name"] == name


@pytest.mark.unit
def test_add_medication_unicode_notes(isolated_database):
    notes = "மருத்துவர் ஆலோசனை 😊 ❤️"

    add_medication(isolated_database, notes=notes)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["notes"] == notes


@pytest.mark.unit
def test_add_medication_special_characters_are_stored_safely(
    isolated_database,
):
    name = "Medicine's \"Special\""
    dosage = "5 mg; DROP TABLE medications; --"
    notes = """Patient's note:
"Take after food"
'; DROP TABLE medications; --
Line two."""

    add_medication(
        isolated_database,
        name=name,
        dosage=dosage,
        notes=notes,
    )

    records = isolated_database.get_medications_for_date("2026-09-23")

    assert len(records) == 1
    assert records[0]["name"] == name
    assert records[0]["dosage"] == dosage
    assert records[0]["notes"] == notes

    # The table must still exist.
    assert len(isolated_database.get_medications_for_date("2026-09-23")) == 1


@pytest.mark.unit
def test_duplicate_medications_are_allowed(isolated_database):
    add_medication(isolated_database)
    add_medication(isolated_database)

    records = isolated_database.get_medications_for_date("2026-09-23")

    assert len(records) == 2
    assert records[0]["id"] != records[1]["id"]
    assert records[0]["name"] == records[1]["name"]


@pytest.mark.unit
def test_multiple_medications_same_date_are_stored(isolated_database):
    add_medication(
        isolated_database,
        name="Folic Acid",
        scheduled_time="08:00",
    )
    add_medication(
        isolated_database,
        name="Iron",
        scheduled_time="13:00",
    )
    add_medication(
        isolated_database,
        name="Calcium",
        scheduled_time="20:00",
    )

    records = isolated_database.get_medications_for_date("2026-09-23")

    assert len(records) == 3


@pytest.mark.unit
def test_add_medication_none_log_date_is_rejected(isolated_database):
    with pytest.raises(sqlite3.IntegrityError):
        add_medication(isolated_database, log_date=None)


@pytest.mark.unit
def test_add_medication_none_name_is_rejected(isolated_database):
    with pytest.raises(sqlite3.IntegrityError):
        add_medication(isolated_database, name=None)


@pytest.mark.unit
def test_add_medication_empty_dosage(isolated_database):
    add_medication(isolated_database, dosage="")

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert record["dosage"] == ""


@pytest.mark.unit
def test_add_medication_commit_survives_connection_reopen(isolated_database):
    add_medication(
        isolated_database,
        name="Persistent Medicine",
        dosage="10 mg",
        scheduled_time="09:00",
        notes="Persistent record",
    )

    database_path = isolated_database.path
    isolated_database.conn.close()

    reopened = sqlite3.connect(database_path)

    try:
        row = reopened.execute(
            """
            SELECT log_date, name, dosage, scheduled_time, taken, notes
            FROM medications
            ORDER BY id
            """
        ).fetchone()

        assert row == (
            "2026-09-23",
            "Persistent Medicine",
            "10 mg",
            "09:00",
            0,
            "Persistent record",
        )
    finally:
        reopened.close()


# ============================================================
# set_medication_taken()
# ============================================================


@pytest.mark.unit
def test_set_medication_taken_default_true_sets_one(isolated_database):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.set_medication_taken(record["id"])

    updated = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert updated["taken"] == 1


@pytest.mark.unit
def test_set_medication_taken_explicit_true_sets_one(isolated_database):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.set_medication_taken(record["id"], True)

    assert isolated_database.get_medications_for_date(
        "2026-09-23"
    )[0]["taken"] == 1


@pytest.mark.unit
def test_set_medication_taken_false_sets_zero(isolated_database):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.set_medication_taken(record["id"], False)

    assert isolated_database.get_medications_for_date(
        "2026-09-23"
    )[0]["taken"] == 0


@pytest.mark.unit
def test_set_medication_taken_none_sets_zero(isolated_database):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.set_medication_taken(record["id"], None)

    assert isolated_database.get_medications_for_date(
        "2026-09-23"
    )[0]["taken"] == 0


@pytest.mark.unit
def test_set_medication_taken_zero_sets_zero(isolated_database):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.set_medication_taken(record["id"], 0)

    assert isolated_database.get_medications_for_date(
        "2026-09-23"
    )[0]["taken"] == 0


@pytest.mark.unit
def test_set_medication_taken_nonzero_value_sets_one(isolated_database):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.set_medication_taken(record["id"], 42)

    assert isolated_database.get_medications_for_date(
        "2026-09-23"
    )[0]["taken"] == 1


@pytest.mark.unit
def test_set_medication_taken_updates_only_target_medication(
    isolated_database,
):
    add_medication(
        isolated_database,
        name="Medicine A",
    )
    add_medication(
        isolated_database,
        name="Medicine B",
    )

    records = isolated_database.get_medications_for_date("2026-09-23")

    isolated_database.set_medication_taken(
        records[0]["id"],
        True,
    )

    updated = isolated_database.get_medications_for_date("2026-09-23")

    assert updated[0]["taken"] == 1
    assert updated[1]["taken"] == 0


@pytest.mark.unit
def test_set_medication_taken_nonexistent_id_is_harmless(
    isolated_database,
):
    add_medication(isolated_database)

    isolated_database.set_medication_taken(999999, True)

    records = isolated_database.get_medications_for_date("2026-09-23")

    assert len(records) == 1
    assert records[0]["taken"] == 0


@pytest.mark.unit
def test_set_medication_taken_repeated_update_is_idempotent(
    isolated_database,
):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.set_medication_taken(record["id"], True)
    isolated_database.set_medication_taken(record["id"], True)

    assert isolated_database.get_medications_for_date(
        "2026-09-23"
    )[0]["taken"] == 1


@pytest.mark.unit
def test_set_medication_taken_persists_after_connection_reopen(
    isolated_database,
):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.set_medication_taken(record["id"], True)

    database_path = isolated_database.path
    isolated_database.conn.close()

    reopened = sqlite3.connect(database_path)

    try:
        row = reopened.execute(
            "SELECT taken FROM medications WHERE id = ?",
            (record["id"],),
        ).fetchone()

        assert row == (1,)
    finally:
        reopened.close()


@pytest.mark.unit
def test_set_medication_taken_does_not_modify_other_fields(
    isolated_database,
):
    add_medication(
        isolated_database,
        log_date="2026-09-23",
        name="Folic Acid",
        dosage="5 mg",
        scheduled_time="08:00",
        notes="Morning",
    )

    before = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.set_medication_taken(
        before["id"],
        True,
    )

    after = isolated_database.get_medications_for_date("2026-09-23")[0]

    assert after["log_date"] == before["log_date"]
    assert after["name"] == before["name"]
    assert after["dosage"] == before["dosage"]
    assert after["scheduled_time"] == before["scheduled_time"]
    assert after["notes"] == before["notes"]
    assert after["taken"] == 1


@pytest.mark.unit
def test_multiple_medications_have_independent_taken_status(
    isolated_database,
):
    add_medication(
        isolated_database,
        name="Medicine A",
    )
    add_medication(
        isolated_database,
        name="Medicine B",
    )
    add_medication(
        isolated_database,
        name="Medicine C",
    )

    records = isolated_database.get_medications_for_date("2026-09-23")

    isolated_database.set_medication_taken(records[0]["id"], True)
    isolated_database.set_medication_taken(records[2]["id"], True)

    updated = isolated_database.get_medications_for_date("2026-09-23")

    assert [record["taken"] for record in updated] == [1, 0, 1]


# ============================================================
# delete_medication()
# ============================================================


@pytest.mark.unit
def test_delete_medication_removes_existing_record(isolated_database):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.delete_medication(record["id"])

    assert isolated_database.get_medications_for_date("2026-09-23") == []


@pytest.mark.unit
def test_delete_medication_preserves_other_records(isolated_database):
    add_medication(isolated_database, name="Keep")
    add_medication(isolated_database, name="Delete")
    add_medication(isolated_database, name="Keep Too")

    records = isolated_database.get_medications_for_date("2026-09-23")

    delete_id = records[1]["id"]

    isolated_database.delete_medication(delete_id)

    remaining = isolated_database.get_medications_for_date("2026-09-23")

    assert len(remaining) == 2
    assert [record["name"] for record in remaining] == [
        "Keep",
        "Keep Too",
    ]


@pytest.mark.unit
def test_delete_medication_nonexistent_id_is_harmless(
    isolated_database,
):
    add_medication(isolated_database)

    isolated_database.delete_medication(999999)

    assert len(
        isolated_database.get_medications_for_date("2026-09-23")
    ) == 1


@pytest.mark.unit
def test_delete_medication_same_id_twice_is_harmless(
    isolated_database,
):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.delete_medication(record["id"])
    isolated_database.delete_medication(record["id"])

    assert isolated_database.get_medications_for_date("2026-09-23") == []


@pytest.mark.unit
def test_delete_medication_removes_record_from_date_query(
    isolated_database,
):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.delete_medication(record["id"])

    assert isolated_database.get_medications_for_date("2026-09-23") == []


@pytest.mark.unit
def test_delete_medication_does_not_affect_other_dates(
    isolated_database,
):
    add_medication(
        isolated_database,
        log_date="2026-09-23",
        name="Delete",
    )
    add_medication(
        isolated_database,
        log_date="2026-09-24",
        name="Keep",
    )

    first_date_records = isolated_database.get_medications_for_date(
        "2026-09-23"
    )

    isolated_database.delete_medication(first_date_records[0]["id"])

    remaining = isolated_database.get_medications_for_date("2026-09-24")

    assert len(remaining) == 1
    assert remaining[0]["name"] == "Keep"


@pytest.mark.unit
def test_delete_medication_commits_change(isolated_database):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    database_path = isolated_database.path

    isolated_database.delete_medication(record["id"])
    isolated_database.conn.close()

    reopened = sqlite3.connect(database_path)

    try:
        row = reopened.execute(
            "SELECT id FROM medications WHERE id = ?",
            (record["id"],),
        ).fetchone()

        assert row is None
    finally:
        reopened.close()


# ============================================================
# get_medications_for_date()
# ============================================================


@pytest.mark.unit
def test_get_medications_for_date_returns_matching_records(
    isolated_database,
):
    add_medication(isolated_database)

    records = isolated_database.get_medications_for_date("2026-09-23")

    assert len(records) == 1
    assert records[0]["log_date"] == "2026-09-23"


@pytest.mark.unit
def test_get_medications_for_date_returns_empty_for_no_match(
    isolated_database,
):
    add_medication(isolated_database)

    assert isolated_database.get_medications_for_date(
        "2026-09-24"
    ) == []


@pytest.mark.unit
def test_get_medications_for_date_returns_only_requested_date(
    isolated_database,
):
    add_medication(
        isolated_database,
        log_date="2026-09-23",
        name="Medicine 23",
    )
    add_medication(
        isolated_database,
        log_date="2026-09-24",
        name="Medicine 24",
    )
    add_medication(
        isolated_database,
        log_date="2026-09-25",
        name="Medicine 25",
    )

    records = isolated_database.get_medications_for_date("2026-09-24")

    assert len(records) == 1
    assert records[0]["name"] == "Medicine 24"


@pytest.mark.unit
def test_get_medications_for_date_orders_by_scheduled_time(
    isolated_database,
):
    add_medication(
        isolated_database,
        name="Evening",
        scheduled_time="20:00",
    )
    add_medication(
        isolated_database,
        name="Morning",
        scheduled_time="08:00",
    )
    add_medication(
        isolated_database,
        name="Afternoon",
        scheduled_time="13:00",
    )

    records = isolated_database.get_medications_for_date("2026-09-23")

    assert [record["name"] for record in records] == [
        "Morning",
        "Afternoon",
        "Evening",
    ]


@pytest.mark.unit
def test_get_medications_for_date_same_scheduled_time_is_supported(
    isolated_database,
):
    add_medication(
        isolated_database,
        name="Medicine A",
        scheduled_time="08:00",
    )
    add_medication(
        isolated_database,
        name="Medicine B",
        scheduled_time="08:00",
    )

    records = isolated_database.get_medications_for_date("2026-09-23")

    assert len(records) == 2
    assert {record["name"] for record in records} == {
        "Medicine A",
        "Medicine B",
    }


@pytest.mark.unit
def test_get_medications_for_date_none_scheduled_time_is_supported(
    isolated_database,
):
    add_medication(
        isolated_database,
        name="No Time",
        scheduled_time=None,
    )
    add_medication(
        isolated_database,
        name="Timed",
        scheduled_time="08:00",
    )

    records = isolated_database.get_medications_for_date("2026-09-23")

    assert len(records) == 2
    assert {record["name"] for record in records} == {
        "No Time",
        "Timed",
    }


@pytest.mark.unit
def test_get_medications_for_date_empty_scheduled_time_is_supported(
    isolated_database,
):
    add_medication(
        isolated_database,
        name="Empty Time",
        scheduled_time="",
    )

    records = isolated_database.get_medications_for_date("2026-09-23")

    assert len(records) == 1
    assert records[0]["scheduled_time"] == ""


@pytest.mark.unit
def test_get_medications_for_date_empty_string_date(
    isolated_database,
):
    add_medication(
        isolated_database,
        log_date="",
    )

    records = isolated_database.get_medications_for_date("")

    assert len(records) == 1
    assert records[0]["log_date"] == ""


@pytest.mark.unit
def test_get_medications_for_date_none_date_returns_empty(
    isolated_database,
):
    add_medication(isolated_database)

    assert isolated_database.get_medications_for_date(None) == []


@pytest.mark.unit
def test_get_medications_for_date_records_have_expected_schema(
    isolated_database,
):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date(
        "2026-09-23"
    )[0]

    assert set(record.keys()) == {
        "id",
        "log_date",
        "name",
        "dosage",
        "scheduled_time",
        "taken",
        "notes",
        "created_at",
    }


@pytest.mark.unit
def test_get_medications_for_date_returns_taken_status(
    isolated_database,
):
    add_medication(isolated_database)

    record = isolated_database.get_medications_for_date("2026-09-23")[0]

    isolated_database.set_medication_taken(record["id"], True)

    updated = isolated_database.get_medications_for_date("2026-09-23")

    assert updated[0]["taken"] == 1
