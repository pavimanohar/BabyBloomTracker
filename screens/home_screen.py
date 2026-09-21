"""BabyBloom home dashboard: a warm, readable daily care overview."""

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem

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

                MDCard:
                    orientation: "vertical"
                    padding: ["16dp", "12dp", "16dp", "12dp"]
                    spacing: "4dp"
                    size_hint_y: None
                    height: "92dp"
                    radius: [20, 20, 20, 20]
                    md_bg_color: app.theme_primary_light

                    MDBoxLayout:
                        size_hint_y: None
                        height: "30dp"
                        spacing: "8dp"

                        MDIcon:
                            icon: "chart-line"
                            theme_text_color: "Custom"
                            text_color: app.theme_accent
                            size_hint: None, None
                            size: "26dp", "26dp"

                        MDLabel:
                            text: "7-day average"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: app.theme_text

                        MDRaisedButton:
                            text: root.average_reading_label
                            size_hint_x: None
                            width: "145dp"
                            on_release: root.open_average_selector()

                    MDLabel:
                        text: root.average_reading_value
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        size_hint_y: None
                        height: self.texture_size[1]

                MDCard:
                    orientation: "vertical"
                    padding: ["14dp", "10dp", "14dp", "10dp"]
                    spacing: "4dp"
                    size_hint_y: None
                    height: "274dp"
                    radius: [20, 20, 20, 20]
                    md_bg_color: app.theme_cream

                    MDBoxLayout:
                        size_hint_y: None
                        height: "34dp"
                        spacing: "6dp"

                        MDIcon:
                            icon: "chart-timeline-variant"
                            theme_text_color: "Custom"
                            text_color: app.theme_accent
                            size_hint: None, None
                            size: "26dp", "26dp"

                        MDLabel:
                            text: "Reading trend"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: app.theme_text

                    MDBoxLayout:
                        size_hint_y: None
                        height: "40dp"
                        spacing: "6dp"

                        MDRaisedButton:
                            text: root.trend_reading_label
                            size_hint_x: None
                            width: "145dp"
                            on_release: root.open_trend_reading_selector()

                        MDRaisedButton:
                            text: root.trend_range_label
                            size_hint_x: None
                            width: "170dp"
                            on_release: root.open_trend_range_dialog()

                    ReadingTrendPlot:
                        id: trend_plot
                        size_hint_y: None
                        height: "145dp"

                    MDLabel:
                        text: root.trend_axis_text
                        halign: "center"
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        font_style: "Caption"
                        size_hint_y: None
                        height: "22dp"

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

<ReadingTrendPlot>:
    size_hint_y: None
    height: "170dp"
"""

class ReadingTrendPlot(Widget):
    """Small dependency-free line chart for the Home dashboard."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.labels = []
        self.values = []
        self.bind(pos=self._redraw, size=self._redraw)

    def set_data(self, labels, values):
        self.labels = list(labels)
        self.values = list(values)
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        if not self.values:
            return

        is_pair = isinstance(self.values[0], (tuple, list))
        if is_pair:
            series = [
                [float(v[0]) for v in self.values],
                [float(v[1]) for v in self.values],
            ]
        else:
            series = [[float(v) for v in self.values]]

        all_values = [v for values in series for v in values]
        lo = min(all_values)
        hi = max(all_values)
        pad = max((hi - lo) * 0.12, 1.0)
        lo -= pad
        hi += pad

        left = self.x + dp(18)
        right = self.right - dp(10)
        bottom = self.y + dp(16)
        top = self.top - dp(14)
        width = max(1.0, right - left)
        height = max(1.0, top - bottom)

        with self.canvas:
            Color(0.78, 0.74, 0.80, 0.55)
            Line(points=[left, bottom, right, bottom], width=1)

            for series_index, vals in enumerate(series):
                Color(0.73, 0.35, 0.48, 1) if series_index == 0 else Color(0.25, 0.50, 0.48, 1)
                if len(vals) == 1:
                    xs = [left + width / 2.0]
                else:
                    xs = [left + width * i / (len(vals) - 1) for i in range(len(vals))]
                ys = [bottom + (v - lo) / (hi - lo) * height for v in vals]
                points = []
                for x, y in zip(xs, ys):
                    points.extend([x, y])
                if len(points) >= 4:
                    Line(points=points, width=dp(2.2))
                for x, y in zip(xs, ys):
                    Ellipse(pos=(x - dp(4), y - dp(4)), size=(dp(8), dp(8)))


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
    average_reading_label = StringProperty("Fasting Sugar")
    average_reading_value = StringProperty("No readings in the last 7 days")
    trend_reading_label = StringProperty("Fasting Sugar")
    trend_range_label = StringProperty("Last 7 available readings")
    trend_axis_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        import os
        self.hero_image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "mom_baby_finger.png")
        self._setup_dialog = None
        self._setup_date = today_str()
        self._setup_unit = "weeks"
        self._average_key = "fasting_sugar"
        self._trend_key = "fasting_sugar"
        self._trend_unit = "days"
        self._trend_amount = 7

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

    def _reading_options(self):
        return [
            ("fasting_sugar", "Fasting Sugar"),
            ("sugar", "Blood Sugar"),
            ("bp", "Blood Pressure"),
            ("o2", "Oxygen (SpO2)"),
            ("pulse", "Pulse"),
            ("weight", "Weight"),
        ]

    def _date_window(self, unit, amount):
        from datetime import date, timedelta
        end = date.fromisoformat(today_str())
        if unit == "days":
            start = end - timedelta(days=max(1, amount) - 1)
        elif unit == "weeks":
            start = end - timedelta(days=max(1, amount) * 7 - 1)
        else:
            start = end - timedelta(days=max(1, amount) * 30 - 1)
        return start, end

    def _values_for_key(self, key, rows_sugar, rows_vitals):
        if key in ("fasting_sugar", "sugar"):
            rows = rows_sugar if key == "sugar" else [r for r in rows_sugar if r.get("fasting")]
            return [(r["log_date"], float(r["value"])) for r in rows if r.get("value") is not None]
        if key == "bp":
            return [(r["log_date"], (float(r["value1"]), float(r["value2"])))
                    for r in rows_vitals if r.get("vital_type") == "BP"
                    and r.get("value1") is not None and r.get("value2") is not None]
        mapping = {"o2": "O2", "pulse": "Pulse", "weight": "Weight"}
        vital_type = mapping.get(key)
        return [(r["log_date"], float(r["value1"])) for r in rows_vitals
                if r.get("vital_type") == vital_type and r.get("value1") is not None]

    def _format_average(self, key, values):
        if not values:
            return "No readings in the last 7 days"
        if key == "bp":
            systolic = sum(v[1][0] for v in values) / len(values)
            diastolic = sum(v[1][1] for v in values) / len(values)
            return f"{systolic:.0f} / {diastolic:.0f} mmHg"
        average = sum(v[1] for v in values) / len(values)
        units = {"fasting_sugar": "mg/dL", "sugar": "mg/dL", "o2": "%", "pulse": "bpm", "weight": "kg"}
        return f"{average:.1f} {units.get(key, '')}".strip()

    def _refresh_health_summary(self):
        db = Database.instance()
        start, end = self._date_window("days", 7)
        sugar = db.get_sugar_range(start.isoformat(), end.isoformat())
        vitals = db.get_vitals_range(start.isoformat(), end.isoformat())

        average_values = self._values_for_key(self._average_key, sugar, vitals)
        self.average_reading_value = self._format_average(self._average_key, average_values)

        if self._trend_unit == "days" and self._trend_amount == 7:
            # Default chart: latest seven available readings, ignoring days
            # with no reading by extending backwards as needed.
            values = self._values_for_key(self._trend_key, sugar, vitals)
            if len(values) < 7:
                from datetime import date, timedelta
                end_date = date.fromisoformat(today_str())
                start_date = end_date - timedelta(days=3650)
                sugar = db.get_sugar_range(start_date.isoformat(), end_date.isoformat())
                vitals = db.get_vitals_range(start_date.isoformat(), end_date.isoformat())
                values = self._values_for_key(self._trend_key, sugar, vitals)
            values = values[-7:]
            self.trend_range_label = "Last 7 available readings"
        else:
            start, end = self._date_window(self._trend_unit, self._trend_amount)
            sugar = db.get_sugar_range(start.isoformat(), end.isoformat())
            vitals = db.get_vitals_range(start.isoformat(), end.isoformat())
            values = self._values_for_key(self._trend_key, sugar, vitals)
            unit_label = {"days": "days", "weeks": "weeks", "months": "months"}[self._trend_unit]
            self.trend_range_label = f"{self._trend_amount} {unit_label}"

        labels = [self._short_date(d) for d, _v in values]
        self.trend_axis_text = "   •   ".join(labels) if labels else "No readings available for this range"
        plot_values = [v for _d, v in values]
        self.ids.trend_plot.set_data(labels, plot_values)
        if self._trend_key == "bp" and labels:
            self.trend_axis_text += "   (Systolic / Diastolic)"

    def _short_date(self, value):
        try:
            from datetime import date
            return date.fromisoformat(value).strftime("%d %b")
        except Exception:
            return value

    def _open_selection_dialog(self, title, options, selected_key, callback):
        content = BoxLayout(orientation="vertical", spacing="2dp", size_hint_y=None,
                            height=f"{50 * len(options)}dp")
        dialog = None
        for key, label in options:
            item = OneLineListItem(text=label)
            item.bind(on_release=lambda _item, k=key: (dialog.dismiss(), callback(k)))
            content.add_widget(item)
        dialog = MDDialog(title=title, type="custom", content_cls=content,
                          buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss())])
        dialog.open()

    def open_average_selector(self):
        self._open_selection_dialog("7-day average", self._reading_options(), self._average_key,
                                    self._set_average_reading)

    def _set_average_reading(self, key):
        self._average_key = key
        label = dict(self._reading_options())[key]
        self.average_reading_label = label
        self._refresh_health_summary()

    def open_trend_reading_selector(self):
        self._open_selection_dialog("Reading trend", self._reading_options(), self._trend_key,
                                    self._set_trend_reading)

    def _set_trend_reading(self, key):
        self._trend_key = key
        self.trend_reading_label = dict(self._reading_options())[key]
        self._refresh_health_summary()

    def open_trend_range_dialog(self):
        content = BoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None, height="150dp")
        amount = TextInput(text=str(self._trend_amount), input_filter="int", multiline=False,
                           hint_text="Number", size_hint_y=None, height="46dp")
        content.add_widget(MDLabel(text="Number of days, weeks or months", size_hint_y=None, height="28dp"))
        content.add_widget(amount)
        row = BoxLayout(spacing="6dp", size_hint_y=None, height="46dp")
        unit_buttons = {}
        dialog = None
        for unit in ("days", "weeks", "months"):
            button = MDRaisedButton(text=unit.capitalize())
            unit_buttons[unit] = button
            button.bind(on_release=lambda _btn, u=unit: self._select_trend_unit(u, unit_buttons))
            row.add_widget(button)
        content.add_widget(row)
        self._select_trend_unit(self._trend_unit, unit_buttons)

        def apply(*_):
            try:
                value = int(amount.text)
            except (TypeError, ValueError):
                value = 0
            if value <= 0:
                return
            self._trend_amount = value
            dialog.dismiss()
            self._refresh_health_summary()

        dialog = MDDialog(title="Trend range", type="custom", content_cls=content,
                          buttons=[MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss()),
                                   MDRaisedButton(text="APPLY", on_release=apply)])
        dialog.open()

    def _select_trend_unit(self, unit, buttons):
        self._trend_unit = unit
        for key, button in buttons.items():
            button.md_bg_color = (0.85, 0.55, 0.65, 1) if key == unit else (0.78, 0.78, 0.78, 1)

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
        self._refresh_health_summary()

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
