from datetime import date, timedelta

import pytest
from kivy.app import App

pytestmark = pytest.mark.integration

from db import Database
from main import BabyBloomApp
from screens.events_screen import EventsScreen
from screens.home_screen import HomeScreen
from screens.medication_screen import MedicationScreen
from screens.notes_screen import NotesScreen
from screens.sugar_screen import SugarScreen
from screens.vitals_screen import VitalsScreen


@pytest.fixture
def real_baby_app(isolated_database):
    app = BabyBloomApp()
    app._run_prepare()
    root = app.build()
    app.root = root
    try:
        yield app
    finally:
        if App.get_running_app() is app:
            app.stop()


def _texts(widget_box):
    values = []
    for child in widget_box.children:
        for attr in ("text", "secondary_text", "title_text", "detail_text", "tertiary_text"):
            value = getattr(child, attr, None)
            if value:
                values.append(value)
    return values


def test_real_app_build_registers_every_production_screen(real_baby_app):
    sm = real_baby_app.root.ids.sm
    assert [screen.name for screen in sm.screens] == [
        "home", "sugar", "vitals", "medications", "export", "events", "notes"
    ]
    assert sm.current == "home"


def test_real_navigation_visits_every_screen_and_returns_home(real_baby_app):
    sm = real_baby_app.root.ids.sm
    for name in ("sugar", "vitals", "medications", "export", "events", "notes", "home"):
        real_baby_app.go_to(name)
        assert sm.current == name
    assert sm.get_screen("home") is real_baby_app.root.ids.sm.get_screen("home")


def test_database_persists_records_across_recreated_singleton(isolated_database):
    db = isolated_database
    db.add_sugar_reading("2026-09-20", "Before Breakfast", 101, "07:00 AM", "06:30 AM", True, "persist")
    db.add_vital_reading("2026-09-20", "Weight", 64.5, None, "08:00 AM", "persist")
    db.add_medication("2026-09-20", "Iron", "1 tablet", "09:00 AM", "persist")

    db.conn.close()
    Database._instance = None
    reopened = Database.instance()
    try:
        assert reopened.get_sugar_for_date("2026-09-20")[0]["value"] == 101.0
        assert reopened.get_vitals_for_date("2026-09-20")[0]["value1"] == 64.5
        assert reopened.get_medications_for_date("2026-09-20")[0]["name"] == "Iron"
    finally:
        reopened.conn.close()
        Database._instance = None


def test_sugar_screen_handles_multiple_meals_and_timings(real_baby_app):
    db = Database.instance()
    day = "2026-09-21"
    for index, slot in enumerate(("Before Breakfast", "After Breakfast", "Before Lunch", "After Lunch", "Before Dinner", "After Dinner")):
        db.add_sugar_reading(day, slot, 90 + index, "08:00 AM", "07:30 AM", slot.startswith("Before"))

    screen = real_baby_app.root.ids.sm.get_screen("sugar")
    screen.current_date = day
    screen.refresh()

    cards = [c for c in screen.ids.entry_box.children if hasattr(c, "title_text")]
    assert len(cards) == 6
    assert {c.title_text for c in cards} == {
        f"{day} — Before Breakfast", f"{day} — After Breakfast",
        f"{day} — Before Lunch", f"{day} — After Lunch",
        f"{day} — Before Dinner", f"{day} — After Dinner",
    }


def test_sugar_screen_refresh_reflects_database_update_and_delete(real_baby_app):
    db = Database.instance()
    day = "2026-09-22"
    db.add_sugar_reading(day, "Before Breakfast", 105, "07:00 AM", "06:30 AM", True)
    row = db.get_sugar_for_date(day)[0]
    screen = real_baby_app.root.ids.sm.get_screen("sugar")
    screen.current_date = day
    screen.refresh()
    assert any("105" in text for text in _texts(screen.ids.entry_box))

    db.update_sugar_reading(row["id"], value=110, notes="updated")
    screen.refresh()
    assert any("110" in text and "updated" in text for text in _texts(screen.ids.entry_box))

    db.delete_sugar_reading(row["id"])
    screen.refresh()
    assert any("No sugar readings recorded yet" in text for text in _texts(screen.ids.entry_box))


def test_vitals_screen_renders_all_supported_vital_types(real_baby_app):
    db = Database.instance()
    day = "2026-09-23"
    values = [("BP", 120, 80), ("O2", 98, None), ("Pulse", 72, None), ("Weight", 65.5, None)]
    for vital_type, value1, value2 in values:
        db.add_vital_reading(day, vital_type, value1, value2, "08:00 AM")

    screen = real_baby_app.root.ids.sm.get_screen("vitals")
    screen.current_date = day
    screen.refresh()
    cards = [c for c in screen.ids.entry_box.children if hasattr(c, "title_text")]
    assert len(cards) == 4
    rendered = "\n".join(_texts(screen.ids.entry_box))
    assert "Blood Pressure" in rendered
    assert "Oxygen" in rendered
    assert "Pulse" in rendered
    assert "Weight" in rendered


def test_vitals_screen_keeps_multiple_same_type_readings(real_baby_app):
    db = Database.instance()
    day = "2026-09-24"
    db.add_vital_reading(day, "Pulse", 70, None, "08:00 AM")
    db.add_vital_reading(day, "Pulse", 76, None, "12:00 PM")
    db.add_vital_reading(day, "Pulse", 81, None, "06:00 PM")

    screen = real_baby_app.root.ids.sm.get_screen("vitals")
    screen.current_date = day
    screen.refresh()
    rendered = "\n".join(_texts(screen.ids.entry_box))
    assert all(str(value) in rendered for value in (70, 76, 81))
    assert len([c for c in screen.ids.entry_box.children if hasattr(c, "title_text")]) == 3


def test_vitals_edit_and_delete_refresh_leave_other_types_intact(real_baby_app):
    db = Database.instance()
    day = "2026-09-25"
    db.add_vital_reading(day, "Pulse", 70, None, "08:00 AM")
    db.add_vital_reading(day, "Weight", 65, None, "08:05 AM")
    pulse = db.get_vitals_for_date(day)[0]
    weight = db.get_vitals_for_date(day)[1]

    db.update_vital_reading(pulse["id"], value1=74)
    screen = real_baby_app.root.ids.sm.get_screen("vitals")
    screen.current_date = day
    screen.refresh()
    rendered = "\n".join(_texts(screen.ids.entry_box))
    assert "74" in rendered and "65" in rendered

    db.delete_vital_reading(pulse["id"])
    screen.refresh()
    rendered = "\n".join(_texts(screen.ids.entry_box))
    assert "74" not in rendered
    assert "65" in rendered
    assert db.get_vitals_for_date(day)[0]["id"] == weight["id"]


def test_medication_screen_reflects_taken_state_after_refresh(real_baby_app):
    db = Database.instance()
    day = "2026-09-26"
    db.add_medication(day, "Vitamin D", "1 tablet", "09:00 AM")
    row = db.get_medications_for_date(day)[0]

    screen = real_baby_app.root.ids.sm.get_screen("medications")
    screen.selected_date = day
    screen.refresh()
    items = list(screen.ids.med_list.children)
    vitamin_d = next(item for item in items if item.text == "Vitamin D")
    assert "Not taken" in vitamin_d.tertiary_text

    db.set_medication_taken(row["id"], True)
    screen.refresh()
    items = list(screen.ids.med_list.children)
    vitamin_d = next(item for item in items if item.text == "Vitamin D")
    assert "Taken" in vitamin_d.tertiary_text


def test_medication_delete_does_not_remove_other_medications(real_baby_app):
    db = Database.instance()
    day = "2026-09-27"
    db.add_medication(day, "Iron", "1", "09:00 AM")
    db.add_medication(day, "Calcium", "1", "01:00 PM")
    rows = db.get_medications_for_date(day)
    iron = next(row for row in rows if row["name"] == "Iron")
    db.delete_medication(iron["id"])

    screen = real_baby_app.root.ids.sm.get_screen("medications")
    screen.selected_date = day
    screen.refresh()
    rendered = "\n".join(_texts(screen.ids.med_list))
    assert "Iron" not in rendered
    assert "Calcium" in rendered


def test_notes_screen_renders_multiline_and_special_characters(real_baby_app):
    db = Database.instance()
    day = "2026-09-28"
    note = "Doctor said: hydration & rest.\nFollow-up <next week> ✓"
    db.add_consultation_note(day, note)

    screen = real_baby_app.root.ids.sm.get_screen("notes")
    screen.selected_date = day
    screen.refresh()
    rendered = "\n".join(_texts(screen.ids.notes_list))
    assert "Doctor said: hydration & rest." in rendered
    assert "Follow-up <next week> ✓" in rendered


def test_events_screen_renders_optional_notes_and_type(real_baby_app):
    db = Database.instance()
    day = "2026-09-29"
    db.add_event(day, "Scan", "ultrasound", "Bring previous report")

    screen = real_baby_app.root.ids.sm.get_screen("events")
    screen.selected_date = day
    screen.refresh()
    rendered = "\n".join(_texts(screen.ids.event_list))
    assert "Scan" in rendered
    assert "ultrasound" in rendered
    assert "Bring previous report" in rendered


def test_calendar_selected_date_changes_summary(real_baby_app):
    db = Database.instance()
    day1 = "2026-09-10"
    day2 = "2026-09-11"
    db.add_event(day1, "Visit")
    db.add_event(day2, "Scan")

    screen = real_baby_app.root.ids.sm.get_screen("home")
    screen.selected_date = day1
    screen.refresh()
    assert "Visit" in screen.summary_text
    assert "Scan" not in screen.summary_text

    screen.selected_date = day2
    screen.refresh()
    assert "Scan" in screen.summary_text
    assert "Visit" not in screen.summary_text


def test_home_summary_contains_all_categories_after_refresh(real_baby_app):
    db = Database.instance()
    day = "2026-09-12"
    db.add_event(day, "Appointment")
    db.add_sugar_reading(day, "Before Breakfast", 99, "07:00 AM", "06:30 AM", True)
    db.add_vital_reading(day, "Pulse", 73, None, "08:00 AM")
    db.add_medication(day, "Iron", "1 tablet", "09:00 AM")
    db.add_consultation_note(day, "Remember hydration")

    screen = real_baby_app.root.ids.sm.get_screen("home")
    screen.selected_date = day
    screen.refresh()
    for expected in ("Appointment", "Before Breakfast", "99", "Pulse", "73", "Iron", "Remember hydration"):
        assert expected in screen.summary_text


def test_home_health_summary_calculates_average_from_real_database(real_baby_app):
    db = Database.instance()
    today = date.today()
    for offset, value in enumerate((70, 80, 90)):
        day = (today - timedelta(days=offset)).isoformat()
        db.add_vital_reading(day, "Pulse", value, None, "08:00 AM")

    screen = real_baby_app.root.ids.sm.get_screen("home")
    screen.selected_date = today.isoformat()
    screen._average_key = "pulse"
    screen._refresh_health_summary()
    assert screen.average_reading_value == "80.0 bpm"


def test_home_trend_range_uses_real_database_values(real_baby_app):
    db = Database.instance()
    today = date.today()
    for offset, value in enumerate((70, 75, 80)):
        day = (today - timedelta(days=offset)).isoformat()
        db.add_vital_reading(day, "Pulse", value, None, "08:00 AM")

    screen = real_baby_app.root.ids.sm.get_screen("home")
    screen.selected_date = today.isoformat()
    screen._trend_key = "pulse"
    screen._trend_unit = "days"
    screen._trend_amount = 3
    screen._refresh_health_summary()
    assert screen.trend_axis_text != "No readings available for this range"
    assert len(screen.ids.trend_plot.labels) == 3
    assert screen.ids.trend_plot.values == [80.0, 75.0, 70.0]


def test_home_empty_health_summary_is_explicit(real_baby_app):
    screen = real_baby_app.root.ids.sm.get_screen("home")
    screen.selected_date = "1900-01-01"
    screen.refresh()
    assert screen.average_reading_value == "No readings in the last 7 days"
    assert screen.trend_axis_text == "No readings available for this range"


def test_all_history_screens_show_empty_state_on_clean_database(real_baby_app):
    sm = real_baby_app.root.ids.sm
    cases = [
        ("sugar", "entry_box", "No sugar readings recorded yet"),
        ("vitals", "entry_box", "No vital readings recorded yet"),
        ("medications", "med_list", "No medications recorded yet"),
        ("events", "event_list", "No events recorded yet"),
        ("notes", "notes_list", "No notes recorded yet"),
    ]
    for screen_name, box_id, expected in cases:
        screen = sm.get_screen(screen_name)
        if hasattr(screen, "current_date"):
            screen.current_date = "1900-01-01"
        if hasattr(screen, "selected_date"):
            screen.selected_date = "1900-01-01"
        screen.refresh()
        assert any(expected in text for text in _texts(screen.ids[box_id]))


def test_screen_navigation_preserves_database_backed_data(real_baby_app):
    db = Database.instance()
    day = "2026-09-13"
    db.add_sugar_reading(day, "After Lunch", 123, "01:30 PM", "01:00 PM", False)
    db.add_vital_reading(day, "O2", 97, None, "02:00 PM")

    sm = real_baby_app.root.ids.sm
    real_baby_app.go_to("sugar")
    sugar = sm.get_screen("sugar")
    sugar.current_date = day
    sugar.refresh()
    assert any("123" in text for text in _texts(sugar.ids.entry_box))

    real_baby_app.go_to("vitals")
    vitals = sm.get_screen("vitals")
    vitals.current_date = day
    vitals.refresh()
    assert any("97" in text for text in _texts(vitals.ids.entry_box))

    real_baby_app.go_to("home")
    home = sm.get_screen("home")
    home.selected_date = day
    home.refresh()
    assert "123" in home.summary_text
    assert "97" in home.summary_text


def test_calendar_screen_can_be_instantiated_and_refreshed_with_real_database(real_baby_app):
    db = Database.instance()
    day = date.today().isoformat()
    db.add_event(day, "Calendar integration")
def test_notes_and_events_are_isolated_when_both_exist(real_baby_app):
    db = Database.instance()
    day = "2026-09-14"
    db.add_event(day, "Event A")
    db.add_consultation_note(day, "Note A")
    event_id = db.get_events_for_date(day)[0]["id"]
    db.delete_event(event_id)

    events = db.get_events_for_date(day)
    notes = db.get_consultation_notes_for_date(day)
    assert events == []
    assert len(notes) == 1
    assert notes[0]["notes"] == "Note A"
