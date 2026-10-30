from datetime import timedelta

import pytest

from src.folego.calculadora import (
    ciclo_atual, ciclo_de, com_dia_pagamento, mudar_dia_pagamento,
    MudancaDiaPagamento,
)
from src.folego.modelos import Ciclo, Configuracoes
from .cenario import data

outubro = Ciclo(data(1, 10), data(31, 10))


def test_rn01_ciclo_vai_do_dia_do_pagamento_ate_a_vespera_do_proximo():
    assert ciclo_de(data(1, 10), 1) == outubro
    assert ciclo_de(data(31, 10), 1) == outubro
    assert ciclo_de(data(20, 10), 15) == Ciclo(data(15, 10), data(14, 11))


def test_rn01_data_antes_do_dia_do_pagamento_pertence_ao_mes_anterior():
    assert ciclo_de(data(14, 10), 15) == Ciclo(data(15, 9), data(14, 10))


def test_rn01_primeiro_e_ultimo_dia_pertencem_ao_ciclo():
    assert data(1, 10) in outubro
    assert data(31, 10) in outubro
    assert data(30, 9) not in outubro
    assert data(1, 11) not in outubro


def test_rn01_ciclo_atravessa_a_virada_do_ano():
    assert ciclo_de(data(10, 1, 2027), 15) == Ciclo(data(15, 12), data(14, 1, 2027))
    assert ciclo_de(data(31, 12), 1) == Ciclo(data(1, 12), data(31, 12))
    assert ciclo_de(data(1, 1, 2027), 1) == Ciclo(data(1, 1, 2027), data(31, 1, 2027))


def test_rn01_mudar_o_dia_de_1_para_15_em_10_10_termina_o_ciclo_em_14_10():
    esperado = MudancaDiaPagamento(Ciclo(data(1, 10), data(14, 10)), None)
    assert mudar_dia_pagamento(outubro, 15, data(10, 10)) == esperado


def test_rn01_depois_da_mudanca_os_ciclos_seguem_o_novo_dia():
    curto = mudar_dia_pagamento(outubro, 15, data(10, 10)).atual
    assert ciclo_de(curto.fim + timedelta(days=1), 15) == Ciclo(data(15, 10), data(14, 11))


def test_rn01_mudar_para_um_dia_que_ja_passou_estica_o_ciclo():
    # dia 15 -> 5 em 20/10: a próxima ocorrência do dia 5 é 05/11
    atual = Ciclo(data(15, 10), data(14, 11))
    assert mudar_dia_pagamento(atual, 5, data(20, 10)).atual == Ciclo(data(15, 10), data(4, 11))


def test_rn01_mudar_para_o_dia_de_hoje_fecha_o_ciclo_ontem_e_abre_um_novo():
    mudanca = mudar_dia_pagamento(outubro, 15, data(15, 10))
    assert mudanca.atual == Ciclo(data(15, 10), data(14, 11))
    assert mudanca.fechado == Ciclo(data(1, 10), data(14, 10))


def test_rn01_mudar_no_primeiro_dia_do_ciclo_para_hoje_nao_fecha_nada():
    # RN02: 31 -> 28 em 28/02/2027; o ciclo do dia 31 também começou em 28/02
    atual = ciclo_de(data(28, 2, 2027), 31)
    assert atual == Ciclo(data(28, 2, 2027), data(30, 3, 2027))
    esperado = MudancaDiaPagamento(Ciclo(data(28, 2, 2027), data(27, 3, 2027)), None)
    assert mudar_dia_pagamento(atual, 28, data(28, 2, 2027)) == esperado


def test_rn01_mudar_para_o_mesmo_dia_nao_muda_nada():
    esperado = MudancaDiaPagamento(outubro, None)
    assert mudar_dia_pagamento(outubro, 1, data(1, 10)) == esperado
    assert mudar_dia_pagamento(outubro, 1, data(10, 10)) == esperado


def test_rn01_mudar_para_31_num_mes_de_30_dias_usa_o_ultimo_dia():
    novembro = Ciclo(data(1, 11), data(30, 11))
    assert mudar_dia_pagamento(novembro, 31, data(10, 11)).atual == Ciclo(data(1, 11), data(29, 11))


def test_rn01_mudanca_com_data_fora_do_ciclo_atual_e_recusada():
    with pytest.raises(ValueError):
        mudar_dia_pagamento(outubro, 15, data(1, 11))


def test_rn01_sem_mudanca_o_ciclo_atual_sai_do_dia_do_pagamento():
    assert Configuracoes().ciclo_irregular is None
    assert ciclo_atual(Configuracoes(), data(20, 10)) == outubro


def test_rn01_depois_de_mudar_o_dia_em_20_10_o_ciclo_atual_vai_ate_14_11():
    config = com_dia_pagamento(Configuracoes(dia_pagamento=1), 15, data(20, 10)).configuracoes
    assert config.ciclo_irregular == Ciclo(data(1, 10), data(14, 11))
    assert ciclo_atual(config, data(25, 10)) == Ciclo(data(1, 10), data(14, 11))
    assert ciclo_atual(config, data(15, 11)) == Ciclo(data(15, 11), data(14, 12))


def test_rn01_depois_de_mudar_o_dia_em_10_10_o_ciclo_atual_vai_ate_14_10():
    config = com_dia_pagamento(Configuracoes(dia_pagamento=1), 15, data(10, 10)).configuracoes
    assert ciclo_atual(config, data(14, 10)) == Ciclo(data(1, 10), data(14, 10))
    assert ciclo_atual(config, data(15, 10)) == Ciclo(data(15, 10), data(14, 11))


def test_rn01_mudar_para_o_dia_de_hoje_nao_guarda_ciclo_irregular():
    config = com_dia_pagamento(Configuracoes(dia_pagamento=1), 15, data(15, 10)).configuracoes
    assert config.ciclo_irregular is None
    assert config.dia_pagamento == 15
    assert ciclo_atual(config, data(15, 10)) == Ciclo(data(15, 10), data(14, 11))


def test_rn01_mudar_o_dia_devolve_junto_o_ciclo_que_fecha():
    assert com_dia_pagamento(Configuracoes(), 15, data(15, 10)).fechado == Ciclo(data(1, 10), data(14, 10))
    assert com_dia_pagamento(Configuracoes(), 15, data(10, 10)).fechado is None


def test_rn01_segunda_mudanca_dentro_do_ciclo_irregular_mantem_o_inicio():
    # 1 -> 15 em 20/10 (ciclo 01/10-14/11) e depois 15 -> 5 em 25/10: vai até 04/11
    primeira = com_dia_pagamento(Configuracoes(dia_pagamento=1), 15, data(20, 10)).configuracoes
    config = com_dia_pagamento(primeira, 5, data(25, 10)).configuracoes
    assert ciclo_atual(config, data(25, 10)) == Ciclo(data(1, 10), data(4, 11))
    assert ciclo_atual(config, data(5, 11)) == Ciclo(data(5, 11), data(4, 12))


def test_rn02_dia_31_em_abril_comeca_no_dia_30():
    assert ciclo_de(data(15, 5, 2027), 31) == Ciclo(data(30, 4, 2027), data(30, 5, 2027))


def test_rn02_depois_do_mes_curto_o_ciclo_volta_ao_dia_configurado():
    assert ciclo_de(data(31, 5, 2027), 31) == Ciclo(data(31, 5, 2027), data(29, 6, 2027))
    assert ciclo_de(data(30, 6, 2027), 31) == Ciclo(data(30, 6, 2027), data(30, 7, 2027))


def test_rn02_fevereiro_sem_ano_bissexto_termina_no_dia_28():
    assert ciclo_de(data(27, 2, 2027), 30) == Ciclo(data(30, 1, 2027), data(27, 2, 2027))
    assert ciclo_de(data(28, 2, 2027), 30) == Ciclo(data(28, 2, 2027), data(29, 3, 2027))
    assert ciclo_de(data(28, 2, 2027), 29) == Ciclo(data(28, 2, 2027), data(28, 3, 2027))


def test_rn02_fevereiro_em_ano_bissexto_usa_o_dia_29():
    assert ciclo_de(data(29, 2, 2028), 29) == Ciclo(data(29, 2, 2028), data(28, 3, 2028))
    assert ciclo_de(data(29, 2, 2028), 30) == Ciclo(data(29, 2, 2028), data(29, 3, 2028))
    assert ciclo_de(data(29, 2, 2028), 31) == Ciclo(data(29, 2, 2028), data(30, 3, 2028))


@pytest.mark.parametrize("dia", [0, 32])
def test_dia_do_pagamento_fora_de_1_a_31_e_recusado(dia):
    with pytest.raises(ValueError):
        ciclo_de(data(1, 10), dia)
