"""
screens/sugar_screen.py — freeform blood sugar log.

Rebuilt to match the Vitals screen's pattern: no fixed slots to fill —
tap "+", pick Meal (Breakfast/Lunch/Dinner) and Timing (Before/After)
from dropdowns, enter the value. Any number of readings per meal per
day. "Fasting" is still derived automatically from Timing (Before =
fasting, After = not) — there's no separate toggle for it.
"""

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.menu import MDDropdownMenu

from db import Database, today_str
from utils.time_input import bind_time_field, now_12h

MEAL_OPTIONS = ["Breakfast", "Lunch", "Dinner"]
TIMING_OPTIONS = ["Before", "After"]

KV = """
<SugarEntryCard>:
    orientation: "vertical"
    size_hint_y: None
    height: "80dp"
    padding: "14dp"
    spacing: "2dp"
    canvas.before:
        Color:
            rgba: app.theme_primary_light
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [16,]
    on_release: root.dispatch_tap()

    MDLabel:
        text: root.title_text
        bold: True
        theme_text_color: "Custom"
        text_color: app.theme_text
        size_hint_y: None
        height: self.texture_size[1]

    MDLabel:
        text: root.detail_text
        theme_text_color: "Custom"
        text_color: app.theme_text
        font_style: "Caption"
        size_hint_y: None
        height: self.texture_size[1]


<SugarScreen>:
    MDBoxLayout:
        orientation: "vertical"
        canvas.before:
            Color:
                rgba: app.theme_cream
            Rectangle:
                pos: self.pos
                size: self.size

        MDTopAppBar:
            title: "Blood Sugar History"
            md_bg_color: app.theme_primary
            right_action_items: [["plus", lambda x: root.open_entry_dialog()]]

        MDLabel:
            text: root.date_label
            halign: "center"
            theme_text_color: "Custom"
            text_color: app.theme_text
            size_hint_y: None
            height: "30dp"

        ScrollView:
            MDBoxLayout:
                id: entry_box
                orientation: "vertical"
                spacing: "10dp"
                padding: "16dp"
                size_hint_y: None
                height: self.minimum_height
"""

Builder.load_string(KV)


class SugarEntryCard(ButtonBehavior, BoxLayout):
    title_text = StringProperty("")
    detail_text = StringProperty("")

    def __init__(self, on_tap, **kwargs):
        super().__init__(**kwargs)
        self._on_tap = on_tap

    def dispatch_tap(self):
        self._on_tap()


class SugarScreen(MDScreen):
    date_label = StringProperty("")
    current_date = StringProperty("")

    def on_pre_enter(self, *args):
        if not self.current_date:
            self.current_date = today_str()
        self.refresh()

    @staticmethod
    def _display_date(value):
        try:
            from datetime import date
            return date.fromisoformat(value).strftime("%d %b %Y")
        except Exception:
            return value

    def open_date_picker(self):
        picker = MDDatePicker()
        picker.bind(on_save=self._date_selected)
        picker.open()

    def _date_selected(self, instance, value, date_range):
        self.current_date = value.strftime("%Y-%m-%d")
        self.refresh()

    def refresh(self):
        box = self.ids.entry_box
        box.clear_widgets()
        db = Database.instance()
        rows = db.get_all_sugar()

        if not rows:
            from kivymd.uix.label import MDLabel
            box.add_widget(MDLabel(
                text="No sugar readings recorded yet. Tap + to add a reading.",
                theme_text_color="Custom", text_color=(0.4, 0.35, 0.4, 1),
                size_hint_y=None, height="40dp",
            ))
            return

        for row in rows:
            card = SugarEntryCard(on_tap=lambda r=row: self.open_entry_dialog(r))
            date_text = row["log_date"]
            card.title_text = f'{date_text} — {row["slot"]}'
            value_str = f'{row["value"]:g} mg/dL' if row.get("value") is not None else "-"
            time_str = row.get("reading_time") or "-"
            fasting = "Fasting" if row.get("fasting") else "Not fasting"
            notes = row.get("notes") or ""
            card.detail_text = f"{value_str}   •   {time_str}   •   {fasting}" + (f"   •   {notes}" if notes else "")
            box.add_widget(card)

    def _make_dropdown_button(self, options, initial, on_select):
        """A tappable field that opens a dropdown menu of `options`,
        used for the Meal and Timing selectors."""
        btn = MDRaisedButton(text=initial)

        def open_menu(*_):
            menu_items = [
                {
                    "text": opt,
                    "viewclass": "OneLineListItem",
                    "on_release": lambda o=opt: choose(o),
                }
                for opt in options
            ]
            menu = MDDropdownMenu(caller=btn, items=menu_items, width_mult=3)

            def choose(opt):
                btn.text = opt
                on_select(opt)
                menu.dismiss()

            menu.open()

        btn.bind(on_release=open_menu)
        return btn

    def open_entry_dialog(self, row=None):
        db = Database.instance()

        # Parse an existing row's combined "Before Breakfast" slot back
        # into its Timing/Meal parts for editing.
        initial_timing, initial_meal = TIMING_OPTIONS[0], MEAL_OPTIONS[0]
        if row and row.get("slot"):
            parts = row["slot"].split(" ", 1)
            if len(parts) == 2 and parts[0] in TIMING_OPTIONS and parts[1] in MEAL_OPTIONS:
                initial_timing, initial_meal = parts[0], parts[1]

        selected = {
            "meal": initial_meal,
            "timing": initial_timing,
            "date": (row.get("log_date") if row else None) or self.current_date or today_str(),
        }

        meal_btn = self._make_dropdown_button(
            MEAL_OPTIONS, initial_meal, lambda v: selected.__setitem__("meal", v))
        timing_btn = self._make_dropdown_button(
            TIMING_OPTIONS, initial_timing, lambda v: selected.__setitem__("timing", v))

        selector_row = BoxLayout(orientation="horizontal", spacing="8dp",
                                  size_hint_y=None, height="48dp")
        selector_row.add_widget(timing_btn)
        selector_row.add_widget(meal_btn)

        date_btn = MDRaisedButton(
            text=f"Date: {self._display_date(selected['date'])}",
            size_hint_y=None,
            height="46dp",
        )

        def choose_date(*_):
            picker = MDDatePicker()
            picker.bind(on_save=lambda _instance, value, _range: set_date(value))
            picker.open()

        def set_date(value):
            selected["date"] = value.strftime("%Y-%m-%d")
            date_btn.text = f"Date: {self._display_date(selected['date'])}"

        date_btn.bind(on_release=choose_date)

        value_field = MDTextField(
            hint_text="Sugar value (mg/dL)",
            input_filter="float",
            text=str(row["value"]) if row and row.get("value") is not None else "",
        )
        time_field = MDTextField(
            hint_text="Reading time (tap to set)",
            text=(row.get("reading_time") if row else "") or now_12h(),
        )
        bind_time_field(time_field)
        prev_meal_field = MDTextField(
            hint_text="Previous meal time (tap to set)",
            text=(row.get("previous_meal_time") if row else "") or "",
        )
        bind_time_field(prev_meal_field)
        notes_field = MDTextField(
            hint_text="Notes (optional)",
            text=(row.get("notes") if row else "") or "",
        )

        content = BoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None)
        content.height = "410dp"
        content.add_widget(date_btn)
        content.add_widget(selector_row)
        for f in (value_field, time_field, prev_meal_field, notes_field):
            content.add_widget(f)

        def save(*_):
            try:
                value = float(value_field.text) if value_field.text.strip() else None
            except ValueError:
                value = None
            slot = f'{selected["timing"]} {selected["meal"]}'
            fasting = selected["timing"] == "Before"
            if row:
                db.update_sugar_reading(
                    row["id"],
                    log_date=selected["date"],
                    slot=slot,
                    value=value,
                    reading_time=time_field.text.strip(),
                    previous_meal_time=prev_meal_field.text.strip(),
                    fasting=1 if fasting else 0,
                    notes=notes_field.text.strip(),
                )
            else:
                db.add_sugar_reading(
                    selected["date"], slot, value,
                    time_field.text.strip(), prev_meal_field.text.strip(),
                    fasting, notes_field.text.strip(),
                )
            dialog.dismiss()
            self.refresh()

        def delete(*_):
            if row:
                db.delete_sugar_reading(row["id"])
            dialog.dismiss()
            self.refresh()

        buttons = [MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss())]
        if row:
            buttons.append(MDFlatButton(text="DELETE", theme_text_color="Custom",
                                         text_color=(0.9, 0.4, 0.4, 1), on_release=delete))
        buttons.append(MDRaisedButton(text="SAVE", on_release=save))

        dialog = MDDialog(
            title="Blood Sugar Reading",
            type="custom",
            content_cls=content,
            buttons=buttons,
        )
        dialog.open()
