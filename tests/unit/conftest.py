
import pytest
from kivy.app import App
from kivymd.app import MDApp

class DummyMDApp(MDApp):
    theme_primary = [246 / 255, 166 / 255, 193 / 255, 1]
    theme_primary_light = [246 / 255, 166 / 255, 193 / 255, 0.35]
    theme_secondary = [169 / 255, 214 / 255, 229 / 255, 1]
    theme_secondary_light = [169 / 255, 214 / 255, 229 / 255, 0.35]
    theme_accent = [201 / 255, 182 / 255, 228 / 255, 1]
    theme_mint = [184 / 255, 230 / 255, 208 / 255, 1]
    theme_cream = [255 / 255, 246 / 255, 238 / 255, 1]
    theme_text = [90 / 255, 74 / 255, 85 / 255, 1]

    def build(self):
        return None

@pytest.fixture
def running_mdapp():
    app = DummyMDApp()
    app._run_prepare()
    try:
        yield app
    finally:
        if App.get_running_app() is app:
            app.stop()
