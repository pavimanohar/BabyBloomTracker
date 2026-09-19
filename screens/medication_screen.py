"""screens/medication_screen.py — daily medication list with add/edit/take/delete."""

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.list import ThreeLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.pickers import MDDatePicker

from db import Database, today_str, now_hhmm

KV = """
<MedicationScreen>:
    MDBoxLayout:
        orientation: "vertical"
        canvas.before:
            Color:
                rgba: app.theme_cream
            Rectangle:
                pos: self.pos
                size: self.size

        MDTopAppBar:
            title: "Medication History"
            md_bg_color: app.theme_secondary
            right_action_items: [["plus", lambda x: root.open_entry_dialog()]]

        MDLabel:
            text: root.date_label
            halign: "center"
            theme_text_color: "Custom"
            text_color: app.theme_text
            size_hint_y: None
            height: "30dp"

        ScrollView:
            MDList:
                id: med_list
"""

Builder.load_string(KV)


class MedicationScreen(MDScreen):
    date_label = StringProperty("")
    current_date = StringProperty("")

    def on_pre_enter(self, *args):
        if not self.current_date:
            self.current_date = today_str()
        self.refresh()

    def open_date_picker(self):
        picker = MDDatePicker()
        picker.bind(on_save=self._date_selected)
        picker.open()

    def _date_selected(self, instance, value, date_range):
        self.current_date = value.strftime("%Y-%m-%d")
        self.refresh()

    def refresh(self):
        self.date_label = "All medication history"
        db = Database.instance()
        med_list = self.ids.med_list
        med_list.clear_widgets()

        rows = db.conn.execute(
            "SELECT * FROM medications ORDER BY log_date DESC, scheduled_time, id DESC"
        ).fetchall()
        cols = [d[0] for d in db.conn.execute("SELECT * FROM medications LIMIT 0").description]
        medications = [dict(zip(cols, row)) for row in rows]

        if not medications:
            from kivymd.uix.list import OneLineListItem
            med_list.add_widget(OneLineListItem(text="No medications recorded yet."))
            return

        for med in medications:
            subtitle = f'{med["log_date"]}  •  {med["dosage"] or "-"}  •  {med["scheduled_time"] or "-"}'
            item = ThreeLineAvatarIconListItem(
                text=med["name"],
                secondary_text=subtitle,
                tertiary_text=(med["notes"] or "") + ("  •  Taken" if med["taken"] else "  •  Not taken"),
            )
            checkbox = IconLeftWidget(
                icon="check-circle" if med["taken"] else "circle-outline",
                theme_text_color="Custom",
                text_color=(0.56, 0.8, 0.61, 1) if med["taken"] else (0.6, 0.6, 0.6, 1),
            )
            checkbox.bind(on_release=lambda *_a, m=med: self.toggle_taken(m))
            item.add_widget(checkbox)
            item.bind(on_release=lambda *_a, m=med: self.open_entry_dialog(m))
            med_list.add_widget(item)

    def toggle_taken(self, med):
        db = Database.instance()
        db.set_medication_taken(med["id"], not med["taken"])
        self.refresh()

    def open_entry_dialog(self, med=None):
        db = Database.instance()

        name_field = MDTextField(hint_text="Medication name", text=med["name"] if med else "")
        dosage_field = MDTextField(hint_text="Dosage (e.g. 500mg)", text=(med["dosage"] if med else "") or "")
        time_field = MDTextField(
            hint_text="Scheduled time (HH:MM)",
            text=(med["scheduled_time"] if med else "") or now_hhmm(),
        )
        notes_field = MDTextField(hint_text="Notes (optional)", text=(med["notes"] if med else "") or "")

        content = BoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="260dp")
        for w in (name_field, dosage_field, time_field, notes_field):
            content.add_widget(w)

        def save(*_):
            if not name_field.text.strip():
                return
            if med:
                db.conn.execute(
                    "UPDATE medications SET name=?, dosage=?, scheduled_time=?, notes=? WHERE id=?",
                    (name_field.text.strip(), dosage_field.text.strip(),
                     time_field.text.strip(), notes_field.text.strip(), med["id"]),
                )
                db.conn.commit()
            else:
                db.add_medication(
                    self.current_date, name_field.text.strip(), dosage_field.text.strip(),
                    time_field.text.strip(), notes_field.text.strip(),
                )
            dialog.dismiss()
            self.refresh()

        def delete(*_):
            if med:
                db.delete_medication(med["id"])
            dialog.dismiss()
            self.refresh()

        buttons = [MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss())]
        if med:
            buttons.append(MDFlatButton(text="DELETE", theme_text_color="Custom",
                                         text_color=(0.9, 0.4, 0.4, 1), on_release=delete))
        buttons.append(MDRaisedButton(text="SAVE", on_release=save))

        dialog = MDDialog(
            title="Edit Medication" if med else "Add Medication",
            type="custom",
            content_cls=content,
            buttons=buttons,
        )
        dialog.open()
