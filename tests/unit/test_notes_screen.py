import screens.notes_screen as mod
from screens.notes_screen import NotesScreen


class FakeField:
    def __init__(self, **kwargs):
        self.text = kwargs.get("text", "")
        self.hint_text = kwargs.get("hint_text", "")
        self.multiline = kwargs.get("multiline", False)


class FakeContent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.children = []

    def add_widget(self, widget):
        self.children.append(widget)


class FakeButton:
    def __init__(self, **kwargs):
        self.text = kwargs.get("text", "")
        self.on_release = kwargs.get("on_release")
        self.kwargs = kwargs

    def dispatch(self, event):
        assert event == "on_release"
        if self.on_release:
            self.on_release(self)


class FakeDialog:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.buttons = kwargs.get("buttons", [])
        self.dismissed = False
        self.opened = False
        FakeDialog.instances.append(self)

    def open(self):
        self.opened = True

    def dismiss(self):
        self.dismissed = True


def _reset_fakes():
    FakeDialog.instances.clear()


def _patch_dialog(monkeypatch):
    monkeypatch.setattr(mod, "MDDialog", FakeDialog)
    monkeypatch.setattr(mod, "MDFlatButton", FakeButton)
    monkeypatch.setattr(mod, "MDRaisedButton", FakeButton)
    monkeypatch.setattr(mod, "MDTextField", FakeField)
    monkeypatch.setattr(mod, "BoxLayout", FakeContent)


def _note_row(db, note_id):
    row = db.conn.execute(
        "SELECT id, log_date, notes FROM consultation_notes WHERE id = ?",
        (note_id,),
    ).fetchone()
    return {"id": row[0], "log_date": row[1], "notes": row[2]}


def test_on_pre_enter_sets_today_when_date_empty(monkeypatch, running_mdapp):
    screen = NotesScreen()
    monkeypatch.setattr(mod, "today_str", lambda: "2026-09-25")

    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))

    screen.selected_date = ""
    screen.on_pre_enter()

    assert screen.selected_date == "2026-09-25"
    assert calls == [True]


def test_on_pre_enter_preserves_existing_date(monkeypatch, running_mdapp):
    screen = NotesScreen()
    monkeypatch.setattr(mod, "today_str", lambda: "SHOULD-NOT-BE-USED")

    calls = []
    monkeypatch.setattr(screen, "refresh", lambda: calls.append(True))

    screen.selected_date = "2026-09-20"
    screen.on_pre_enter()

    assert screen.selected_date == "2026-09-20"
    assert calls == [True]


def test_refresh_empty_shows_placeholder(running_mdapp, isolated_database):
    screen = NotesScreen()

    screen.refresh()

    assert len(screen.ids.notes_list.children) == 1
    item = screen.ids.notes_list.children[0]
    assert item.text == "No notes recorded yet."
    assert item.secondary_text == "Tap + to add a note."


def test_refresh_flattens_newlines_and_limits_text_to_80_chars(
    running_mdapp, isolated_database
):
    note_text = "A" * 100 + "\nSecond line"
    isolated_database.add_consultation_note("2026-09-23", note_text)

    screen = NotesScreen()
    screen.refresh()

    item = screen.ids.notes_list.children[0]
    assert len(item.text) == 80
    assert "\n" not in item.text
    assert item.text == ("A" * 80)
    assert item.secondary_text == "2026-09-23"


def test_refresh_displays_multiple_notes_in_database_order(
    running_mdapp, isolated_database
):
    isolated_database.add_consultation_note("2026-09-22", "Older")
    isolated_database.add_consultation_note("2026-09-24", "Newer")
    isolated_database.add_consultation_note("2026-09-23", "Middle")

    screen = NotesScreen()
    screen.refresh()

    # Kivy stores children in reverse insertion order.
    displayed = screen.ids.notes_list.children
    assert [item.text for item in displayed] == ["Older", "Middle", "Newer"]


def test_refresh_item_release_calls_delete_note(monkeypatch, running_mdapp, isolated_database):
    isolated_database.add_consultation_note("2026-09-23", "Delete me")

    screen = NotesScreen()
    calls = []
    monkeypatch.setattr(screen, "delete_note", lambda note: calls.append(note))

    screen.refresh()

    item = screen.ids.notes_list.children[0]
    item.dispatch("on_release")

    assert len(calls) == 1
    assert calls[0]["notes"] == "Delete me"
    assert calls[0]["log_date"] == "2026-09-23"


def test_open_add_note_creates_expected_dialog(monkeypatch, running_mdapp):
    _reset_fakes()
    _patch_dialog(monkeypatch)

    screen = NotesScreen()
    screen.selected_date = "2026-09-25"

    screen.open_add_note()

    assert len(FakeDialog.instances) == 1
    dialog = FakeDialog.instances[0]
    assert dialog.opened is True
    assert dialog.kwargs["title"] == "Add Note — 2026-09-25"
    assert dialog.kwargs["type"] == "custom"

    content = dialog.kwargs["content_cls"]
    assert len(content.children) == 1
    assert content.children[0].hint_text == "Notes"
    assert content.children[0].multiline is True

    assert [button.text for button in dialog.buttons] == ["CANCEL", "SAVE"]


def test_open_add_note_save_empty_does_nothing(
    monkeypatch, running_mdapp, isolated_database
):
    _reset_fakes()
    _patch_dialog(monkeypatch)

    screen = NotesScreen()
    screen.selected_date = "2026-09-25"
    refresh_calls = []
    monkeypatch.setattr(screen, "refresh", lambda: refresh_calls.append(True))

    screen.open_add_note()

    dialog = FakeDialog.instances[0]
    field = dialog.kwargs["content_cls"].children[0]
    field.text = "   "

    dialog.buttons[1].dispatch("on_release")

    rows = isolated_database.conn.execute(
        "SELECT * FROM consultation_notes"
    ).fetchall()

    assert rows == []
    assert dialog.dismissed is False
    assert refresh_calls == []


def test_open_add_note_save_adds_note_and_refreshes(
    monkeypatch, running_mdapp, isolated_database
):
    _reset_fakes()
    _patch_dialog(monkeypatch)

    screen = NotesScreen()
    screen.selected_date = "2026-09-25"
    refresh_calls = []
    monkeypatch.setattr(screen, "refresh", lambda: refresh_calls.append(True))

    screen.open_add_note()

    dialog = FakeDialog.instances[0]
    field = dialog.kwargs["content_cls"].children[0]
    field.text = "  Consultation completed  "

    dialog.buttons[1].dispatch("on_release")

    row = isolated_database.conn.execute(
        "SELECT log_date, notes FROM consultation_notes"
    ).fetchone()

    assert row[0] == "2026-09-25"
    assert row[1] == "Consultation completed"
    assert dialog.dismissed is True
    assert refresh_calls == [True]


def test_open_add_note_cancel_dismisses_without_saving(
    monkeypatch, running_mdapp, isolated_database
):
    _reset_fakes()
    _patch_dialog(monkeypatch)

    screen = NotesScreen()
    screen.selected_date = "2026-09-25"

    screen.open_add_note()

    dialog = FakeDialog.instances[0]
    field = dialog.kwargs["content_cls"].children[0]
    field.text = "This should not be saved"

    dialog.buttons[0].dispatch("on_release")

    rows = isolated_database.conn.execute(
        "SELECT * FROM consultation_notes"
    ).fetchall()

    assert rows == []
    assert dialog.dismissed is True


def test_delete_note_creates_confirmation_dialog(
    monkeypatch, running_mdapp, isolated_database
):
    _reset_fakes()
    _patch_dialog(monkeypatch)

    isolated_database.add_consultation_note("2026-09-23", "Existing note")
    row = isolated_database.conn.execute(
        "SELECT id FROM consultation_notes"
    ).fetchone()
    note = _note_row(isolated_database, row[0])

    screen = NotesScreen()
    screen.delete_note(note)

    dialog = FakeDialog.instances[0]
    assert dialog.opened is True
    assert dialog.kwargs["title"] == "Delete this note?"
    assert dialog.kwargs["text"] == "Existing note"
    assert [button.text for button in dialog.buttons] == ["CANCEL", "DELETE"]


def test_delete_note_cancel_preserves_note(
    monkeypatch, running_mdapp, isolated_database
):
    _reset_fakes()
    _patch_dialog(monkeypatch)

    isolated_database.add_consultation_note("2026-09-23", "Keep this")
    row = isolated_database.conn.execute(
        "SELECT id FROM consultation_notes"
    ).fetchone()
    note = _note_row(isolated_database, row[0])

    screen = NotesScreen()
    refresh_calls = []
    monkeypatch.setattr(screen, "refresh", lambda: refresh_calls.append(True))

    screen.delete_note(note)

    dialog = FakeDialog.instances[0]
    dialog.buttons[0].dispatch("on_release")

    remaining = isolated_database.conn.execute(
        "SELECT notes FROM consultation_notes WHERE id = ?",
        (note["id"],),
    ).fetchone()

    assert remaining[0] == "Keep this"
    assert dialog.dismissed is True
    assert refresh_calls == []


def test_delete_note_confirmation_deletes_note_and_refreshes(
    monkeypatch, running_mdapp, isolated_database
):
    _reset_fakes()
    _patch_dialog(monkeypatch)

    isolated_database.add_consultation_note("2026-09-23", "Delete this")

    row = isolated_database.conn.execute(
        "SELECT id FROM consultation_notes"
    ).fetchone()
    note = _note_row(isolated_database, row[0])

    screen = NotesScreen()
    refresh_calls = []
    monkeypatch.setattr(screen, "refresh", lambda: refresh_calls.append(True))

    screen.delete_note(note)

    dialog = FakeDialog.instances[0]
    dialog.buttons[1].dispatch("on_release")

    remaining = isolated_database.conn.execute(
        "SELECT * FROM consultation_notes WHERE id = ?",
        (note["id"],),
    ).fetchall()

    assert remaining == []
    assert dialog.dismissed is True
    assert refresh_calls == [True]
