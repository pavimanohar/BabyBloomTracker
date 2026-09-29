from datetime import date
from unittest.mock import Mock

import screens.sugar_screen as mod
from screens.sugar_screen import SugarEntryCard, SugarScreen


class FakeField:
    def __init__(self, **kwargs):
        self.text = kwargs.get("text", "")
        self.hint_text = kwargs.get("hint_text", "")
        self.input_filter = kwargs.get("input_filter")
        self.bind_calls = []

    def bind(self, **kwargs):
        self.bind_calls.append(kwargs)


class FakeButton:
    def __init__(self, **kwargs):
        self.text = kwargs.get("text", "")
        self.kwargs = kwargs
        self._bindings = {}
        if "on_release" in kwargs:
            self._bindings["on_release"] = kwargs["on_release"]

    def bind(self, **kwargs):
        self._bindings.update(kwargs)

    def dispatch(self, event):
        callback = self._bindings.get(event)
        if callback:
            callback(self)


class FakeContent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.height = kwargs.get("height")
        self.children = []

    def add_widget(self, widget):
        self.children.append(widget)


class FakeDialog:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.buttons = kwargs.get("buttons", [])
        self.opened = False
        self.dismissed = False
        FakeDialog.instances.append(self)

    def open(self):
        self.opened = True

    def dismiss(self):
        self.dismissed = True


class FakeMenu:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.items = kwargs.get("items", [])
        self.dismissed = False
        self.opened = False
        FakeMenu.instances.append(self)

    def open(self):
        self.opened = True

    def dismiss(self):
        self.dismissed = True


class FakePicker:
    instances = []

    def __init__(self):
        self.bind_calls = {}
        self.opened = False
        FakePicker.instances.append(self)

    def bind(self, **kwargs):
        self.bind_calls.update(kwargs)

    def open(self):
        self.opened = True


def patch_dialog_widgets(monkeypatch):
    FakeDialog.instances.clear()
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    monkeypatch.setattr(mod, "MDFlatButton", FakeButton)
    monkeypatch.setattr(mod, "MDRaisedButton", FakeButton)
    monkeypatch.setattr(mod, "MDTextField", FakeField)
    monkeypatch.setattr(mod, "BoxLayout", FakeContent)


def test_sugar_entry_card_dispatches_callback(running_mdapp):
    seen = []

    card = SugarEntryCard(lambda: seen.append("called"))
    card.dispatch_tap()

    assert seen == ["called"]


def test_on_pre_enter_sets_today_when_date_empty(monkeypatch, running_mdapp):
    screen = SugarScreen()
    monkeypatch.setattr(mod, "today_str", lambda: "2026-09-25")
    screen.refresh = Mock()

    screen.current_date = ""
    screen.on_pre_enter()

    assert screen.current_date == "2026-09-25"
    screen.refresh.assert_called_once()


def test_on_pre_enter_preserves_existing_date(monkeypatch, running_mdapp):
    screen = SugarScreen()
    monkeypatch.setattr(mod, "today_str", lambda: "SHOULD-NOT-BE-CALLED")
    screen.refresh = Mock()

    screen.current_date = "2026-09-20"
    screen.on_pre_enter()

    assert screen.current_date == "2026-09-20"
    screen.refresh.assert_called_once()


def test_display_date_valid(running_mdapp):
    assert SugarScreen._display_date("2026-09-25") == "25 Sep 2026"


def test_display_date_invalid_returns_original(running_mdapp):
    assert SugarScreen._display_date("not-a-date") == "not-a-date"


def test_open_date_picker_binds_and_opens(monkeypatch, running_mdapp):
    picker = FakePicker()
    monkeypatch.setattr(mod, "MDDatePicker", lambda: picker)

    screen = SugarScreen()
    screen.open_date_picker()

    assert picker.opened is True
    assert picker.bind_calls["on_save"].__self__ is screen
    assert picker.bind_calls["on_save"].__func__ is screen._date_selected.__func__


def test_date_selected_updates_date_and_refreshes(running_mdapp):
    screen = SugarScreen()
    screen.refresh = Mock()

    screen._date_selected(None, date(2026, 9, 25), None)

    assert screen.current_date == "2026-09-25"
    screen.refresh.assert_called_once()


def test_refresh_empty_shows_placeholder(monkeypatch, running_mdapp):
    screen = SugarScreen()
    db = Mock()
    db.get_all_sugar.return_value = []
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )

    screen.refresh()

    assert len(screen.ids.entry_box.children) == 1
    assert "No sugar readings recorded yet." in screen.ids.entry_box.children[0].text


def test_refresh_formats_complete_fasting_row(monkeypatch, running_mdapp):
    screen = SugarScreen()
    db = Mock()
    db.get_all_sugar.return_value = [{
        "log_date": "2026-09-25",
        "slot": "Before Breakfast",
        "value": 105.5,
        "reading_time": "08:00 AM",
        "fasting": 1,
        "notes": "Feeling good",
    }]
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )

    screen.refresh()

    card = screen.ids.entry_box.children[0]
    assert card.title_text == "2026-09-25 — Before Breakfast"
    assert "105.5 mg/dL" in card.detail_text
    assert "08:00 AM" in card.detail_text
    assert "Fasting" in card.detail_text
    assert "Feeling good" in card.detail_text


def test_refresh_formats_missing_optional_values(monkeypatch, running_mdapp):
    screen = SugarScreen()
    db = Mock()
    db.get_all_sugar.return_value = [{
        "log_date": "2026-09-25",
        "slot": "After Dinner",
        "value": None,
        "reading_time": "",
        "fasting": 0,
        "notes": "",
    }]
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )

    screen.refresh()

    card = screen.ids.entry_box.children[0]
    assert card.detail_text == "-   •   -   •   Not fasting"


def test_refresh_card_tap_opens_matching_row(monkeypatch, running_mdapp):
    screen = SugarScreen()
    row = {
        "id": 7,
        "log_date": "2026-09-25",
        "slot": "Before Lunch",
        "value": 110,
        "reading_time": "12:00 PM",
        "fasting": 1,
        "notes": "",
    }
    db = Mock()
    db.get_all_sugar.return_value = [row]
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )
    screen.open_entry_dialog = Mock()

    screen.refresh()
    card = screen.ids.entry_box.children[0]
    card.dispatch("on_release")

    screen.open_entry_dialog.assert_called_once_with(row)


def test_dropdown_button_creates_menu_and_selects_option(
    monkeypatch, running_mdapp
):
    FakeMenu.instances.clear()
    monkeypatch.setattr(mod, "MDDropdownMenu", FakeMenu)

    screen = SugarScreen()
    selected = []
    button = screen._make_dropdown_button(
        ["Breakfast", "Lunch"], "Breakfast", selected.append
    )

    assert button.text == "Breakfast"
    button.dispatch("on_release")

    menu = FakeMenu.instances[0]
    assert menu.opened is True
    assert len(menu.items) == 2
    assert menu.items[0]["text"] == "Breakfast"

    menu.items[1]["on_release"]()

    assert button.text == "Lunch"
    assert selected == ["Lunch"]
    assert menu.dismissed is True


def test_open_entry_dialog_add_creates_expected_dialog(
    monkeypatch, running_mdapp
):
    patch_dialog_widgets(monkeypatch)
    monkeypatch.setattr(mod, "bind_time_field", lambda field: None)
    monkeypatch.setattr(mod, "now_12h", lambda: "09:30 AM")

    screen = SugarScreen()
    screen.current_date = "2026-09-25"

    screen.open_entry_dialog()

    dialog = FakeDialog.instances[0]
    assert dialog.opened is True
    assert dialog.kwargs["title"] == "Blood Sugar Reading"
    assert [b.text for b in dialog.buttons] == ["CANCEL", "SAVE"]

    content = dialog.kwargs["content_cls"]
    assert content.height == "410dp"
    assert len(content.children) == 6


def test_open_entry_dialog_edit_parses_existing_slot(
    monkeypatch, running_mdapp
):
    patch_dialog_widgets(monkeypatch)
    monkeypatch.setattr(mod, "bind_time_field", lambda field: None)

    row = {
        "id": 4,
        "log_date": "2026-09-22",
        "slot": "After Dinner",
        "value": 130,
        "reading_time": "08:30 PM",
        "previous_meal_time": "06:30 PM",
        "fasting": 0,
        "notes": "existing",
    }

    screen = SugarScreen()
    screen.current_date = "2026-09-25"
    screen.open_entry_dialog(row)

    dialog = FakeDialog.instances[0]
    assert [b.text for b in dialog.buttons] == ["CANCEL", "DELETE", "SAVE"]

    content = dialog.kwargs["content_cls"]
    assert content.children[0].text == "Date: 22 Sep 2026"
    assert content.children[2].text == "130"
    assert content.children[3].text == "08:30 PM"
    assert content.children[4].text == "06:30 PM"
    assert content.children[5].text == "existing"


def test_open_entry_dialog_add_save_valid_before_meal(
    monkeypatch, running_mdapp
):
    patch_dialog_widgets(monkeypatch)
    monkeypatch.setattr(mod, "bind_time_field", lambda field: None)

    db = Mock()
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )

    screen = SugarScreen()
    screen.current_date = "2026-09-25"
    refresh_calls = []
    screen.refresh = lambda: refresh_calls.append(True)

    screen.open_entry_dialog()
    dialog = FakeDialog.instances[0]
    content = dialog.kwargs["content_cls"]

    # value, time, previous meal, notes
    content.children[2].text = "115.5"
    content.children[3].text = "08:00 AM"
    content.children[4].text = "07:00 AM"
    content.children[5].text = "fasting check"

    dialog.buttons[1].dispatch("on_release")

    db.add_sugar_reading.assert_called_once_with(
        "2026-09-25",
        "Before Breakfast",
        115.5,
        "08:00 AM",
        "07:00 AM",
        True,
        "fasting check",
    )
    assert dialog.dismissed is True
    assert refresh_calls == [True]


def test_open_entry_dialog_add_save_invalid_value_becomes_none(
    monkeypatch, running_mdapp
):
    patch_dialog_widgets(monkeypatch)
    monkeypatch.setattr(mod, "bind_time_field", lambda field: None)

    db = Mock()
    db.get_all_sugar.return_value = []

    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )

    screen = SugarScreen()
    screen.current_date = "2026-09-25"
    screen.open_entry_dialog()

    dialog = FakeDialog.instances[0]
    content = dialog.kwargs["content_cls"]
    content.children[2].text = "not-a-number"
    content.children[3].text = "10:00 AM"
    content.children[4].text = ""
    content.children[5].text = ""

    dialog.buttons[1].dispatch("on_release")

    args = db.add_sugar_reading.call_args.args
    assert args[0] == "2026-09-25"
    assert args[1] == "Before Breakfast"
    assert args[2] is None
    assert args[5] is True


def test_open_entry_dialog_add_save_empty_value_becomes_none(
    monkeypatch, running_mdapp
):
    patch_dialog_widgets(monkeypatch)
    monkeypatch.setattr(mod, "bind_time_field", lambda field: None)

    db = Mock()
    db.get_all_sugar.return_value = []

    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )

    screen = SugarScreen()
    screen.current_date = "2026-09-25"
    screen.open_entry_dialog()

    dialog = FakeDialog.instances[0]
    content = dialog.kwargs["content_cls"]
    content.children[2].text = "   "
    content.children[3].text = ""
    content.children[4].text = ""
    content.children[5].text = ""

    dialog.buttons[1].dispatch("on_release")

    assert db.add_sugar_reading.call_args.args[2] is None


def test_open_entry_dialog_edit_save_updates_existing_row(
    monkeypatch, running_mdapp
):
    patch_dialog_widgets(monkeypatch)
    monkeypatch.setattr(mod, "bind_time_field", lambda field: None)
    monkeypatch.setattr(mod, "MDDropdownMenu", FakeMenu)

    db = Mock()
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )

    row = {
        "id": 9,
        "log_date": "2026-09-22",
        "slot": "After Dinner",
        "value": 130,
        "reading_time": "08:30 PM",
        "previous_meal_time": "06:30 PM",
        "fasting": 0,
        "notes": "old",
    }

    screen = SugarScreen()
    screen.current_date = "2026-09-25"
    refresh_calls = []
    screen.refresh = lambda: refresh_calls.append(True)
    screen.open_entry_dialog(row)

    dialog = FakeDialog.instances[0]
    content = dialog.kwargs["content_cls"]
    content.children[2].text = "140"
    content.children[3].text = "09:00 PM"
    content.children[4].text = "07:00 PM"
    content.children[5].text = "updated"

    selector_row = content.children[1]
    timing_button = selector_row.children[0]
    meal_button = selector_row.children[1]

    # Open each dropdown and choose the same values; this executes choose().
    timing_button.dispatch("on_release")
    timing_menu = FakeMenu.instances[-1]
    timing_menu.items[1]["on_release"]()  # After

    meal_button.dispatch("on_release")
    meal_menu = FakeMenu.instances[-1]
    meal_menu.items[2]["on_release"]()  # Dinner

    dialog.buttons[-1].dispatch("on_release")

    db.update_sugar_reading.assert_called_once_with(
        9,
        log_date="2026-09-22",
        slot="After Dinner",
        value=140.0,
        reading_time="09:00 PM",
        previous_meal_time="07:00 PM",
        fasting=0,
        notes="updated",
    )
    assert dialog.dismissed is True
    assert refresh_calls == [True]


def test_open_entry_dialog_cancel_dismisses(monkeypatch, running_mdapp):
    patch_dialog_widgets(monkeypatch)
    monkeypatch.setattr(mod, "bind_time_field", lambda field: None)

    screen = SugarScreen()
    screen.open_entry_dialog()

    dialog = FakeDialog.instances[0]
    dialog.buttons[0].dispatch("on_release")

    assert dialog.dismissed is True


def test_open_entry_dialog_edit_delete_deletes_row(
    monkeypatch, running_mdapp
):
    patch_dialog_widgets(monkeypatch)
    monkeypatch.setattr(mod, "bind_time_field", lambda field: None)

    db = Mock()
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )

    row = {
        "id": 12,
        "log_date": "2026-09-25",
        "slot": "Before Lunch",
        "value": 100,
        "reading_time": "12:00 PM",
        "previous_meal_time": "10:00 AM",
        "fasting": 1,
        "notes": "",
    }

    screen = SugarScreen()
    refresh_calls = []
    screen.refresh = lambda: refresh_calls.append(True)
    screen.open_entry_dialog(row)

    dialog = FakeDialog.instances[0]
    dialog.buttons[1].dispatch("on_release")

    db.delete_sugar_reading.assert_called_once_with(12)
    assert dialog.dismissed is True
    assert refresh_calls == [True]


def test_open_entry_dialog_date_picker_changes_selected_date(
    monkeypatch, running_mdapp
):
    patch_dialog_widgets(monkeypatch)
    monkeypatch.setattr(mod, "bind_time_field", lambda field: None)

    FakePicker.instances.clear()
    monkeypatch.setattr(mod, "MDDatePicker", FakePicker)

    screen = SugarScreen()
    screen.current_date = "2026-09-25"
    screen.open_entry_dialog()

    dialog = FakeDialog.instances[0]
    date_button = dialog.kwargs["content_cls"].children[0]

    date_button.dispatch("on_release")

    picker = FakePicker.instances[0]
    assert picker.opened is True

    picker.bind_calls["on_save"](None, date(2026, 9, 24), None)
    assert date_button.text == "Date: 24 Sep 2026"


def test_dropdown_choose_updates_callback_and_button(
    monkeypatch, running_mdapp
):
    FakeMenu.instances.clear()
    monkeypatch.setattr(mod, "MDDropdownMenu", FakeMenu)

    screen = SugarScreen()
    selected = []
    button = screen._make_dropdown_button(
        ["Breakfast", "Lunch", "Dinner"], "Breakfast", selected.append
    )

    button.dispatch("on_release")
    menu = FakeMenu.instances[-1]
    menu.items[2]["on_release"]()

    assert button.text == "Dinner"
    assert selected == ["Dinner"]
    assert menu.dismissed is True
