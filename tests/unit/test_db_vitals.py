import sqlite3
import pytest


class TestVitals:
    # A. add_vital_reading() — 20 tests

    def test_add_bp_reading(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "BP", 120, 80, "09:00 AM", "Routine check"
        )
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert row["vital_type"] == "BP"
        assert row["value1"] == 120
        assert row["value2"] == 80

    def test_add_o2_reading(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "O2", 98, None, "09:05 AM"
        )
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert row["vital_type"] == "O2"
        assert row["value1"] == 98
        assert row["value2"] is None

    def test_add_pulse_reading(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 72, None, "09:10 AM"
        )
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert row["vital_type"] == "Pulse"
        assert row["value1"] == 72
        assert row["value2"] is None

    def test_add_weight_reading(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Weight", 65.5, None, "09:15 AM"
        )
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert row["vital_type"] == "Weight"
        assert row["value1"] == 65.5
        assert row["value2"] is None

    def test_add_vital_all_supplied_fields(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "BP", 121, 81, "10:20 AM", "All fields"
        )
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert row["log_date"] == "2026-09-23"
        assert row["vital_type"] == "BP"
        assert row["value1"] == 121
        assert row["value2"] == 81
        assert row["reading_time"] == "10:20 AM"
        assert row["notes"] == "All fields"
        assert row["created_at"] is not None

    def test_add_bp_stores_both_values(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "BP", 130, 85, "11:00 AM"
        )
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert row["value1"] == 130
        assert row["value2"] == 85

    def test_add_non_bp_with_value2_none(self, isolated_database):
        for vital_type in ("O2", "Pulse", "Weight"):
            isolated_database.add_vital_reading(
                "2026-09-23", vital_type, 10, None, "11:10 AM"
            )
        rows = isolated_database.get_vitals_for_date("2026-09-23")
        assert all(row["value2"] is None for row in rows)

    def test_add_vital_empty_notes(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 70, None, "12:00 PM", ""
        )
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["notes"] == ""

    def test_add_vital_none_notes(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 70, None, "12:00 PM", None
        )
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["notes"] is None

    def test_add_vital_none_value1(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", None, None, "12:00 PM"
        )
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["value1"] is None

    def test_add_vital_none_value2(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "BP", 120, None, "12:00 PM"
        )
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["value2"] is None

    def test_add_vital_empty_type(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "", 1, None, "12:00 PM"
        )
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["vital_type"] == ""

    def test_add_vital_none_type_rejected(self, isolated_database):
        with pytest.raises(sqlite3.IntegrityError):
            isolated_database.add_vital_reading(
                "2026-09-23", None, 1, None, "12:00 PM"
            )

    def test_add_vital_none_date_rejected(self, isolated_database):
        with pytest.raises(sqlite3.IntegrityError):
            isolated_database.add_vital_reading(
                None, "Pulse", 70, None, "12:00 PM"
            )

    def test_add_vital_unicode_notes(self, isolated_database):
        notes = "检查 ✓ मातृत्व 💗"
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 72, None, "12:00 PM", notes
        )
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["notes"] == notes

    def test_add_vital_sql_like_text(self, isolated_database):
        vital_type = "BP'); DROP TABLE vitals_log; --"
        notes = "100% _ test ?"
        isolated_database.add_vital_reading(
            "2026-09-23", vital_type, 120, 80, "12:00 PM", notes
        )
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert row["vital_type"] == vital_type
        assert row["notes"] == notes

    def test_add_vital_very_large_numeric_values(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 1e308, -1e308, "12:00 PM"
        )
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert row["value1"] == 1e308
        assert row["value2"] == -1e308

    def test_add_vital_negative_numeric_values(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Weight", -10.5, None, "12:00 PM"
        )
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["value1"] == -10.5

    def test_add_duplicate_vital_readings_allowed(self, isolated_database):
        args = ("2026-09-23", "Pulse", 72, None, "12:00 PM", "same")
        isolated_database.add_vital_reading(*args)
        isolated_database.add_vital_reading(*args)
        rows = isolated_database.get_vitals_for_date("2026-09-23")
        assert len(rows) == 2
        assert rows[0]["id"] < rows[1]["id"]

    def test_add_vital_commit_survives_reopen(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Weight", 65.5, None, "12:00 PM"
        )
        path = isolated_database.path
        isolated_database.conn.close()
        isolated_database.conn = sqlite3.connect(path)
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["value1"] == 65.5

    # B. update_vital_reading() — 18 tests

    def test_update_value1(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 70, None, "09:00 AM"
        )
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, value1=75)
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["value1"] == 75

    def test_update_value2(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "BP", 120, 80, "09:00 AM"
        )
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, value2=85)
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["value2"] == 85

    def test_update_vital_type(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 70, None, "09:00 AM"
        )
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, vital_type="O2")
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["vital_type"] == "O2"

    def test_update_log_date(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 70, None, "09:00 AM"
        )
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, log_date="2026-09-24")
        assert isolated_database.get_vitals_for_date("2026-09-24")[0]["id"] == entry_id

    def test_update_reading_time(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 70, None, "09:00 AM"
        )
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, reading_time="10:30 PM")
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["reading_time"] == "10:30 PM"

    def test_update_notes(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 70, None, "09:00 AM", "old"
        )
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, notes="new")
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["notes"] == "new"

    def test_update_multiple_fields(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "BP", 120, 80, "09:00 AM", "old"
        )
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(
            entry_id, value1=130, value2=85, reading_time="10:00 AM", notes="new"
        )
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert (row["value1"], row["value2"], row["reading_time"], row["notes"]) == (
            130, 85, "10:00 AM", "new"
        )

    def test_update_all_mutable_columns(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "BP", 120, 80, "09:00 AM", "old"
        )
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(
            entry_id,
            log_date="2026-09-24",
            vital_type="O2",
            value1=98,
            value2=None,
            reading_time="10:00 AM",
            notes="updated",
        )
        row = isolated_database.get_vitals_for_date("2026-09-24")[0]
        assert row["id"] == entry_id
        assert row["vital_type"] == "O2"
        assert row["value1"] == 98
        assert row["value2"] is None
        assert row["reading_time"] == "10:00 AM"
        assert row["notes"] == "updated"

    def test_update_with_no_fields_is_noop(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Pulse", 70, None, "09:00 AM", "unchanged"
        )
        before = isolated_database.get_vitals_for_date("2026-09-23")[0].copy()
        isolated_database.update_vital_reading(before["id"])
        after = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert after == before

    def test_update_nonexistent_id_is_noop(self, isolated_database):
        isolated_database.update_vital_reading(999999, value1=100)
        assert isolated_database.get_all_vitals() == []

    def test_update_does_not_affect_other_record(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        isolated_database.add_vital_reading("2026-09-23", "O2", 98, None, "10:00 AM")
        rows = isolated_database.get_vitals_for_date("2026-09-23")
        isolated_database.update_vital_reading(rows[0]["id"], value1=75)
        updated = isolated_database.get_vitals_for_date("2026-09-23")
        assert updated[0]["value1"] == 75
        assert updated[1]["value1"] == 98

    def test_update_value1_to_none(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, value1=None)
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["value1"] is None

    def test_update_value2_to_none(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "BP", 120, 80, "09:00 AM")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, value2=None)
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["value2"] is None

    def test_update_notes_to_none(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM", "old")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, notes=None)
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["notes"] is None

    def test_update_to_empty_strings(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM", "old")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, vital_type="", reading_time="", notes="")
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert row["vital_type"] == ""
        assert row["reading_time"] == ""
        assert row["notes"] == ""

    def test_update_sql_like_string(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        text = "x'); DROP TABLE vitals_log; --"
        isolated_database.update_vital_reading(entry_id, notes=text)
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["notes"] == text

    def test_update_persists_after_reopen(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.update_vital_reading(entry_id, value1=75)
        path = isolated_database.path
        isolated_database.conn.close()
        isolated_database.conn = sqlite3.connect(path)
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["value1"] == 75

    def test_update_preserves_primary_key(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        entry_id = row["id"]
        isolated_database.update_vital_reading(entry_id, value1=75)
        assert isolated_database.get_vitals_for_date("2026-09-23")[0]["id"] == entry_id

    # C. delete_vital_reading() — 7 tests

    def test_delete_existing_vital(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.delete_vital_reading(entry_id)
        assert isolated_database.get_vitals_for_date("2026-09-23") == []

    def test_delete_one_of_multiple_vitals(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        isolated_database.add_vital_reading("2026-09-23", "O2", 98, None, "10:00 AM")
        rows = isolated_database.get_vitals_for_date("2026-09-23")
        isolated_database.delete_vital_reading(rows[0]["id"])
        assert [r["vital_type"] for r in isolated_database.get_vitals_for_date("2026-09-23")] == ["O2"]

    def test_delete_nonexistent_vital(self, isolated_database):
        isolated_database.delete_vital_reading(999999)
        assert isolated_database.get_all_vitals() == []

    def test_delete_same_vital_twice(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.delete_vital_reading(entry_id)
        isolated_database.delete_vital_reading(entry_id)
        assert isolated_database.get_all_vitals() == []

    def test_deleted_vital_absent_from_date_query(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.delete_vital_reading(entry_id)
        assert all(r["id"] != entry_id for r in isolated_database.get_vitals_for_date("2026-09-23"))

    def test_delete_does_not_affect_other_vitals(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        isolated_database.add_vital_reading("2026-09-24", "O2", 98, None, "10:00 AM")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.delete_vital_reading(entry_id)
        assert len(isolated_database.get_vitals_for_date("2026-09-24")) == 1

    def test_delete_persists_after_reopen(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        entry_id = isolated_database.get_vitals_for_date("2026-09-23")[0]["id"]
        isolated_database.delete_vital_reading(entry_id)
        path = isolated_database.path
        isolated_database.conn.close()
        isolated_database.conn = sqlite3.connect(path)
        assert isolated_database.get_vitals_for_date("2026-09-23") == []

    # D. get_vitals_for_date() — 10 tests

    def test_get_vitals_for_date_matching(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        assert len(isolated_database.get_vitals_for_date("2026-09-23")) == 1

    def test_get_vitals_for_date_empty(self, isolated_database):
        assert isolated_database.get_vitals_for_date("2026-09-23") == []

    def test_get_vitals_for_date_excludes_other_dates(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        isolated_database.add_vital_reading("2026-09-24", "O2", 98, None, "10:00 AM")
        assert [r["vital_type"] for r in isolated_database.get_vitals_for_date("2026-09-23")] == ["Pulse"]

    def test_get_vitals_for_date_ordered_by_id(self, isolated_database):
        for vital_type in ("Pulse", "O2", "Weight"):
            isolated_database.add_vital_reading(
                "2026-09-23", vital_type, 1, None, "09:00 AM"
            )
        rows = isolated_database.get_vitals_for_date("2026-09-23")
        assert [r["vital_type"] for r in rows] == ["Pulse", "O2", "Weight"]
        assert [r["id"] for r in rows] == sorted(r["id"] for r in rows)

    def test_get_vitals_for_date_empty_string(self, isolated_database):
        assert isolated_database.get_vitals_for_date("") == []

    def test_get_vitals_for_date_none(self, isolated_database):
        assert isolated_database.get_vitals_for_date(None) == []

    def test_get_vitals_for_date_schema(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        assert set(isolated_database.get_vitals_for_date("2026-09-23")[0]) == {
            "id", "log_date", "vital_type", "value1", "value2",
            "reading_time", "notes", "created_at"
        }

    def test_get_vitals_for_date_bp_values(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "BP", 120, 80, "09:00 AM")
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert (row["value1"], row["value2"]) == (120, 80)

    def test_get_vitals_for_date_non_bp_value2(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "O2", 98, None, "09:00 AM")
        row = isolated_database.get_vitals_for_date("2026-09-23")[0]
        assert row["value1"] == 98
        assert row["value2"] is None

    def test_get_vitals_for_date_sql_like_date(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-%", "Pulse", 70, None, "09:00 AM"
        )
        assert len(isolated_database.get_vitals_for_date("2026-09-%")) == 1
        assert isolated_database.get_vitals_for_date("2026-09-23") == []

    # E. get_vitals_range() — 14 tests

    def test_get_vitals_range_inside_range(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-10", "Pulse", 70, None, "09:00 AM")
        isolated_database.add_vital_reading("2026-09-20", "O2", 98, None, "10:00 AM")
        rows = isolated_database.get_vitals_range("2026-09-01", "2026-09-30")
        assert len(rows) == 2

    def test_get_vitals_range_empty(self, isolated_database):
        isolated_database.add_vital_reading("2026-08-10", "Pulse", 70, None, "09:00 AM")
        assert isolated_database.get_vitals_range("2026-09-01", "2026-09-30") == []

    def test_get_vitals_range_includes_start(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-01", "Pulse", 70, None, "09:00 AM")
        assert len(isolated_database.get_vitals_range("2026-09-01", "2026-09-10")) == 1

    def test_get_vitals_range_includes_end(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-10", "Pulse", 70, None, "09:00 AM")
        assert len(isolated_database.get_vitals_range("2026-09-01", "2026-09-10")) == 1

    def test_get_vitals_range_excludes_before(self, isolated_database):
        isolated_database.add_vital_reading("2026-08-31", "Pulse", 70, None, "09:00 AM")
        assert isolated_database.get_vitals_range("2026-09-01", "2026-09-30") == []

    def test_get_vitals_range_excludes_after(self, isolated_database):
        isolated_database.add_vital_reading("2026-10-01", "Pulse", 70, None, "09:00 AM")
        assert isolated_database.get_vitals_range("2026-09-01", "2026-09-30") == []

    def test_get_vitals_range_multiple_dates(self, isolated_database):
        for date in ("2026-09-05", "2026-09-10", "2026-09-20"):
            isolated_database.add_vital_reading(date, "Pulse", 70, None, "09:00 AM")
        assert len(isolated_database.get_vitals_range("2026-09-01", "2026-09-30")) == 3

    def test_get_vitals_range_multiple_same_date(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-10", "Pulse", 70, None, "09:00 AM")
        isolated_database.add_vital_reading("2026-09-10", "O2", 98, None, "10:00 AM")
        assert len(isolated_database.get_vitals_range("2026-09-10", "2026-09-10")) == 2

    def test_get_vitals_range_ordered_by_date(self, isolated_database):
        for date in ("2026-09-20", "2026-09-02", "2026-09-10"):
            isolated_database.add_vital_reading(date, "Pulse", 70, None, "09:00 AM")
        rows = isolated_database.get_vitals_range("2026-09-01", "2026-09-30")
        assert [r["log_date"] for r in rows] == [
            "2026-09-02", "2026-09-10", "2026-09-20"
        ]

    def test_get_vitals_range_same_date_ordered_by_id(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-10", "Pulse", 70, None, "09:00 AM")
        isolated_database.add_vital_reading("2026-09-10", "O2", 98, None, "10:00 AM")
        rows = isolated_database.get_vitals_range("2026-09-10", "2026-09-10")
        assert [r["vital_type"] for r in rows] == ["Pulse", "O2"]
        assert rows[0]["id"] < rows[1]["id"]

    def test_get_vitals_range_same_start_and_end(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-10", "Pulse", 70, None, "09:00 AM")
        isolated_database.add_vital_reading("2026-09-11", "O2", 98, None, "10:00 AM")
        assert len(isolated_database.get_vitals_range("2026-09-10", "2026-09-10")) == 1

    def test_get_vitals_range_start_after_end(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-10", "Pulse", 70, None, "09:00 AM")
        assert isolated_database.get_vitals_range("2026-09-20", "2026-09-10") == []

    def test_get_vitals_range_empty_strings(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-10", "Pulse", 70, None, "09:00 AM")
        assert isolated_database.get_vitals_range("", "") == []

    def test_get_vitals_range_none_values(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-10", "Pulse", 70, None, "09:00 AM")
        assert isolated_database.get_vitals_range(None, None) == []

    # F. get_all_vitals() — 8 tests

    def test_get_all_vitals_returns_all(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        isolated_database.add_vital_reading("2026-09-24", "O2", 98, None, "10:00 AM")
        assert len(isolated_database.get_all_vitals()) == 2

    def test_get_all_vitals_empty(self, isolated_database):
        assert isolated_database.get_all_vitals() == []

    def test_get_all_vitals_multiple_dates(self, isolated_database):
        for date in ("2026-09-23", "2026-09-24", "2026-09-25"):
            isolated_database.add_vital_reading(date, "Pulse", 70, None, "09:00 AM")
        assert len(isolated_database.get_all_vitals()) == 3

    def test_get_all_vitals_ordered_by_date(self, isolated_database):
        for date in ("2026-09-25", "2026-09-23", "2026-09-24"):
            isolated_database.add_vital_reading(date, "Pulse", 70, None, "09:00 AM")
        assert [r["log_date"] for r in isolated_database.get_all_vitals()] == [
            "2026-09-23", "2026-09-24", "2026-09-25"
        ]

    def test_get_all_vitals_same_date_ordered_by_id(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        isolated_database.add_vital_reading("2026-09-23", "O2", 98, None, "10:00 AM")
        rows = isolated_database.get_all_vitals()
        assert [r["vital_type"] for r in rows] == ["Pulse", "O2"]
        assert rows[0]["id"] < rows[1]["id"]

    def test_get_all_vitals_all_types(self, isolated_database):
        for vital_type in ("BP", "O2", "Pulse", "Weight"):
            isolated_database.add_vital_reading(
                "2026-09-23", vital_type, 100, 50 if vital_type == "BP" else None, "09:00 AM"
            )
        assert {r["vital_type"] for r in isolated_database.get_all_vitals()} == {
            "BP", "O2", "Pulse", "Weight"
        }

    def test_get_all_vitals_schema(self, isolated_database):
        isolated_database.add_vital_reading("2026-09-23", "Pulse", 70, None, "09:00 AM")
        assert set(isolated_database.get_all_vitals()[0]) == {
            "id", "log_date", "vital_type", "value1", "value2",
            "reading_time", "notes", "created_at"
        }

    def test_get_all_vitals_persists_after_reopen(self, isolated_database):
        isolated_database.add_vital_reading(
            "2026-09-23", "Weight", 65.5, None, "09:00 AM"
        )
        path = isolated_database.path
        isolated_database.conn.close()
        isolated_database.conn = sqlite3.connect(path)
        assert len(isolated_database.get_all_vitals()) == 1
