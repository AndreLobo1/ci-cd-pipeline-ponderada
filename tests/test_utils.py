from core.utils import parse_number


def test_parse_number_handles_ptbr_and_us_formats() -> None:
    assert parse_number("4.160,00") == 4160.0
    assert parse_number("2.722,50") == 2722.5
    assert parse_number("1,234.56") == 1234.56
    assert parse_number("R$ 1.234,00") == 1234.0
    assert parse_number("27,5") == 27.5




# Run 03 – Muitos testes parametrizados
import pytest as _pytest


@_pytest.mark.parametrize("value", list(range(30)))
def test_parametrized_batch_volume(value):
    """30 casos parametrizados para aumentar volume de testes."""
    assert isinstance(value, int)
    assert value >= 0


# Run 07 – Teste propositalmente quebrado
def test_intentional_failure_for_experiment():
    """Teste corrigido — agora passa corretamente."""
    result = 1 + 1
    assert result == 2, "Resultado correto"


# Run 12 – Alto volume de testes parametrizados
@_pytest.mark.parametrize("n", list(range(50)))
def test_high_volume_parametrized(n):
    """50 casos para verificar relação quantidade×duração."""
    assert n * 2 == n + n
