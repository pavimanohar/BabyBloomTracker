import pytest

import screens.events_screen as mod
from screens.events_screen import EventsScreen


class FakeDialog:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.content_cls = kwargs.get("content_cls")
        self.buttons = kwargs.get("buttons", [])
        self.dismissed = False
        self.opened = False
        FakeDialog.instances.append(self)

    def open(self):
        self.opened = True

    def dismiss(self):
        self.dismissed = True


@pytest.fixture(autouse=True)
def reset_fake_dialog():
    FakeDialog.instances.clear()
    yield
    FakeDialog.instances.clear()


@pytest.fixture
def screen(isolated_database, running_mdapp):
    return EventsScreen()


def test_events_screen_initial_state(screen):
    assert screen.selected_date == ""


def test_on_pre_enter_sets_today_when_date_empty(screen, monkeypatch):
    monkeypatch.setattr(mod, "today_str", lambda: "2026-09-23")
    called = []
    screen.refresh = lambda: called.append(True)
    screen.on_pre_enter()
    assert screen.selected_date == "2026-09-23"
    assert called == [True]


def test_on_pre_enter_preserves_existing_date(screen):
    screen.selected_date = "2026-01-15"
    called = []
    screen.refresh = lambda: called.append(True)
    screen.on_pre_enter()
    assert screen.selected_date == "2026-01-15"
    assert called == [True]


def test_refresh_empty_database(screen):
    screen.refresh()
    assert len(screen.ids.event_list.children) == 1
    item = screen.ids.event_list.children[0]
    assert item.text == "No events recorded yet."
    assert item.secondary_text == "Tap + to add an event."


def test_refresh_event_without_notes(screen, isolated_database):
    isolated_database.add_event("2026-09-23", "Doctor Appointment", "appointment", "")
    screen.refresh()
    item = screen.ids.event_list.children[0]
    assert item.text == "Doctor Appointment"
    assert item.secondary_text == "2026-09-23  •  appointment"


def test_refresh_event_with_notes(screen, isolated_database):
    isolated_database.add_event("2026-09-23", "Scan", "medical", "Bring previous reports")
    screen.refresh()
    item = screen.ids.event_list.children[0]
    assert item.text == "Scan"
    assert item.secondary_text == "2026-09-23  •  medical  •  Bring previous reports"


def test_refresh_multiple_events_ordered_by_date_and_id(screen, isolated_database):
    isolated_database.add_event("2026-09-20", "Older Event", "appointment", "")
    isolated_database.add_event("2026-09-22", "Middle Event", "test", "")
    isolated_database.add_event("2026-09-23", "Newer Event", "appointment", "")
    screen.refresh()
    displayed = screen.ids.event_list.children
    assert [item.text for item in displayed] == ["Older Event", "Middle Event", "Newer Event"]


def test_refresh_clears_existing_widgets(screen, isolated_database):
    isolated_database.add_event("2026-09-23", "Event One", "appointment", "")
    screen.refresh()
    assert len(screen.ids.event_list.children) == 1
    isolated_database.add_event("2026-09-24", "Event Two", "appointment", "")
    screen.refresh()
    assert len(screen.ids.event_list.children) == 2
    assert {item.text for item in screen.ids.event_list.children} == {"Event One", "Event Two"}


def test_refresh_item_release_binds_delete_event(screen, isolated_database, monkeypatch):
    isolated_database.add_event("2026-09-23","Delete Me","appointment","",)
    event_id = isolated_database.conn.execute("SELECT id FROM calendar_events WHERE title = ?",("Delete Me",),).fetchone()[0]
    screen.refresh()
    item = screen.ids.event_list.children[0]
    captured = []
    monkeypatch.setattr(screen, "delete_event", lambda event: captured.append(event))
    item.dispatch("on_release")
    assert len(captured) == 1
    assert captured[0]["id"] == event_id
    assert captured[0]["title"] == "Delete Me"


def test_open_add_event_creates_dialog(screen, monkeypatch):
    screen.selected_date = "2026-09-23"
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    screen.open_add_event()
    dialog = FakeDialog.instances[0]
    assert dialog.opened is True
    assert dialog.kwargs["title"] == "Add Event — 2026-09-23"
    assert dialog.kwargs["type"] == "custom"
    fields = dialog.content_cls.children
    assert len(fields) == 3
    assert fields[2].hint_text == "Title"
    assert fields[1].hint_text == "Type"
    assert fields[1].text == "appointment"
    assert fields[0].hint_text == "Notes (optional)"


def test_open_add_event_empty_title_does_not_save(screen, isolated_database, monkeypatch):
    screen.selected_date = "2026-09-23"
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    screen.open_add_event()
    dialog = FakeDialog.instances[0]
    dialog.content_cls.children[2].text = "   "
    dialog.buttons[1].dispatch("on_release")
    rows = isolated_database.conn.execute("SELECT * FROM calendar_events").fetchall()
    assert rows == []
    assert dialog.dismissed is False


def test_open_add_event_saves_valid_event(screen, isolated_database, monkeypatch):
    screen.selected_date = "2026-09-23"
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    refresh_calls = []
    screen.refresh = lambda: refresh_calls.append(True)
    screen.open_add_event()
    dialog = FakeDialog.instances[0]
    fields = dialog.content_cls.children
    fields[2].text = "Doctor Visit"
    fields[1].text = "medical"
    fields[0].text = "Bring reports"
    dialog.buttons[1].dispatch("on_release")
    row = isolated_database.conn.execute("SELECT * FROM calendar_events").fetchone()
    assert row is not None
    assert row[1] == "2026-09-23"
    assert row[2] == "Doctor Visit"
    assert row[3] == "medical"
    assert row[4] == "Bring reports"
    assert dialog.dismissed is True
    assert refresh_calls == [True]


def test_open_add_event_uses_default_type_when_blank(screen, isolated_database, monkeypatch):
    screen.selected_date = "2026-09-23"
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    screen.open_add_event()
    fields = FakeDialog.instances[0].content_cls.children
    fields[2].text = "Appointment"
    fields[1].text = "   "
    fields[0].text = ""
    FakeDialog.instances[0].buttons[1].dispatch("on_release")
    row = isolated_database.conn.execute("SELECT * FROM calendar_events").fetchone()
    assert row[2] == "Appointment"
    assert row[3] == "appointment"
    assert row[4] == ""


def test_open_add_event_strips_input(screen, isolated_database, monkeypatch):
    screen.selected_date = "2026-09-23"
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    screen.open_add_event()
    fields = FakeDialog.instances[0].content_cls.children
    fields[2].text = "  Doctor Visit  "
    fields[1].text = "  appointment  "
    fields[0].text = "  Bring reports  "
    FakeDialog.instances[0].buttons[1].dispatch("on_release")
    row = isolated_database.conn.execute("SELECT * FROM calendar_events").fetchone()
    assert row[2] == "Doctor Visit"
    assert row[3] == "appointment"
    assert row[4] == "Bring reports"


def test_open_add_event_cancel_dismisses_dialog(screen, monkeypatch):
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    screen.open_add_event()
    FakeDialog.instances[0].buttons[0].dispatch("on_release")
    assert FakeDialog.instances[0].dismissed is True


def test_delete_event_creates_confirmation_dialog(screen, monkeypatch):
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    screen.delete_event({"id": 1, "title": "Doctor Visit"})
    dialog = FakeDialog.instances[0]
    assert dialog.opened is True
    assert dialog.kwargs["title"] == "Delete this event?"
    assert dialog.kwargs["text"] == "Doctor Visit"
    assert len(dialog.buttons) == 2


def test_delete_event_cancel_does_not_delete(screen, isolated_database, monkeypatch):

    isolated_database.add_event("2026-09-23","Keep Me","appointment","")
    event_id = isolated_database.conn.execute("SELECT id FROM calendar_events WHERE title = ?", ("Keep Me",),).fetchone()[0]
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    screen.delete_event({"id": event_id, "title": "Keep Me"})
    dialog = FakeDialog.instances[0]
    dialog.buttons[0].dispatch("on_release")
    row = isolated_database.conn.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
    assert row is not None
    assert row[2] == "Keep Me"
    assert dialog.dismissed is True


def test_delete_event_deletes_event_and_refreshes(screen, isolated_database, monkeypatch):
    event_id = isolated_database.add_event("2026-09-23", "Delete Me", "appointment", "")
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    refresh_calls = []
    screen.refresh = lambda: refresh_calls.append(True)
    screen.delete_event({"id": event_id, "title": "Delete Me"})
    dialog = FakeDialog.instances[0]
    dialog.buttons[1].dispatch("on_release")
    row = isolated_database.conn.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
    assert row is None
    assert dialog.dismissed is True
    assert refresh_calls == [True]
