from pathlib import Path
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.integration

import db
import main
import screens.calendar_screen as calendar_mod
import screens.events_screen as events_mod
import screens.export_screen as export_mod
import screens.home_screen as home_mod
import screens.medication_screen as medication_mod
import screens.notes_screen as notes_mod
import screens.sugar_screen as sugar_mod
import screens.vitals_screen as vitals_mod
from screens.calendar_screen import CalendarScreen
from screens.events_screen import EventsScreen
from screens.export_screen import ExportScreen
from screens.home_screen import HomeScreen
from screens.medication_screen import MedicationScreen
from screens.notes_screen import NotesScreen
from screens.sugar_screen import SugarScreen
from screens.vitals_screen import VitalsScreen


class CapturedDialog:
    instances = []

    def __init__(self, **kwargs):
        self.title = kwargs.get("title", "")
        self.text = kwargs.get("text", "")
        self.content_cls = kwargs.get("content_cls")
        self.buttons = kwargs.get("buttons", [])
        self.dismissed = False
        self.opened = False
        CapturedDialog.instances.append(self)

    def open(self):
        self.opened = True

    def dismiss(self):
        self.dismissed = True


def button(dialog, text):
    return next(b for b in dialog.buttons if b.text == text)


def field(content, hint):
    return next(w for w in content.children if getattr(w, "hint_text", None) == hint)


@pytest.fixture
def integration_db(isolated_database, monkeypatch):
    monkeypatch.setattr(
        db.Database,
        "instance",
        classmethod(lambda cls: isolated_database),
    )
    return isolated_database


@pytest.fixture
def dialogs(monkeypatch):
    CapturedDialog.instances.clear()
    for module in (
        sugar_mod,
        vitals_mod,
        medication_mod,
        notes_mod,
        events_mod,
        calendar_mod,
        home_mod,
        export_mod,
    ):
        monkeypatch.setattr(module, "MDDialog", CapturedDialog)
    return CapturedDialog


@pytest.fixture
def stable_time(monkeypatch):
    monkeypatch.setattr(sugar_mod, "bind_time_field", lambda _field: None)
    monkeypatch.setattr(vitals_mod, "bind_time_field", lambda _field: None)
    monkeypatch.setattr(sugar_mod, "now_12h", lambda: "08:00 AM")
    monkeypatch.setattr(vitals_mod, "now_12h", lambda: "09:00 AM")
    monkeypatch.setattr(medication_mod, "now_hhmm", lambda: "10:00")


def test_real_app_build_creates_all_screens_and_navigation(integration_db):
    app = main.BabyBloomApp()
    app._run_prepare()
    try:
        root = app.build()
        app.root = root
        sm = root.ids.sm

        assert {s.name for s in sm.screens} == {
            "home", "sugar", "vitals", "medications", "export", "events", "notes"
        }
        assert sm.current == "home"

        for name in ("sugar", "vitals", "medications", "export", "events", "notes", "home"):
            app.go_to(name)
            assert sm.current == name
    finally:
        app.stop()


def test_complete_daily_record_is_visible_across_all_history_screens(
    running_mdapp, integration_db
):
    day = "2026-09-23"
    integration_db.add_sugar_reading(day, "Before Breakfast", 95, "07:30", "20:30", True, "good")
    integration_db.add_vital_reading(day, "BP", 120, 80, "09:00 AM", "morning")
    integration_db.add_medication(day, "Iron", "1 tablet", "10:00", "after food")
    integration_db.add_event(day, "Ultrasound", "scan", "routine")
    integration_db.add_consultation_note(day, "Discussed hydration")

    sugar = SugarScreen()
    vitals = VitalsScreen()
    meds = MedicationScreen()
    events = EventsScreen()
    notes = NotesScreen()
    for screen in (sugar, vitals, meds):
        screen.current_date = day
    events.selected_date = day
    notes.selected_date = day

    sugar.refresh()
    vitals.refresh()
    meds.refresh()
    events.refresh()
    notes.refresh()

    assert len(sugar.ids.entry_box.children) == 1
    assert "95 mg/dL" in sugar.ids.entry_box.children[0].detail_text
    assert len(vitals.ids.entry_box.children) == 1
    assert "120/80" in vitals.ids.entry_box.children[0].detail_text
    assert len(meds.ids.med_list.children) == 1
    assert meds.ids.med_list.children[0].text == "Iron"
    assert events.ids.event_list.children[0].text == "Ultrasound"
    assert notes.ids.notes_list.children[0].text == "Discussed hydration"


def test_sugar_add_edit_delete_workflow(
    running_mdapp, integration_db, dialogs, stable_time
):
    screen = SugarScreen()
    screen.current_date = "2026-09-23"
    screen.refresh = Mock(wraps=screen.refresh)

    screen.open_entry_dialog()
    dialog = dialogs.instances[-1]
    field(dialog.content_cls, "Sugar value (mg/dL)").text = "110"
    field(dialog.content_cls, "Reading time (tap to set)").text = "08:00 AM"
    field(dialog.content_cls, "Previous meal time (tap to set)").text = "20:30"
    field(dialog.content_cls, "Notes (optional)").text = "morning"
    button(dialog, "SAVE").dispatch("on_release")

    row = integration_db.get_all_sugar()[0]
    assert row["value"] == 110
    assert row["slot"] == "Before Breakfast"
    assert row["fasting"] == 1

    screen.refresh.reset_mock()
    screen.open_entry_dialog(row)
    dialog = dialogs.instances[-1]
    field(dialog.content_cls, "Sugar value (mg/dL)").text = "125"
    field(dialog.content_cls, "Notes (optional)").text = "updated"
    button(dialog, "SAVE").dispatch("on_release")

    row = integration_db.get_all_sugar()[0]
    assert row["value"] == 125
    assert row["notes"] == "updated"

    screen.open_entry_dialog(row)
    button(dialogs.instances[-1], "DELETE").dispatch("on_release")
    assert integration_db.get_all_sugar() == []


def test_vitals_bp_and_single_value_workflows(
    running_mdapp, integration_db, dialogs, stable_time
):
    screen = VitalsScreen()
    screen.current_date = "2026-09-23"

    screen.open_entry_dialog("BP")
    dialog = dialogs.instances[-1]
    field(dialog.content_cls, "Systolic (mmHg)").text = "120"
    field(dialog.content_cls, "Diastolic (mmHg)").text = "80"
    field(dialog.content_cls, "Time (tap to set)").text = "09:00 AM"
    button(dialog, "SAVE").dispatch("on_release")

    screen.open_entry_dialog("O2")
    dialog = dialogs.instances[-1]
    field(dialog.content_cls, "SpO2 (%)").text = "98"
    field(dialog.content_cls, "Time (tap to set)").text = "10:00 AM"
    button(dialog, "SAVE").dispatch("on_release")

    rows = integration_db.get_vitals_for_date("2026-09-23")
    assert {r["vital_type"] for r in rows} == {"BP", "O2"}
    assert next(r for r in rows if r["vital_type"] == "BP")["value2"] == 80


def test_vitals_edit_delete_workflow(running_mdapp, integration_db, dialogs, stable_time):
    integration_db.add_vital_reading("2026-09-23", "Pulse", 75, None, "11:00 AM", "normal")
    row = integration_db.get_all_vitals()[0]
    screen = VitalsScreen()
    screen.current_date = "2026-09-23"

    screen.open_entry_dialog("Pulse", row)
    dialog = dialogs.instances[-1]
    field(dialog.content_cls, "Pulse (bpm)").text = "82"
    button(dialog, "SAVE").dispatch("on_release")
    assert integration_db.get_all_vitals()[0]["value1"] == 82

    screen.open_entry_dialog("Pulse", integration_db.get_all_vitals()[0])
    button(dialogs.instances[-1], "DELETE").dispatch("on_release")
    assert integration_db.get_all_vitals() == []


def test_medication_add_toggle_edit_delete_workflow(running_mdapp, integration_db, dialogs, stable_time):
    screen = MedicationScreen()
    screen.current_date = "2026-09-23"

    screen.open_entry_dialog()
    dialog = dialogs.instances[-1]
    field(dialog.content_cls, "Medication name").text = "Iron"
    field(dialog.content_cls, "Dosage (e.g. 500mg)").text = "1 tablet"
    field(dialog.content_cls, "Scheduled time (HH:MM)").text = "10:00"
    field(dialog.content_cls, "Notes (optional)").text = "after breakfast"
    button(dialog, "SAVE").dispatch("on_release")

    row = integration_db.get_medications_for_date("2026-09-23")[0]
    assert row["name"] == "Iron"
    assert row["taken"] == 0

    screen.toggle_taken(row)
    row = integration_db.get_medications_for_date("2026-09-23")[0]
    assert row["taken"] == 1

    screen.open_entry_dialog(row)
    dialog = dialogs.instances[-1]
    field(dialog.content_cls, "Dosage (e.g. 500mg)").text = "2 tablets"
    button(dialog, "SAVE").dispatch("on_release")
    row = integration_db.get_medications_for_date("2026-09-23")[0]
    assert row["dosage"] == "2 tablets"
    assert row["taken"] == 1

    screen.open_entry_dialog(row)
    button(dialogs.instances[-1], "DELETE").dispatch("on_release")
    assert integration_db.get_medications_for_date("2026-09-23") == []


def test_notes_add_delete_workflow(running_mdapp, integration_db, dialogs):
    screen = NotesScreen()
    screen.selected_date = "2026-09-23"
    screen.open_add_note()
    dialog = dialogs.instances[-1]
    field(dialog.content_cls, "Notes").text = "Doctor advised more rest"
    button(dialog, "SAVE").dispatch("on_release")

    row = integration_db.get_consultation_notes_for_date("2026-09-23")[0]
    assert row["notes"] == "Doctor advised more rest"

    screen.delete_note(row)
    button(dialogs.instances[-1], "DELETE").dispatch("on_release")
    assert integration_db.get_consultation_notes_for_date("2026-09-23") == []


def test_event_add_delete_workflow(running_mdapp, integration_db, dialogs):
    screen = EventsScreen()
    screen.selected_date = "2026-09-23"
    screen.open_add_event()
    dialog = dialogs.instances[-1]
    field(dialog.content_cls, "Title").text = "Ultrasound"
    field(dialog.content_cls, "Type").text = "scan"
    field(dialog.content_cls, "Notes (optional)").text = "Routine"
    button(dialog, "SAVE").dispatch("on_release")

    row = integration_db.get_events_for_date("2026-09-23")[0]
    assert row["title"] == "Ultrasound"
    assert row["event_type"] == "scan"

    screen.delete_event(row)
    button(dialogs.instances[-1], "DELETE").dispatch("on_release")
    assert integration_db.get_events_for_date("2026-09-23") == []


def test_calendar_summary_integrates_all_record_categories(running_mdapp, integration_db):
    day = "2026-09-23"
    integration_db.add_event(day, "Scan", "appointment", "clinic")
    integration_db.add_sugar_reading(day, "Before Breakfast", 100, "07:00", "20:00", True, "fasting")
    integration_db.add_vital_reading(day, "BP", 120, 80, "09:00", "bp note")
    integration_db.add_medication(day, "Iron", "1 tab", "10:00", "")
    integration_db.add_consultation_note(day, "Rest well")

    screen = CalendarScreen()
    screen.selected_date = day
    screen._refresh_summary(integration_db)

    texts = [child.children[-1].text for child in screen.ids.summary_list.children]
    joined = " | ".join(texts)
    assert "Event: Scan" in joined
    assert "Fasting sugar before breakfast: 100 mg/dL" in joined
    assert "Blood Pressure: 120.0/80.0 mmHg" in joined
    assert "Medication: Iron" in joined
    assert "Note: Rest well" in joined


def test_home_summary_integrates_all_record_categories(running_mdapp, integration_db, monkeypatch):
    day = "2026-09-23"
    integration_db.add_event(day, "Scan", "appointment", "clinic")
    integration_db.add_sugar_reading(day, "After Lunch", 130, "14:00", "13:00", False, "")
    integration_db.add_vital_reading(day, "Weight", 65, None, "18:00", "")
    integration_db.add_medication(day, "Vitamin", "1", "20:00", "")
    integration_db.add_consultation_note(day, "Feeling good")
    monkeypatch.setattr(home_mod, "today_str", lambda: day)

    screen = HomeScreen()
    screen.selected_date = day
    screen.refresh()

    assert "Event  •  Scan" in screen.summary_text
    assert "After Lunch  •  130 mg/dL" in screen.summary_text
    assert "Weight  •  65.0 kg" in screen.summary_text
    assert "Medication  •  Vitamin" in screen.summary_text
    assert "Note  •  Feeling good" in screen.summary_text


def test_home_health_summary_uses_real_database_values(running_mdapp, integration_db, monkeypatch):
    day = "2026-09-23"
    monkeypatch.setattr(home_mod, "today_str", lambda: day)
    integration_db.add_sugar_reading(day, "Before Breakfast", 90, "07:00", "20:00", True, "")
    integration_db.add_sugar_reading(day, "After Breakfast", 110, "09:00", "08:00", False, "")
    integration_db.add_vital_reading(day, "Weight", 60, None, "10:00", "")
    integration_db.add_vital_reading(day, "Weight", 62, None, "18:00", "")

    screen = HomeScreen()
    screen._average_key = "sugar"
    screen._trend_key = "sugar"
    screen._trend_unit = "days"
    screen._trend_amount = 7
    screen._refresh_health_summary()

    assert screen.average_reading_value == "100.0 mg/dL"
    assert screen.trend_axis_text != "No readings available for this range"
    assert "23 Sep" in screen.trend_axis_text


def test_home_quick_add_routes_to_correct_real_screens(running_mdapp, integration_db, monkeypatch):
    app = main.BabyBloomApp()
    app._run_prepare()
    try:
        root = app.build()
        app.root = root
        home = root.ids.sm.get_screen("home")
        home.selected_date = "2026-09-23"

        targets = {
            "sugar": "open_entry_dialog",
            "vitals": "open_type_chooser",
            "medications": "open_entry_dialog",
            "events": "open_add_event",
            "notes": "open_add_note",
        }
        for name, method in targets.items():
            screen = root.ids.sm.get_screen(name)
            setattr(screen, method, Mock())

        home._quick_add_sugar()
        home._quick_add_vitals()
        home._quick_add_medication()
        home._quick_add_event()
        home._quick_add_note()

        assert root.ids.sm.get_screen("sugar").current_date == "2026-09-23"
        assert root.ids.sm.get_screen("vitals").current_date == "2026-09-23"
        assert root.ids.sm.get_screen("medications").current_date == "2026-09-23"
        assert root.ids.sm.get_screen("events").selected_date == "2026-09-23"
        assert root.ids.sm.get_screen("notes").selected_date == "2026-09-23"
        for name, method in targets.items():
            getattr(root.ids.sm.get_screen(name), method).assert_called_once()
    finally:
        app.stop()


def test_export_pdf_reads_real_database_and_combines_categories(
    running_mdapp, integration_db, isolated_export_directory, monkeypatch
):
    day = "2026-09-23"
    integration_db.add_sugar_reading(day, "Before Breakfast", 95, "07:30", "20:00", True, "")
    integration_db.add_vital_reading(day, "BP", 120, 80, "09:00", "")
    integration_db.add_medication(day, "Iron", "1", "10:00", "")
    integration_db.add_event(day, "Scan", "appointment", "")
    integration_db.add_consultation_note(day, "Rest")
    monkeypatch.setattr(export_mod, "get_export_dir", lambda: str(isolated_export_directory))

    from utils import export_utils
    monkeypatch.setattr(export_utils, "get_export_dir", lambda: str(isolated_export_directory))

    path = export_utils.export_selected_reports_to_pdf([
        {"category": "sugar", "label": "Blood Sugar", "start": day, "end": day},
        {"category": "vitals", "label": "Vitals", "start": day, "end": day},
        {"category": "medications", "label": "Medication", "start": day, "end": day},
        {"category": "calendar", "label": "Event", "start": day, "end": day},
        {"category": "consultation", "label": "Note", "start": day, "end": day},
    ], filename="integration_report.pdf")

    assert Path(path).is_file()
    assert Path(path).stat().st_size > 0
    assert Path(path).parent == Path(isolated_export_directory)


def test_export_screen_selection_and_generation_workflow(
    running_mdapp, integration_db, isolated_export_directory, monkeypatch
):
    day = "2026-09-23"
    integration_db.add_sugar_reading(day, "Before Breakfast", 100, "07:00", "20:00", True, "")

    screen = ExportScreen()
    monkeypatch.setattr(export_mod, "get_export_dir", lambda: str(isolated_export_directory))
    monkeypatch.setattr(export_mod, "save_to_public_downloads", lambda *_args: None)
    notifications = []
    monkeypatch.setattr(screen, "_notify", notifications.append)

    screen._select_reading("sugar", "Blood Sugar")
    screen.start_date_label = day
    screen.end_date_label = day
    screen.add_report()

    assert len(screen.report_selections) == 1
    screen.generate_pdf()

    assert screen.report_selections == []
    assert screen.generated_pdf_path is not None
    assert Path(screen.generated_pdf_path).is_file()
    assert any("PDF generated successfully" in message for message in notifications)


def test_export_screen_rejects_duplicate_selection_and_clear_removes_it(
    running_mdapp, integration_db
):
    screen = ExportScreen()
    screen._select_reading("sugar", "Blood Sugar")
    screen.start_date_label = "2026-09-23"
    screen.end_date_label = "2026-09-23"
    screen.add_report()
    screen.selected_reading = "sugar"
    screen.selected_reading_label = "Blood Sugar"
    screen.start_date_label = "2026-09-23"
    screen.end_date_label = "2026-09-23"
    screen.add_report()
    assert len(screen.report_selections) == 1

    screen.clear_selection()
    assert screen.report_selections == []


def test_date_range_isolated_between_history_and_export(integration_db, isolated_export_directory, monkeypatch):
    integration_db.add_sugar_reading("2026-09-22", "Before Breakfast", 90, "07:00", "20:00", True, "old")
    integration_db.add_sugar_reading("2026-09-23", "Before Breakfast", 100, "07:00", "20:00", True, "current")
    integration_db.add_sugar_reading("2026-09-24", "Before Breakfast", 110, "07:00", "20:00", True, "new")

    rows = integration_db.get_sugar_range("2026-09-23", "2026-09-23")
    assert [r["value"] for r in rows] == [100]

    from utils import export_utils
    monkeypatch.setattr(export_utils, "get_export_dir", lambda: str(isolated_export_directory))
    path = export_utils.export_selected_reports_to_pdf([
        {"category": "sugar", "label": "Blood Sugar", "start": "2026-09-23", "end": "2026-09-23"}
    ], filename="range_report.pdf")
    assert Path(path).is_file()


def test_multiple_readings_same_day_survive_cross_screen_refresh(running_mdapp, integration_db):
    day = "2026-09-23"
    integration_db.add_sugar_reading(day, "Before Breakfast", 90, "07:00", "20:00", True, "")
    integration_db.add_sugar_reading(day, "After Breakfast", 120, "09:00", "08:00", False, "")
    integration_db.add_vital_reading(day, "Pulse", 72, None, "10:00", "")
    integration_db.add_vital_reading(day, "Pulse", 76, None, "18:00", "")

    sugar = SugarScreen()
    vitals = VitalsScreen()
    sugar.current_date = day
    vitals.current_date = day
    sugar.refresh()
    vitals.refresh()

    assert len(sugar.ids.entry_box.children) == 2
    assert len(vitals.ids.entry_box.children) == 2
    assert len(integration_db.get_sugar_for_date(day)) == 2
    assert len(integration_db.get_vitals_for_date(day)) == 2


def test_delete_one_record_does_not_remove_other_categories(
    running_mdapp, integration_db, dialogs, stable_time
):
    day = "2026-09-23"
    integration_db.add_sugar_reading(day, "Before Breakfast", 90, "07:00", "20:00", True, "")
    integration_db.add_vital_reading(day, "Pulse", 72, None, "10:00", "")
    integration_db.add_medication(day, "Iron", "1", "11:00", "")

    sugar = SugarScreen()
    sugar.current_date = day
    row = integration_db.get_sugar_for_date(day)[0]
    sugar.open_entry_dialog(row)
    button(dialogs.instances[-1], "DELETE").dispatch("on_release")

    assert integration_db.get_sugar_for_date(day) == []
    assert len(integration_db.get_vitals_for_date(day)) == 1
    assert len(integration_db.get_medications_for_date(day)) == 1


def test_shared_time_input_is_attached_by_sugar_and_vitals_dialogs(
    running_mdapp, integration_db, dialogs, stable_time
):
    sugar = SugarScreen()
    sugar.current_date = "2026-09-23"
    sugar.open_entry_dialog()
    sugar_fields = [w for w in dialogs.instances[-1].content_cls.children if hasattr(w, "input_filter")]

    vitals = VitalsScreen()
    vitals.current_date = "2026-09-23"
    vitals.open_entry_dialog("Pulse")
    vital_fields = [w for w in dialogs.instances[-1].content_cls.children if hasattr(w, "input_filter")]

    assert len(sugar_fields) >= 3
    assert len(vital_fields) >= 2
    assert callable(field(dialogs.instances[-2].content_cls, "Reading time (tap to set)").input_filter)
    assert callable(field(dialogs.instances[-2].content_cls, "Previous meal time (tap to set)").input_filter)
    assert callable(field(dialogs.instances[-1].content_cls, "Time (tap to set)").input_filter)
