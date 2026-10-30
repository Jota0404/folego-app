from src.folego.apresentacao.configuracoes import ler_formulario
from src.folego.modelos import Configuracoes

BASE = Configuracoes(primeiro_uso_concluido=True)


def test_ler_formulario_valido():
    nova = ler_formulario("5", "350,00", "70", "87,5", BASE)
    assert (nova.dia_pagamento, nova.limite_semanal_manual) == (5, 35000)
    assert (nova.percentual_atencao, nova.percentual_critico) == (7000, 8750)
    assert nova.primeiro_uso_concluido


def test_ler_formulario_limite_vazio_e_automatico():
    assert ler_formulario("1", " ", "70", "90", BASE).limite_semanal_manual is None


def test_ler_formulario_erros():
    for args in [("0", "", "70", "90"), ("32", "", "70", "90"), ("x", "", "70", "90"),
                 ("1", "abc", "70", "90"), ("1", "", "abc", "90"), ("1", "", "70", "")]:
        assert isinstance(ler_formulario(*args, BASE), str), args
