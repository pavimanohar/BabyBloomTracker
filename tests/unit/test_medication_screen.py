from unittest.mock import Mock
import pytest

import screens.medication_screen as mod
from screens.medication_screen import MedicationScreen


class FakeButton:
    def __init__(self, **kwargs):
        self.text = kwargs.get("text", "")
        self.on_release = kwargs.get("on_release")

    def dispatch(self, event="on_release"):
        if event != "on_release":
            raise KeyError(event)
        if self.on_release:
            return self.on_release(self)


class FakeDialog:
    instances = []

    def __init__(self, **kwargs):
        self.title = kwargs.get("title")
        self.type = kwargs.get("type")
        self.content_cls = kwargs.get("content_cls")
        self.buttons = kwargs.get("buttons", [])
        self.dismissed = False
        self.opened = False
        FakeDialog.instances.append(self)

    def open(self):
        self.opened = True

    def dismiss(self):
        self.dismissed = True


class FakePicker:
    instances = []

    def __init__(self, **_kwargs):
        self.bind_calls = []
        self.opened = False
        FakePicker.instances.append(self)

    def bind(self, **kwargs):
        self.bind_calls.append(kwargs)

    def open(self):
        self.opened = True


class FakeContent:
    """Minimal BoxLayout double that preserves Kivy's reverse children order."""

    def __init__(self, **kwargs):
        self.orientation = kwargs.get("orientation")
        self.spacing = kwargs.get("spacing")
        self.size_hint_y = kwargs.get("size_hint_y")
        self.height = kwargs.get("height")
        self.children = []

    def add_widget(self, widget, *args, **kwargs):
        self.children.insert(0, widget)


class FakeField:
    def __init__(self, **kwargs):
        self.text = kwargs.get("text", "")
        self.hint_text = kwargs.get("hint_text", "")


@pytest.fixture(autouse=True)
def reset_fakes():
    FakeDialog.instances.clear()
    FakePicker.instances.clear()


@pytest.fixture
def screen(running_mdapp, isolated_database):
    s = MedicationScreen()
    s.current_date = "2026-09-23"
    return s


def _patch_dialog_widgets(monkeypatch):
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    monkeypatch.setattr(mod, "MDFlatButton", FakeButton)
    monkeypatch.setattr(mod, "MDRaisedButton", FakeButton)
    monkeypatch.setattr(mod, "MDTextField", FakeField)
    monkeypatch.setattr(mod, "BoxLayout", FakeContent)


def _medication_dict(database, name):
    row = database.conn.execute(
        "SELECT * FROM medications WHERE name = ?", (name,)
    ).fetchone()
    cols = [
        d[0]
        for d in database.conn.execute(
            "SELECT * FROM medications LIMIT 0"
        ).description
    ]
    return dict(zip(cols, row))


def _find_icon_widget(widget):
    """Find the IconLeftWidget created by refresh()."""
    if hasattr(widget, "icon"):
        return widget
    for child in getattr(widget, "children", []):
        found = _find_icon_widget(child)
        if found is not None:
            return found
    return None


def test_on_pre_enter_sets_today_when_date_empty(
    monkeypatch, isolated_database, running_mdapp
):
    screen = MedicationScreen()
    screen.current_date = ""
    monkeypatch.setattr(mod, "today_str", lambda: "2026-09-25")
    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))

    screen.on_pre_enter()

    assert screen.current_date == "2026-09-25"
    assert calls == [True]


def test_on_pre_enter_preserves_existing_date(monkeypatch, running_mdapp):
    screen = MedicationScreen()
    screen.current_date = "2026-01-15"
    monkeypatch.setattr(
        mod, "today_str", lambda: pytest.fail("today_str should not be called")
    )
    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))

    screen.on_pre_enter()

    assert screen.current_date == "2026-01-15"
    assert calls == [True]


def test_open_date_picker_binds_and_opens(monkeypatch, running_mdapp):
    monkeypatch.setattr(mod, "MDDatePicker", FakePicker)
    screen = MedicationScreen()

    screen.open_date_picker()

    picker = FakePicker.instances[0]
    assert picker.opened is True
    assert len(picker.bind_calls) == 1
    callback = picker.bind_calls[0]["on_save"]
    assert callback.__self__ is screen
    assert callback.__func__ is MedicationScreen._date_selected


def test_date_selected_updates_date_and_refreshes(monkeypatch, running_mdapp):
    screen = MedicationScreen()
    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))

    class Value:
        def strftime(self, fmt):
            assert fmt == "%Y-%m-%d"
            return "2026-09-24"

    screen._date_selected(None, Value(), None)

    assert screen.current_date == "2026-09-24"
    assert calls == [True]


def test_refresh_empty_database_shows_empty_message(screen):
    screen.refresh()

    assert screen.date_label == "All medication history"
    assert len(screen.ids.med_list.children) == 1
    assert screen.ids.med_list.children[0].text == "No medications recorded yet."


def test_refresh_populates_taken_and_not_taken_medications(
    screen, isolated_database
):
    isolated_database.add_medication(
        "2026-09-23", "Vitamin D", "1000 IU", "09:00", "Morning"
    )
    isolated_database.add_medication(
        "2026-09-22", "Iron", "", "", ""
    )

    screen.refresh()

    assert screen.date_label == "All medication history"
    displayed = screen.ids.med_list.children
    assert [item.text for item in displayed] == ["Iron", "Vitamin D"]

    iron = next(item for item in displayed if item.text == "Iron")
    vitamin = next(item for item in displayed if item.text == "Vitamin D")

    assert iron.secondary_text == "2026-09-22  •  -  •  -"
    assert iron.tertiary_text == "  •  Not taken"
    assert _find_icon_widget(iron).icon == "circle-outline"

    assert vitamin.secondary_text == "2026-09-23  •  1000 IU  •  09:00"
    assert vitamin.tertiary_text == "Morning  •  Not taken"
    assert _find_icon_widget(vitamin).icon == "circle-outline"


def test_refresh_taken_medication_display_and_checkbox(
    screen, isolated_database
):
    isolated_database.add_medication(
        "2026-09-23", "Prenatal", "1 tablet", "08:00", "With breakfast"
    )
    med = isolated_database.conn.execute(
        "SELECT id FROM medications WHERE name = ?", ("Prenatal",)
    ).fetchone()
    isolated_database.set_medication_taken(med[0], True)

    screen.refresh()

    item = screen.ids.med_list.children[0]
    assert item.text == "Prenatal"
    assert item.tertiary_text == "With breakfast  •  Taken"
    assert _find_icon_widget(item).icon == "check-circle"


def test_refresh_item_release_opens_edit_dialog(
    monkeypatch, screen, isolated_database
):
    isolated_database.add_medication(
        "2026-09-23", "Tablet", "1", "10:00", "Note"
    )
    _patch_dialog_widgets(monkeypatch)

    screen.refresh()
    item = screen.ids.med_list.children[0]
    item.dispatch("on_release")

    assert len(FakeDialog.instances) == 1
    dialog = FakeDialog.instances[0]
    assert dialog.title == "Edit Medication"
    assert [b.text for b in dialog.buttons] == ["CANCEL", "DELETE", "SAVE"]
    assert dialog.opened is True


def test_refresh_checkbox_release_toggles_taken(
    monkeypatch, screen, isolated_database
):
    isolated_database.add_medication(
        "2026-09-23", "Tablet", "1", "10:00", ""
    )
    screen.refresh()
    item = screen.ids.med_list.children[0]
    checkbox = _find_icon_widget(item)
    assert checkbox is not None

    calls = []
    monkeypatch.setattr(screen, "toggle_taken", lambda med: calls.append(med))

    checkbox.dispatch("on_release")

    assert len(calls) == 1
    assert calls[0]["name"] == "Tablet"
    assert calls[0]["id"] is not None


def test_toggle_taken_false_to_true(monkeypatch, screen, isolated_database):
    isolated_database.add_medication(
        "2026-09-23", "Tablet", "1", "10:00", ""
    )
    med = _medication_dict(isolated_database, "Tablet")

    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))
    screen.toggle_taken(med)

    row = isolated_database.conn.execute(
        "SELECT taken FROM medications WHERE id = ?", (med["id"],)
    ).fetchone()
    assert row[0] == 1
    assert calls == [True]


def test_toggle_taken_true_to_false(monkeypatch, screen, isolated_database):
    isolated_database.add_medication(
        "2026-09-23", "Tablet", "1", "10:00", ""
    )
    med = _medication_dict(isolated_database, "Tablet")
    isolated_database.set_medication_taken(med["id"], True)
    med["taken"] = 1

    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))
    screen.toggle_taken(med)

    updated = isolated_database.conn.execute(
        "SELECT taken FROM medications WHERE id = ?", (med["id"],)
    ).fetchone()
    assert updated[0] == 0
    assert calls == [True]


def test_open_medication_dialog_empty_name_does_nothing(
    monkeypatch, running_mdapp, isolated_database
):
    _patch_dialog_widgets(monkeypatch)

    screen = MedicationScreen()
    screen.current_date = "2026-09-23"
    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))

    screen.open_entry_dialog()

    dialog = FakeDialog.instances[0]
    name_field = next(
        field for field in dialog.content_cls.children
        if field.hint_text == "Medication name"
    )
    name_field.text = "   "

    dialog.buttons[-1].dispatch("on_release")

    assert isolated_database.conn.execute(
        "SELECT COUNT(*) FROM medications"
    ).fetchone()[0] == 0
    assert dialog.dismissed is False
    assert calls == []


def test_open_medication_dialog_adds_new_medication(
    monkeypatch, running_mdapp, isolated_database
):
    _patch_dialog_widgets(monkeypatch)
    monkeypatch.setattr(mod, "now_hhmm", lambda: "11:22")

    screen = MedicationScreen()
    screen.current_date = "2026-09-23"
    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))

    screen.open_entry_dialog()

    dialog = FakeDialog.instances[0]
    fields = {
        field.hint_text: field
        for field in dialog.content_cls.children
    }
    name = fields["Medication name"]
    dosage = fields["Dosage (e.g. 500mg)"]
    time = fields["Scheduled time (HH:MM)"]
    notes = fields["Notes (optional)"]

    assert name.text == ""
    assert dosage.text == ""
    assert time.text == "11:22"
    assert notes.text == ""
    assert [b.text for b in dialog.buttons] == ["CANCEL", "SAVE"]

    name.text = "  Vitamin D  "
    dosage.text = "1000 IU"
    time.text = "09:30"
    notes.text = "Morning"

    dialog.buttons[-1].dispatch("on_release")

    row = isolated_database.conn.execute(
        "SELECT log_date, name, dosage, scheduled_time, notes FROM medications"
    ).fetchone()
    assert tuple(row) == (
        "2026-09-23", "Vitamin D", "1000 IU", "09:30", "Morning"
    )
    assert dialog.dismissed is True
    assert calls == [True]


def test_open_medication_dialog_cancel_dismisses(
    monkeypatch, running_mdapp, isolated_database
):
    _patch_dialog_widgets(monkeypatch)

    screen = MedicationScreen()
    screen.current_date = "2026-09-23"
    screen.open_entry_dialog()

    dialog = FakeDialog.instances[0]
    dialog.buttons[0].dispatch("on_release")

    assert dialog.dismissed is True
    assert isolated_database.conn.execute(
        "SELECT COUNT(*) FROM medications"
    ).fetchone()[0] == 0


def test_open_medication_dialog_updates_existing_medication(
    monkeypatch, running_mdapp, isolated_database
):
    isolated_database.add_medication(
        "2026-09-23", "Old Name", "1 tablet", "08:00", "Old note"
    )
    med = _medication_dict(isolated_database, "Old Name")
    _patch_dialog_widgets(monkeypatch)

    screen = MedicationScreen()
    screen.current_date = "2026-09-23"
    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))

    screen.open_entry_dialog(med)

    dialog = FakeDialog.instances[0]
    fields = {
        field.hint_text: field
        for field in dialog.content_cls.children
    }

    assert dialog.title == "Edit Medication"
    assert [b.text for b in dialog.buttons] == ["CANCEL", "DELETE", "SAVE"]
    assert fields["Medication name"].text == "Old Name"
    assert fields["Dosage (e.g. 500mg)"].text == "1 tablet"
    assert fields["Scheduled time (HH:MM)"].text == "08:00"
    assert fields["Notes (optional)"].text == "Old note"

    fields["Medication name"].text = "New Name"
    fields["Dosage (e.g. 500mg)"].text = "2 tablets"
    fields["Scheduled time (HH:MM)"].text = "20:00"
    fields["Notes (optional)"].text = "Updated"

    dialog.buttons[-1].dispatch("on_release")

    row = isolated_database.conn.execute(
        "SELECT name, dosage, scheduled_time, notes FROM medications WHERE id = ?",
        (med["id"],),
    ).fetchone()
    assert tuple(row) == ("New Name", "2 tablets", "20:00", "Updated")
    assert dialog.dismissed is True
    assert calls == [True]


def test_open_medication_dialog_deletes_existing_medication(
    monkeypatch, running_mdapp, isolated_database
):
    isolated_database.add_medication(
        "2026-09-23", "Delete Me", "1", "12:00", ""
    )
    med = _medication_dict(isolated_database, "Delete Me")
    _patch_dialog_widgets(monkeypatch)

    screen = MedicationScreen()
    screen.current_date = "2026-09-23"
    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))

    screen.open_entry_dialog(med)

    dialog = FakeDialog.instances[0]
    delete_button = next(
        b for b in dialog.buttons if b.text == "DELETE"
    )
    delete_button.dispatch("on_release")

    row = isolated_database.conn.execute(
        "SELECT * FROM medications WHERE id = ?", (med["id"],)
    ).fetchone()
    assert row is None
    assert dialog.dismissed is True
    assert calls == [True]


def test_open_medication_dialog_edit_cancel_preserves_medication(
    monkeypatch, running_mdapp, isolated_database
):
    isolated_database.add_medication(
        "2026-09-23", "Keep Me", "1", "12:00", "Keep"
    )
    med = _medication_dict(isolated_database, "Keep Me")
    _patch_dialog_widgets(monkeypatch)

    screen = MedicationScreen()
    screen.current_date = "2026-09-23"
    screen.open_entry_dialog(med)

    dialog = FakeDialog.instances[0]
    dialog.buttons[0].dispatch("on_release")

    row = isolated_database.conn.execute(
        "SELECT name, dosage, scheduled_time, notes FROM medications WHERE id = ?",
        (med["id"],),
    ).fetchone()
    assert tuple(row) == ("Keep Me", "1", "12:00", "Keep")
    assert dialog.dismissed is True


def test_open_medication_dialog_new_delete_closure_false_branch(
    monkeypatch, running_mdapp
):
    _patch_dialog_widgets(monkeypatch)
    screen = MedicationScreen()
    screen.current_date = "2026-09-23"
    screen.refresh = Mock()

    captured = []

    def tracer(frame, event, arg):
        if event == "return" and frame.f_code.co_name == "open_entry_dialog":
            captured.append(frame.f_locals.get("delete"))
        return tracer

    import sys
    old_trace = sys.gettrace()
    sys.settrace(tracer)
    try:
        screen.open_entry_dialog()
    finally:
        sys.settrace(old_trace)

    delete = captured[-1]
    assert delete is not None
    delete()

    screen.refresh.assert_called_once()
