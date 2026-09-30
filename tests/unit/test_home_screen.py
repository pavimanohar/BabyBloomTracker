from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import screens.home_screen as mod
from screens.home_screen import ReadingTrendPlot, HomeScreen


# ============================================================================
# ReadingTrendPlot
# ============================================================================


def test_reading_trend_plot_set_data(running_mdapp):
    plot = ReadingTrendPlot()
    plot._redraw = Mock()

    plot.set_data(["a", "b"], [1, 2])

    assert plot.labels == ["a", "b"]
    assert plot.values == [1, 2]
    plot._redraw.assert_called_once()


def test_reading_trend_plot_empty_values(running_mdapp):
    plot = ReadingTrendPlot()

    plot._redraw()

    assert True


def test_reading_trend_plot_scalar_values(running_mdapp):
    plot = ReadingTrendPlot()
    plot.size = (300, 150)
    plot.pos = (0, 0)

    plot.set_data(["a", "b", "c"], [1, 2, 3])

    assert plot.values == [1, 2, 3]


def test_reading_trend_plot_bp_pairs(running_mdapp):
    plot = ReadingTrendPlot()
    plot.size = (300, 150)
    plot.pos = (0, 0)

    plot.set_data(["a", "b"], [(120, 80), (125, 82)])

    assert plot.values[0] == (120, 80)


def test_reading_trend_plot_single_point(running_mdapp):
    """
    Covers the single-value branch in ReadingTrendPlot._redraw().
    """
    plot = ReadingTrendPlot()
    plot.size = (300, 150)
    plot.pos = (0, 0)

    plot.set_data(["24 Sep"], [100])

    assert plot.values == [100]


# ============================================================================
# HomeScreen initialization
# ============================================================================


def test_home_init(monkeypatch, running_mdapp):
    monkeypatch.setattr(mod, "today_str", lambda: "2026-09-23")

    screen = HomeScreen()

    assert screen.selected_date == ""
    assert screen._setup_date == "2026-09-23"
    assert screen._average_key == "fasting_sugar"
    assert screen._trend_amount == 7


# ============================================================================
# Pregnancy inspiration
# ============================================================================


def test_set_inspiration_all_boundaries(running_mdapp):
    screen = HomeScreen()

    screen._set_inspiration(13 * 7)
    assert "positive" in screen.inspiration_title.lower()

    screen._set_inspiration(14 * 7)
    assert "milestone" in screen.inspiration_text

    screen._set_inspiration(28 * 7)
    assert "come a long way" in screen.inspiration_text

    screen._set_inspiration(37 * 7)
    assert "closer" in screen.inspiration_text


# ============================================================================
# Date window
# ============================================================================


@pytest.mark.parametrize(
    "unit,amount,expected_days",
    [
        ("days", 1, 0),
        ("days", 7, 6),
        ("weeks", 1, 6),
        ("weeks", 2, 13),
        ("months", 1, 29),
    ],
)
def test_date_window(
    monkeypatch,
    running_mdapp,
    unit,
    amount,
    expected_days,
):
    monkeypatch.setattr(mod, "today_str", lambda: "2026-09-23")

    screen = HomeScreen()

    start, end = screen._date_window(unit, amount)

    assert end == date(2026, 9, 23)
    assert (end - start).days == expected_days


# ============================================================================
# Reading options / value extraction / averages
# ============================================================================


def test_reading_options(running_mdapp):
    assert [k for k, _ in HomeScreen()._reading_options()] == [
        "fasting_sugar",
        "sugar",
        "bp",
        "o2",
        "pulse",
        "weight",
    ]


def test_values_for_key_all_types(running_mdapp):
    screen = HomeScreen()

    sugar = [
        {
            "log_date": "2026-09-20",
            "value": 100,
            "fasting": 1,
        },
        {
            "log_date": "2026-09-21",
            "value": 110,
            "fasting": 0,
        },
    ]

    vitals = [
        {
            "log_date": "2026-09-20",
            "vital_type": "BP",
            "value1": 120,
            "value2": 80,
        },
        {
            "log_date": "2026-09-21",
            "vital_type": "O2",
            "value1": 98,
        },
        {
            "log_date": "2026-09-21",
            "vital_type": "Pulse",
            "value1": 72,
        },
        {
            "log_date": "2026-09-21",
            "vital_type": "Weight",
            "value1": 65,
        },
    ]

    assert screen._values_for_key(
        "fasting_sugar",
        sugar,
        vitals,
    ) == [
        ("2026-09-20", 100.0)
    ]

    assert screen._values_for_key(
        "sugar",
        sugar,
        vitals,
    ) == [
        ("2026-09-20", 100.0),
        ("2026-09-21", 110.0),
    ]

    assert screen._values_for_key(
        "bp",
        sugar,
        vitals,
    ) == [
        ("2026-09-20", (120.0, 80.0))
    ]

    assert screen._values_for_key(
        "o2",
        sugar,
        vitals,
    ) == [
        ("2026-09-21", 98.0)
    ]

    assert screen._values_for_key(
        "pulse",
        sugar,
        vitals,
    ) == [
        ("2026-09-21", 72.0)
    ]

    assert screen._values_for_key(
        "weight",
        sugar,
        vitals,
    ) == [
        ("2026-09-21", 65.0)
    ]


@pytest.mark.parametrize(
    "key,values,expected",
    [
        (
            "sugar",
            [],
            "No readings in the last 7 days",
        ),
        (
            "sugar",
            [("d", 100), ("d2", 110)],
            "105.0 mg/dL",
        ),
        (
            "bp",
            [("d", (120, 80)), ("d2", (130, 90))],
            "125 / 85 mmHg",
        ),
        (
            "o2",
            [("d", 98)],
            "98.0 %",
        ),
        (
            "pulse",
            [("d", 72)],
            "72.0 bpm",
        ),
        (
            "weight",
            [("d", 65)],
            "65.0 kg",
        ),
        (
            "unknown",
            [("d", 10)],
            "10.0",
        ),
    ],
)
def test_format_average(
    running_mdapp,
    key,
    values,
    expected,
):
    assert HomeScreen()._format_average(
        key,
        values,
    ) == expected


# ============================================================================
# Date formatting
# ============================================================================


def test_short_date(running_mdapp):
    screen = HomeScreen()

    assert screen._short_date("2026-09-23") == "23 Sep"
    assert screen._short_date("bad") == "bad"


def test_display_date_valid(running_mdapp):
    assert HomeScreen._display_date("2026-09-23") == "23 Sep 2026"


def test_display_date_invalid_returns_original(running_mdapp):
    assert HomeScreen._display_date("bad-date") == "bad-date"


# ============================================================================
# Pregnancy setup
# ============================================================================


def test_save_pregnancy_setup_invalid_values(
    running_mdapp,
    monkeypatch,
):
    screen = HomeScreen()

    db = Mock()

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    screen._save_pregnancy_setup("abc", None)
    screen._save_pregnancy_setup("-1", None)

    screen._setup_date = "2999-01-01"
    screen._save_pregnancy_setup("5", None)

    db.set_setting.assert_not_called()


def test_save_pregnancy_setup_valid(
    monkeypatch,
    running_mdapp,
):
    screen = HomeScreen()

    screen._setup_date = "2026-09-20"
    screen._setup_unit = "weeks"

    dialog = Mock()
    screen._setup_dialog = dialog

    db = Mock()

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    screen._refresh_pregnancy_journey = Mock()

    monkeypatch.setattr(
        mod,
        "today_str",
        lambda: "2026-09-23",
    )

    screen._save_pregnancy_setup("5", None)

    assert db.set_setting.call_count == 3
    dialog.dismiss.assert_called_once()
    assert screen._setup_dialog is None


@pytest.mark.parametrize(
    "unit,value,elapsed,expected",
    [
        ("days", 10, 2, "12 days"),
        ("weeks", 5, 2, "5 weeks"),
        ("months", 2, 10, "2 months"),
    ],
)
def test_refresh_pregnancy_journey_units(
    monkeypatch,
    running_mdapp,
    unit,
    value,
    elapsed,
    expected,
):
    screen = HomeScreen()

    db = Mock()
    db.get_setting.side_effect = [
        "2026-09-21",
        str(value),
        unit,
    ]

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    monkeypatch.setattr(
        mod,
        "today_str",
        lambda: "2026-09-23",
    )

    screen._set_inspiration = Mock()

    screen._refresh_pregnancy_journey()

    assert expected in screen.pregnancy_duration_text


def test_refresh_pregnancy_journey_missing_reference(
    running_mdapp,
    monkeypatch,
):
    screen = HomeScreen()

    db = Mock()
    db.get_setting.return_value = None

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    screen._refresh_pregnancy_journey()

    assert screen.pregnancy_duration_text.startswith(
        "Set your pregnancy"
    )


def test_refresh_pregnancy_journey_bad_data(
    running_mdapp,
    monkeypatch,
):
    screen = HomeScreen()

    db = Mock()
    db.get_setting.side_effect = [
        "bad",
        "x",
        "weeks",
    ]

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    screen._refresh_pregnancy_journey()

    assert (
        screen.pregnancy_duration_text
        == "Your pregnancy journey is ready to track."
    )


def test_open_pregnancy_setup_when_dialog_already_exists(
    running_mdapp,
):
    screen = HomeScreen()

    existing_dialog = object()
    screen._setup_dialog = existing_dialog

    result = screen._open_pregnancy_setup()

    assert result is None
    assert screen._setup_dialog is existing_dialog


def test_open_pregnancy_setup_creates_dialog(
    monkeypatch,
    running_mdapp,
):
    captured = []

    monkeypatch.setattr(
        mod.MDDialog,
        "open",
        lambda self: captured.append(self),
    )

    screen = HomeScreen()

    screen._open_pregnancy_setup()

    assert screen._setup_dialog is not None
    assert captured


def test_select_setup_unit(running_mdapp):
    screen = HomeScreen()

    buttons = {
        "days": Mock(),
        "weeks": Mock(),
        "months": Mock(),
    }

    screen._select_setup_unit("days", buttons)

    assert screen._setup_unit == "days"


def test_setup_date_selected(running_mdapp):
    screen = HomeScreen()

    button = Mock()

    screen._setup_date_selected(
        date(2026, 9, 23),
        button,
    )

    assert screen._setup_date == "2026-09-23"
    assert "23 Sep 2026" in button.text


def test_open_setup_date_picker(
    monkeypatch,
    running_mdapp,
):
    picker = Mock()

    monkeypatch.setattr(
        mod,
        "MDDatePicker",
        lambda: picker,
    )

    screen = HomeScreen()

    screen._open_setup_date_picker(Mock())

    picker.open.assert_called_once()


# ============================================================================
# Health summary
# ============================================================================


def test_refresh_health_summary_empty(
    monkeypatch,
    running_mdapp,
):
    screen = HomeScreen()

    db = Mock()
    db.get_sugar_range.return_value = []
    db.get_vitals_range.return_value = []

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    plot = Mock()
    screen.ids.trend_plot = plot

    screen._refresh_health_summary()

    assert (
        screen.average_reading_value
        == "No readings in the last 7 days"
    )
    assert "No readings available" in screen.trend_axis_text
    plot.set_data.assert_called_once()


def test_refresh_health_summary_non_default_trend_range(
    monkeypatch,
    running_mdapp,
):
    """
    Covers the non-default trend-range branch:
    lines 667-672.
    """
    screen = HomeScreen()

    screen._trend_unit = "weeks"
    screen._trend_amount = 2
    screen._trend_key = "sugar"

    db = Mock()

    db.get_sugar_range.side_effect = [
        [],
        [
            {
                "log_date": "2026-09-22",
                "value": 105,
                "fasting": 0,
            }
        ],
    ]

    db.get_vitals_range.side_effect = [
        [],
        [],
    ]

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    plot = Mock()
    screen.ids.trend_plot = plot

    monkeypatch.setattr(
        mod,
        "today_str",
        lambda: "2026-09-23",
    )

    screen._refresh_health_summary()

    assert screen.trend_range_label == "2 weeks"
    assert screen.trend_axis_text == "22 Sep"

    plot.set_data.assert_called_once_with(
        ["22 Sep"],
        [105.0],
    )


def test_refresh_health_summary_bp_trend(
    monkeypatch,
    running_mdapp,
):
    """
    Covers the BP-specific axis suffix at line 679.
    """
    screen = HomeScreen()

    screen._trend_key = "bp"
    screen._trend_unit = "weeks"
    screen._trend_amount = 2

    db = Mock()

    db.get_sugar_range.return_value = []

    db.get_vitals_range.return_value = [
        {
            "log_date": "2026-09-22",
            "vital_type": "BP",
            "value1": 120,
            "value2": 80,
        }
    ]

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    plot = Mock()
    screen.ids.trend_plot = plot

    monkeypatch.setattr(
        mod,
        "today_str",
        lambda: "2026-09-23",
    )

    screen._refresh_health_summary()

    assert screen.trend_range_label == "2 weeks"
    assert "(Systolic / Diastolic)" in screen.trend_axis_text

    plot.set_data.assert_called_once_with(
        ["22 Sep"],
        [(120.0, 80.0)],
    )


# ============================================================================
# Trend range dialog
# ============================================================================


def test_open_trend_range_dialog_creates_dialog(
    running_mdapp,
    monkeypatch,
):
    captured = []

    monkeypatch.setattr(
        mod.MDDialog,
        "open",
        lambda self: captured.append(self),
    )

    screen = HomeScreen()

    screen.open_trend_range_dialog()

    assert captured


def test_open_trend_range_dialog_invalid_text_does_not_apply(
    running_mdapp,
    monkeypatch,
):
    """
    Covers the ValueError/invalid-input path in the APPLY callback.
    """
    screen = HomeScreen()
    screen._trend_amount = 7
    screen._refresh_health_summary = Mock()

    captured = []

    monkeypatch.setattr(
        mod.MDDialog,
        "open",
        lambda self: captured.append(self),
    )

    monkeypatch.setattr(
        mod.MDDialog,
        "dismiss",
        Mock(),
    )

    screen.open_trend_range_dialog()

    dialog = captured[0]

    amount = dialog.content_cls.children[-2]

    amount.text = "abc"

    apply_button = next(
        button
        for button in dialog.buttons
        if getattr(button, "text", "") == "APPLY"
    )

    apply_button.dispatch("on_release")

    assert screen._trend_amount == 7
    screen._refresh_health_summary.assert_not_called()


def test_open_trend_range_dialog_zero_does_not_apply(
    running_mdapp,
    monkeypatch,
):
    """
    Covers the value <= 0 path in the APPLY callback.
    """
    screen = HomeScreen()
    screen._trend_amount = 7
    screen._refresh_health_summary = Mock()

    captured = []

    monkeypatch.setattr(
        mod.MDDialog,
        "open",
        lambda self: captured.append(self),
    )

    screen.open_trend_range_dialog()

    dialog = captured[0]

    amount = dialog.content_cls.children[-2]
    amount.text = "0"

    apply_button = next(
        button
        for button in dialog.buttons
        if getattr(button, "text", "") == "APPLY"
    )

    apply_button.dispatch("on_release")

    assert screen._trend_amount == 7
    screen._refresh_health_summary.assert_not_called()


def test_open_trend_range_dialog_valid_apply(
    running_mdapp,
    monkeypatch,
):
    """
    Covers the successful APPLY path:
    lines 743-745.
    """
    screen = HomeScreen()
    screen._trend_amount = 7
    screen._refresh_health_summary = Mock()

    captured = []

    monkeypatch.setattr(
        mod.MDDialog,
        "open",
        lambda self: captured.append(self),
    )

    monkeypatch.setattr(
        mod.MDDialog,
        "dismiss",
        Mock(),
    )

    screen.open_trend_range_dialog()

    dialog = captured[0]

    amount = dialog.content_cls.children[-2]
    amount.text = "14"

    apply_button = next(
        button
        for button in dialog.buttons
        if getattr(button, "text", "") == "APPLY"
    )

    apply_button.dispatch("on_release")

    assert screen._trend_amount == 14
    screen._refresh_health_summary.assert_called_once()


def test_select_trend_unit(running_mdapp):
    screen = HomeScreen()

    buttons = {
        "days": Mock(),
        "weeks": Mock(),
        "months": Mock(),
    }

    screen._select_trend_unit("weeks", buttons)

    assert screen._trend_unit == "weeks"
    assert (
        buttons["weeks"].md_bg_color
        != buttons["days"].md_bg_color
    )


# ============================================================================
# Selection dialogs
# ============================================================================


def test_open_selection_dialog_creates_items(
    running_mdapp,
    monkeypatch,
):
    screen = HomeScreen()

    captured = []

    monkeypatch.setattr(
        mod.MDDialog,
        "open",
        lambda self: captured.append(self),
    )

    screen._open_selection_dialog(
        "Title",
        [("a", "A"), ("b", "B")],
        "a",
        Mock(),
    )

    assert captured


def test_open_average_selector_delegates(running_mdapp):
    screen = HomeScreen()

    screen._open_selection_dialog = Mock()

    screen.open_average_selector()

    screen._open_selection_dialog.assert_called_once()


def test_open_trend_reading_selector_delegates(running_mdapp):
    screen = HomeScreen()

    screen._open_selection_dialog = Mock()

    screen.open_trend_reading_selector()

    screen._open_selection_dialog.assert_called_once()


def test_set_average_reading(
    monkeypatch,
    running_mdapp,
):
    screen = HomeScreen()

    screen._refresh_health_summary = Mock()

    screen._set_average_reading("bp")

    assert screen._average_key == "bp"
    assert screen.average_reading_label == "Blood Pressure"

    screen._refresh_health_summary.assert_called_once()


def test_set_trend_reading(running_mdapp):
    screen = HomeScreen()

    screen._refresh_health_summary = Mock()

    screen._set_trend_reading("o2")

    assert screen._trend_key == "o2"
    assert screen.trend_reading_label == "Oxygen (SpO2)"

    screen._refresh_health_summary.assert_called_once()


# ============================================================================
# Date picker
# ============================================================================


def test_open_date_picker(
    running_mdapp,
    monkeypatch,
):
    picker = Mock()

    monkeypatch.setattr(
        mod,
        "MDDatePicker",
        lambda: picker,
    )

    screen = HomeScreen()

    screen.open_date_picker()

    picker.open.assert_called_once()


def test_date_selected_refreshes(running_mdapp):
    screen = HomeScreen()

    screen.refresh = Mock()

    screen._date_selected(
        None,
        date(2026, 9, 23),
        None,
    )

    assert screen.selected_date == "2026-09-23"

    screen.refresh.assert_called_once()


# ============================================================================
# HomeScreen.refresh
# ============================================================================


def test_refresh_with_all_record_types(
    monkeypatch,
    running_mdapp,
):
    """
    Exercises the complete populated refresh path:
    events, sugar, vitals, medications and consultation notes.
    """
    screen = HomeScreen()

    screen.selected_date = "2026-09-23"

    db = Mock()

    db.get_events_for_date.return_value = [
        {"title": "Doctor appointment"},
        {"title": ""},
        {"title": None},
        {"title": "  Ultrasound  "},
    ]

    db.get_sugar_for_date.return_value = [
        {
            "slot": "Before Breakfast",
            "value": 95,
        },
        {
            "slot": "After Lunch",
            "value": None,
        },
    ]

    db.get_vitals_for_date.return_value = [
        {
            "vital_type": "BP",
            "value1": 120,
            "value2": 80,
        },
        {
            "vital_type": "O2",
            "value1": 98,
            "value2": None,
        },
        {
            "vital_type": "Pulse",
            "value1": 72,
            "value2": None,
        },
        {
            "vital_type": "Weight",
            "value1": 65,
            "value2": None,
        },
        {
            "vital_type": "Unknown",
            "value1": 10,
            "value2": 20,
        },
        {
            "vital_type": "BP",
            "value1": None,
            "value2": 80,
        },
    ]

    db.get_medications_for_date.return_value = [
        {
            "name": "Iron",
            "dosage": "1 tablet",
            "taken": 1,
        },
        {
            "name": "Vitamin D",
            "dosage": "",
            "taken": 0,
        },
        {
            "name": "",
            "dosage": "1 tablet",
            "taken": 1,
        },
        {
            "name": None,
            "dosage": "",
            "taken": 0,
        },
    ]

    db.get_consultation_notes_for_date.return_value = [
        {"notes": "Drink more water"},
        {"notes": ""},
        {"notes": None},
    ]

    db.get_sugar_range.return_value = []
    db.get_vitals_range.return_value = []

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    screen._refresh_health_summary = Mock()

    screen.refresh()

    expected_lines = [
        "Event  •  Doctor appointment",
        "Event  •  Ultrasound",
        "Before Breakfast  •  95 mg/dL",
        "Blood Pressure  •  120 / 80 mmHg",
        "Oxygen  •  98 %",
        "Pulse  •  72 bpm",
        "Weight  •  65 kg",
        "Unknown  •  10 / 20",
        "Medication  •  Iron  •  1 tablet  •  Taken",
        "Medication  •  Vitamin D  •  Not taken",
        "Note  •  Drink more water",
    ]

    assert screen.date_label == "23 Sep 2026"
    assert screen.summary_text == "\n".join(expected_lines)

    expected_height = f"{max(145, 76 + len(expected_lines) * 28)}dp"
    assert screen.summary_card_height == expected_height

    screen._refresh_health_summary.assert_called_once()


def test_refresh_empty_day(
    monkeypatch,
    running_mdapp,
):
    screen = HomeScreen()
    screen.selected_date = "2026-09-23"

    db = Mock()

    db.get_events_for_date.return_value = []
    db.get_sugar_for_date.return_value = []
    db.get_vitals_for_date.return_value = []
    db.get_medications_for_date.return_value = []
    db.get_consultation_notes_for_date.return_value = []

    db.get_sugar_range.return_value = []
    db.get_vitals_range.return_value = []

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    screen._refresh_health_summary = Mock()

    screen.refresh()

    assert (
        screen.summary_text
        == (
            "Nothing has been recorded for this day yet.\n"
            "Use the buttons below whenever you want to add something."
        )
    )

    assert screen.summary_card_height == "165dp"

    screen._refresh_health_summary.assert_called_once()


# ============================================================================
# Screen navigation / quick add
# ============================================================================


def test_prepare_screen(running_mdapp):
    screen = HomeScreen()

    screen.selected_date = "2026-09-23"

    target = SimpleNamespace(
        current_date="",
        selected_date="",
    )

    screen.manager = SimpleNamespace(
        get_screen=lambda _: target
    )

    assert screen._prepare_screen("x") is target
    assert target.current_date == "2026-09-23"
    assert target.selected_date == "2026-09-23"


def test_prepare_screen_only_selected_date(running_mdapp):
    screen = HomeScreen()

    screen.selected_date = "2026-09-23"

    target = SimpleNamespace(selected_date="")

    screen.manager = SimpleNamespace(
        get_screen=lambda _: target
    )

    screen._prepare_screen("x")

    assert target.selected_date == "2026-09-23"


def test_target_screen(running_mdapp):
    target = object()

    screen = HomeScreen()

    screen.manager = SimpleNamespace(
        get_screen=lambda name: target
    )

    assert screen._target_screen("sugar") is target


def test_quick_add_event_and_note(running_mdapp):
    screen = HomeScreen()

    target = Mock()

    screen._prepare_screen = Mock(
        return_value=target
    )

    screen._quick_add_event()
    target.open_add_event.assert_called_once()

    screen._quick_add_note()
    target.open_add_note.assert_called_once()


def test_quick_add_all_actions(running_mdapp):
    screen = HomeScreen()

    target = Mock()

    screen._prepare_screen = Mock(
        return_value=target
    )

    screen._quick_add_sugar()
    screen._quick_add_vitals()
    screen._quick_add_medication()

    target.open_entry_dialog.assert_called()
    target.open_type_chooser.assert_called_once()


def test_open_quick_add_creates_dialog(
    running_mdapp,
    monkeypatch,
):
    captured = []

    monkeypatch.setattr(
        mod.MDDialog,
        "open",
        lambda self: captured.append(self),
    )

    HomeScreen().open_quick_add()

    assert captured


# ============================================================================
# on_pre_enter
# ============================================================================


def test_on_pre_enter_without_reference_schedules_setup(
    monkeypatch,
    running_mdapp,
):
    screen = HomeScreen()

    screen.selected_date = ""

    screen._refresh_pregnancy_journey = Mock()
    screen.refresh = Mock()

    db = Mock()
    db.get_setting.return_value = None

    monkeypatch.setattr(
        mod.Database,
        "instance",
        classmethod(lambda cls: db),
    )

    scheduled = []

    monkeypatch.setattr(
        mod.Clock,
        "schedule_once",
        lambda cb, delay: scheduled.append((cb, delay)),
    )

    monkeypatch.setattr(
        mod,
        "today_str",
        lambda: "2026-09-23",
    )

    screen.on_pre_enter()

    assert screen.selected_date == "2026-09-23"
    assert scheduled[0][1] == 0.2



def test_home_on_pre_enter_existing_date_and_reference_does_not_schedule(
    running_mdapp, monkeypatch
):
    screen = HomeScreen()
    screen.selected_date = "2026-09-23"
    screen._refresh_pregnancy_journey = Mock()
    screen.refresh = Mock()

    db = Mock()
    db.get_setting.return_value = "2026-09-01"
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )
    schedule = Mock()
    monkeypatch.setattr(mod.Clock, "schedule_once", schedule)

    screen.on_pre_enter()

    schedule.assert_not_called()


def test_home_on_pre_enter_scheduled_callback_executes(
    running_mdapp, monkeypatch
):
    screen = HomeScreen()
    screen.selected_date = ""
    screen._refresh_pregnancy_journey = Mock()
    screen.refresh = Mock()
    screen._open_pregnancy_setup = Mock()

    db = Mock()
    db.get_setting.return_value = None
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )

    scheduled = []
    monkeypatch.setattr(
        mod.Clock, "schedule_once",
        lambda callback, delay: scheduled.append((callback, delay)),
    )
    monkeypatch.setattr(mod, "today_str", lambda: "2026-09-23")

    screen.on_pre_enter()
    scheduled[0][0](0)

    screen._open_pregnancy_setup.assert_called_once()


def test_home_pregnancy_setup_dialog_callbacks(
    running_mdapp, monkeypatch
):
    captured = []
    monkeypatch.setattr(mod.MDDialog, "open", lambda self: captured.append(self))
    monkeypatch.setattr(mod.MDDatePicker, "open", lambda self: None)

    screen = HomeScreen()
    screen._open_pregnancy_setup()
    dialog = captured[-1]

    # Exercise the per-unit lambda bindings.
    unit_button = _find_widget_by_text(dialog.content_cls, "Days")
    assert unit_button is not None
    unit_button.dispatch("on_release")
    assert screen._setup_unit == "days"

    # Exercise the date-button lambda and the date-picker on_save lambda.
    date_button = _find_widget_by_text_prefix(dialog.content_cls, "Reference date:")
    assert date_button is not None
    screen._open_setup_date_picker = Mock()
    # The original binding was created before the instance method was replaced,
    # so invoke the bound callback captured by the button.
    date_button.dispatch("on_release")
    screen._open_setup_date_picker.assert_called_once()

    # Exercise the SAVE lambda with a valid value and a real dialog.
    db = Mock()
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )
    monkeypatch.setattr(mod, "today_str", lambda: "2026-09-23")
    screen._refresh_pregnancy_journey = Mock()
    screen._setup_date = "2026-09-20"
    dialog.buttons[0].dispatch("on_release")

    assert db.set_setting.call_count == 3


def test_home_setup_date_picker_on_save_callback(running_mdapp, monkeypatch):
    picker_holder = []

    class FakePicker:
        def bind(self, **kwargs):
            self.callback = kwargs["on_save"]

        def open(self):
            picker_holder.append(self)

    monkeypatch.setattr(mod, "MDDatePicker", FakePicker)
    screen = HomeScreen()
    button = type("Button", (), {"text": ""})()

    screen._open_setup_date_picker(button)
    picker = picker_holder[0]

    class Value:
        def strftime(self, fmt):
            assert fmt == "%Y-%m-%d"
            return "2026-09-22"

    picker.callback(None, Value(), None)
    assert screen._setup_date == "2026-09-22"
    assert "22 Sep 2026" in button.text


def test_home_save_setup_without_dialog_covers_false_branch(
    running_mdapp, monkeypatch
):
    screen = HomeScreen()
    screen._setup_date = "2026-09-20"
    screen._setup_unit = "weeks"
    screen._setup_dialog = None

    db = Mock()
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )
    monkeypatch.setattr(mod, "today_str", lambda: "2026-09-23")
    screen._refresh_pregnancy_journey = Mock()

    screen._save_pregnancy_setup("5", None)

    db.set_setting.assert_called()


def test_home_health_summary_uses_existing_seven_readings(
    running_mdapp, monkeypatch
):
    screen = HomeScreen()
    screen._average_key = "sugar"
    screen._trend_key = "sugar"
    screen._trend_unit = "days"
    screen._trend_amount = 7

    rows = [
        {"log_date": f"2026-09-{day:02d}", "value": 100 + day, "fasting": 0}
        for day in range(17, 24)
    ]
    db = Mock()
    db.get_sugar_range.return_value = rows
    db.get_vitals_range.return_value = []
    monkeypatch.setattr(
        mod.Database, "instance", classmethod(lambda cls: db)
    )
    monkeypatch.setattr(mod, "today_str", lambda: "2026-09-23")

    screen._refresh_health_summary()

    assert screen.trend_range_label == "Last 7 available readings"
    # No fallback query is needed when seven readings are already available.
    assert db.get_sugar_range.call_count == 1


def test_home_selection_dialog_item_and_cancel_callbacks(
    running_mdapp, monkeypatch
):
    captured = []
    monkeypatch.setattr(mod.MDDialog, "open", lambda self: captured.append(self))

    callback = Mock()
    screen = HomeScreen()
    screen._open_selection_dialog(
        "Select", [("a", "A"), ("b", "B")], "a", callback
    )
    dialog = captured[-1]

    item = next(
        child for child in dialog.content_cls.children
        if getattr(child, "text", None) == "A"
    )
    item.dispatch("on_release")
    callback.assert_called_once_with("a")

    # Re-open to execute the CANCEL lambda.
    screen._open_selection_dialog(
        "Select", [("a", "A")], "a", callback
    )
    captured[-1].buttons[0].dispatch("on_release")


def test_home_trend_unit_and_cancel_callbacks(running_mdapp, monkeypatch):
    captured = []
    monkeypatch.setattr(mod.MDDialog, "open", lambda self: captured.append(self))

    screen = HomeScreen()
    screen.open_trend_range_dialog()
    dialog = captured[-1]

    unit_button = _find_widget_by_text(dialog.content_cls, "Days")
    assert unit_button is not None
    unit_button.dispatch("on_release")
    assert screen._trend_unit == "days"

    dialog.buttons[0].dispatch("on_release")


def test_home_quick_add_item_and_cancel_callbacks(running_mdapp, monkeypatch):
    captured = []
    monkeypatch.setattr(mod.MDDialog, "open", lambda self: captured.append(self))

    screen = HomeScreen()
    screen._quick_add_sugar = Mock()
    screen.open_quick_add()
    dialog = captured[-1]

    button = _find_widget_containing_text(dialog.content_cls, "Sugar")
    assert button is not None
    button.dispatch("on_release")
    screen._quick_add_sugar.assert_called_once()

    screen.open_quick_add()
    captured[-1].buttons[0].dispatch("on_release")


def test_home_prepare_screen_without_selected_date_attribute(
    running_mdapp, monkeypatch
):
    screen = HomeScreen()
    screen.selected_date = "2026-09-23"

    target = SimpleNamespace(current_date="")
    monkeypatch.setattr(screen, "_target_screen", lambda name: target)

    result = screen._prepare_screen("dummy")

    assert result is target
    assert target.current_date == "2026-09-23"
    assert not hasattr(target, "selected_date")


def _find_widget_by_text(widget, text):
    """Recursively find a Kivy widget whose text matches."""
    if getattr(widget, "text", None) == text:
        return widget

    for child in getattr(widget, "children", []):
        result = _find_widget_by_text(child, text)
        if result is not None:
            return result

    return None

def _find_widget_by_text(widget, text):
    """Recursively find a Kivy widget whose text matches."""
    if getattr(widget, "text", None) == text:
        return widget
    for child in getattr(widget, "children", []):
        result = _find_widget_by_text(child, text)
        if result is not None:
            return result
    return None

def _find_widget_containing_text(widget, text):
    """Recursively find a widget whose text contains the requested text."""
    value = getattr(widget, "text", None)
    if isinstance(value, str) and text in value:
        return widget
    for child in getattr(widget, "children", []):
        result = _find_widget_containing_text(child, text)
        if result is not None:
            return result
    return None

def _find_widget_by_text_prefix(widget, prefix):
    """Recursively find a Kivy widget whose text starts with prefix."""
    text = getattr(widget, "text", None)
    if isinstance(text, str) and text.startswith(prefix):
        return widget
    for child in getattr(widget, "children", []):
        result = _find_widget_by_text_prefix(child, prefix)
        if result is not None:
            return result
    return None
