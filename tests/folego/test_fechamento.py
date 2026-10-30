from src.folego.calculadora import ciclos_para_fechar
from src.folego.modelos import Ciclo, Configuracoes
from . import cenario
from .cenario import data

config = Configuracoes()
outubro = Ciclo(data(1, 10), data(31, 10))
novembro = Ciclo(data(1, 11), data(30, 11))


def test_sem_gastos_e_sem_ciclos_fechados_nao_ha_o_que_fechar():
    assert ciclos_para_fechar(None, None, config, data(3, 12)) == []


def test_o_ciclo_fecha_no_dia_seguinte_ao_ultimo_dia_dele():
    assert ciclos_para_fechar(None, data(5, 10), config, data(31, 10)) == []
    assert ciclos_para_fechar(None, data(5, 10), config, data(1, 11)) == [outubro]


def test_ciclos_que_terminaram_com_o_app_parado_tambem_fecham():
    assert ciclos_para_fechar(None, data(5, 10), config, data(3, 12)) == [outubro, novembro]


def test_depois_do_ultimo_fechado_so_fecha_os_seguintes_que_ja_terminaram():
    assert ciclos_para_fechar(outubro, data(5, 10), config, data(15, 11)) == []
    assert ciclos_para_fechar(outubro, data(5, 10), config, data(1, 12)) == [novembro]


def test_rn01_o_ciclo_irregular_depois_da_mudanca_do_dia_fecha_inteiro():
    # P14: dia 1 -> 15 em 20/10 deixou o ciclo atual de 01/10 a 14/11
    irregular = Configuracoes(dia_pagamento=15, ciclo_irregular=Ciclo(data(1, 10), data(14, 11)))
    assert ciclos_para_fechar(None, data(5, 10), irregular, data(20, 11)) == [
        Ciclo(data(1, 10), data(14, 11))
    ]
    assert ciclos_para_fechar(None, data(5, 10), irregular, data(15, 12)) == [
        Ciclo(data(1, 10), data(14, 11)),
        Ciclo(data(15, 11), data(14, 12)),
    ]


def test_rn05_o_retrato_guarda_os_totais_do_ciclo():
    fechado = cenario.orcamento.fechar(outubro)
    assert fechado.ciclo == outubro
    assert fechado.resumo.fixas == 120_000
    assert fechado.resumo.disponivel == 150_000
    assert fechado.reserva_invadida == 0
