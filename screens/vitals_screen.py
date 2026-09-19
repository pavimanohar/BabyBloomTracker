"""
screens/vitals_screen.py — freeform vitals log: Blood Pressure, Oxygen
(SpO2), Pulse, Weight. Unlike the Sugar screen's fixed six slots, none
of these are mandatory and any of them can be added any number of
times per day — tap "+", pick a type, fill in its value(s).
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
from kivymd.uix.list import OneLineIconListItem, IconLeftWidget

from db import Database, VITAL_TYPES, VITAL_TYPE_ORDER, today_str
from utils.export_utils import format_vital_value
from utils.time_input import bind_time_field, now_12h

KV = """
<VitalEntryCard>:
    orientation: "vertical"
    size_hint_y: None
    height: "84dp"
    padding: "14dp"
    spacing: "2dp"
    canvas.before:
        Color:
            rgba: app.theme_mint
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


<VitalsScreen>:
    MDBoxLayout:
        orientation: "vertical"
        canvas.before:
            Color:
                rgba: app.theme_cream
            Rectangle:
                pos: self.pos
                size: self.size

        MDTopAppBar:
            title: "Vitals History"
            md_bg_color: app.theme_mint
            right_action_items: [["plus", lambda x: root.open_type_chooser()]]

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


class VitalEntryCard(ButtonBehavior, BoxLayout):
    title_text = StringProperty("")
    detail_text = StringProperty("")

    def __init__(self, on_tap, **kwargs):
        super().__init__(**kwargs)
        self._on_tap = on_tap

    def dispatch_tap(self):
        self._on_tap()


class VitalsScreen(MDScreen):
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
        box = self.ids.entry_box
        box.clear_widgets()
        db = Database.instance()
        rows = db.get_all_vitals()

        if not rows:
            from kivymd.uix.label import MDLabel
            box.add_widget(MDLabel(
                text="No vital readings recorded yet. Tap + to add a reading.",
                theme_text_color="Custom", text_color=(0.4, 0.35, 0.4, 1),
                size_hint_y=None, height="40dp",
            ))
            return

        for row in rows:
            spec = VITAL_TYPES.get(row["vital_type"], {})
            card = VitalEntryCard(on_tap=lambda r=row: self.open_entry_dialog(r["vital_type"], r))
            card.title_text = f'{row["log_date"]} — {spec.get("label", row["vital_type"])}'
            value_str = format_vital_value(row)
            unit = spec.get("unit", "")
            time_str = row.get("reading_time") or "-"
            notes = row.get("notes") or ""
            card.detail_text = f"{value_str} {unit}   •   {time_str}" + (f"   •   {notes}" if notes else "")
            box.add_widget(card)

    def open_type_chooser(self):
        buttons = [MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss())]

        content = BoxLayout(orientation="vertical", spacing="6dp", size_hint_y=None)
        content.height = f"{48 * len(VITAL_TYPE_ORDER)}dp"

        def pick(vtype):
            dialog.dismiss()
            self.open_entry_dialog(vtype)

        for vtype in VITAL_TYPE_ORDER:
            spec = VITAL_TYPES[vtype]
            item = OneLineIconListItem(text=spec["label"])
            item.add_widget(IconLeftWidget(icon=spec.get("icon", "circle-outline")))
            item.bind(on_release=lambda *_a, v=vtype: pick(v))
            content.add_widget(item)

        dialog = MDDialog(
            title="What would you like to log?",
            type="custom",
            content_cls=content,
            buttons=buttons,
        )
        dialog.open()

    def open_entry_dialog(self, vital_type, row=None):
        db = Database.instance()
        spec = VITAL_TYPES[vital_type]

        value1_field = MDTextField(
            hint_text=f'{spec["value1_label"]} ({spec["unit"]})',
            input_filter="float",
            text=str(row["value1"]) if row and row.get("value1") is not None else "",
        )
        value2_field = None
        if spec.get("two_values"):
            value2_field = MDTextField(
                hint_text=f'{spec["value2_label"]} ({spec["unit"]})',
                input_filter="float",
                text=str(row["value2"]) if row and row.get("value2") is not None else "",
            )
        time_field = MDTextField(
            hint_text="Time (tap to set)",
            text=(row.get("reading_time") if row else "") or now_12h(),
        )
        bind_time_field(time_field)
        notes_field = MDTextField(
            hint_text="Notes (optional)",
            text=(row.get("notes") if row else "") or "",
        )

        fields = [value1_field]
        if value2_field:
            fields.append(value2_field)
        fields += [time_field, notes_field]

        content = BoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None)
        content.height = f"{60 * len(fields) + 20}dp"
        for f in fields:
            content.add_widget(f)

        def parse_float(field):
            try:
                return float(field.text) if field.text.strip() else None
            except ValueError:
                return None

        def save(*_):
            value1 = parse_float(value1_field)
            value2 = parse_float(value2_field) if value2_field else None
            if row:
                db.update_vital_reading(
                    row["id"], value1=value1, value2=value2,
                    reading_time=time_field.text.strip(),
                    notes=notes_field.text.strip(),
                )
            else:
                db.add_vital_reading(
                    self.current_date, vital_type, value1, value2,
                    time_field.text.strip(), notes_field.text.strip(),
                )
            dialog.dismiss()
            self.refresh()

        def delete(*_):
            if row:
                db.delete_vital_reading(row["id"])
            dialog.dismiss()
            self.refresh()

        buttons = [MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss())]
        if row:
            buttons.append(MDFlatButton(text="DELETE", theme_text_color="Custom",
                                         text_color=(0.9, 0.4, 0.4, 1), on_release=delete))
        buttons.append(MDRaisedButton(text="SAVE", on_release=save))

        dialog = MDDialog(
            title=spec["label"],
            type="custom",
            content_cls=content,
            buttons=buttons,
        )
        dialog.open()
