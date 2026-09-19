"""
screens/export_screen.py — export/print the sugar log.

Two formats:
  - .xlsx  (tabular, opens in Excel / Google Sheets / Samsung Notes' sheet viewer)
  - .pdf   (print-ready table — hand it straight to a printer or your OB/GYN)

On Android, after writing the file we fire the system share/"open with"
sheet via plyer, so the user can pick a printer app (e.g. Samsung's own
Print Service, or Google Cloud Print alternatives) directly.
"""

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.list import TwoLineIconListItem, IconLeftWidget

from db import Database, today_str
from utils.export_utils import (
    export_sugar_to_excel, export_sugar_to_pdf, get_export_dir, save_to_public_downloads,
)

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
            title: "Export / Print Sugar Log"
            md_bg_color: app.theme_mint

        MDBoxLayout:
            orientation: "vertical"
            padding: "16dp"
            spacing: "10dp"
            size_hint_y: None
            height: "180dp"

            MDTextField:
                id: from_date
                hint_text: "From date (YYYY-MM-DD, blank = all time)"

            MDTextField:
                id: to_date
                hint_text: "To date (YYYY-MM-DD, blank = today)"

            MDBoxLayout:
                spacing: "12dp"
                size_hint_y: None
                height: "48dp"

                MDRaisedButton:
                    text: "Export to Excel"
                    md_bg_color: app.theme_primary
                    on_release: root.do_export("xlsx")

                MDRaisedButton:
                    text: "Export / Print PDF"
                    md_bg_color: app.theme_secondary
                    on_release: root.do_export("pdf")

        MDLabel:
            text: "Previous exports"
            bold: True
            theme_text_color: "Custom"
            text_color: app.theme_text
            size_hint_y: None
            height: "30dp"
            padding: ["16dp", 0]

        ScrollView:
            MDList:
                id: export_list
"""

Builder.load_string(KV)


class ExportScreen(MDScreen):
    status = StringProperty("")

    def on_pre_enter(self, *args):
        self.refresh_list()

    def do_export(self, fmt):
        db = Database.instance()
        start = self.ids.from_date.text.strip()
        end = self.ids.to_date.text.strip() or today_str()

        if start:
            rows = db.get_sugar_range(start, end)
        else:
            rows = db.get_all_sugar()

        if not rows:
            self._notify("No sugar readings found for that range.")
            return

        try:
            if fmt == "xlsx":
                path = export_sugar_to_excel(rows)
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                path = export_sugar_to_pdf(rows)
                mime = "application/pdf"
        except ImportError as e:
            self._notify(f"Missing library: {e}. Check requirements.txt.")
            return

        visible_path = save_to_public_downloads(path, mime)
        if visible_path:
            self._notify(f"Saved to {visible_path}\n\nOpen it from your Files app or "
                          f"Downloads app any time.")
        else:
            self._share_or_notify(path)
        self.refresh_list()

    def _share_or_notify(self, path):
        try:
            from plyer import share
            share.share(title="BabyBloom export", filepath=path)
        except Exception:
            self._notify(f"Saved to:\n{path}")

    def _notify(self, message):
        dialog = MDDialog(
            title="BabyBloom",
            text=message,
            buttons=[MDFlatButton(text="OK", on_release=lambda *_: dialog.dismiss())],
        )
        dialog.open()

    def refresh_list(self):
        import os
        export_list = self.ids.export_list
        export_list.clear_widgets()
        export_dir = get_export_dir()
        if not os.path.isdir(export_dir):
            return
        files = sorted(os.listdir(export_dir), reverse=True)[:20]
        for f in files:
            icon = "file-excel" if f.endswith(".xlsx") else "file-pdf-box"
            item = TwoLineIconListItem(text=f, secondary_text="Also in Downloads/BabyBloom")
            item.add_widget(IconLeftWidget(icon=icon))
            full_path = os.path.join(export_dir, f)
            item.bind(on_release=lambda *_a, p=full_path: self._share_or_notify(p))
            export_list.add_widget(item)
