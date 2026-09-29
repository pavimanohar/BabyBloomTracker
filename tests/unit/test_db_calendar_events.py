import sqlite3
import pytest


class TestCalendarEvents:
    def test_add_event_normal(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Doctor appointment")
        rows = isolated_database.get_events_for_date("2026-09-23")
        assert len(rows) == 1 and rows[0]["title"] == "Doctor appointment"

    def test_add_event_all_supplied_fields(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Scan", "scan", "Growth scan")
        row = isolated_database.get_events_for_date("2026-09-23")[0]
        assert row["event_date"] == "2026-09-23"
        assert row["title"] == "Scan"
        assert row["event_type"] == "scan"
        assert row["notes"] == "Growth scan"
        assert row["created_at"] is not None

    def test_add_event_default_event_type(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Appointment")
        assert isolated_database.get_events_for_date("2026-09-23")[0]["event_type"] == "appointment"

    def test_add_event_empty_event_type(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Event", "")
        assert isolated_database.get_events_for_date("2026-09-23")[0]["event_type"] == ""

    def test_add_event_none_event_type(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Event", None)
        assert isolated_database.get_events_for_date("2026-09-23")[0]["event_type"] is None

    def test_add_event_empty_notes(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Event", notes="")
        assert isolated_database.get_events_for_date("2026-09-23")[0]["notes"] == ""

    def test_add_event_none_notes(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Event", notes=None)
        assert isolated_database.get_events_for_date("2026-09-23")[0]["notes"] is None

    def test_add_event_empty_title_accepted(self, isolated_database):
        isolated_database.add_event("2026-09-23", "")
        assert isolated_database.get_events_for_date("2026-09-23")[0]["title"] == ""

    def test_add_event_none_title_rejected(self, isolated_database):
        with pytest.raises(sqlite3.IntegrityError):
            isolated_database.add_event("2026-09-23", None)

    def test_add_event_none_date_rejected(self, isolated_database):
        with pytest.raises(sqlite3.IntegrityError):
            isolated_database.add_event(None, "Event")

    def test_add_event_unicode_title(self, isolated_database):
        title = "அம்மா மருத்துவர் 👩‍⚕️"
        isolated_database.add_event("2026-09-23", title)
        assert isolated_database.get_events_for_date("2026-09-23")[0]["title"] == title

    def test_add_event_unicode_notes(self, isolated_database):
        notes = "健康检查 — ✓ 💗"
        isolated_database.add_event("2026-09-23", "Event", notes=notes)
        assert isolated_database.get_events_for_date("2026-09-23")[0]["notes"] == notes

    def test_add_event_sql_like_text(self, isolated_database):
        title = "Robert'); DROP TABLE calendar_events; --"
        notes = "100% _ test ?"
        isolated_database.add_event("2026-09-23", title, "other", notes)
        row = isolated_database.get_events_for_date("2026-09-23")[0]
        assert row["title"] == title and row["notes"] == notes
        assert len(isolated_database.get_events_for_date("2026-09-23")) == 1

    def test_add_event_very_long_title(self, isolated_database):
        title = "T" * 100_000
        isolated_database.add_event("2026-09-23", title)
        assert isolated_database.get_events_for_date("2026-09-23")[0]["title"] == title

    def test_add_event_very_long_notes(self, isolated_database):
        notes = "N" * 100_000
        isolated_database.add_event("2026-09-23", "Event", notes=notes)
        assert isolated_database.get_events_for_date("2026-09-23")[0]["notes"] == notes

    def test_add_duplicate_events_allowed(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Appointment")
        isolated_database.add_event("2026-09-23", "Appointment")
        rows = isolated_database.get_events_for_date("2026-09-23")
        assert len(rows) == 2 and rows[0]["id"] < rows[1]["id"]

    def test_add_multiple_events_same_date(self, isolated_database):
        for title in ["A", "B", "C"]:
            isolated_database.add_event("2026-09-23", title)
        assert [r["title"] for r in isolated_database.get_events_for_date("2026-09-23")] == ["A", "B", "C"]

    def test_add_event_commit_survives_reopen(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Persistent")
        path = isolated_database.path
        isolated_database.conn.close()
        isolated_database.conn = sqlite3.connect(path)
        assert isolated_database.get_events_for_date("2026-09-23")[0]["title"] == "Persistent"

    def test_delete_existing_event(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Delete me")
        event_id = isolated_database.get_events_for_date("2026-09-23")[0]["id"]
        isolated_database.delete_event(event_id)
        assert isolated_database.get_events_for_date("2026-09-23") == []

    def test_delete_one_of_multiple_events(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Keep")
        isolated_database.add_event("2026-09-23", "Delete")
        rows = isolated_database.get_events_for_date("2026-09-23")
        isolated_database.delete_event(rows[1]["id"])
        assert [r["title"] for r in isolated_database.get_events_for_date("2026-09-23")] == ["Keep"]

    def test_delete_nonexistent_event(self, isolated_database):
        isolated_database.delete_event(999999)
        assert isolated_database.get_events_for_date("2026-09-23") == []

    def test_delete_same_event_twice(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Delete twice")
        event_id = isolated_database.get_events_for_date("2026-09-23")[0]["id"]
        isolated_database.delete_event(event_id)
        isolated_database.delete_event(event_id)
        assert isolated_database.get_events_for_date("2026-09-23") == []

    def test_deleted_event_absent_from_query(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Delete me")
        event_id = isolated_database.get_events_for_date("2026-09-23")[0]["id"]
        isolated_database.delete_event(event_id)
        assert all(r["id"] != event_id for r in isolated_database.get_events_for_date("2026-09-23"))

    def test_delete_does_not_affect_other_dates(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Today")
        isolated_database.add_event("2026-09-24", "Tomorrow")
        event_id = isolated_database.get_events_for_date("2026-09-23")[0]["id"]
        isolated_database.delete_event(event_id)
        assert [r["title"] for r in isolated_database.get_events_for_date("2026-09-24")] == ["Tomorrow"]

    def test_delete_persists_after_reopen(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Delete me")
        event_id = isolated_database.get_events_for_date("2026-09-23")[0]["id"]
        isolated_database.delete_event(event_id)
        path = isolated_database.path
        isolated_database.conn.close()
        isolated_database.conn = sqlite3.connect(path)
        assert isolated_database.get_events_for_date("2026-09-23") == []

    def test_get_events_for_date_matching(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Event")
        assert len(isolated_database.get_events_for_date("2026-09-23")) == 1

    def test_get_events_for_date_empty(self, isolated_database):
        assert isolated_database.get_events_for_date("2026-09-23") == []

    def test_get_events_for_date_filters_other_dates(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Today")
        isolated_database.add_event("2026-09-24", "Tomorrow")
        assert [r["title"] for r in isolated_database.get_events_for_date("2026-09-23")] == ["Today"]

    def test_get_events_for_date_ordered_by_id(self, isolated_database):
        for title in ["First", "Second", "Third"]:
            isolated_database.add_event("2026-09-23", title)
        rows = isolated_database.get_events_for_date("2026-09-23")
        assert [r["title"] for r in rows] == ["First", "Second", "Third"]
        assert [r["id"] for r in rows] == sorted(r["id"] for r in rows)

    def test_get_events_for_date_empty_string(self, isolated_database):
        assert isolated_database.get_events_for_date("") == []

    def test_get_events_for_date_none(self, isolated_database):
        assert isolated_database.get_events_for_date(None) == []

    def test_get_events_for_date_schema(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Event")
        assert set(isolated_database.get_events_for_date("2026-09-23")[0]) == {"id", "event_date", "title", "event_type", "notes", "created_at"}

    def test_get_events_for_date_event_type(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Scan", "scan")
        assert isolated_database.get_events_for_date("2026-09-23")[0]["event_type"] == "scan"

    def test_get_events_for_date_nullable_notes(self, isolated_database):
        isolated_database.add_event("2026-09-23", "Event", notes=None)
        assert isolated_database.get_events_for_date("2026-09-23")[0]["notes"] is None

    def test_get_events_for_date_sql_like_values(self, isolated_database):
        title = "%_literal"
        isolated_database.add_event("2026-09-23", title)
        assert isolated_database.get_events_for_date("2026-09-23")[0]["title"] == title

    def test_get_events_for_month_matching(self, isolated_database):
        isolated_database.add_event("2026-09-05", "September")
        isolated_database.add_event("2026-09-20", "September 2")
        assert [r["title"] for r in isolated_database.get_events_for_month(2026, 9)] == ["September", "September 2"]

    def test_get_events_for_month_empty(self, isolated_database):
        isolated_database.add_event("2026-08-31", "August")
        assert isolated_database.get_events_for_month(2026, 9) == []

    def test_get_events_for_month_first_day(self, isolated_database):
        isolated_database.add_event("2026-09-01", "First")
        assert [r["title"] for r in isolated_database.get_events_for_month(2026, 9)] == ["First"]

    def test_get_events_for_month_last_day(self, isolated_database):
        isolated_database.add_event("2026-09-30", "Last")
        assert [r["title"] for r in isolated_database.get_events_for_month(2026, 9)] == ["Last"]

    def test_get_events_for_month_excludes_previous_month(self, isolated_database):
        isolated_database.add_event("2026-08-31", "Previous")
        isolated_database.add_event("2026-09-01", "Current")
        assert [r["title"] for r in isolated_database.get_events_for_month(2026, 9)] == ["Current"]

    def test_get_events_for_month_excludes_next_month(self, isolated_database):
        isolated_database.add_event("2026-09-30", "Current")
        isolated_database.add_event("2026-10-01", "Next")
        assert [r["title"] for r in isolated_database.get_events_for_month(2026, 9)] == ["Current"]

    def test_get_events_for_month_multiple_events_same_day(self, isolated_database):
        isolated_database.add_event("2026-09-10", "A")
        isolated_database.add_event("2026-09-10", "B")
        assert [r["title"] for r in isolated_database.get_events_for_month(2026, 9)] == ["A", "B"]

    def test_get_events_for_month_ordered_by_event_date(self, isolated_database):
        for date, title in [("2026-09-20", "20th"), ("2026-09-02", "2nd"), ("2026-09-10", "10th")]:
            isolated_database.add_event(date, title)
        rows = isolated_database.get_events_for_month(2026, 9)
        assert [r["event_date"] for r in rows] == ["2026-09-02", "2026-09-10", "2026-09-20"]

    def test_get_events_for_month_same_date_contains_all(self, isolated_database):
        isolated_database.add_event("2026-09-10", "A")
        isolated_database.add_event("2026-09-10", "B")
        rows = isolated_database.get_events_for_month(2026, 9)
        assert {r["title"] for r in rows} == {"A", "B"}

    def test_get_events_for_month_january(self, isolated_database):
        isolated_database.add_event("2026-01-15", "January")
        isolated_database.add_event("2026-11-15", "November")
        assert [r["title"] for r in isolated_database.get_events_for_month(2026, 1)] == ["January"]

    def test_get_events_for_month_december(self, isolated_database):
        isolated_database.add_event("2026-12-15", "December")
        isolated_database.add_event("2027-01-15", "January")
        assert [r["title"] for r in isolated_database.get_events_for_month(2026, 12)] == ["December"]

    def test_get_events_for_month_year_padding(self, isolated_database):
        isolated_database.add_event("0026-09-15", "Padded year")
        assert [r["title"] for r in isolated_database.get_events_for_month(26, 9)] == ["Padded year"]

    def test_get_events_for_month_unusual_month_values(self, isolated_database):
        isolated_database.add_event("2026-00-15", "Zero month")
        isolated_database.add_event("2026-13-15", "Thirteen month")
        assert [r["title"] for r in isolated_database.get_events_for_month(2026, 0)] == ["Zero month"]
        assert [r["title"] for r in isolated_database.get_events_for_month(2026, 13)] == ["Thirteen month"]
