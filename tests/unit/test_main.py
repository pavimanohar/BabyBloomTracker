import pytest

from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager
from kivymd.app import MDApp

import main
from main import BabyBloomApp, NavButton, RootLayout


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class DummyMDApp(MDApp):
    """Minimal running MDApp required by KivyMD widgets in NavButton tests."""

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


class DummyScreen(Screen):
    """Minimal screen used to isolate BabyBloomApp.build() from real screens."""

    pass


@pytest.fixture
def isolated_nav_items(monkeypatch):
    """
    Replace production screen classes with lightweight Screen classes.

    This isolates main.py's build() logic from the lifecycle/database logic
    belonging to the individual application screens.
    """

    items = [
        ("home", "home-heart", "Home", DummyScreen),
        ("sugar", "water-check", "Sugar", DummyScreen),
        ("vitals", "heart-pulse", "Vitals", DummyScreen),
        ("medications", "pill", "Meds", DummyScreen),
        ("export", "printer", "Export", DummyScreen),
        ("events", "calendar-star", "Events", DummyScreen),
        ("notes", "note-text", "Notes", DummyScreen),
    ]

    monkeypatch.setattr(main, "NAV_ITEMS", items)
    return items


@pytest.fixture
def isolated_app(monkeypatch, isolated_nav_items):
    """
    Create BabyBloomApp with isolated navigation screens and a harmless
    database spy.
    """

    database_calls = []

    def fake_database_instance(cls):
        database_calls.append(cls)
        return object()

    monkeypatch.setattr(
        main.Database,
        "instance",
        classmethod(fake_database_instance),
    )

    app = BabyBloomApp()
    return app, isolated_nav_items, database_calls


# ---------------------------------------------------------------------------
# NavButton.__init__
# ---------------------------------------------------------------------------

def test_navbutton_normal_construction(running_mdapp):
    button = NavButton("home", "home-heart", "Home", lambda name: None)

    assert isinstance(button, NavButton)
    assert button.name == "home"
    assert len(button.children) == 2


def test_navbutton_stores_name(running_mdapp):
    button = NavButton("sugar", "water-check", "Sugar", lambda name: None)

    assert button.name == "sugar"


def test_navbutton_configures_icon(running_mdapp):
    button = NavButton("home", "home-heart", "Home", lambda name: None)

    icon_button = next(
        child for child in button.children
        if child.__class__.__name__ == "MDIconButton"
    )

    assert icon_button.icon == "home-heart"


def test_navbutton_configures_label(running_mdapp):
    button = NavButton("home", "home-heart", "Home", lambda name: None)

    label = next(
        child for child in button.children
        if child.__class__.__name__ == "MDLabel"
    )

    assert label.text == "Home"
    assert label.halign == "center"


def test_navbutton_layout_configuration(running_mdapp):
    button = NavButton("home", "home-heart", "Home", lambda name: None)

    assert button.orientation == "vertical"
    assert list(button.size_hint) == [None, 1]
    assert button.width == pytest.approx(80)


def test_navbutton_contains_button_and_label(running_mdapp):
    button = NavButton("home", "home-heart", "Home", lambda name: None)

    child_types = {child.__class__.__name__ for child in button.children}

    assert child_types == {"MDIconButton", "MDLabel"}


def test_navbutton_callback_receives_name(running_mdapp):
    received = []

    def on_tap(name):
        received.append(name)

    button = NavButton("vitals", "heart-pulse", "Vitals", on_tap)

    icon_button = next(
        child for child in button.children
        if child.__class__.__name__ == "MDIconButton"
    )

    icon_button.dispatch("on_release")

    assert received == ["vitals"]


def test_navbutton_forwards_parent_kwargs(running_mdapp):
    button = NavButton(
        "home",
        "home-heart",
        "Home",
        lambda name: None,
        disabled=True,
    )

    assert button.disabled is True


# ---------------------------------------------------------------------------
# NAV_ITEMS
# ---------------------------------------------------------------------------

def test_nav_items_contains_expected_entries():
    expected_names = [
        "home",
        "sugar",
        "vitals",
        "medications",
        "export",
        "events",
        "notes",
    ]

    assert [item[0] for item in main.NAV_ITEMS] == expected_names


def test_nav_items_entries_have_four_fields():
    assert all(len(item) == 4 for item in main.NAV_ITEMS)


def test_nav_items_contains_expected_icons_and_labels():
    expected = [
        ("home", "home-heart", "Home"),
        ("sugar", "water-check", "Sugar"),
        ("vitals", "heart-pulse", "Vitals"),
        ("medications", "pill", "Meds"),
        ("export", "printer", "Export"),
        ("events", "calendar-star", "Events"),
        ("notes", "note-text", "Notes"),
    ]

    actual = [(name, icon, label) for name, icon, label, _cls in main.NAV_ITEMS]

    assert actual == expected


# ---------------------------------------------------------------------------
# BabyBloomApp.build()
# ---------------------------------------------------------------------------

def test_build_returns_root_layout(isolated_app):
    app, _items, _calls = isolated_app

    root = app.build()

    assert isinstance(root, RootLayout)


def test_build_sets_application_title(isolated_app):
    app, _items, _calls = isolated_app

    app.build()

    assert app.title == main.APP_TITLE


def test_build_sets_application_icon(isolated_app):
    app, _items, _calls = isolated_app

    app.build()

    expected = main.os.path.join(main.BASE_DIR, "assets", "icon.png")
    assert app.icon == expected


def test_build_sets_light_theme(isolated_app):
    app, _items, _calls = isolated_app

    app.build()

    assert app.theme_cls.theme_style == "Light"


def test_build_sets_pink_primary_palette(isolated_app):
    app, _items, _calls = isolated_app

    app.build()

    assert app.theme_cls.primary_palette == "Pink"


def test_build_initializes_database_once(isolated_app):
    app, _items, calls = isolated_app

    app.build()

    assert calls == [main.Database]


def test_build_creates_screen_manager(isolated_app):
    app, _items, _calls = isolated_app

    root = app.build()

    assert isinstance(root.ids.sm, ScreenManager)


def test_build_sets_fade_transition(isolated_app):
    app, _items, _calls = isolated_app

    root = app.build()

    transition = root.ids.sm.transition

    assert transition.__class__.__name__ == "FadeTransition"
    assert transition.duration == pytest.approx(0.15)


def test_build_adds_all_navigation_screens(isolated_app):
    app, items, _calls = isolated_app

    root = app.build()
    screen_manager = root.ids.sm

    assert len(screen_manager.screens) == len(items)
    assert {screen.name for screen in screen_manager.screens} == {
        item[0] for item in items
    }


def test_build_uses_navigation_screen_classes(isolated_app):
    app, items, _calls = isolated_app

    root = app.build()
    screen_manager = root.ids.sm

    for name, _icon, _label, screen_cls in items:
        assert isinstance(screen_manager.get_screen(name), screen_cls)


def test_build_adds_all_navigation_buttons(isolated_app):
    app, items, _calls = isolated_app

    root = app.build()
    nav_bar = root.ids.nav_bar

    assert len(nav_bar.children) == len(items)


def test_build_navigation_button_names(isolated_app):
    app, items, _calls = isolated_app

    root = app.build()
    actual_names = {
        child.name
        for child in root.ids.nav_bar.children
        if isinstance(child, NavButton)
    }

    assert actual_names == {item[0] for item in items}


def test_build_initial_screen_is_home(isolated_app):
    app, _items, _calls = isolated_app

    root = app.build()

    assert root.ids.sm.current == "home"


def test_build_returns_configured_root(isolated_app):
    app, items, _calls = isolated_app

    root = app.build()

    assert isinstance(root, RootLayout)
    assert root.ids.sm.current == "home"
    assert len(root.ids.sm.screens) == len(items)


def test_build_calls_database_instance_each_time_build_is_called(isolated_app):
    app, _items, calls = isolated_app

    app.build()
    app.build()

    assert calls == [main.Database, main.Database]


# ---------------------------------------------------------------------------
# BabyBloomApp.go_to()
# ---------------------------------------------------------------------------

@pytest.fixture
def navigation_app(isolated_app):
    app, items, _calls = isolated_app

    root = app.build()

    # MDApp.run() normally assigns the returned root to app.root.
    # Unit testing build() directly does not perform that assignment.
    app.root = root

    return app, items


@pytest.mark.parametrize(
    "screen_name",
    [
        "home",
        "sugar",
        "vitals",
        "medications",
        "export",
        "events",
        "notes",
    ],
)
def test_go_to_valid_screen(navigation_app, screen_name):
    app, _items = navigation_app

    app.go_to(screen_name)

    assert app.root.ids.sm.current == screen_name


def test_go_to_unknown_screen_raises(navigation_app):
    app, _items = navigation_app

    with pytest.raises(Exception) as exc_info:
        app.go_to("unknown")

    assert "No Screen with name" in str(exc_info.value)


def test_go_to_empty_screen_name_raises(navigation_app):
    app, _items = navigation_app

    with pytest.raises(Exception) as exc_info:
        app.go_to("")

    assert "No Screen with name" in str(exc_info.value)


def test_go_to_non_string_value_raises(navigation_app):
    app, _items = navigation_app

    with pytest.raises(Exception):
        app.go_to(123)

@pytest.mark.unit
def test_main_module_entry_point(monkeypatch):
    import runpy

    run_called = []

    def fake_run(self):
        run_called.append(True)

    monkeypatch.setattr(MDApp, "run", fake_run)

    runpy.run_path(
        main.__file__,
        run_name="__main__",
    )

    assert main.Window.softinput_mode == "below_target"
    assert run_called == [True]
