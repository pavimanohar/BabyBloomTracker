"""Calendar screen: month view plus all daily BabyBloom records."""

import calendar
from datetime import date

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import TwoLineListItem
from kivymd.uix.label import MDLabel

from db import Database, today_str, VITAL_TYPES

KV = """
<DayCell>:
    size_hint_y: None
    height: "48dp"
    md_bg_color: root.bg_color
    radius: [10, 10, 10, 10]

    MDLabel:
        text: root.day_text
        halign: "center"
        theme_text_color: "Custom"
        text_color: app.theme_text
        bold: root.has_events

<CalendarScreen>:
    MDBoxLayout:
        orientation: "vertical"
        canvas.before:
            Color:
                rgba: app.theme_cream
            Rectangle:
                pos: self.pos
                size: self.size

        MDTopAppBar:
            title: root.month_label
            md_bg_color: app.theme_accent
            left_action_items: [["chevron-left", lambda x: root.change_month(-1)]]
            right_action_items: [["chevron-right", lambda x: root.change_month(1)], ["plus", lambda x: root.open_add_event(None)]]

        GridLayout:
            id: weekday_row
            cols: 7
            size_hint_y: None
            height: "28dp"

        GridLayout:
            id: day_grid
            cols: 7
            spacing: "4dp"
            padding: "8dp"
            size_hint_y: None
            height: "260dp"

        MDBoxLayout:
            size_hint_y: None
            height: "44dp"

        MDLabel:
            id: selected_label
            text: root.selected_label
            theme_text_color: "Custom"
            text_color: app.theme_text
            bold: True
            size_hint_y: None
            height: "34dp"
            padding: ["12dp", 0]

        ScrollView:
            bar_width: "4dp"
            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: ["12dp", "4dp", "12dp", "24dp"]
                spacing: "8dp"

                MDBoxLayout:
                    size_hint_y: None
                    height: "46dp"
                    spacing: "6dp"
                    MDLabel:
                        text: "Quick add"
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        bold: True
                        size_hint_x: None
                        width: "74dp"
                    MDRaisedButton:
                        text: "Events"
                        on_release: root.open_add_event(None)
                    MDRaisedButton:
                        text: "Sugar"
                        on_release: root.open_add_sugar()
                    MDRaisedButton:
                        text: "Vitals"
                        on_release: root.open_add_vitals()
                    MDRaisedButton:
                        text: "Meds"
                        on_release: root.open_add_medication()
                    MDRaisedButton:
                        text: "Notes"
                        on_release: root.open_add_consultation_note()

                MDBoxLayout:
                    id: summary_card
                    orientation: "vertical"
                    size_hint_y: None
                    height: self.minimum_height
                    padding: ["14dp", "12dp", "14dp", "14dp"]
                    spacing: "8dp"
                    canvas.before:
                        Color:
                            rgba: app.theme_primary_light
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [14, 14, 14, 14]

                    MDLabel:
                        text: "Daily Summary"
                        bold: True
                        font_style: "H6"
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        size_hint_y: None
                        height: "30dp"

                    MDLabel:
                        text: root.selected_label
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        font_style: "Caption"
                        size_hint_y: None
                        height: "22dp"

                    MDBoxLayout:
                        id: summary_list
                        orientation: "vertical"
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: "6dp"
"""

Builder.load_string(KV)


class DayCell(MDFlatButton):
    day_text = StringProperty("")
    has_events = False
    bg_color = [1, 1, 1, 1]

    def __init__(self, day_num, on_tap, is_today=False, has_events=False, **kwargs):
        super().__init__(**kwargs)
        self.day_num = day_num
        self.day_text = str(day_num) if day_num else ""
        self.has_events = has_events
        if day_num:
            self.bg_color = (0.98, 0.75, 0.83, 1) if is_today else (1, 1, 1, 0.6)
            self.bind(on_release=lambda *_: on_tap(day_num))


class CalendarScreen(MDScreen):
    month_label = StringProperty("")
    selected_label = StringProperty("")
    year = NumericProperty(0)
    month = NumericProperty(0)
    selected_date = StringProperty("")

    def on_pre_enter(self, *args):
        if not self.year:
            t = date.today()
            self.year, self.month = t.year, t.month
            self.selected_date = today_str()
        self.render_month()

    def change_month(self, delta):
        m = self.month + delta
        y = self.year
        if m > 12:
            m, y = 1, y + 1
        elif m < 1:
            m, y = 12, y - 1
        self.year, self.month = y, m
        self.render_month()

    def render_month(self):
        self.month_label = date(self.year, self.month, 1).strftime("%B %Y")
        db = Database.instance()
        events = db.get_events_for_month(self.year, self.month)
        days_with_events = {int(e["event_date"].split("-")[2]) for e in events}

        weekday_row = self.ids.weekday_row
        weekday_row.clear_widgets()
        for wd in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]:
            weekday_row.add_widget(MDLabel(text=wd, halign="center",
                                           theme_text_color="Custom", text_color=(0.35, 0.28, 0.32, 1)))

        day_grid = self.ids.day_grid
        day_grid.clear_widgets()
        today = date.today()
        cal = calendar.monthcalendar(self.year, self.month)
        day_grid.height = f"{48 * len(cal)}dp"

        for week in cal:
            for day_num in week:
                is_today = (day_num and self.year == today.year
                            and self.month == today.month and day_num == today.day)
                cell = DayCell(day_num, self.select_day, is_today=is_today,
                               has_events=day_num in days_with_events)
                day_grid.add_widget(cell)

        self.refresh_all()

    def select_day(self, day_num):
        self.selected_date = f"{self.year:04d}-{self.month:02d}-{day_num:02d}"
        self.refresh_all()

    def refresh_all(self):
        self.selected_label = f"Records on {self.selected_date}"
        self._refresh_summary(Database.instance())

    def _summary_line(self, text, secondary=""):
        row = BoxLayout(orientation="vertical", size_hint_y=None, height="52dp", padding=["2dp", "2dp"])
        primary = MDLabel(
            text=text,
            theme_text_color="Custom",
            text_color=(0.20, 0.16, 0.18, 1),
            font_style="Body1",
            size_hint_y=None,
            height="28dp",
        )
        row.add_widget(primary)
        if secondary:
            sub = MDLabel(
                text=secondary,
                theme_text_color="Custom",
                text_color=(0.42, 0.36, 0.39, 1),
                font_style="Caption",
                size_hint_y=None,
                height="20dp",
            )
            row.add_widget(sub)
        return row

    def _refresh_summary(self, db):
        """Read-only, human-readable summary for the selected date."""
        box = self.ids.summary_list
        box.clear_widgets()

        events = db.get_events_for_date(self.selected_date)
        sugar = db.get_sugar_for_date(self.selected_date)
        vitals = db.get_vitals_for_date(self.selected_date)
        meds = db.get_medications_for_date(self.selected_date)
        notes = db.get_consultation_notes_for_date(self.selected_date)

        # Events
        if events:
            for event in events:
                detail = event.get("notes") or event.get("event_type") or ""
                box.add_widget(self._summary_line(f'Event: {event["title"]}', detail))
        else:
            box.add_widget(self._summary_line("Events: No events recorded"))

        # Sugar readings
        if sugar:
            for reading in sugar:
                value = reading.get("value")
                value_text = "-" if value is None else f"{value:g} mg/dL"
                slot = reading.get("slot") or "Sugar"
                if reading.get("fasting"):
                    sentence = f"Fasting sugar {slot.lower()}: {value_text}"
                else:
                    sentence = f"Sugar {slot.lower()}: {value_text}"
                secondary = reading.get("reading_time") or ""
                box.add_widget(self._summary_line(sentence, secondary))
        else:
            box.add_widget(self._summary_line("Sugar: No reading recorded"))

        # Vitals
        if vitals:
            for reading in vitals:
                spec = VITAL_TYPES.get(reading["vital_type"], {})
                label = spec.get("label", reading["vital_type"])
                if reading.get("value1") is None:
                    value = "-"
                else:
                    value = str(reading["value1"])
                    if reading.get("value2") is not None:
                        value += f'/{reading["value2"]}'
                unit = spec.get("unit", "")
                box.add_widget(self._summary_line(f"{label}: {value} {unit}".rstrip(), reading.get("reading_time") or ""))
        else:
            box.add_widget(self._summary_line("Vitals: No readings recorded"))

        # Medications
        if meds:
            for med in meds:
                status = "Taken" if med.get("taken") else "Not taken"
                detail = " • ".join(x for x in [med.get("dosage"), med.get("scheduled_time"), status] if x)
                box.add_widget(self._summary_line(f'Medication: {med["name"]}', detail))
        else:
            box.add_widget(self._summary_line("Medications: No records recorded"))

        # Notes
        if notes:
            for note in notes:
                box.add_widget(self._summary_line(f'Note: {note["notes"]}'))
        else:
            box.add_widget(self._summary_line("Notes: No notes recorded"))

    # ----- Quick add from the selected calendar date -----
    def _refresh_after_dialog(self, *_args):
        Clock.schedule_once(lambda *_: self.refresh_all(), 0.6)

    def open_add_sugar(self):
        screen = self.manager.get_screen("sugar")
        screen.current_date = self.selected_date
        screen.open_entry_dialog()
        self._refresh_after_dialog()

    def open_add_vitals(self):
        screen = self.manager.get_screen("vitals")
        screen.current_date = self.selected_date
        screen.open_type_chooser()
        self._refresh_after_dialog()

    def open_add_medication(self):
        screen = self.manager.get_screen("medications")
        screen.current_date = self.selected_date
        screen.open_entry_dialog()
        self._refresh_after_dialog()

    def open_add_consultation_note(self):
        notes_field = MDTextField(hint_text="Add a note", multiline=True)
        content = BoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="160dp")
        content.add_widget(notes_field)

        def save(*_):
            text = notes_field.text.strip()
            if not text:
                return
            Database.instance().add_consultation_note(self.selected_date, text)
            dialog.dismiss()
            self.refresh_all()

        dialog = MDDialog(
            title=f"Notes — {self.selected_date}", type="custom", content_cls=content,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss()),
                     MDRaisedButton(text="SAVE", on_release=save)],
        )
        dialog.open()

    # ----- Events -----
    def open_add_event(self, _):
        title_field = MDTextField(hint_text="Title (e.g. Ultrasound scan)")
        type_field = MDTextField(hint_text="Type (appointment / scan / reminder / other)", text="appointment")
        date_field = MDTextField(hint_text="Date (YYYY-MM-DD)", text=self.selected_date)
        notes_field = MDTextField(hint_text="Notes (optional)")
        content = BoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="260dp")
        for w in (title_field, date_field, type_field, notes_field):
            content.add_widget(w)

        def save(*_):
            if not title_field.text.strip():
                return
            Database.instance().add_event(
                date_field.text.strip() or self.selected_date,
                title_field.text.strip(), type_field.text.strip() or "appointment",
                notes_field.text.strip())
            dialog.dismiss()
            self.render_month()

        dialog = MDDialog(
            title="Add Event", type="custom", content_cls=content,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss()),
                     MDRaisedButton(text="SAVE", on_release=save)],
        )
        dialog.open()

    def confirm_delete(self, event):
        def do_delete(*_):
            Database.instance().delete_event(event["id"])
            dialog.dismiss()
            self.render_month()
        dialog = MDDialog(
            title="Delete this event?", text=event["title"],
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss()),
                     MDFlatButton(text="DELETE", theme_text_color="Custom",
                                  text_color=(0.9, 0.4, 0.4, 1), on_release=do_delete)],
        )
        dialog.open()

    def confirm_delete_note(self, note):
        def do_delete(*_):
            Database.instance().delete_consultation_note(note["id"])
            dialog.dismiss()
            self.refresh_all()
        dialog = MDDialog(
            title="Delete this note?", text=note["notes"],
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss()),
                     MDFlatButton(text="DELETE", theme_text_color="Custom",
                                  text_color=(0.9, 0.4, 0.4, 1), on_release=do_delete)],
        )
        dialog.open()
