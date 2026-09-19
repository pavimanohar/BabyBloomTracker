"""
main.py — BabyBloom: Pregnancy Care Tracker

Entry point. Sets up the KivyMD app, the pastel "babies" theme, a
ScreenManager holding the five sections, and a bottom nav bar to
switch between them.

Run on desktop for quick iteration:
    python3 main.py

Package into an .apk:
    python3 ../build_apk.py      (see that file's docstring)
"""

import os

from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ListProperty
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel

from db import Database
from theme import PALETTE, hex_to_rgba, APP_TITLE

from screens.home_screen import HomeScreen
from screens.sugar_screen import SugarScreen
from screens.vitals_screen import VitalsScreen
from screens.medication_screen import MedicationScreen
from screens.export_screen import ExportScreen
from screens.events_screen import EventsScreen
from screens.notes_screen import NotesScreen

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ROOT_KV = """
<RootLayout>:
    orientation: "vertical"

    ScreenManager:
        id: sm

    ScrollView:
        id: nav_scroll
        size_hint_y: None
        height: "64dp"
        do_scroll_y: False
        do_scroll_x: True
        bar_width: 0
        effect_cls: "ScrollEffect"
        MDBoxLayout:
            id: nav_bar
            size_hint_x: None
            width: self.minimum_width
            size_hint_y: None
            height: "64dp"
            md_bg_color: app.theme_primary
            padding: ["4dp", "4dp"]
"""

Builder.load_string(ROOT_KV)


class RootLayout(MDBoxLayout):
    pass


NAV_ITEMS = [
    ("home", "home-heart", "Home", HomeScreen),
    ("sugar", "water-check", "Sugar", SugarScreen),
    ("vitals", "heart-pulse", "Vitals", VitalsScreen),
    ("medications", "pill", "Meds", MedicationScreen),
    ("export", "printer", "Export", ExportScreen),
    ("events", "calendar-star", "Events", EventsScreen),
    ("notes", "note-text", "Notes", NotesScreen),
]


class NavButton(MDBoxLayout):
    def __init__(self, name, icon, label, on_tap, **kwargs):
        super().__init__(orientation="vertical", size_hint=(None, 1), width="80dp", **kwargs)
        self.name = name
        btn = MDIconButton(icon=icon, theme_text_color="Custom", text_color=(1, 1, 1, 1))
        btn.bind(on_release=lambda *_: on_tap(name))
        lbl = MDLabel(text=label, halign="center", font_style="Caption",
                       theme_text_color="Custom", text_color=(1, 1, 1, 1),
                       size_hint_y=None, height="16dp")
        self.add_widget(btn)
        self.add_widget(lbl)


class BabyBloomApp(MDApp):
    theme_primary = ListProperty(hex_to_rgba(PALETTE["primary"]))
    theme_primary_light = ListProperty(hex_to_rgba(PALETTE["primary"], 0.35))
    theme_secondary = ListProperty(hex_to_rgba(PALETTE["secondary"]))
    theme_secondary_light = ListProperty(hex_to_rgba(PALETTE["secondary"], 0.35))
    theme_accent = ListProperty(hex_to_rgba(PALETTE["accent"]))
    theme_mint = ListProperty(hex_to_rgba(PALETTE["mint"]))
    theme_cream = ListProperty(hex_to_rgba(PALETTE["cream"]))
    theme_text = ListProperty(hex_to_rgba(PALETTE["text"]))

    def build(self):
        self.title = APP_TITLE
        self.icon = os.path.join(BASE_DIR, "assets", "icon.png")
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Pink"

        Database.instance()  # create tables up front

        root = RootLayout()
        sm = root.ids.sm
        sm.transition = FadeTransition(duration=0.15)

        for name, icon, label, screen_cls in NAV_ITEMS:
            sm.add_widget(screen_cls(name=name))
            root.ids.nav_bar.add_widget(NavButton(name, icon, label, self.go_to))

        sm.current = "home"
        return root

    def go_to(self, screen_name):
        self.root.ids.sm.current = screen_name


if __name__ == "__main__":
    Window.softinput_mode = "below_target"
    BabyBloomApp().run()
