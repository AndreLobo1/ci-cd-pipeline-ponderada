from core.utils import parse_number


def test_parse_number_handles_ptbr_and_us_formats() -> None:
    assert parse_number("4.160,00") == 4160.0
    assert parse_number("2.722,50") == 2722.5
    assert parse_number("1,234.56") == 1234.56
    assert parse_number("R$ 1.234,00") == 1234.0
    assert parse_number("27,5") == 27.5



# Run 02 – Teste lento (sleep artificial)
import time as _time


def test_slow_operation_simulates_heavy_computation():
    """Simula operação pesada com sleep de 4 segundos."""
    _time.sleep(4)
    assert True


# Run 03 – Muitos testes parametrizados
import pytest as _pytest


@_pytest.mark.parametrize("value", list(range(30)))
def test_parametrized_batch_volume(value):
    """30 casos parametrizados para aumentar volume de testes."""
    assert isinstance(value, int)
    assert value >= 0
