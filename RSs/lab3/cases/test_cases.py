from main import division
import pytest

def test_division():
    assert division(10, 2) == 5
    assert division(20, 2) == 10
    assert division(10, -2) == -5
    assert division(10, 2) == 5

@pytest.mark.parametrize("a, b, expected_result", [(10, 2, 5), (20, 2, 10), (30, -3, -10,), (5, 2, 2.5)])


def test_division_ok(a, b, expected_result):
    assert division(a, b) == expected_result

@pytest.mark.parametrize("expected_exception, divider, divis", [(ZeroDivisionError, 0, 10), (TypeError, "2", 20)])


def test_division_with_error(expected_exception, divider, divis):
    with pytest.raises(expected_exception):
        division(divis, divider)
