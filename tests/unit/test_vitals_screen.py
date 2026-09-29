from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from kivymd.uix.button import MDFlatButton, MDRaisedButton

import screens.vitals_screen as mod
from screens.vitals_screen import (
    VitalEntryCard,
    VitalsScreen,
    VITAL_TYPES,
    VITAL_TYPE_ORDER,
)

def make_screen():
    screen = VitalsScreen()
    screen.ids["entry_box"] = Mock()
    return screen


# ============================================================================
# VitalEntryCard
# ============================================================================

def test_vital_entry_card_initializes_and_dispatches_callback(running_mdapp):
    callback = Mock()

    card = VitalEntryCard(callback)

    assert card._on_tap is callback

    card.dispatch_tap()

    callback.assert_called_once_with()


# ============================================================================
# VitalsScreen lifecycle / date
# ============================================================================

def test_on_pre_enter_sets_today_when_current_date_empty(running_mdapp):
    screen = make_screen()

    with patch.object(mod, "today_str", return_value="2026-09-24"), \
         patch.object(screen, "refresh") as refresh:

        screen.current_date = ""
        screen.on_pre_enter()

    assert screen.current_date == "2026-09-24"
    refresh.assert_called_once()


def test_on_pre_enter_preserves_existing_date(running_mdapp):
    screen = make_screen()

    with patch.object(mod, "today_str") as today, \
         patch.object(screen, "refresh") as refresh:

        screen.current_date = "2026-01-15"
        screen.on_pre_enter()

    assert screen.current_date == "2026-01-15"
    today.assert_not_called()
    refresh.assert_called_once()


def test_open_date_picker(running_mdapp):
    screen = make_screen()
    picker = Mock()

    with patch.object(mod, "MDDatePicker", return_value=picker):
        screen.open_date_picker()

    picker.bind.assert_called_once_with(on_save=screen._date_selected)
    picker.open.assert_called_once()


def test_date_selected_updates_date_and_refreshes(running_mdapp):
    screen = make_screen()

    with patch.object(screen, "refresh") as refresh:
        screen._date_selected(
            None,
            datetime(2026, 9, 25),
            None,
        )

    assert screen.current_date == "2026-09-25"
    refresh.assert_called_once()


# ============================================================================
# refresh()
# ============================================================================

def test_refresh_empty(running_mdapp):
    screen = make_screen()

    db = Mock()
    db.get_all_vitals.return_value = []

    with patch.object(mod.Database, "instance", return_value=db):
        screen.refresh()

    screen.ids.entry_box.clear_widgets.assert_called_once()
    screen.ids.entry_box.add_widget.assert_called_once()

    widget = screen.ids.entry_box.add_widget.call_args.args[0]

    assert widget.text == (
        "No vital readings recorded yet. Tap + to add a reading."
    )


def test_refresh_formats_bp_row_with_time_and_notes(running_mdapp):
    screen = make_screen()

    row = {
        "id": 1,
        "log_date": "2026-09-24",
        "vital_type": "BP",
        "value1": 120,
        "value2": 80,
        "reading_time": "10:30 AM",
        "notes": "Morning reading",
    }

    db = Mock()
    db.get_all_vitals.return_value = [row]

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(
             mod,
             "format_vital_value",
             return_value="120/80",
         ):

        screen.refresh()

    screen.ids.entry_box.add_widget.assert_called_once()

    card = screen.ids.entry_box.add_widget.call_args.args[0]

    assert isinstance(card, VitalEntryCard)
    assert card.title_text == "2026-09-24 — Blood Pressure"
    assert card.detail_text == (
        "120/80 mmHg   •   10:30 AM   •   Morning reading"
    )


def test_refresh_formats_row_without_time_or_notes(running_mdapp):
    screen = make_screen()

    row = {
        "id": 2,
        "log_date": "2026-09-24",
        "vital_type": "Pulse",
        "value1": 72,
        "value2": None,
        "reading_time": "",
        "notes": "",
    }

    db = Mock()
    db.get_all_vitals.return_value = [row]

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(
             mod,
             "format_vital_value",
             return_value="72",
         ):

        screen.refresh()

    card = screen.ids.entry_box.add_widget.call_args.args[0]

    assert card.title_text == "2026-09-24 — Pulse"
    assert card.detail_text == "72 bpm   •   -"


def test_refresh_handles_unknown_vital_type(running_mdapp):
    screen = make_screen()

    row = {
        "id": 3,
        "log_date": "2026-09-24",
        "vital_type": "UnknownVital",
        "value1": 10,
        "value2": None,
        "reading_time": "08:00",
        "notes": None,
    }

    db = Mock()
    db.get_all_vitals.return_value = [row]

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(
             mod,
             "format_vital_value",
             return_value="10",
         ):

        screen.refresh()

    card = screen.ids.entry_box.add_widget.call_args.args[0]

    assert card.title_text == "2026-09-24 — UnknownVital"
    assert card.detail_text == "10    •   08:00"


def test_refresh_card_callback_opens_correct_entry(running_mdapp):
    screen = make_screen()

    row = {
        "id": 10,
        "log_date": "2026-09-24",
        "vital_type": "Pulse",
        "value1": 72,
        "value2": None,
        "reading_time": "09:00",
        "notes": "",
    }

    db = Mock()
    db.get_all_vitals.return_value = [row]

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "format_vital_value", return_value="72"):

        screen.refresh()

    card = screen.ids.entry_box.add_widget.call_args.args[0]

    with patch.object(screen, "open_entry_dialog") as open_dialog:
        card.dispatch_tap()

    open_dialog.assert_called_once_with("Pulse", row)


# ============================================================================
# Type chooser
# ============================================================================

def test_open_type_chooser(running_mdapp):
    screen = make_screen()
    dialog = Mock()

    with patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog:
        screen.open_type_chooser()

    assert mock_dialog.call_args.kwargs["title"] == (
        "What would you like to log?"
    )

    content = mock_dialog.call_args.kwargs["content_cls"]

    assert len(content.children) == len(VITAL_TYPE_ORDER)
    assert dialog.open.called


def test_type_chooser_pick_opens_selected_type(running_mdapp):
    screen = make_screen()
    dialog = Mock()

    with patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(screen, "open_entry_dialog") as open_dialog:

        screen.open_type_chooser()

        content = mock_dialog.call_args.kwargs["content_cls"]

        # Kivy stores children in reverse insertion order.
        first_item = content.children[-1]

        first_item.dispatch("on_release")

    dialog.dismiss.assert_called_once()
    open_dialog.assert_called_once_with(VITAL_TYPE_ORDER[0])


# ============================================================================
# Helpers for open_entry_dialog()
# ============================================================================

def open_new_dialog(screen, vital_type, running_app_fixture):
    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"):

        screen.open_entry_dialog(vital_type)

    content = mock_dialog.call_args.kwargs["content_cls"]

    return db, dialog, content


# ============================================================================
# open_entry_dialog() - new records
# ============================================================================

@pytest.mark.parametrize("vital_type", VITAL_TYPE_ORDER)
def test_open_entry_dialog_supports_every_vital_type(
    running_mdapp,
    vital_type,
):
    screen = make_screen()

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"):

        screen.open_entry_dialog(vital_type)

    assert dialog.open.called
    assert len(
        mock_dialog.call_args.kwargs["content_cls"].children
    ) == (4 if VITAL_TYPES[vital_type].get("two_values") else 3)


def test_open_entry_dialog_single_value_new(running_mdapp):
    screen = make_screen()

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"), \
         patch.object(mod, "now_12h", return_value="10:00 AM"):

        screen.open_entry_dialog("Pulse")

    content = mock_dialog.call_args.kwargs["content_cls"]

    assert len(content.children) == 3
    assert dialog.open.called

    fields = list(reversed(content.children))

    assert fields[0].hint_text == "Pulse (bpm)"
    assert fields[0].text == ""
    assert fields[1].hint_text == "Time (tap to set)"
    assert fields[1].text == "10:00 AM"
    assert fields[2].hint_text == "Notes (optional)"


def test_open_entry_dialog_bp_has_two_value_fields(running_mdapp):
    screen = make_screen()

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"), \
         patch.object(mod, "now_12h", return_value="08:00 AM"):

        screen.open_entry_dialog("BP")

    content = mock_dialog.call_args.kwargs["content_cls"]

    assert len(content.children) == 4

    fields = list(reversed(content.children))

    assert fields[0].hint_text == "Systolic (mmHg)"
    assert fields[1].hint_text == "Diastolic (mmHg)"


def test_open_entry_dialog_new_save_single_value(running_mdapp):
    screen = make_screen()
    screen.current_date = "2026-09-24"

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"), \
         patch.object(mod, "now_12h", return_value="09:00 AM"):

        screen.open_entry_dialog("Pulse")

    content = mock_dialog.call_args.kwargs["content_cls"]
    fields = list(reversed(content.children))

    fields[0].text = "72"
    fields[1].text = "09:15 AM"
    fields[2].text = "Resting"

    save_button = next(
        b
        for b in mock_dialog.call_args.kwargs["buttons"]
        if isinstance(b, MDRaisedButton)
        and b.text == "SAVE"
    )

    with patch.object(screen, "refresh"):
        save_button.dispatch("on_release")

    db.add_vital_reading.assert_called_once_with(
        "2026-09-24",
        "Pulse",
        72.0,
        None,
        "09:15 AM",
        "Resting",
    )

    dialog.dismiss.assert_called_once()


def test_open_entry_dialog_new_empty_value_becomes_none(running_mdapp):
    screen = make_screen()
    screen.current_date = "2026-09-24"

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"), \
         patch.object(mod, "now_12h", return_value="09:00 AM"):

        screen.open_entry_dialog("Pulse")

    content = mock_dialog.call_args.kwargs["content_cls"]
    fields = list(reversed(content.children))

    fields[0].text = ""
    fields[1].text = ""
    fields[2].text = ""

    save_button = next(
        b
        for b in mock_dialog.call_args.kwargs["buttons"]
        if isinstance(b, MDRaisedButton)
        and b.text == "SAVE"
    )

    with patch.object(screen, "refresh"):
        save_button.dispatch("on_release")

    db.add_vital_reading.assert_called_once_with(
        "2026-09-24",
        "Pulse",
        None,
        None,
        "",
        "",
    )


def test_open_entry_dialog_invalid_numeric_value_becomes_none(running_mdapp):
    screen = make_screen()
    screen.current_date = "2026-09-24"

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"), \
         patch.object(mod, "now_12h", return_value="09:00 AM"):

        screen.open_entry_dialog("Weight")

    content = mock_dialog.call_args.kwargs["content_cls"]
    fields = list(reversed(content.children))

    fields[0].text = "invalid"
    fields[1].text = "10:30 AM"
    fields[2].text = "Bad input"

    save_button = next(
        b
        for b in mock_dialog.call_args.kwargs["buttons"]
        if isinstance(b, MDRaisedButton)
        and b.text == "SAVE"
    )

    with patch.object(screen, "refresh"):
        save_button.dispatch("on_release")

    db.add_vital_reading.assert_called_once_with(
        "2026-09-24",
        "Weight",
        None,
        None,
        "10:30 AM",
        "Bad input",
    )


def test_open_entry_dialog_new_bp_save_parses_both_values(running_mdapp):
    screen = make_screen()
    screen.current_date = "2026-09-24"

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"), \
         patch.object(mod, "now_12h", return_value="08:00 AM"):

        screen.open_entry_dialog("BP")

    content = mock_dialog.call_args.kwargs["content_cls"]
    fields = list(reversed(content.children))

    fields[0].text = "120"
    fields[1].text = "80"
    fields[2].text = "08:15 AM"
    fields[3].text = "Morning"

    save_button = next(
        b
        for b in mock_dialog.call_args.kwargs["buttons"]
        if isinstance(b, MDRaisedButton)
        and b.text == "SAVE"
    )

    with patch.object(screen, "refresh"):
        save_button.dispatch("on_release")

    db.add_vital_reading.assert_called_once_with(
        "2026-09-24",
        "BP",
        120.0,
        80.0,
        "08:15 AM",
        "Morning",
    )


# ============================================================================
# open_entry_dialog() - existing record
# ============================================================================

def test_open_entry_dialog_existing_prefills_values(running_mdapp):
    screen = make_screen()

    row = {
        "id": 42,
        "log_date": "2026-09-23",
        "vital_type": "BP",
        "value1": 125,
        "value2": 82,
        "reading_time": "08:30 AM",
        "notes": "Existing reading",
    }

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"):

        screen.open_entry_dialog("BP", row)

    content = mock_dialog.call_args.kwargs["content_cls"]
    fields = list(reversed(content.children))

    assert fields[0].text == "125"
    assert fields[1].text == "82"
    assert fields[2].text == "08:30 AM"
    assert fields[3].text == "Existing reading"


def test_open_entry_dialog_existing_save_updates_record(running_mdapp):
    screen = make_screen()

    row = {
        "id": 42,
        "log_date": "2026-09-23",
        "vital_type": "Pulse",
        "value1": 70,
        "value2": None,
        "reading_time": "08:30 AM",
        "notes": "Old",
    }

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"):

        screen.open_entry_dialog("Pulse", row)

    content = mock_dialog.call_args.kwargs["content_cls"]
    fields = list(reversed(content.children))

    fields[0].text = "75"
    fields[1].text = "09:15 AM"
    fields[2].text = "Updated"

    save_button = next(
        b
        for b in mock_dialog.call_args.kwargs["buttons"]
        if isinstance(b, MDRaisedButton)
        and b.text == "SAVE"
    )

    with patch.object(screen, "refresh"):
        save_button.dispatch("on_release")

    db.update_vital_reading.assert_called_once_with(
        42,
        value1=75.0,
        value2=None,
        reading_time="09:15 AM",
        notes="Updated",
    )

    dialog.dismiss.assert_called_once()


def test_open_entry_dialog_existing_delete(running_mdapp):
    screen = make_screen()

    row = {
        "id": 42,
        "log_date": "2026-09-23",
        "vital_type": "Weight",
        "value1": 65,
        "value2": None,
        "reading_time": "07:00 AM",
        "notes": "",
    }

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"):

        screen.open_entry_dialog("Weight", row)

    delete_button = next(
        b
        for b in mock_dialog.call_args.kwargs["buttons"]
        if isinstance(b, MDFlatButton)
        and b.text == "DELETE"
    )

    with patch.object(screen, "refresh"):
        delete_button.dispatch("on_release")

    db.delete_vital_reading.assert_called_once_with(42)
    dialog.dismiss.assert_called_once()


def test_open_entry_dialog_new_has_no_delete_button(running_mdapp):
    screen = make_screen()

    db = Mock()
    dialog = Mock()

    with patch.object(mod.Database, "instance", return_value=db), \
         patch.object(mod, "MDDialog", return_value=dialog) as mock_dialog, \
         patch.object(mod, "bind_time_field"):

        screen.open_entry_dialog("Pulse")

    buttons = mock_dialog.call_args.kwargs["buttons"]

    assert not any(
        isinstance(b, MDFlatButton) and b.text == "DELETE"
        for b in buttons
    )
