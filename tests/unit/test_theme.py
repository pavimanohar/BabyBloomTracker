import pytest

from theme import hex_to_rgba


def test_hex_to_rgba_standard_six_digit_with_hash():
    assert hex_to_rgba("#F6A6C1") == pytest.approx(
        [246 / 255, 166 / 255, 193 / 255, 1.0]
    )


def test_hex_to_rgba_six_digit_without_hash():
    assert hex_to_rgba("F6A6C1") == pytest.approx(
        [246 / 255, 166 / 255, 193 / 255, 1.0]
    )


def test_hex_to_rgba_lowercase():
    assert hex_to_rgba("#abcdef") == pytest.approx(
        [171 / 255, 205 / 255, 239 / 255, 1.0]
    )


def test_hex_to_rgba_mixed_case():
    assert hex_to_rgba("#AbCdEf") == pytest.approx(
        [171 / 255, 205 / 255, 239 / 255, 1.0]
    )


def test_hex_to_rgba_black():
    assert hex_to_rgba("#000000") == [0.0, 0.0, 0.0, 1.0]


def test_hex_to_rgba_white():
    assert hex_to_rgba("#FFFFFF") == [1.0, 1.0, 1.0, 1.0]


def test_hex_to_rgba_red():
    assert hex_to_rgba("#FF0000") == [1.0, 0.0, 0.0, 1.0]


def test_hex_to_rgba_green():
    assert hex_to_rgba("#00FF00") == [0.0, 1.0, 0.0, 1.0]


def test_hex_to_rgba_blue():
    assert hex_to_rgba("#0000FF") == [0.0, 0.0, 1.0, 1.0]


def test_hex_to_rgba_alpha_one():
    assert hex_to_rgba("#123456", 1.0) == pytest.approx(
        [18 / 255, 52 / 255, 86 / 255, 1.0]
    )


def test_hex_to_rgba_alpha_zero():
    assert hex_to_rgba("#123456", 0.0) == pytest.approx(
        [18 / 255, 52 / 255, 86 / 255, 0.0]
    )


def test_hex_to_rgba_alpha_half():
    assert hex_to_rgba("#123456", 0.5) == pytest.approx(
        [18 / 255, 52 / 255, 86 / 255, 0.5]
    )


def test_hex_to_rgba_alpha_near_lower_boundary():
    assert hex_to_rgba("#123456", 0.0001)[3] == pytest.approx(0.0001)


def test_hex_to_rgba_alpha_near_upper_boundary():
    assert hex_to_rgba("#123456", 0.9999)[3] == pytest.approx(0.9999)


def test_hex_to_rgba_integer_alpha():
    assert hex_to_rgba("#123456", 1) == pytest.approx(
        [18 / 255, 52 / 255, 86 / 255, 1]
    )


def test_hex_to_rgba_different_valid_colors_same_alpha():
    assert hex_to_rgba("#112233", 0.25)[3] == 0.25
    assert hex_to_rgba("#AABBCC", 0.25)[3] == 0.25


def test_hex_to_rgba_three_digit_hex_fails_due_to_missing_components():
    with pytest.raises(ValueError):
        hex_to_rgba("#ABC")


def test_hex_to_rgba_invalid_hex_character_raises_value_error():
    with pytest.raises(ValueError):
        hex_to_rgba("#GG0000")


def test_hex_to_rgba_empty_string_raises_value_error():
    with pytest.raises(ValueError):
        hex_to_rgba("")


def test_hex_to_rgba_none_raises_attribute_error():
    with pytest.raises(AttributeError):
        hex_to_rgba(None)


def test_hex_to_rgba_non_string_raises_attribute_error():
    with pytest.raises(AttributeError):
        hex_to_rgba(123456)


def test_hex_to_rgba_longer_than_six_digits_uses_first_six_digits():
    assert hex_to_rgba("#123456789") == pytest.approx(
        [18 / 255, 52 / 255, 86 / 255, 1.0]
    )
