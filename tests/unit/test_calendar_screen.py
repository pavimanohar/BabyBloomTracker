from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import screens.calendar_screen as mod
from screens.calendar_screen import DayCell, CalendarScreen


def test_daycell_sets_empty_text_for_zero(running_mdapp):
    cell = DayCell(0, lambda _: None)

    assert cell.day_num == 0
    assert cell.day_text == ""
    assert cell.bg_color == [1, 1, 1, 1]


def test_daycell_sets_today_style_and_callback(running_mdapp):
    seen = []

    cell = DayCell(
        12,
        seen.append,
        is_today=True,
        has_events=True,
    )

    assert cell.day_text == "12"
    assert cell.has_events is True
    assert tuple(cell.bg_color) == (0.98, 0.75, 0.83, 1)

    cell.dispatch("on_release")

    assert seen == [12]


def test_daycell_non_today_style(running_mdapp):
    cell = DayCell(
        12,
        lambda _: None,
        is_today=False,
    )

    assert tuple(cell.bg_color) == (1, 1, 1, 0.6)


def test_calendar_on_pre_enter_initializes_date(monkeypatch, running_mdapp):
    screen = CalendarScreen()
    screen.year = 0
    screen.month = 0

    monkeypatch.setattr(
        mod,
        "today_str",
        lambda: "2026-09-23",
    )

    screen.render_month = Mock()

    screen.on_pre_enter()

    assert (screen.year, screen.month) == (2026, 9)
    assert screen.selected_date == "2026-09-23"
    screen.render_month.assert_called_once()


def test_calendar_on_pre_enter_preserves_existing_month(
    monkeypatch,
    running_mdapp,
):
    screen = CalendarScreen()
    screen.year = 2025
    screen.month = 4
    screen.selected_date = "2025-04-15"

    monkeypatch.setattr(
        mod,
        "today_str",
        lambda: "2026-09-23",
    )

    screen.render_month = Mock()

    screen.on_pre_enter()

    assert (screen.year, screen.month) == (2025, 4)
    assert screen.selected_date == "2025-04-15"
    screen.render_month.assert_called_once()


@pytest.mark.parametrize(
    "year,month,delta,expected",
    [
        (2026, 9, 1, (2026, 10)),
        (2026, 12, 1, (2027, 1)),
        (2026, 1, -1, (2025, 12)),
        (2026, 9, -1, (2026, 8)),
    ],
)
def test_change_month_boundaries(
    running_mdapp,
    year,
    month,
    delta,
    expected,
):
    screen = CalendarScreen()
    screen.year = year
    screen.month = month
    screen.render_month = Mock()

    screen.change_month(delta)

    assert (screen.year, screen.month) == expected
    screen.render_month.assert_called_once()


def test_select_day_updates_selected_date(running_mdapp):
    screen = CalendarScreen()
    screen.year = 2026
    screen.month = 9
    screen.refresh_all = Mock()

    screen.select_day(7)

    assert screen.selected_date == "2026-09-07"
    screen.refresh_all.assert_called_once()


def test_summary_line_without_secondary(running_mdapp):
    screen = CalendarScreen()

    row = screen._summary_line("Hello")

    assert len(row.children) == 1
    assert row.children[0].text == "Hello"


def test_summary_line_with_secondary(running_mdapp):
    screen = CalendarScreen()

    row = screen._summary_line(
        "Hello",
        "Detail",
    )

    assert len(row.children) == 2

    texts = {child.text for child in row.children}

    assert texts == {"Hello", "Detail"}


def test_refresh_all_updates_label_and_summary(
    running_mdapp,
    monkeypatch,
):
    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"

    fake_db = Mock()

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: fake_db),
    )

    screen._refresh_summary = Mock()

    screen.refresh_all()

    assert screen.selected_label == "Records on 2026-09-23"
    screen._refresh_summary.assert_called_once_with(fake_db)


def test_refresh_summary_empty_data(running_mdapp):
    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"

    screen.ids.summary_list.clear_widgets()

    db = Mock()
    db.get_events_for_date.return_value = []
    db.get_sugar_for_date.return_value = []
    db.get_vitals_for_date.return_value = []
    db.get_medications_for_date.return_value = []
    db.get_consultation_notes_for_date.return_value = []

    screen._refresh_summary(db)

    texts = [
        child.text
        for row in screen.ids.summary_list.children
        for child in row.children
        if hasattr(child, "text")
    ]

    assert any(
        "Events: No events recorded" in text
        for text in texts
    )
    assert any(
        "Sugar: No reading recorded" in text
        for text in texts
    )
    assert any(
        "Vitals: No readings recorded" in text
        for text in texts
    )
    assert any(
        "Medications: No records recorded" in text
        for text in texts
    )
    assert any(
        "Notes: No notes recorded" in text
        for text in texts
    )


def test_refresh_summary_formats_all_record_types(running_mdapp):
    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"

    screen.ids.summary_list.clear_widgets()

    db = Mock()

    db.get_events_for_date.return_value = [
        {
            "title": "Scan",
            "notes": "Clinic",
        }
    ]

    db.get_sugar_for_date.return_value = [
        {
            "value": 105,
            "slot": "Before Breakfast",
            "fasting": 1,
            "reading_time": "08:00",
        },
        {
            "value": None,
            "slot": "After Lunch",
            "fasting": 0,
            "reading_time": "",
        },
    ]

    db.get_vitals_for_date.return_value = [
        {
            "vital_type": "BP",
            "value1": 120,
            "value2": 80,
            "reading_time": "09:00",
        },
        {
            "vital_type": "Weight",
            "value1": None,
            "value2": None,
            "reading_time": "",
        },
    ]

    db.get_medications_for_date.return_value = [
        {
            "name": "Iron",
            "dosage": "1 tab",
            "scheduled_time": "09:00",
            "taken": 1,
        },
    ]

    db.get_consultation_notes_for_date.return_value = [
        {
            "notes": "Feeling good",
        }
    ]

    screen._refresh_summary(db)

    texts = [
        child.text
        for row in screen.ids.summary_list.children
        for child in row.children
        if hasattr(child, "text")
    ]

    joined = "\n".join(texts)

    assert "Event: Scan" in joined
    assert "Fasting sugar before breakfast: 105 mg/dL" in joined
    assert "Sugar after lunch: -" in joined
    assert "Blood Pressure: 120/80 mmHg" in joined
    assert "Weight: -" in joined
    assert "Medication: Iron" in joined
    assert "Note: Feeling good" in joined


def test_refresh_summary_event_falls_back_to_event_type(
    running_mdapp,
):
    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"
    screen.ids.summary_list.clear_widgets()

    db = Mock()
    db.get_events_for_date.return_value = [
        {
            "title": "Appointment",
            "notes": "",
            "event_type": "appointment",
        }
    ]
    db.get_sugar_for_date.return_value = []
    db.get_vitals_for_date.return_value = []
    db.get_medications_for_date.return_value = []
    db.get_consultation_notes_for_date.return_value = []

    screen._refresh_summary(db)

    texts = [
        child.text
        for row in screen.ids.summary_list.children
        for child in row.children
        if hasattr(child, "text")
    ]

    assert "Event: Appointment" in texts
    assert "appointment" in texts


def test_refresh_summary_medication_not_taken(running_mdapp):
    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"
    screen.ids.summary_list.clear_widgets()

    db = Mock()
    db.get_events_for_date.return_value = []
    db.get_sugar_for_date.return_value = []
    db.get_vitals_for_date.return_value = []
    db.get_medications_for_date.return_value = [
        {
            "name": "Vitamin",
            "dosage": "1 tablet",
            "scheduled_time": "20:00",
            "taken": 0,
        }
    ]
    db.get_consultation_notes_for_date.return_value = []

    screen._refresh_summary(db)

    texts = [
        child.text
        for row in screen.ids.summary_list.children
        for child in row.children
        if hasattr(child, "text")
    ]

    joined = "\n".join(texts)

    assert "Medication: Vitamin" in joined
    assert "Not taken" in joined


def test_refresh_after_dialog_schedules_refresh(
    monkeypatch,
    running_mdapp,
):
    screen = CalendarScreen()

    scheduled = []

    monkeypatch.setattr(
        mod.Clock,
        "schedule_once",
        lambda callback, delay: scheduled.append(
            (callback, delay)
        ),
    )

    screen._refresh_after_dialog()

    assert len(scheduled) == 1
    assert scheduled[0][1] == 0.6


def test_refresh_after_dialog_callback_refreshes(
    monkeypatch,
    running_mdapp,
):
    screen = CalendarScreen()
    screen.refresh_all = Mock()

    scheduled = []

    monkeypatch.setattr(
        mod.Clock,
        "schedule_once",
        lambda callback, delay: scheduled.append(
            (callback, delay)
        ),
    )

    screen._refresh_after_dialog()

    callback, delay = scheduled[0]

    assert delay == 0.6

    callback()

    screen.refresh_all.assert_called_once()


def test_quick_add_sugar_sets_date_and_refreshes(
    running_mdapp,
):
    screen = CalendarScreen()

    target = Mock()

    screen.selected_date = "2026-09-23"
    screen.manager = SimpleNamespace(
        get_screen=lambda name: target
    )
    screen._refresh_after_dialog = Mock()

    screen.open_add_sugar()

    assert target.current_date == screen.selected_date
    target.open_entry_dialog.assert_called_once()
    screen._refresh_after_dialog.assert_called_once()


def test_quick_add_vitals_sets_date_and_refreshes(
    running_mdapp,
):
    screen = CalendarScreen()

    target = Mock()

    screen.selected_date = "2026-09-23"
    screen.manager = SimpleNamespace(
        get_screen=lambda name: target
    )
    screen._refresh_after_dialog = Mock()

    screen.open_add_vitals()

    assert target.current_date == screen.selected_date
    target.open_type_chooser.assert_called_once()
    screen._refresh_after_dialog.assert_called_once()


def test_quick_add_medication_sets_date_and_refreshes(
    running_mdapp,
):
    screen = CalendarScreen()

    target = Mock()

    screen.selected_date = "2026-09-23"
    screen.manager = SimpleNamespace(
        get_screen=lambda name: target
    )
    screen._refresh_after_dialog = Mock()

    screen.open_add_medication()

    assert target.current_date == screen.selected_date
    target.open_entry_dialog.assert_called_once()
    screen._refresh_after_dialog.assert_called_once()


class FakeDialog:
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.open_called = False
        self.dismiss_called = False
        FakeDialog.created.append(self)

    def open(self):
        self.open_called = True

    def dismiss(self):
        self.dismiss_called = True


def test_open_add_consultation_note_dialog(
    monkeypatch,
    running_mdapp,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"

    screen.open_add_consultation_note()

    assert len(FakeDialog.created) == 1

    dialog = FakeDialog.created[0]

    assert dialog.open_called is True
    assert dialog.kwargs["title"] == "Notes — 2026-09-23"
    assert dialog.kwargs["type"] == "custom"
    assert len(dialog.kwargs["buttons"]) == 2


def test_open_add_consultation_note_save_empty_is_ignored(
    monkeypatch,
    running_mdapp,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    fake_db = Mock()

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: fake_db),
    )

    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"

    screen.open_add_consultation_note()

    dialog = FakeDialog.created[0]
    content = dialog.kwargs["content_cls"]
    notes_field = content.children[0]

    notes_field.text = "   "

    save_button = dialog.kwargs["buttons"][1]
    save_button.dispatch("on_release")

    fake_db.add_consultation_note.assert_not_called()
    assert dialog.dismiss_called is False


def test_open_add_consultation_note_save_valid_note(
    monkeypatch,
    running_mdapp,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    fake_db = Mock()

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: fake_db),
    )

    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"
    screen.refresh_all = Mock()

    screen.open_add_consultation_note()

    dialog = FakeDialog.created[0]
    content = dialog.kwargs["content_cls"]
    notes_field = content.children[0]

    notes_field.text = "  Feeling good  "

    save_button = dialog.kwargs["buttons"][1]
    save_button.dispatch("on_release")

    fake_db.add_consultation_note.assert_called_once_with(
        "2026-09-23",
        "Feeling good",
    )
    assert dialog.dismiss_called is True
    screen.refresh_all.assert_called_once()


def test_open_add_event_builds_dialog(
    running_mdapp,
    monkeypatch,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"

    screen.open_add_event(None)

    assert len(FakeDialog.created) == 1

    dialog = FakeDialog.created[0]

    assert dialog.open_called is True
    assert dialog.kwargs["title"] == "Add Event"
    assert dialog.kwargs["type"] == "custom"
    assert len(dialog.kwargs["buttons"]) == 2


def test_open_add_event_save_empty_title_is_ignored(
    running_mdapp,
    monkeypatch,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    fake_db = Mock()

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: fake_db),
    )

    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"

    screen.open_add_event(None)

    dialog = FakeDialog.created[0]
    content = dialog.kwargs["content_cls"]

    fields = list(content.children)

    title_field = next(
        field
        for field in fields
        if field.hint_text.startswith("Title")
    )

    title_field.text = "   "

    save_button = dialog.kwargs["buttons"][1]
    save_button.dispatch("on_release")

    fake_db.add_event.assert_not_called()
    assert dialog.dismiss_called is False


def test_open_add_event_save_valid_event(
    running_mdapp,
    monkeypatch,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    fake_db = Mock()

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: fake_db),
    )

    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"
    screen.render_month = Mock()

    screen.open_add_event(None)

    dialog = FakeDialog.created[0]
    content = dialog.kwargs["content_cls"]

    fields = list(content.children)

    title_field = next(
        field
        for field in fields
        if field.hint_text.startswith("Title")
    )
    date_field = next(
        field
        for field in fields
        if field.hint_text.startswith("Date")
    )
    type_field = next(
        field
        for field in fields
        if field.hint_text.startswith("Type")
    )
    notes_field = next(
        field
        for field in fields
        if field.hint_text.startswith("Notes")
    )

    title_field.text = "Ultrasound"
    date_field.text = "2026-09-24"
    type_field.text = "scan"
    notes_field.text = "Clinic"

    save_button = dialog.kwargs["buttons"][1]
    save_button.dispatch("on_release")

    fake_db.add_event.assert_called_once_with(
        "2026-09-24",
        "Ultrasound",
        "scan",
        "Clinic",
    )

    assert dialog.dismiss_called is True
    screen.render_month.assert_called_once()


def test_open_add_event_save_uses_defaults_for_blank_optional_fields(
    running_mdapp,
    monkeypatch,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    fake_db = Mock()

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: fake_db),
    )

    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"
    screen.render_month = Mock()

    screen.open_add_event(None)

    dialog = FakeDialog.created[0]
    content = dialog.kwargs["content_cls"]

    fields = list(content.children)

    title_field = next(
        field
        for field in fields
        if field.hint_text.startswith("Title")
    )
    date_field = next(
        field
        for field in fields
        if field.hint_text.startswith("Date")
    )
    type_field = next(
        field
        for field in fields
        if field.hint_text.startswith("Type")
    )
    notes_field = next(
        field
        for field in fields
        if field.hint_text.startswith("Notes")
    )

    title_field.text = "Appointment"
    date_field.text = "   "
    type_field.text = "   "
    notes_field.text = "   "

    save_button = dialog.kwargs["buttons"][1]
    save_button.dispatch("on_release")

    fake_db.add_event.assert_called_once_with(
        "2026-09-23",
        "Appointment",
        "appointment",
        "",
    )

    assert dialog.dismiss_called is True
    screen.render_month.assert_called_once()


def test_confirm_delete_builds_dialog(
    running_mdapp,
    monkeypatch,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    screen = CalendarScreen()

    event = {
        "id": 1,
        "title": "Scan",
    }

    screen.confirm_delete(event)

    assert len(FakeDialog.created) == 1

    dialog = FakeDialog.created[0]

    assert dialog.open_called is True
    assert dialog.kwargs["title"] == "Delete this event?"
    assert dialog.kwargs["text"] == "Scan"
    assert len(dialog.kwargs["buttons"]) == 2


def test_confirm_delete_delete_callback(
    running_mdapp,
    monkeypatch,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    fake_db = Mock()

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: fake_db),
    )

    screen = CalendarScreen()
    screen.render_month = Mock()

    event = {
        "id": 42,
        "title": "Ultrasound",
    }

    screen.confirm_delete(event)

    dialog = FakeDialog.created[0]

    delete_button = dialog.kwargs["buttons"][1]
    delete_button.dispatch("on_release")

    fake_db.delete_event.assert_called_once_with(42)
    assert dialog.dismiss_called is True
    screen.render_month.assert_called_once()


def test_confirm_delete_note_builds_dialog(
    running_mdapp,
    monkeypatch,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    screen = CalendarScreen()

    note = {
        "id": 1,
        "notes": "Feeling good",
    }

    screen.confirm_delete_note(note)

    assert len(FakeDialog.created) == 1

    dialog = FakeDialog.created[0]

    assert dialog.open_called is True
    assert dialog.kwargs["title"] == "Delete this note?"
    assert dialog.kwargs["text"] == "Feeling good"
    assert len(dialog.kwargs["buttons"]) == 2


def test_confirm_delete_note_delete_callback(
    running_mdapp,
    monkeypatch,
):
    FakeDialog.created = []

    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    fake_db = Mock()

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: fake_db),
    )

    screen = CalendarScreen()
    screen.refresh_all = Mock()

    note = {
        "id": 42,
        "notes": "Consultation note",
    }

    screen.confirm_delete_note(note)

    dialog = FakeDialog.created[0]

    delete_button = dialog.kwargs["buttons"][1]
    delete_button.dispatch("on_release")

    fake_db.delete_consultation_note.assert_called_once_with(42)
    assert dialog.dismiss_called is True
    screen.refresh_all.assert_called_once()


def test_render_month_with_events(
    monkeypatch,
    running_mdapp,
):
    screen = CalendarScreen()
    screen.year = 2026
    screen.month = 9

    db = Mock()

    db.get_events_for_month.return_value = [
        {
            "event_date": "2026-09-23",
        }
    ]

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    screen.refresh_all = Mock()

    screen.render_month()

    assert screen.month_label == "September 2026"
    assert len(screen.ids.weekday_row.children) == 7
    assert len(screen.ids.day_grid.children) > 0

    screen.refresh_all.assert_called_once()


def test_render_month_without_events(
    monkeypatch,
    running_mdapp,
):
    screen = CalendarScreen()
    screen.year = 2026
    screen.month = 2

    db = Mock()
    db.get_events_for_month.return_value = []

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    screen.refresh_all = Mock()

    screen.render_month()

    assert screen.month_label == "February 2026"
    assert len(screen.ids.weekday_row.children) == 7
    assert len(screen.ids.day_grid.children) > 0

    screen.refresh_all.assert_called_once()


def test_refresh_summary_vital_without_second_value_covers_value2_false(running_mdapp):
    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"
    screen.ids.summary_list.clear_widgets()

    db = Mock()
    db.get_events_for_date.return_value = []
    db.get_sugar_for_date.return_value = []
    db.get_vitals_for_date.return_value = [
        {
            "vital_type": "Weight",
            "value1": 65,
            "value2": None,
            "reading_time": "",
        }
    ]
    db.get_medications_for_date.return_value = []
    db.get_consultation_notes_for_date.return_value = []

    screen._refresh_summary(db)

    texts = [
        child.text
        for row in screen.ids.summary_list.children
        for child in row.children
        if hasattr(child, "text")
    ]
    assert any("Weight: 65 kg" in text for text in texts)


@pytest.mark.parametrize(
    "method,args",
    [
        ("open_add_consultation_note", ()),
        ("open_add_event", (None,)),
    ],
)
def test_calendar_dialog_cancel_callbacks_are_executable(
    running_mdapp, monkeypatch, method, args
):
    FakeDialog.created = []
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    screen = CalendarScreen()
    screen.selected_date = "2026-09-23"
    getattr(screen, method)(*args)

    dialog = FakeDialog.created[-1]
    dialog.kwargs["buttons"][0].dispatch("on_release")
    assert dialog.dismiss_called is True


@pytest.mark.parametrize(
    "method,event",
    [
        ("confirm_delete", {"id": 1, "title": "Scan"}),
        ("confirm_delete_note", {"id": 2, "notes": "Feeling good"}),
    ],
)
def test_calendar_delete_dialog_cancel_callbacks_are_executable(
    running_mdapp, monkeypatch, method, event
):
    FakeDialog.created = []
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)

    screen = CalendarScreen()
    getattr(screen, method)(event)

    dialog = FakeDialog.created[-1]
    dialog.kwargs["buttons"][0].dispatch("on_release")
    assert dialog.dismiss_called is True
