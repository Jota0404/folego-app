import pytest

from src.folego.formatos import (
    formatar_data, formatar_dia_mes, formatar_percentual, formatar_reais,
    ler_centavos, ler_pontos_base,
)
from .cenario import data


def test_reais_com_milhar_e_centavos():
    assert formatar_reais(150_000) == "R$ 1.500,00"
    assert formatar_reais(38_888) == "R$ 388,88"
    assert formatar_reais(1) == "R$ 0,01"
    assert formatar_reais(0) == "R$ 0,00"
    assert formatar_reais(123_456_789) == "R$ 1.234.567,89"
    assert formatar_reais(-10_000) == "-R$ 100,00"


def test_le_valores_digitados_no_formato_brasileiro():
    assert ler_centavos("1.500,00") == 150_000
    assert ler_centavos("1500") == 150_000
    assert ler_centavos("1500,5") == 150_050
    assert ler_centavos("R$ 0,01") == 1
    assert ler_centavos("1.500") == 150_000
    assert ler_centavos("0") == 0


def test_ponto_com_1_ou_2_digitos_no_fim_e_centavo_e_com_3_digitos_e_milhar():
    assert ler_centavos("1500.50") == 150_050
    assert ler_centavos("12.5") == 1_250
    assert ler_centavos("1.50") == 150
    assert ler_centavos("1.500") == 150_000
    assert ler_pontos_base("10.5") == 1050


@pytest.mark.parametrize("texto", [
    "", "abc", "1,505", "1.5000", "1.500.5", "-10",
    "99999999999999999999", "1,2,3", "12a", "1,500.50",
])
def test_texto_que_nao_e_valor_nao_vira_dinheiro(texto):
    assert ler_centavos(texto) is None


def test_percentuais_em_pontos_base():
    assert formatar_percentual(1000) == "10%"
    assert formatar_percentual(1050) == "10,5%"
    assert formatar_percentual(1025) == "10,25%"
    assert ler_pontos_base("10") == 1000
    assert ler_pontos_base("10,5") == 1050
    assert ler_pontos_base("10,25%") == 1025
    assert ler_pontos_base("10,255") is None
    assert ler_pontos_base("dez") is None


def test_data_no_formato_brasileiro():
    assert formatar_data(data(6, 10)) == "06/10/2026"
    assert formatar_dia_mes(data(6, 10)) == "06/10"
