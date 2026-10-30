import pytest
from src.financas import calcular_saldo, validar_valor


# Teste 1: Caminho Feliz
def test_calcular_saldo_positivo():
    salarios = [3000.0, 500.0]
    despesas = [1000.0, 200.0]
    assert calcular_saldo(salarios, despesas) == 2300.0


# Teste 2: Entrada Inválida
def test_validar_valor_negativo():
    with pytest.raises(ValueError):
        validar_valor(-50)


# Teste 3: Caso Limite
def test_saldo_zerado():
    salarios = [1000.0]
    despesas = [1000.0]
    assert calcular_saldo(salarios, despesas) == 0.0
