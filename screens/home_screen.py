"""BabyBloom home dashboard: a warm, readable daily care overview."""

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.label import MDLabel

from db import Database, today_str

KV = """
<HomeScreen>:
    MDBoxLayout:
        orientation: "vertical"
        canvas.before:
            Color:
                rgba: app.theme_cream
            Rectangle:
                pos: self.pos
                size: self.size

        MDTopAppBar:
            title: "BabyBloom"
            md_bg_color: app.theme_primary
            right_action_items: [["calendar", lambda x: root.open_date_picker()]]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: ["14dp", "12dp", "14dp", "18dp"]
                spacing: "12dp"
                size_hint_y: None
                height: self.minimum_height

                MDCard:
                    orientation: "vertical"
                    padding: ["14dp", "12dp", "14dp", "12dp"]
                    spacing: "8dp"
                    size_hint_y: None
                    height: "126dp"
                    radius: [22, 22, 22, 22]
                    md_bg_color: app.theme_primary_light

                    MDLabel:
                        text: root.inspiration_title
                        bold: True
                        font_style: "H6"
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        size_hint_y: None
                        height: "30dp"

                    MDLabel:
                        text: root.inspiration_text
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        text_size: self.width, None
                        size_hint_y: None
                        height: self.texture_size[1]

                MDCard:
                    orientation: "horizontal"
                    padding: ["8dp", "10dp", "14dp", "10dp"]
                    spacing: "12dp"
                    size_hint_y: None
                    height: "118dp"
                    radius: [22, 22, 22, 22]
                    md_bg_color: app.theme_primary_light

                    Image:
                        source: root.hero_image_path
                        allow_stretch: True
                        keep_ratio: True
                        size_hint_x: None
                        width: "118dp"

                    MDBoxLayout:
                        orientation: "vertical"
                        spacing: "2dp"
                        size_hint_y: None
                        height: self.minimum_height
                        pos_hint: {"center_y": 0.5}

                        MDLabel:
                            text: "Welcome Mama"
                            font_style: "H5"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: app.theme_text
                            size_hint_y: None
                            height: self.texture_size[1]

                        MDLabel:
                            text: "A little look at you and baby, one day at a time."
                            theme_text_color: "Custom"
                            text_color: app.theme_text
                            font_style: "Caption"
                            text_size: self.width, None
                            size_hint_y: None
                            height: self.texture_size[1]

                MDCard:
                    orientation: "vertical"
                    padding: ["16dp", "12dp", "16dp", "12dp"]
                    spacing: "4dp"
                    size_hint_y: None
                    height: "94dp"
                    radius: [20, 20, 20, 20]
                    md_bg_color: app.theme_cream

                    MDBoxLayout:
                        size_hint_y: None
                        height: "28dp"
                        spacing: "8dp"

                        MDIcon:
                            icon: "baby-face-outline"
                            theme_text_color: "Custom"
                            text_color: app.theme_accent
                            size_hint: None, None
                            size: "24dp", "24dp"

                        MDLabel:
                            text: "Your pregnancy journey"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: app.theme_text

                    MDLabel:
                        text: root.pregnancy_duration_text
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        size_hint_y: None
                        height: self.texture_size[1]

                MDBoxLayout:
                    size_hint_y: None
                    height: "48dp"
                    spacing: "8dp"

                    MDLabel:
                        text: "Your day"
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        valign: "middle"

                    MDRaisedButton:
                        text: root.date_label
                        md_bg_color: app.theme_secondary
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        size_hint_x: None
                        width: "154dp"
                        on_release: root.open_date_picker()

                MDCard:
                    orientation: "vertical"
                    padding: ["16dp", "14dp", "16dp", "14dp"]
                    spacing: "8dp"
                    size_hint_y: None
                    height: root.summary_card_height
                    radius: [20, 20, 20, 20]
                    md_bg_color: app.theme_cream

                    MDBoxLayout:
                        size_hint_y: None
                        height: "30dp"
                        spacing: "8dp"

                        MDIcon:
                            icon: "clipboard-text-outline"
                            theme_text_color: "Custom"
                            text_color: app.theme_accent
                            size_hint: None, None
                            size: "26dp", "26dp"

                        MDLabel:
                            text: "Today at a glance"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: app.theme_text

                    MDLabel:
                        text: root.summary_text
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        text_size: self.width, None
                        size_hint_y: None
                        height: self.texture_size[1]
                        valign: "top"

                MDLabel:
                    text: "Add something"
                    font_style: "H6"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: app.theme_text
                    size_hint_y: None
                    height: "28dp"

                MDCard:
                    orientation: "vertical"
                    padding: "12dp"
                    spacing: "8dp"
                    size_hint_y: None
                    height: "154dp"
                    radius: [20, 20, 20, 20]
                    md_bg_color: app.theme_primary_light

                    MDLabel:
                        text: "Keep today's little details together"
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        font_style: "Caption"
                        size_hint_y: None
                        height: "22dp"

                    MDBoxLayout:
                        spacing: "8dp"
                        size_hint_y: None
                        height: "52dp"

                        MDRaisedButton:
                            text: "Sugar"
                            md_bg_color: app.theme_secondary
                            theme_text_color: "Custom"
                            text_color: app.theme_text
                            on_release: root._quick_add_sugar()

                        MDRaisedButton:
                            text: "Vitals"
                            md_bg_color: app.theme_secondary
                            theme_text_color: "Custom"
                            text_color: app.theme_text
                            on_release: root._quick_add_vitals()

                        MDRaisedButton:
                            text: "Medication"
                            md_bg_color: app.theme_secondary
                            theme_text_color: "Custom"
                            text_color: app.theme_text
                            on_release: root._quick_add_medication()

                    MDBoxLayout:
                        spacing: "8dp"
                        size_hint_y: None
                        height: "52dp"

                        MDRaisedButton:
                            text: "Event"
                            md_bg_color: app.theme_accent
                            on_release: root._quick_add_event()

                        MDRaisedButton:
                            text: "Note"
                            md_bg_color: app.theme_accent
                            on_release: root._quick_add_note()

                        Widget:

                MDLabel:
                    text: "Your records are saved locally on this device."
                    halign: "center"
                    theme_text_color: "Custom"
                    text_color: app.theme_text
                    font_style: "Caption"
                    size_hint_y: None
                    height: "24dp"
"""

Builder.load_string(KV)


class HomeScreen(MDScreen):
    date_label = StringProperty("")
    summary_text = StringProperty("")
    summary_card_height = StringProperty("150dp")
    selected_date = StringProperty("")
    pregnancy_duration_text = StringProperty("Set your pregnancy journey to see your progress here.")
    inspiration_title = StringProperty("A little positive note for you")
    inspiration_text = StringProperty("Every small step counts. You and your little one are taking this journey one day at a time.")
    hero_image_path = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        import os
        self.hero_image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "mom_baby_finger.png")
        self._setup_dialog = None
        self._setup_date = today_str()
        self._setup_unit = "weeks"

    def on_pre_enter(self, *args):
        if not self.selected_date:
            self.selected_date = today_str()
        self._refresh_pregnancy_journey()
        self.refresh()
        db = Database.instance()
        if not db.get_setting("pregnancy_reference_date"):
            Clock.schedule_once(lambda _dt: self._open_pregnancy_setup(), 0.2)

    def _open_pregnancy_setup(self):
        if self._setup_dialog:
            return
        content = BoxLayout(orientation="vertical", spacing="10dp", size_hint_y=None, height="238dp")

        content.add_widget(MDLabel(
            text="Tell BabyBloom how far along you are. This is saved once and updated automatically every day.",
            size_hint_y=None, height="52dp"))

        value_input = TextInput(text="0", input_filter="int", multiline=False, hint_text="Number", size_hint_y=None, height="48dp")
        content.add_widget(value_input)

        unit_row = BoxLayout(spacing="6dp", size_hint_y=None, height="44dp")
        unit_buttons = {}
        for unit in ("days", "weeks", "months"):
            button = MDRaisedButton(text=unit.capitalize(), size_hint_x=1)
            unit_buttons[unit] = button
            button.bind(on_release=lambda _btn, u=unit: self._select_setup_unit(u, unit_buttons))
            unit_row.add_widget(button)
        content.add_widget(unit_row)

        date_button = MDRaisedButton(text=f"Reference date: {self._display_date(self._setup_date)}", size_hint_y=None, height="44dp")
        date_button.bind(on_release=lambda *_: self._open_setup_date_picker(date_button))
        content.add_widget(date_button)
        self._setup_unit = "weeks"
        self._select_setup_unit("weeks", unit_buttons)

        self._setup_dialog = MDDialog(
            title="Set your pregnancy journey",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="SAVE", on_release=lambda *_: self._save_pregnancy_setup(value_input.text, date_button)),
            ],
        )
        self._setup_dialog.open()

    def _select_setup_unit(self, unit, buttons):
        self._setup_unit = unit
        for key, button in buttons.items():
            button.md_bg_color = (0.85, 0.55, 0.65, 1) if key == unit else (0.78, 0.78, 0.78, 1)

    def _open_setup_date_picker(self, button):
        picker = MDDatePicker()
        picker.bind(on_save=lambda _instance, value, _range: self._setup_date_selected(value, button))
        picker.open()

    def _setup_date_selected(self, value, button):
        self._setup_date = value.strftime("%Y-%m-%d")
        button.text = f"Reference date: {self._display_date(self._setup_date)}"

    def _save_pregnancy_setup(self, raw_value, _date_button):
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            return
        if value < 0:
            return
        today = today_str()
        if self._setup_date > today:
            return
        db = Database.instance()
        db.set_setting("pregnancy_reference_date", self._setup_date)
        db.set_setting("pregnancy_reference_value", str(value))
        db.set_setting("pregnancy_reference_unit", self._setup_unit)
        if self._setup_dialog:
            self._setup_dialog.dismiss()
            self._setup_dialog = None
        self._refresh_pregnancy_journey()

    def _refresh_pregnancy_journey(self):
        db = Database.instance()
        ref_date = db.get_setting("pregnancy_reference_date")
        if not ref_date:
            return
        try:
            value = int(db.get_setting("pregnancy_reference_value", "0"))
            unit = db.get_setting("pregnancy_reference_unit", "weeks")
            from datetime import date
            elapsed_days = (date.fromisoformat(today_str()) - date.fromisoformat(ref_date)).days
            if unit == "days":
                total_days = value + elapsed_days
                display = f"{total_days} days"
            elif unit == "months":
                total_days = value * 30 + elapsed_days
                display = f"{max(0, total_days // 30)} months"
            else:
                total_days = value * 7 + elapsed_days
                display = f"{max(0, total_days // 7)} weeks"
            self.pregnancy_duration_text = f"You are {display} along"
            self._set_inspiration(total_days)
        except Exception:
            self.pregnancy_duration_text = "Your pregnancy journey is ready to track."

    def _set_inspiration(self, total_days):
        weeks = max(0, total_days // 7)
        if weeks < 14:
            self.inspiration_title = "A little positive note for you"
            self.inspiration_text = "New beginnings can feel big and small at the same time. Be gentle with yourself and celebrate each day of this journey."
        elif weeks < 28:
            self.inspiration_title = "A little positive note for you"
            self.inspiration_text = "You are moving through another beautiful milestone. Take things one day at a time and make space for rest and little moments of joy."
        elif weeks < 37:
            self.inspiration_title = "A little positive note for you"
            self.inspiration_text = "You have come a long way, Mama. Keep taking today as it comes, and cherish the little moments with your baby."
        else:
            self.inspiration_title = "A little positive note for you"
            self.inspiration_text = "Your journey is getting closer to a wonderful new chapter. Breathe, rest, and take today one gentle step at a time."

    def open_date_picker(self):
        picker = MDDatePicker()
        picker.bind(on_save=self._date_selected)
        picker.open()

    def _date_selected(self, _instance, value, _date_range):
        self.selected_date = value.strftime("%Y-%m-%d")
        self.refresh()

    def refresh(self):
        self.date_label = self._display_date(self.selected_date)
        db = Database.instance()
        date_value = self.selected_date
        lines = []

        events = db.get_events_for_date(date_value)
        for e in events:
            title = (e.get("title") or "").strip()
            if title:
                lines.append(f"Event  •  {title}")

        sugar = db.get_sugar_for_date(date_value)
        for r in sugar:
            if r.get("value") is not None:
                lines.append(f'{r["slot"]}  •  {r["value"]:g} mg/dL')

        vitals = db.get_vitals_for_date(date_value)
        labels = {"BP": "Blood Pressure", "O2": "Oxygen", "Pulse": "Pulse", "Weight": "Weight"}
        units = {"BP": "mmHg", "O2": "%", "Pulse": "bpm", "Weight": "kg"}
        for r in vitals:
            if r.get("value1") is None:
                continue
            value = str(r["value1"])
            if r.get("value2") is not None:
                value += f' / {r["value2"]}'
            unit = units.get(r["vital_type"], "")
            lines.append(f'{labels.get(r["vital_type"], r["vital_type"])}  •  {value} {unit}'.rstrip())

        meds = db.get_medications_for_date(date_value)
        for m in meds:
            name = (m.get("name") or "").strip()
            if not name:
                continue
            status = "Taken" if m.get("taken") else "Not taken"
            dosage = f'  •  {m["dosage"]}' if m.get("dosage") else ""
            lines.append(f"Medication  •  {name}{dosage}  •  {status}")

        notes = db.get_consultation_notes_for_date(date_value)
        for n in notes:
            note = (n.get("notes") or "").strip()
            if note:
                lines.append(f"Note  •  {note}")

        if lines:
            self.summary_text = "\n".join(lines)
            self.summary_card_height = f"{max(145, 76 + len(lines) * 28)}dp"
        else:
            self.summary_text = "Nothing has been recorded for this day yet.\nUse the buttons below whenever you want to add something."
            self.summary_card_height = "165dp"

    @staticmethod
    def _display_date(value):
        try:
            from datetime import date
            return date.fromisoformat(value).strftime("%d %b %Y")
        except Exception:
            return value

    def _target_screen(self, name):
        return self.manager.get_screen(name)

    def open_quick_add(self):
        options = [
            ("Sugar", self._quick_add_sugar),
            ("Vitals", self._quick_add_vitals),
            ("Medication", self._quick_add_medication),
            ("Event", self._quick_add_event),
            ("Note", self._quick_add_note),
        ]
        content = BoxLayout(orientation="vertical", spacing="4dp", size_hint_y=None, height=f"{52 * len(options)}dp")
        dialog = None
        for label, callback in options:
            button = MDRaisedButton(text=label, size_hint_y=None, height="46dp")
            button.bind(on_release=lambda *_a, cb=callback: (dialog.dismiss(), cb()))
            content.add_widget(button)
        dialog = MDDialog(title="Add to BabyBloom", type="custom", content_cls=content,
                          buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss())])
        dialog.open()

    def _prepare_screen(self, name):
        screen = self._target_screen(name)
        if hasattr(screen, "current_date"):
            screen.current_date = self.selected_date
        if hasattr(screen, "selected_date"):
            screen.selected_date = self.selected_date
        return screen

    def _quick_add_sugar(self):
        screen = self._prepare_screen("sugar")
        screen.open_entry_dialog()

    def _quick_add_vitals(self):
        screen = self._prepare_screen("vitals")
        screen.open_type_chooser()

    def _quick_add_medication(self):
        screen = self._prepare_screen("medications")
        screen.open_entry_dialog()

    def _quick_add_event(self):
        screen = self._prepare_screen("events")
        screen.open_add_event()

    def _quick_add_note(self):
        screen = self._prepare_screen("notes")
        screen.open_add_note()
