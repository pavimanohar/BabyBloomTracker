from datetime import datetime
from unittest.mock import Mock
import utils.time_input as mod


def test_make_time_mask_filter_allows_valid_parts():
    field = Mock()
    field.text = ""
    filt = mod.make_time_mask_filter(field)
    assert callable(filt)
    assert filt("1") == "1"
    assert filt("12") == "12:"


def test_make_time_mask_filter_rejects_bad_characters():
    field = Mock()
    field.text = ""
    filt = mod.make_time_mask_filter(field)
    assert filt("a") == ""
    assert filt(":") == ""


def test_bind_time_field_binds_focus_handler(running_mdapp, monkeypatch):
    field = Mock()
    field.bind = Mock()
    mod.bind_time_field(field)
    field.bind.assert_called_once()


def test_now_12h_format(monkeypatch):
    class FakeDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 9, 23, 14, 5)
    monkeypatch.setattr(mod, "_dt", FakeDateTime)
    assert mod.now_12h() == "02:05 PM"


def test_time_mask_complete_sequence():
    field = Mock()
    field.text = ""
    filt = mod.make_time_mask_filter(field)
    assert filt("1") == "1"
    field.text = "1"
    assert filt("2") == "2:"
    field.text = "12:"
    assert filt("3") == "3"
    field.text = "12:3"
    assert filt("0") == "0 "
    field.text = "12:30 "
    assert filt("p") == "PM"


def test_time_mask_from_undo_passthrough():
    field = Mock()
    field.text = ""
    filt = mod.make_time_mask_filter(field)
    assert filt("abc", from_undo=True) == "abc"


def test_time_mask_rejects_invalid_first_and_minute_chars():
    field = Mock()
    field.text = ""
    filt = mod.make_time_mask_filter(field)
    assert filt("9") == ""
    field.text = "12:"
    assert filt("x") == ""
    field.text = "12:6"
    assert filt("0") == "0 "


def test_bind_time_field_picker_valid_and_save(monkeypatch):
    field = Mock()
    field.text = "02:30 PM"
    picker = Mock()
    monkeypatch.setattr(mod, "MDTimePicker", lambda: picker)
    mod.bind_time_field(field)
    callback = field.bind.call_args.kwargs["focus"]
    callback(field, True)
    picker.set_time.assert_called_once()
    save = picker.bind.call_args.kwargs["on_save"]
    from datetime import time
    save(picker, time(9, 5))
    assert field.text == "09:05 AM"
    picker.open.assert_called_once()


def test_bind_time_field_picker_invalid_time(monkeypatch):
    field = Mock()
    field.text = "bad"
    picker = Mock()
    monkeypatch.setattr(mod, "MDTimePicker", lambda: picker)
    mod.bind_time_field(field)
    callback = field.bind.call_args.kwargs["focus"]
    callback(field, True)
    picker.set_time.assert_not_called()
    picker.open.assert_called_once()


def test_bind_time_field_ignores_unfocus(monkeypatch):
    field = Mock()
    field.text = ""
    picker = Mock()
    monkeypatch.setattr(mod, "MDTimePicker", lambda: picker)
    mod.bind_time_field(field)
    callback = field.bind.call_args.kwargs["focus"]
    callback(field, False)
    picker.open.assert_not_called()

def test_time_mask_filter_handles_empty_value():
    from utils.time_input import make_time_mask_filter

    field = type("Field", (), {"text": ""})()
    filt = make_time_mask_filter(field)

    assert filt("") == ""


def test_time_mask_filter_rejects_non_digit_character():
    from utils.time_input import make_time_mask_filter

    field = type("Field", (), {"text": ""})()
    filt = make_time_mask_filter(field)

    assert filt("a") == ""


def test_time_mask_filter_limits_minutes():
    from utils.time_input import make_time_mask_filter

    field = type("Field", (), {"text": ""})()
    filt = make_time_mask_filter(field)

    result = filt("12:9")

    assert result == "12:"


def test_time_mask_filter_builds_valid_time_prefix():
    from utils.time_input import make_time_mask_filter

    field = type("Field", (), {"text": ""})()
    filt = make_time_mask_filter(field)

    result = filt("12:34")

    assert result == "12:34 "

def test_time_mask_allows_single_digit_hour():
    field = Mock()
    field.text = ""
    filt = mod.make_time_mask_filter(field)

    assert filt("0") == "0"
    assert filt("5") == ""


def test_time_mask_allows_second_digit_for_single_digit_hour():
    field = Mock()
    field.text = "1"
    filt = mod.make_time_mask_filter(field)

    assert filt("2") == "2:"


def test_time_mask_rejects_extra_character_at_colon_position():
    field = Mock()
    field.text = "12:"
    filt = mod.make_time_mask_filter(field)

    assert filt("x") == ""


def test_time_mask_rejects_extra_character_after_minutes():
    field = Mock()
    field.text = "12:34 "
    filt = mod.make_time_mask_filter(field)

    assert filt("x") == ""

def test_time_mask_allows_second_digit_for_hour_0_to_9():
    field = Mock()
    field.text = "5"
    filt = mod.make_time_mask_filter(field)

    assert filt("6") == "6:"


def test_time_mask_ignores_character_at_auto_colon_position():
    field = Mock()
    field.text = "12"
    filt = mod.make_time_mask_filter(field)

    assert filt(":") == ""


def test_time_mask_ignores_character_at_auto_space_position():
    field = Mock()
    field.text = "12:34"
    filt = mod.make_time_mask_filter(field)

    assert filt(" ") == ""
