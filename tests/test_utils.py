import pytest
import time

from core.utils import parse_number


# ---------------------------------------------------------------------------
# Testes originais
# ---------------------------------------------------------------------------

def test_parse_number_handles_ptbr_and_us_formats() -> None:
    assert parse_number("4.160,00") == 4160.0
    assert parse_number("2.722,50") == 2722.5
    assert parse_number("1,234.56") == 1234.56
    assert parse_number("R$ 1.234,00") == 1234.0
    assert parse_number("27,5") == 27.5


# ---------------------------------------------------------------------------
# Run 03 – Muitos testes parametrizados (30 casos)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", list(range(30)))
def test_parametrized_batch_volume(value):
    """30 casos parametrizados para aumentar volume de testes."""
    assert isinstance(value, int)
    assert value >= 0


# ---------------------------------------------------------------------------
# Run 07/08 – Teste corrigido (era intencional na run 07)
# ---------------------------------------------------------------------------

def test_intentional_failure_for_experiment():
    """Corrigido — pipeline verde de volta."""
    result = 1 + 1
    assert result == 2, "Resultado correto"


# ---------------------------------------------------------------------------
# Run 12 – Alto volume de testes parametrizados (50 casos)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n", list(range(50)))
def test_high_volume_parametrized(n):
    """50 casos para verificar relação quantidade×duração."""
    assert n * 2 == n + n
