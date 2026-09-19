"""Notes history screen."""
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import TwoLineListItem
from db import Database, today_str

KV = '''
<NotesScreen>:
    MDBoxLayout:
        orientation: "vertical"
        canvas.before:
            Color:
                rgba: app.theme_cream
            Rectangle:
                pos: self.pos
                size: self.size
        MDTopAppBar:
            title: "Notes History"
            md_bg_color: app.theme_accent
            right_action_items: [["plus", lambda x: root.open_add_note()]]
        ScrollView:
            MDList:
                id: notes_list
'''
Builder.load_string(KV)


class NotesScreen(MDScreen):
    selected_date = StringProperty("")

    def on_pre_enter(self, *args):
        if not self.selected_date:
            self.selected_date = today_str()
        self.refresh()

    def refresh(self):
        box = self.ids.notes_list
        box.clear_widgets()
        db = Database.instance()
        rows = db.conn.execute(
            "SELECT * FROM consultation_notes ORDER BY log_date DESC, id DESC"
        ).fetchall()
        cols = [d[0] for d in db.conn.execute("SELECT * FROM consultation_notes LIMIT 0").description]
        notes = [dict(zip(cols, row)) for row in rows]
        if not notes:
            box.add_widget(TwoLineListItem(text="No notes recorded yet.", secondary_text="Tap + to add a note."))
            return
        for note in notes:
            text = note["notes"].replace("\n", " ")
            item = TwoLineListItem(text=text[:80], secondary_text=note["log_date"])
            item.bind(on_release=lambda *_a, n=note: self.delete_note(n))
            box.add_widget(item)

    def open_add_note(self):
        field = MDTextField(hint_text="Notes", multiline=True)
        content = BoxLayout(orientation="vertical", size_hint_y=None, height="180dp")
        content.add_widget(field)

        def save(*_):
            if not field.text.strip():
                return
            Database.instance().add_consultation_note(self.selected_date, field.text.strip())
            dialog.dismiss()
            self.refresh()

        dialog = MDDialog(
            title=f"Add Note — {self.selected_date}",
            type="custom",
            content_cls=content,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss()),
                     MDRaisedButton(text="SAVE", on_release=save)],
        )
        dialog.open()

    def delete_note(self, note):
        def do(*_):
            Database.instance().delete_consultation_note(note["id"])
            dialog.dismiss()
            self.refresh()
        dialog = MDDialog(
            title="Delete this note?",
            text=note["notes"],
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss()),
                     MDFlatButton(text="DELETE", on_release=do)],
        )
        dialog.open()
