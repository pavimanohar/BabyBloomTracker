from datetime import date, timedelta
from pathlib import Path

import pytest

from db import Database
from utils.export_utils import export_combined_to_pdf


pytestmark = pytest.mark.scenario


def _texts(widget_box):
    values = []
    for child in widget_box.children:
        for attr in (
            "text",
            "secondary_text",
            "tertiary_text",
            "title_text",
            "detail_text",
        ):
            value = getattr(child, attr, None)
            if value:
                values.append(value)
    return values


def test_journey_daily_health_logging_to_home(real_baby_app):
    db = Database.instance()
    day = "2026-10-01"

    db.add_sugar_reading(day, "Before Breakfast", 101, "07:00 AM", "06:30 AM", True)
    db.add_vital_reading(day, "BP", 120, 80, "08:00 AM")
    db.add_vital_reading(day, "Pulse", 72, None, "08:01 AM")
    db.add_vital_reading(day, "O2", 98, None, "08:02 AM")
    db.add_vital_reading(day, "Weight", 65.0, None, "08:03 AM")

    sm = real_baby_app.root.ids.sm
    real_baby_app.go_to("sugar")
    sugar = sm.get_screen("sugar")
    sugar.current_date = day
    sugar.refresh()
    assert any("101" in text for text in _texts(sugar.ids.entry_box))

    real_baby_app.go_to("vitals")
    vitals = sm.get_screen("vitals")
    vitals.current_date = day
    vitals.refresh()
    rendered = "\n".join(_texts(vitals.ids.entry_box))
    assert all(value in rendered for value in ("Blood Pressure", "Pulse", "Oxygen", "Weight"))

    real_baby_app.go_to("home")
    home = sm.get_screen("home")
    home.selected_date = day
    home.refresh()
    assert home.selected_date == day


def test_journey_medication_taken_and_persisted_across_navigation(real_baby_app):
    db = Database.instance()
    day = "2026-10-02"
    db.add_medication(day, "Prenatal Vitamin", "1 tablet", "09:00 AM")
    row = db.get_medications_for_date(day)[0]

    sm = real_baby_app.root.ids.sm
    real_baby_app.go_to("medications")
    medications = sm.get_screen("medications")
    medications.refresh()
    item = next(item for item in medications.ids.med_list.children if item.text == "Prenatal Vitamin")
    assert "Not taken" in item.tertiary_text

    medications.toggle_taken(row)
    item = next(item for item in medications.ids.med_list.children if item.text == "Prenatal Vitamin")
    assert "Taken" in item.tertiary_text
    assert db.get_medications_for_date(day)[0]["taken"] == 1

    real_baby_app.go_to("home")
    real_baby_app.go_to("medications")
    medications.refresh()
    item = next(item for item in medications.ids.med_list.children if item.text == "Prenatal Vitamin")
    assert "Taken" in item.tertiary_text


def test_journey_consultation_note_and_vitals_survive_revisit(real_baby_app):
    db = Database.instance()
    day = "2026-10-03"
    note = "Consultation: hydration advised.\nFollow-up in one week."
    db.add_consultation_note(day, note)
    db.add_vital_reading(day, "Weight", 64.5, None, "10:00 AM")

    sm = real_baby_app.root.ids.sm
    real_baby_app.go_to("notes")
    notes = sm.get_screen("notes")
    notes.selected_date = day
    notes.refresh()
    assert any("hydration advised" in text and "Follow-up" in text for text in _texts(notes.ids.notes_list))

    real_baby_app.go_to("vitals")
    vitals = sm.get_screen("vitals")
    vitals.current_date = day
    vitals.refresh()
    assert any("64.5" in text for text in _texts(vitals.ids.entry_box))

    real_baby_app.go_to("notes")
    notes.refresh()
    assert any("hydration advised" in text for text in _texts(notes.ids.notes_list))


def test_journey_event_and_note_remain_independent(real_baby_app):
    db = Database.instance()
    day = "2026-10-04"
    db.add_event(day, "Hospital", "Routine check", "Carry reports")
    db.add_consultation_note(day, "Doctor discussion completed")

    sm = real_baby_app.root.ids.sm
    real_baby_app.go_to("events")
    events = sm.get_screen("events")
    events.selected_date = day
    events.refresh()
    assert any("Hospital" in text for text in _texts(events.ids.event_list))
    assert any("Carry reports" in text for text in _texts(events.ids.event_list))

    real_baby_app.go_to("notes")
    notes = sm.get_screen("notes")
    notes.selected_date = day
    notes.refresh()
    assert any("Doctor discussion completed" in text for text in _texts(notes.ids.notes_list))

    db.delete_event(db.get_events_for_date(day)[0]["id"])
    events.refresh()
    assert any("No events recorded yet" in text for text in _texts(events.ids.event_list))
    assert db.get_consultation_notes_for_date(day)[0]["notes"] == "Doctor discussion completed"


def test_journey_full_day_record_reaches_home_calendar_and_export(real_baby_app, tmp_path):
    db = Database.instance()
    day = "2026-10-05"
    db.add_sugar_reading(day, "After Lunch", 118, "02:00 PM", "01:30 PM", False, "Good")
    db.add_vital_reading(day, "BP", 118, 78, "02:10 PM")
    db.add_medication(day, "Iron", "1 tablet", "03:00 PM", "After food")
    db.add_event(day, "Doctor", "Follow-up", "Bring reports")
    db.add_consultation_note(day, "Everything stable")

    sm = real_baby_app.root.ids.sm
    real_baby_app.go_to("home")
    home = sm.get_screen("home")
    home.selected_date = day
    home.refresh()

    real_baby_app.go_to("export")
    export = sm.get_screen("export")
    assert export is not None

    records = {
        "sugar": db.get_sugar_for_date(day),
        "vitals": db.get_vitals_for_date(day),
        "medications": db.get_medications_for_date(day),
        "calendar": db.get_events_for_date(day),
        "consultation": db.get_consultation_notes_for_date(day),
    }
    output = tmp_path / "full_day.pdf"
    export_combined_to_pdf(records, ranges=[(day, day)], filename=str(output), title="BabyBloom Report")
    output = tmp_path / "full_day.pdf"
    assert output.exists()
    assert output.stat().st_size > 0


def test_journey_multi_day_history_displays_multiple_vital_dates(real_baby_app):
    db = Database.instance()
    day1 = "2026-10-06"
    day2 = "2026-10-07"
    db.add_sugar_reading(day1, "Before Breakfast", 99, "07:00 AM", "06:30 AM", True)
    db.add_sugar_reading(day2, "Before Breakfast", 111, "07:00 AM", "06:30 AM", True)
    db.add_vital_reading(day1, "Pulse", 70, None, "08:00 AM")
    db.add_vital_reading(day2, "Pulse", 82, None, "08:00 AM")

    sm = real_baby_app.root.ids.sm
    real_baby_app.go_to("sugar")
    sugar = sm.get_screen("sugar")
    sugar.current_date = day1
    sugar.refresh()
    rendered = "\n".join(_texts(sugar.ids.entry_box))
    assert "99" in rendered and "111" in rendered

    sugar.current_date = day2
    sugar.refresh()
    rendered = "\n".join(_texts(sugar.ids.entry_box))
    assert "111" in rendered and "99" in rendered

    real_baby_app.go_to("vitals")
    vitals = sm.get_screen("vitals")
    vitals.current_date = day1
    vitals.refresh()
    rendered = "\n".join(_texts(vitals.ids.entry_box))
    assert "70" in rendered and "82" in rendered


def test_journey_correct_reading_then_delete_removes_user_visible_record(real_baby_app):
    db = Database.instance()
    day = "2026-10-08"
    db.add_sugar_reading(day, "Before Breakfast", 150, "07:00 AM", "06:30 AM", True)
    row = db.get_sugar_for_date(day)[0]

    sm = real_baby_app.root.ids.sm
    real_baby_app.go_to("sugar")
    sugar = sm.get_screen("sugar")
    sugar.current_date = day
    sugar.refresh()
    assert any("150" in text for text in _texts(sugar.ids.entry_box))

    db.update_sugar_reading(row["id"], value=110, notes="corrected")
    sugar.refresh()
    rendered = "\n".join(_texts(sugar.ids.entry_box))
    assert "110" in rendered and "corrected" in rendered and "150" not in rendered

    db.delete_sugar_reading(row["id"])
    sugar.refresh()
    assert any("No sugar readings recorded yet" in text for text in _texts(sugar.ids.entry_box))


def test_journey_three_day_health_history_produces_real_trend_inputs(real_baby_app):
    db = Database.instance()
    today = date.today()
    values = (70, 75, 80)
    for offset, value in enumerate(values):
        day = (today - timedelta(days=offset)).isoformat()
        db.add_vital_reading(day, "Pulse", value, None, "08:00 AM")

    sm = real_baby_app.root.ids.sm
    real_baby_app.go_to("home")
    home = sm.get_screen("home")
    home.selected_date = today.isoformat()
    home._average_key = "pulse"
    home._trend_key = "pulse"
    home._trend_unit = "days"
    home._trend_amount = 3
    home._refresh_health_summary()

    assert home.average_reading_value == "75.0 bpm"
    assert len(home.ids.trend_plot.values) == 3
    assert home.ids.trend_plot.values == [80.0, 75.0, 70.0]

