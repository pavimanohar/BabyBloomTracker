import pytest


@pytest.mark.unit
def test_python_test_framework_works():
    """Verify that pytest itself is working."""
    assert True


@pytest.mark.unit
def test_fixture_works(sample_text):
    """Verify that pytest fixtures are working."""
    assert sample_text == "BabyBloomTracker"


@pytest.mark.unit
def test_basic_python_operation():
    """Basic sanity test."""
    result = 10 + 20
    assert result == 30


@pytest.mark.unit
def test_expected_exception():
    """Verify exception assertion support."""
    with pytest.raises(ValueError):
        int("not-a-number")
