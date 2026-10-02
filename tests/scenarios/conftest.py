import pytest
from kivy.app import App

from main import BabyBloomApp


@pytest.fixture
def real_baby_app(isolated_database):
    app = BabyBloomApp()
    app._run_prepare()
    root = app.build()
    app.root = root
    try:
        yield app
    finally:
        if App.get_running_app() is app:
            app.stop()


def _texts(widget_box):
    values = []
    for child in widget_box.children:
        for attr in (
            "text",
            "secondary_text",
            "tertiary_text",
            "title_text",
            "detail_text",
        ):
            value = getattr(child, attr, None)
            if value:
                values.append(value)
    return values

