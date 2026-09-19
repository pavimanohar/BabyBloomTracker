"""BabyBloom report selection and PDF generation screen."""

import os
from datetime import date

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.list import OneLineListItem

from utils.export_utils import (
    export_selected_reports_to_pdf,
    get_export_dir,
    save_to_public_downloads,
    open_exported_file,
    delete_export,
    share_exported_file,
)

PDF_MIME = "application/pdf"

READING_OPTIONS = [
    ("sugar", "Blood Sugar"),
    ("vitals", "Vitals"),
    ("medications", "Medication"),
    ("calendar", "Event"),
    ("consultation", "Note"),
]

KV = """
<ExportScreen>:
    MDBoxLayout:
        orientation: "vertical"
        canvas.before:
            Color:
                rgba: app.theme_cream
            Rectangle:
                pos: self.pos
                size: self.size

        MDTopAppBar:
            title: "Export / Print"
            md_bg_color: app.theme_mint

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: ["14dp", "12dp", "14dp", "16dp"]
                spacing: "10dp"
                size_hint_y: None
                height: self.minimum_height

                MDCard:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "5dp"
                    size_hint_y: None
                    height: "112dp"
                    radius: [18, 18, 18, 18]
                    md_bg_color: app.theme_primary_light

                    MDLabel:
                        text: "Create a BabyBloom report"
                        bold: True
                        font_style: "H6"
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        size_hint_y: None
                        height: self.texture_size[1]

                    MDLabel:
                        text: "Choose a reading and the date range you want to include. Add more selections to combine them into one PDF."
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        font_style: "Caption"
                        text_size: self.width, None
                        size_hint_y: None
                        height: self.texture_size[1]

                MDLabel:
                    text: "Reading"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: app.theme_text
                    size_hint_y: None
                    height: "24dp"

                MDRaisedButton:
                    id: reading_button
                    text: root.selected_reading_label
                    md_bg_color: app.theme_secondary
                    theme_text_color: "Custom"
                    text_color: app.theme_text
                    size_hint_y: None
                    height: "48dp"
                    on_release: root.open_reading_menu(self)

                MDLabel:
                    text: "Date range"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: app.theme_text
                    size_hint_y: None
                    height: "24dp"

                MDBoxLayout:
                    spacing: "8dp"
                    size_hint_y: None
                    height: "54dp"

                    MDRaisedButton:
                        text: root.start_date_label
                        md_bg_color: app.theme_cream
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        size_hint_x: 0.5
                        on_release: root.open_date_picker("start")

                    MDRaisedButton:
                        text: root.end_date_label
                        md_bg_color: app.theme_cream
                        theme_text_color: "Custom"
                        text_color: app.theme_text
                        size_hint_x: 0.5
                        on_release: root.open_date_picker("end")

                MDRaisedButton:
                    text: "Add to report"
                    md_bg_color: app.theme_accent
                    size_hint_y: None
                    height: "48dp"
                    on_release: root.add_report()

                MDLabel:
                    text: "Reports to combine"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: app.theme_text
                    size_hint_y: None
                    height: "32dp"

                MDList:
                    id: selection_list
                    size_hint_y: None
                    height: self.minimum_height

                MDBoxLayout:
                    spacing: "10dp"
                    size_hint_y: None
                    height: "50dp"

                    MDFlatButton:
                        text: "Clear selection"
                        on_release: root.clear_selection()

                    MDRaisedButton:
                        text: "Generate PDF"
                        md_bg_color: app.theme_secondary
                        on_release: root.generate_pdf()

                MDLabel:
                    text: "Latest PDF"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: app.theme_text
                    size_hint_y: None
                    height: "32dp"

                MDList:
                    id: generated_list
                    size_hint_y: None
                    height: self.minimum_height

                MDLabel:
                    text: "Previous exports"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: app.theme_text
                    size_hint_y: None
                    height: "32dp"

                MDList:
                    id: export_list
                    size_hint_y: None
                    height: self.minimum_height
"""

Builder.load_string(KV)


class ExportScreen(MDScreen):
    status = StringProperty("")
    selected_reading = StringProperty("")
    selected_reading_label = StringProperty("Select reading")
    start_date_label = StringProperty("Start Date")
    end_date_label = StringProperty("End Date")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report_selections = []
        self.reading_menu = None
        self.generated_pdf_path = None
        self._date_target = None

    def on_pre_enter(self, *args):
        self.refresh_selection_list()
        self.refresh_generated_list()
        self.refresh_list()

    def open_reading_menu(self, caller):
        # Avoid MDDropdownMenu because KivyMD 1.2.0 can crash on Android
        # while calculating its target height. Use an explicit dialog list.
        content = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height="250dp",
            spacing=0,
        )

        for key, label in READING_OPTIONS:
            item = OneLineListItem(
                text=label,
                size_hint_y=None,
                height="50dp",
            )
            item.bind(
                on_release=lambda _item, k=key, l=label: self._select_reading(k, l)
            )
            content.add_widget(item)

        self.reading_menu = MDDialog(
            title="Select reading",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda *_: self._dismiss_reading_menu(),
                )
            ],
        )
        self.reading_menu.open()

    def _select_reading(self, key, label):
        self.selected_reading = key
        self.selected_reading_label = label
        self._dismiss_reading_menu()

    def _dismiss_reading_menu(self):
        if self.reading_menu:
            self.reading_menu.dismiss()
            self.reading_menu = None

    def open_date_picker(self, target):
        self._date_target = target
        current = self.start_date_label if target == "start" else self.end_date_label
        try:
            default = date.fromisoformat(current) if current not in ("Start Date", "End Date") else date.today()
        except ValueError:
            default = date.today()
        picker = MDDatePicker(year=default.year, month=default.month, day=default.day)
        picker.bind(on_save=self._date_selected)
        picker.open()

    def _date_selected(self, _picker, value, _range):
        formatted = value.strftime("%Y-%m-%d")
        if self._date_target == "start":
            self.start_date_label = formatted
        else:
            self.end_date_label = formatted
        self._date_target = None

    def add_report(self):
        if not self.selected_reading:
            self._notify("Please select a reading first.")
            return
        if self.start_date_label == "Start Date" or self.end_date_label == "End Date":
            self._notify("Please select both Start Date and End Date.")
            return

        try:
            start = date.fromisoformat(self.start_date_label)
            end = date.fromisoformat(self.end_date_label)
        except ValueError:
            self._notify("Please select valid dates.")
            return

        if start > end:
            self._notify("Start Date cannot be after End Date.")
            return

        item = {
            "category": self.selected_reading,
            "label": self.selected_reading_label,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        if item not in self.report_selections:
            self.report_selections.append(item)
        self.refresh_selection_list()

        self.selected_reading = ""
        self.selected_reading_label = "Select reading"
        self.start_date_label = "Start Date"
        self.end_date_label = "End Date"

    def remove_selection(self, index):
        if 0 <= index < len(self.report_selections):
            self.report_selections.pop(index)
            self.refresh_selection_list()

    def clear_selection(self):
        self.report_selections = []
        self.refresh_selection_list()

    def refresh_selection_list(self):
        target = self.ids.selection_list
        target.clear_widgets()
        if not self.report_selections:
            target.add_widget(OneLineListItem(text="No reports added yet."))
            return

        for index, item in enumerate(self.report_selections):
            row = MDBoxLayout(size_hint_y=None, height="56dp", padding=["8dp", 0], spacing="4dp")
            label = MDLabel(
                text=f"{item['label']}  |  {self._display_date(item['start'])} – {self._display_date(item['end'])}",
                theme_text_color="Custom",
                text_color=(0.35, 0.28, 0.32, 1),
                shorten=True,
                shorten_from="right",
            )
            row.add_widget(label)
            remove_btn = MDIconButton(icon="close-circle-outline")
            remove_btn.bind(on_release=lambda *_a, i=index: self.remove_selection(i))
            row.add_widget(remove_btn)
            target.add_widget(row)

    def generate_pdf(self):
        if not self.report_selections:
            self._notify("Add at least one report before generating the PDF.")
            return
        try:
            path = export_selected_reports_to_pdf(self.report_selections)
            save_to_public_downloads(path, PDF_MIME)
        except ImportError as e:
            self._notify(f"Missing library: {e}. Check requirements.txt.")
            return
        except Exception as e:
            self._notify(f"PDF generation failed: {e}")
            return

        self.report_selections = []
        self.generated_pdf_path = path
        self.refresh_selection_list()
        self.refresh_generated_list()
        self.refresh_list()
        self._notify(f"PDF generated successfully.\n\n{os.path.basename(path)}\n\nUse Share, View or Delete below.")

    def _share_or_notify(self, path):
        if not share_exported_file(path, PDF_MIME):
            self._notify("Unable to open the Android share sheet for this PDF.")

    def _view_or_notify(self, path):
        if not open_exported_file(path, PDF_MIME):
            self._notify("Unable to open the PDF viewer. Please install a PDF viewer app.")

    def _confirm_delete_file(self, filename, full_path):
        def do_delete(*_):
            delete_export(full_path)
            dialog.dismiss()
            self.refresh_generated_list()
            self.refresh_list()

        dialog = MDDialog(
            title="Delete this PDF?",
            text=f"{filename}\n\nThis removes the PDF from BabyBloom's export folder. A copy already saved in Downloads/BabyBloom may remain.",
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *_: dialog.dismiss()),
                MDFlatButton(
                    text="DELETE",
                    theme_text_color="Custom",
                    text_color=(0.9, 0.4, 0.4, 1),
                    on_release=do_delete,
                ),
            ],
        )
        dialog.open()

    def refresh_generated_list(self):
        target = self.ids.generated_list
        target.clear_widgets()
        if self.generated_pdf_path and os.path.isfile(self.generated_pdf_path):
            self._add_pdf_action_row(target, os.path.basename(self.generated_pdf_path))
        else:
            target.add_widget(OneLineListItem(text="Generate a PDF to see Share, View and Delete options here."))

    def refresh_list(self):
        target = self.ids.export_list
        target.clear_widgets()
        export_dir = get_export_dir()
        if not os.path.isdir(export_dir):
            return
        files = sorted([f for f in os.listdir(export_dir) if f.lower().endswith(".pdf")], reverse=True)[:20]
        if not files:
            target.add_widget(OneLineListItem(text="No generated PDFs yet."))
            return
        for filename in files:
            self._add_pdf_action_row(target, filename)

    def _add_pdf_action_row(self, target, filename):
        full_path = os.path.join(get_export_dir(), filename)
        row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="56dp", padding=["8dp", "4dp"], spacing="2dp")
        row.add_widget(MDLabel(text=filename, shorten=True, shorten_from="right", theme_text_color="Custom", text_color=(0.35, 0.28, 0.32, 1)))
        share_btn = MDIconButton(icon="share-variant")
        share_btn.bind(on_release=lambda *_a, p=full_path: self._share_or_notify(p))
        row.add_widget(share_btn)
        view_btn = MDIconButton(icon="eye-outline")
        view_btn.bind(on_release=lambda *_a, p=full_path: self._view_or_notify(p))
        row.add_widget(view_btn)
        delete_btn = MDIconButton(icon="trash-can-outline")
        delete_btn.bind(on_release=lambda *_a, n=filename, p=full_path: self._confirm_delete_file(n, p))
        row.add_widget(delete_btn)
        target.add_widget(row)

    @staticmethod
    def _display_date(value):
        try:
            return date.fromisoformat(value).strftime("%d %b %Y")
        except ValueError:
            return value

    def _notify(self, message):
        dialog = MDDialog(title="BabyBloom", text=message, buttons=[MDFlatButton(text="OK", on_release=lambda *_: dialog.dismiss())])
        dialog.open()
