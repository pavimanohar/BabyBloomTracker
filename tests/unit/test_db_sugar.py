import sqlite3

import pytest


def add_reading(
    database,
    log_date="2026-09-23",
    slot="Before Breakfast",
    value=95.5,
    reading_time="07:30",
    previous_meal_time="20:30",
    fasting=False,
    notes="Normal reading",
):
    database.add_sugar_reading(
        log_date,
        slot,
        value,
        reading_time,
        previous_meal_time,
        fasting,
        notes,
    )


# ============================================================
# add_sugar_reading()
# ============================================================


@pytest.mark.unit
def test_add_sugar_reading_persists_record(isolated_database):
    add_reading(isolated_database)

    records = isolated_database.get_all_sugar()

    assert len(records) == 1
    assert records[0]["log_date"] == "2026-09-23"
    assert records[0]["slot"] == "Before Breakfast"
    assert records[0]["value"] == 95.5
    assert records[0]["reading_time"] == "07:30"
    assert records[0]["previous_meal_time"] == "20:30"
    assert records[0]["fasting"] == 0
    assert records[0]["notes"] == "Normal reading"
    assert records[0]["id"] > 0


@pytest.mark.unit
def test_add_sugar_reading_stores_all_supplied_fields(isolated_database):
    add_reading(
        isolated_database,
        log_date="2026-09-24",
        slot="After Lunch",
        value=142.75,
        reading_time="14:10",
        previous_meal_time="13:00",
        fasting=True,
        notes="Post meal reading",
    )

    record = isolated_database.get_all_sugar()[0]

    assert record["log_date"] == "2026-09-24"
    assert record["slot"] == "After Lunch"
    assert record["value"] == 142.75
    assert record["reading_time"] == "14:10"
    assert record["previous_meal_time"] == "13:00"
    assert record["fasting"] == 1
    assert record["notes"] == "Post meal reading"


@pytest.mark.unit
def test_add_sugar_reading_fasting_true_stores_one(isolated_database):
    add_reading(isolated_database, fasting=True)

    assert isolated_database.get_all_sugar()[0]["fasting"] == 1


@pytest.mark.unit
def test_add_sugar_reading_fasting_false_stores_zero(isolated_database):
    add_reading(isolated_database, fasting=False)

    assert isolated_database.get_all_sugar()[0]["fasting"] == 0


@pytest.mark.unit
def test_add_sugar_reading_fasting_none_stores_zero(isolated_database):
    add_reading(isolated_database, fasting=None)

    assert isolated_database.get_all_sugar()[0]["fasting"] == 0


@pytest.mark.unit
def test_add_sugar_reading_empty_notes(isolated_database):
    add_reading(isolated_database, notes="")

    assert isolated_database.get_all_sugar()[0]["notes"] == ""


@pytest.mark.unit
def test_add_sugar_reading_none_notes(isolated_database):
    add_reading(isolated_database, notes=None)

    assert isolated_database.get_all_sugar()[0]["notes"] is None


@pytest.mark.unit
def test_add_sugar_reading_none_value(isolated_database):
    add_reading(isolated_database, value=None)

    assert isolated_database.get_all_sugar()[0]["value"] is None


@pytest.mark.unit
def test_add_sugar_reading_zero_value(isolated_database):
    add_reading(isolated_database, value=0)

    assert isolated_database.get_all_sugar()[0]["value"] == 0


@pytest.mark.unit
def test_add_sugar_reading_decimal_value(isolated_database):
    add_reading(isolated_database, value=123.456)

    assert isolated_database.get_all_sugar()[0]["value"] == pytest.approx(123.456)


@pytest.mark.unit
def test_add_sugar_reading_very_large_value(isolated_database):
    value = 1_000_000_000.123

    add_reading(isolated_database, value=value)

    assert isolated_database.get_all_sugar()[0]["value"] == pytest.approx(value)


@pytest.mark.unit
def test_add_sugar_reading_negative_value(isolated_database):
    add_reading(isolated_database, value=-10.5)

    assert isolated_database.get_all_sugar()[0]["value"] == pytest.approx(-10.5)


@pytest.mark.unit
def test_add_sugar_reading_unicode_notes(isolated_database):
    notes = "மருத்துவர் ஆலோசனை ❤️ 😊"

    add_reading(isolated_database, notes=notes)

    assert isolated_database.get_all_sugar()[0]["notes"] == notes


@pytest.mark.unit
def test_add_sugar_reading_special_characters_are_stored_safely(
    isolated_database,
):
    notes = """Patient's reading:
"Normal" value.
SQL-like text: '; DROP TABLE sugar_log; --
Line two."""

    add_reading(isolated_database, notes=notes)

    records = isolated_database.get_all_sugar()

    assert len(records) == 1
    assert records[0]["notes"] == notes

    # Confirm the table still exists.
    assert isolated_database.get_all_sugar() == records


@pytest.mark.unit
def test_add_sugar_reading_very_long_notes(isolated_database):
    notes = "A" * 100_000

    add_reading(isolated_database, notes=notes)

    assert isolated_database.get_all_sugar()[0]["notes"] == notes


@pytest.mark.unit
def test_add_duplicate_sugar_readings_are_allowed(isolated_database):
    add_reading(isolated_database, notes="Same")
    add_reading(isolated_database, notes="Same")

    records = isolated_database.get_all_sugar()

    assert len(records) == 2
    assert records[0]["notes"] == records[1]["notes"]
    assert records[0]["id"] != records[1]["id"]


@pytest.mark.unit
def test_multiple_sugar_readings_same_date_are_stored(isolated_database):
    add_reading(isolated_database, slot="Before Breakfast")
    add_reading(isolated_database, slot="After Breakfast")

    records = isolated_database.get_sugar_for_date("2026-09-23")

    assert len(records) == 2


@pytest.mark.unit
def test_add_sugar_reading_none_log_date_is_rejected(isolated_database):
    with pytest.raises(sqlite3.IntegrityError):
        add_reading(isolated_database, log_date=None)


@pytest.mark.unit
def test_add_sugar_reading_none_slot_is_rejected(isolated_database):
    with pytest.raises(sqlite3.IntegrityError):
        add_reading(isolated_database, slot=None)


@pytest.mark.unit
def test_add_sugar_reading_commit_survives_connection_reopen(isolated_database):
    add_reading(isolated_database, notes="Persistent sugar reading")

    database_path = isolated_database.path
    isolated_database.conn.close()

    reopened = sqlite3.connect(database_path)

    try:
        rows = reopened.execute(
            """
            SELECT log_date, slot, value, notes
            FROM sugar_log
            ORDER BY id
            """
        ).fetchall()

        assert rows == [
            (
                "2026-09-23",
                "Before Breakfast",
                95.5,
                "Persistent sugar reading",
            )
        ]
    finally:
        reopened.close()


# ============================================================
# get_sugar_for_date()
# ============================================================


@pytest.mark.unit
def test_get_sugar_for_date_returns_matching_records(isolated_database):
    add_reading(isolated_database)

    records = isolated_database.get_sugar_for_date("2026-09-23")

    assert len(records) == 1
    assert records[0]["log_date"] == "2026-09-23"


@pytest.mark.unit
def test_get_sugar_for_date_returns_empty_for_no_match(isolated_database):
    add_reading(isolated_database)

    assert isolated_database.get_sugar_for_date("2026-09-24") == []


@pytest.mark.unit
def test_get_sugar_for_date_returns_only_requested_date(isolated_database):
    add_reading(isolated_database, log_date="2026-09-23")
    add_reading(isolated_database, log_date="2026-09-24")
    add_reading(isolated_database, log_date="2026-09-25")

    records = isolated_database.get_sugar_for_date("2026-09-24")

    assert len(records) == 1
    assert records[0]["log_date"] == "2026-09-24"


@pytest.mark.unit
def test_get_sugar_for_date_orders_by_id(isolated_database):
    add_reading(isolated_database, notes="First")
    add_reading(isolated_database, notes="Second")
    add_reading(isolated_database, notes="Third")

    records = isolated_database.get_sugar_for_date("2026-09-23")

    assert [record["notes"] for record in records] == [
        "First",
        "Second",
        "Third",
    ]

    assert [record["id"] for record in records] == sorted(
        record["id"] for record in records
    )


@pytest.mark.unit
def test_get_sugar_for_date_empty_string(isolated_database):
    add_reading(isolated_database, log_date="")

    records = isolated_database.get_sugar_for_date("")

    assert len(records) == 1
    assert records[0]["log_date"] == ""


@pytest.mark.unit
def test_get_sugar_for_date_none_returns_empty_list(isolated_database):
    add_reading(isolated_database)

    assert isolated_database.get_sugar_for_date(None) == []


@pytest.mark.unit
def test_get_sugar_for_date_records_have_expected_schema(isolated_database):
    add_reading(isolated_database)

    record = isolated_database.get_sugar_for_date("2026-09-23")[0]

    assert set(record.keys()) == {
        "id",
        "log_date",
        "slot",
        "value",
        "reading_time",
        "previous_meal_time",
        "fasting",
        "notes",
        "created_at",
    }


# ============================================================
# get_sugar_range()
# ============================================================


@pytest.mark.unit
def test_get_sugar_range_returns_records_inside_range(isolated_database):
    add_reading(isolated_database, log_date="2026-09-22")
    add_reading(isolated_database, log_date="2026-09-23")
    add_reading(isolated_database, log_date="2026-09-24")

    records = isolated_database.get_sugar_range(
        "2026-09-22",
        "2026-09-24",
    )

    assert len(records) == 3


@pytest.mark.unit
def test_get_sugar_range_includes_start_date(isolated_database):
    add_reading(isolated_database, log_date="2026-09-22")
    add_reading(isolated_database, log_date="2026-09-23")

    records = isolated_database.get_sugar_range(
        "2026-09-22",
        "2026-09-22",
    )

    assert len(records) == 1
    assert records[0]["log_date"] == "2026-09-22"


@pytest.mark.unit
def test_get_sugar_range_includes_end_date(isolated_database):
    add_reading(isolated_database, log_date="2026-09-23")
    add_reading(isolated_database, log_date="2026-09-24")

    records = isolated_database.get_sugar_range(
        "2026-09-24",
        "2026-09-24",
    )

    assert len(records) == 1
    assert records[0]["log_date"] == "2026-09-24"


@pytest.mark.unit
def test_get_sugar_range_excludes_records_outside_range(isolated_database):
    add_reading(isolated_database, log_date="2026-09-21")
    add_reading(isolated_database, log_date="2026-09-23")
    add_reading(isolated_database, log_date="2026-09-25")

    records = isolated_database.get_sugar_range(
        "2026-09-22",
        "2026-09-24",
    )

    assert len(records) == 1
    assert records[0]["log_date"] == "2026-09-23"


@pytest.mark.unit
def test_get_sugar_range_single_day(isolated_database):
    add_reading(isolated_database, log_date="2026-09-23")
    add_reading(isolated_database, log_date="2026-09-24")

    records = isolated_database.get_sugar_range(
        "2026-09-23",
        "2026-09-23",
    )

    assert len(records) == 1


@pytest.mark.unit
def test_get_sugar_range_empty_result(isolated_database):
    add_reading(isolated_database, log_date="2026-09-23")

    assert isolated_database.get_sugar_range(
        "2026-10-01",
        "2026-10-02",
    ) == []


@pytest.mark.unit
def test_get_sugar_range_orders_by_date_then_id(isolated_database):
    add_reading(
        isolated_database,
        log_date="2026-09-24",
        notes="September 24",
    )
    add_reading(
        isolated_database,
        log_date="2026-09-23",
        notes="September 23 first",
    )
    add_reading(
        isolated_database,
        log_date="2026-09-23",
        notes="September 23 second",
    )

    records = isolated_database.get_sugar_range(
        "2026-09-23",
        "2026-09-24",
    )

    assert [record["notes"] for record in records] == [
        "September 23 first",
        "September 23 second",
        "September 24",
    ]


@pytest.mark.unit
def test_get_sugar_range_start_after_end_returns_empty(isolated_database):
    add_reading(isolated_database, log_date="2026-09-23")

    assert isolated_database.get_sugar_range(
        "2026-09-25",
        "2026-09-22",
    ) == []


@pytest.mark.unit
def test_get_sugar_range_none_start_returns_empty(isolated_database):
    add_reading(isolated_database, log_date="2026-09-23")

    assert isolated_database.get_sugar_range(
        None,
        "2026-09-24",
    ) == []


@pytest.mark.unit
def test_get_sugar_range_none_end_returns_empty(isolated_database):
    add_reading(isolated_database, log_date="2026-09-23")

    assert isolated_database.get_sugar_range(
        "2026-09-22",
        None,
    ) == []


# ============================================================
# get_all_sugar()
# ============================================================


@pytest.mark.unit
def test_get_all_sugar_returns_all_records(isolated_database):
    add_reading(isolated_database, log_date="2026-09-22")
    add_reading(isolated_database, log_date="2026-09-23")
    add_reading(isolated_database, log_date="2026-09-24")

    records = isolated_database.get_all_sugar()

    assert len(records) == 3


@pytest.mark.unit
def test_get_all_sugar_empty_database(isolated_database):
    assert isolated_database.get_all_sugar() == []


@pytest.mark.unit
def test_get_all_sugar_orders_by_date_then_id(isolated_database):
    add_reading(isolated_database, log_date="2026-09-25", notes="25")
    add_reading(isolated_database, log_date="2026-09-23", notes="23 first")
    add_reading(isolated_database, log_date="2026-09-24", notes="24")
    add_reading(isolated_database, log_date="2026-09-23", notes="23 second")

    records = isolated_database.get_all_sugar()

    assert [record["notes"] for record in records] == [
        "23 first",
        "23 second",
        "24",
        "25",
    ]


@pytest.mark.unit
def test_get_all_sugar_same_date_ordered_by_id(isolated_database):
    add_reading(isolated_database, notes="First")
    add_reading(isolated_database, notes="Second")

    records = isolated_database.get_all_sugar()

    assert [record["notes"] for record in records] == [
        "First",
        "Second",
    ]


@pytest.mark.unit
def test_get_all_sugar_records_have_expected_schema(isolated_database):
    add_reading(isolated_database)

    record = isolated_database.get_all_sugar()[0]

    assert set(record.keys()) == {
        "id",
        "log_date",
        "slot",
        "value",
        "reading_time",
        "previous_meal_time",
        "fasting",
        "notes",
        "created_at",
    }


# ============================================================
# update_sugar_reading()
# ============================================================


@pytest.mark.unit
def test_update_sugar_reading_updates_one_field(isolated_database):
    add_reading(isolated_database, notes="Original")

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        notes="Updated",
    )

    updated = isolated_database.get_all_sugar()[0]

    assert updated["notes"] == "Updated"


@pytest.mark.unit
def test_update_sugar_reading_updates_multiple_fields(isolated_database):
    add_reading(
        isolated_database,
        value=100,
        reading_time="07:00",
        notes="Original",
    )

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        value=125.5,
        reading_time="08:15",
        notes="Updated",
    )

    updated = isolated_database.get_all_sugar()[0]

    assert updated["value"] == pytest.approx(125.5)
    assert updated["reading_time"] == "08:15"
    assert updated["notes"] == "Updated"


@pytest.mark.unit
def test_update_sugar_reading_updates_value(isolated_database):
    add_reading(isolated_database, value=100)

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        value=150.5,
    )

    assert isolated_database.get_all_sugar()[0]["value"] == pytest.approx(150.5)


@pytest.mark.unit
def test_update_sugar_reading_updates_slot(isolated_database):
    add_reading(isolated_database, slot="Before Breakfast")

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        slot="After Breakfast",
    )

    assert isolated_database.get_all_sugar()[0]["slot"] == "After Breakfast"


@pytest.mark.unit
def test_update_sugar_reading_updates_reading_time(isolated_database):
    add_reading(isolated_database, reading_time="07:00")

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        reading_time="08:30",
    )

    assert isolated_database.get_all_sugar()[0]["reading_time"] == "08:30"


@pytest.mark.unit
def test_update_sugar_reading_updates_previous_meal_time(isolated_database):
    add_reading(isolated_database, previous_meal_time="20:00")

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        previous_meal_time="21:30",
    )

    assert (
        isolated_database.get_all_sugar()[0]["previous_meal_time"]
        == "21:30"
    )


@pytest.mark.unit
def test_update_sugar_reading_updates_fasting_to_true(isolated_database):
    add_reading(isolated_database, fasting=False)

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        fasting=1,
    )

    assert isolated_database.get_all_sugar()[0]["fasting"] == 1


@pytest.mark.unit
def test_update_sugar_reading_updates_fasting_to_false(isolated_database):
    add_reading(isolated_database, fasting=True)

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        fasting=0,
    )

    assert isolated_database.get_all_sugar()[0]["fasting"] == 0


@pytest.mark.unit
def test_update_sugar_reading_updates_notes(isolated_database):
    add_reading(isolated_database, notes="Original")

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        notes="Updated notes",
    )

    assert isolated_database.get_all_sugar()[0]["notes"] == "Updated notes"


@pytest.mark.unit
def test_update_sugar_reading_to_empty_string(isolated_database):
    add_reading(isolated_database, notes="Original")

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        notes="",
    )

    assert isolated_database.get_all_sugar()[0]["notes"] == ""


@pytest.mark.unit
def test_update_sugar_reading_nullable_field_to_none(isolated_database):
    add_reading(
        isolated_database,
        value=100,
        reading_time="07:00",
        previous_meal_time="20:00",
        notes="Original",
    )

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        value=None,
        reading_time=None,
        previous_meal_time=None,
        notes=None,
    )

    updated = isolated_database.get_all_sugar()[0]

    assert updated["value"] is None
    assert updated["reading_time"] is None
    assert updated["previous_meal_time"] is None
    assert updated["notes"] is None


@pytest.mark.unit
def test_update_sugar_reading_without_fields_is_noop(isolated_database):
    add_reading(isolated_database, notes="Original")

    before = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(before["id"])

    after = isolated_database.get_all_sugar()[0]

    assert after == before


@pytest.mark.unit
def test_update_sugar_reading_nonexistent_id_is_harmless(isolated_database):
    add_reading(isolated_database, notes="Existing")

    isolated_database.update_sugar_reading(
        999999,
        notes="Should not be inserted",
    )

    records = isolated_database.get_all_sugar()

    assert len(records) == 1
    assert records[0]["notes"] == "Existing"


@pytest.mark.unit
def test_update_sugar_reading_invalid_column_raises_sqlite_error(
    isolated_database,
):
    add_reading(isolated_database)

    record = isolated_database.get_all_sugar()[0]

    with pytest.raises(sqlite3.OperationalError):
        isolated_database.update_sugar_reading(
            record["id"],
            definitely_not_a_column="value",
        )


@pytest.mark.unit
def test_update_sugar_reading_sql_like_value_is_stored_as_data(
    isolated_database,
):
    add_reading(isolated_database)

    record = isolated_database.get_all_sugar()[0]

    malicious_text = "'; DROP TABLE sugar_log; --"

    isolated_database.update_sugar_reading(
        record["id"],
        notes=malicious_text,
    )

    updated = isolated_database.get_all_sugar()

    assert len(updated) == 1
    assert updated[0]["notes"] == malicious_text


@pytest.mark.unit
def test_update_sugar_reading_commits_changes(isolated_database):
    add_reading(isolated_database, notes="Original")

    record = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        record["id"],
        notes="Committed",
    )

    database_path = isolated_database.path
    isolated_database.conn.close()

    reopened = sqlite3.connect(database_path)

    try:
        row = reopened.execute(
            "SELECT notes FROM sugar_log WHERE id = ?",
            (record["id"],),
        ).fetchone()

        assert row == ("Committed",)
    finally:
        reopened.close()


@pytest.mark.unit
def test_update_sugar_reading_preserves_unspecified_fields(
    isolated_database,
):
    add_reading(
        isolated_database,
        log_date="2026-09-23",
        slot="Before Breakfast",
        value=100,
        reading_time="07:00",
        previous_meal_time="20:00",
        fasting=False,
        notes="Original",
    )

    before = isolated_database.get_all_sugar()[0]

    isolated_database.update_sugar_reading(
        before["id"],
        notes="Changed only",
    )

    after = isolated_database.get_all_sugar()[0]

    assert after["log_date"] == before["log_date"]
    assert after["slot"] == before["slot"]
    assert after["value"] == before["value"]
    assert after["reading_time"] == before["reading_time"]
    assert after["previous_meal_time"] == before["previous_meal_time"]
    assert after["fasting"] == before["fasting"]
    assert after["notes"] == "Changed only"


# ============================================================
# delete_sugar_reading()
# ============================================================


@pytest.mark.unit
def test_delete_sugar_reading_removes_existing_record(isolated_database):
    add_reading(isolated_database)

    record = isolated_database.get_all_sugar()[0]

    isolated_database.delete_sugar_reading(record["id"])

    assert isolated_database.get_all_sugar() == []


@pytest.mark.unit
def test_delete_sugar_reading_preserves_other_records(isolated_database):
    add_reading(isolated_database, notes="Keep")
    add_reading(isolated_database, notes="Delete")
    add_reading(isolated_database, notes="Keep too")

    records = isolated_database.get_all_sugar()

    delete_id = records[1]["id"]

    isolated_database.delete_sugar_reading(delete_id)

    remaining = isolated_database.get_all_sugar()

    assert len(remaining) == 2
    assert [record["notes"] for record in remaining] == [
        "Keep",
        "Keep too",
    ]


@pytest.mark.unit
def test_delete_sugar_reading_nonexistent_id_is_harmless(isolated_database):
    add_reading(isolated_database)

    isolated_database.delete_sugar_reading(999999)

    assert len(isolated_database.get_all_sugar()) == 1


@pytest.mark.unit
def test_delete_sugar_reading_same_id_twice_is_harmless(isolated_database):
    add_reading(isolated_database)

    record = isolated_database.get_all_sugar()[0]

    isolated_database.delete_sugar_reading(record["id"])
    isolated_database.delete_sugar_reading(record["id"])

    assert isolated_database.get_all_sugar() == []


@pytest.mark.unit
def test_delete_sugar_reading_removes_record_from_date_query(
    isolated_database,
):
    add_reading(isolated_database)

    record = isolated_database.get_all_sugar()[0]

    isolated_database.delete_sugar_reading(record["id"])

    assert isolated_database.get_sugar_for_date("2026-09-23") == []


@pytest.mark.unit
def test_delete_sugar_reading_does_not_affect_other_dates(
    isolated_database,
):
    add_reading(
        isolated_database,
        log_date="2026-09-23",
        notes="Delete",
    )
    add_reading(
        isolated_database,
        log_date="2026-09-24",
        notes="Keep",
    )

    records = isolated_database.get_all_sugar()

    delete_id = records[0]["id"]

    isolated_database.delete_sugar_reading(delete_id)

    remaining = isolated_database.get_all_sugar()

    assert len(remaining) == 1
    assert remaining[0]["log_date"] == "2026-09-24"
    assert remaining[0]["notes"] == "Keep"


@pytest.mark.unit
def test_delete_sugar_reading_commits_change(isolated_database):
    add_reading(isolated_database)

    record = isolated_database.get_all_sugar()[0]
    database_path = isolated_database.path

    isolated_database.delete_sugar_reading(record["id"])
    isolated_database.conn.close()

    reopened = sqlite3.connect(database_path)

    try:
        row = reopened.execute(
            "SELECT id FROM sugar_log WHERE id = ?",
            (record["id"],),
        ).fetchone()

        assert row is None
    finally:
        reopened.close()
