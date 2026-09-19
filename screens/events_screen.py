"""Events history screen."""
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
<EventsScreen>:
    MDBoxLayout:
        orientation: "vertical"
        canvas.before:
            Color:
                rgba: app.theme_cream
            Rectangle:
                pos: self.pos
                size: self.size
        MDTopAppBar:
            title: "Events History"
            md_bg_color: app.theme_accent
            right_action_items: [["plus", lambda x: root.open_add_event()]]
        ScrollView:
            MDList:
                id: event_list
'''
Builder.load_string(KV)


class EventsScreen(MDScreen):
    selected_date = StringProperty("")

    def on_pre_enter(self, *args):
        if not self.selected_date:
            self.selected_date = today_str()
        self.refresh()

    def refresh(self):
        box = self.ids.event_list
        box.clear_widgets()
        rows = Database.instance().conn.execute(
            "SELECT * FROM calendar_events ORDER BY event_date DESC, id DESC"
        ).fetchall()
        cols = [d[0] for d in Database.instance().conn.execute("SELECT * FROM calendar_events LIMIT 0").description]
        events = [dict(zip(cols, row)) for row in rows]
        if not events:
            box.add_widget(TwoLineListItem(text="No events recorded yet.", secondary_text="Tap + to add an event."))
            return
        for event in events:
            subtitle = f'{event["event_date"]}  •  {event["event_type"]}'
            if event.get("notes"):
                subtitle += f'  •  {event["notes"]}'
            item = TwoLineListItem(text=event["title"], secondary_text=subtitle)
            item.bind(on_release=lambda *_a, ev=event: self.delete_event(ev))
            box.add_widget(item)

    def open_add_event(self):
        title = MDTextField(hint_text="Title")
        typ = MDTextField(hint_text="Type", text="appointment")
        notes = MDTextField(hint_text="Notes (optional)")
        content = BoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="210dp")
        for w in (title, typ, notes):
            content.add_widget(w)

        def save(*_):
            if not title.text.strip():
                return
            Database.instance().add_event(
                self.selected_date, title.text.strip(), typ.text.strip() or "appointment", notes.text.strip()
            )
            dialog.dismiss()
            self.refresh()

        dialog = MDDialog(
            title=f"Add Event — {self.selected_date}",
            type="custom",
            content_cls=content,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss()),
                     MDRaisedButton(text="SAVE", on_release=save)],
        )
        dialog.open()

    def delete_event(self, event):
        def do(*_):
            Database.instance().delete_event(event["id"])
            dialog.dismiss()
            self.refresh()
        dialog = MDDialog(
            title="Delete this event?",
            text=event["title"],
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss()),
                     MDFlatButton(text="DELETE", on_release=do)],
        )
        dialog.open()
