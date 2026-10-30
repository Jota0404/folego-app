from dataclasses import replace
from datetime import timedelta

from src.folego.calculadora import (
    ativa_em, ciclo_de, entra_em, mudar_dia_pagamento, valor_no_ciclo,
)
from src.folego.modelos import (
    Ciclo, ContaFixa, Entrada, Gasto, MetaReserva, Resumo, TipoEntrada, TipoMeta,
)
from . import cenario
from .cenario import aluguel, celular, data

base = cenario.orcamento
outubro = Ciclo(data(1, 10), data(31, 10))


def ciclo(mes, ano=2026):
    return ciclo_de(data(1, mes, ano), cenario.DIA_PAGAMENTO)


def com_gastos(*gastos):
    return replace(base, gastos=list(gastos))


def test_rn03_conta_de_3_meses_vale_nos_3_ciclos_a_partir_do_inicio():
    assert not ativa_em(celular, ciclo(9))
    assert ativa_em(celular, ciclo(10))
    assert ativa_em(celular, ciclo(11))
    assert ativa_em(celular, ciclo(12))
    assert not ativa_em(celular, ciclo(1, 2027))


def test_rn03_conta_de_1_mes_so_vale_no_ciclo_de_inicio():
    conta = ContaFixa(5_000, ciclo_inicio=data(1, 10), duracao_meses=1)
    assert ativa_em(conta, ciclo(10))
    assert not ativa_em(conta, ciclo(11))


def test_rn03_duracao_com_dia_do_pagamento_31_conta_fevereiro_e_abril():
    conta = ContaFixa(10_000, ciclo_inicio=data(31, 1, 2027), duracao_meses=2)
    assert ativa_em(conta, ciclo_de(data(31, 1, 2027), 31))
    assert ativa_em(conta, ciclo_de(data(28, 2, 2027), 31))
    assert not ativa_em(conta, ciclo_de(data(31, 3, 2027), 31))


def test_rn03_mudanca_do_dia_que_cria_dois_ciclos_no_mes_desconta_nos_dois():
    # 1 -> 15 em 10/10 cria 01-14/10 e 15/10-14/11, os dois "de outubro"
    atual = mudar_dia_pagamento(outubro, 15, data(10, 10)).atual
    ciclos = [atual]
    while len(ciclos) < 5:
        ciclos.append(ciclo_de(ciclos[-1].fim + timedelta(days=1), 15))
    assert ciclos[-1].inicio == data(15, 1, 2027)
    assert [ativa_em(celular, c) for c in ciclos] == [True, True, True, True, False]


def test_rn03_mudanca_de_31_para_1_que_pula_fevereiro_desconta_uma_vez_a_menos():
    # limitação aceita pelo dono (P15)
    conta = ContaFixa(10_000, ciclo_inicio=data(31, 12), duracao_meses=3)
    janeiro = mudar_dia_pagamento(ciclo_de(data(5, 2, 2027), 31), 1, data(5, 2, 2027)).atual
    assert janeiro == Ciclo(data(31, 1, 2027), data(28, 2, 2027))
    proximo = ciclo_de(data(1, 3, 2027), 1)
    ciclos = [ciclo_de(data(31, 12), 31), janeiro, proximo]
    assert [ativa_em(conta, c) for c in ciclos] == [True, True, False]


def test_rn04_conta_sem_fim_continua_ativa_anos_depois():
    assert ativa_em(aluguel, ciclo(10, 2036))


def test_rn04_conta_encerrada_no_meio_do_ciclo_ainda_desconta_nele():
    encerrado = replace(aluguel, encerrada_em=data(10, 10))
    assert ativa_em(encerrado, ciclo(10))
    assert not ativa_em(encerrado, ciclo(11))
    assert replace(base, contas=[encerrado, celular]).resumo(outubro).disponivel == 150_000


def test_rn04_conta_encerrada_no_ultimo_ou_no_primeiro_dia_do_ciclo():
    assert ativa_em(replace(aluguel, encerrada_em=data(31, 10)), ciclo(10))
    assert not ativa_em(replace(aluguel, encerrada_em=data(31, 10)), ciclo(11))
    assert ativa_em(replace(aluguel, encerrada_em=data(1, 11)), ciclo(11))


def test_rn04_conta_com_duracao_encerrada_antes_do_fim_sai_no_ciclo_seguinte():
    encerrado = replace(celular, encerrada_em=data(15, 11))
    assert ativa_em(encerrado, ciclo(11))
    assert not ativa_em(encerrado, ciclo(12))


def test_rn05_editar_o_valor_da_conta_muda_o_ciclo_atual_e_os_futuros():
    editado = replace(base, contas=[replace(aluguel, valor_centavos=110_000), celular])
    assert base.resumo(outubro).disponivel == 150_000
    assert editado.resumo(outubro).disponivel == 140_000
    assert editado.resumo(ciclo(11)).disponivel == 140_000
    assert editado.resumo(ciclo(1, 2027)).disponivel == 160_000


def test_rn06_metas_de_valor_fixo_e_percentual_se_somam():
    duas = replace(base, metas=[cenario.reserva, MetaReserva(TipoMeta.VALOR, 50_000)])
    assert duas.resumo(outubro).reserva == 80_000
    assert duas.resumo(outubro).disponivel == 100_000


def test_rn06_meta_inativa_nao_reserva_nada():
    inativa = replace(base, metas=[replace(cenario.reserva, ativa=False)])
    assert inativa.resumo(outubro).reserva == 0
    assert inativa.resumo(outubro).disponivel == 180_000


def test_rn06_meta_percentual_incide_sobre_todas_as_entradas_do_ciclo():
    freela = Entrada(100_000, TipoEntrada.AVULSA, data_inicio=data(20, 10))
    assert replace(base, entradas=[*base.entradas, freela]).resumo(outubro).reserva == 40_000


def test_rn07_reserva_sai_antes_dos_gastos_e_nao_entra_no_disponivel():
    resumo = com_gastos(Gasto(50_000, data(5, 10))).resumo(outubro)
    assert resumo == Resumo(entradas=300_000, fixas=120_000, reserva=30_000, gastos=50_000)
    assert resumo.disponivel == 100_000


def test_rn07_so_os_gastos_do_ciclo_entram_no_disponivel():
    resumo = com_gastos(
        Gasto(1_000, data(30, 9)), Gasto(2_000, data(31, 10)), Gasto(4_000, data(1, 11))
    ).resumo(outubro)
    assert resumo.gastos == 2_000


def test_rn07_entrada_avulsa_so_entra_no_ciclo_da_sua_data():
    freela = Entrada(50_000, TipoEntrada.AVULSA, data_inicio=data(31, 10))
    assert entra_em(freela, ciclo(10))
    assert not entra_em(freela, ciclo(11))
    assert not entra_em(freela, ciclo(9))


def test_rn07_entrada_recorrente_vale_nos_ciclos_que_comecam_entre_inicio_e_fim():
    # P13: emprego novo a partir de 20/10 só conta a partir do pagamento de 01/11
    salario = Entrada(300_000, TipoEntrada.RECORRENTE, data_inicio=data(20, 10), data_fim=data(5, 12))
    assert not entra_em(salario, ciclo(9))
    assert not entra_em(salario, ciclo(10))
    assert entra_em(salario, ciclo(11))
    assert entra_em(salario, ciclo(12))
    assert not entra_em(salario, ciclo(1, 2027))


def test_rn08_metas_iguais_a_entradas_menos_fixas_cabem():
    cabe = replace(base, metas=[*base.metas, MetaReserva(TipoMeta.VALOR, 150_000)])
    assert cabe.resumo(outubro).falta_para_metas == 0
    mais = replace(base, metas=[*base.metas, MetaReserva(TipoMeta.VALOR, 150_001)])
    assert mais.resumo(outubro).falta_para_metas == 1


def test_rn08_conta_fixa_nova_que_deixa_as_metas_maiores_mostra_quanto_falta():
    nova = ContaFixa(170_000, ciclo_inicio=data(1, 10))
    assert replace(base, contas=[*base.contas, nova]).resumo(outubro).falta_para_metas == 20_000


def test_rn08_meta_inativa_nao_entra_na_soma():
    inativa = MetaReserva(TipoMeta.VALOR, 500_000, ativa=False)
    assert replace(base, metas=[*base.metas, inativa]).resumo(outubro).falta_para_metas == 0


def test_rn09_disponivel_zerado_nao_invade_e_um_centavo_a_mais_invade():
    assert com_gastos(Gasto(150_000, data(5, 10))).resumo(outubro).reserva_invadida == 0
    assert com_gastos(Gasto(150_001, data(5, 10))).resumo(outubro).reserva_invadida == 1


def test_rn09_valor_invadido_pode_passar_do_total_da_reserva():
    resumo = com_gastos(Gasto(200_000, data(5, 10))).resumo(outubro)
    assert resumo.reserva == 30_000
    assert resumo.reserva_invadida == 50_000


def test_rn09_varios_gastos_somam_o_valor_invadido():
    resumo = com_gastos(Gasto(100_000, data(2, 10)), Gasto(70_000, data(20, 10))).resumo(outubro)
    assert resumo.disponivel == -20_000
    assert resumo.reserva_invadida == 20_000


def test_rn09_sem_gastos_nao_ha_reserva_invadida_mesmo_com_metas_que_nao_cabem():
    # P12: conta nova deixa o disponível em -200 sem gasto nenhum; é o aviso da RN08
    sem_folga = replace(base, contas=[*base.contas, ContaFixa(170_000, ciclo_inicio=data(1, 10))])
    resumo = sem_folga.resumo(outubro)
    assert resumo.disponivel == -20_000
    assert resumo.reserva_invadida == 0
    assert resumo.falta_para_metas == 20_000
    com_gasto = replace(sem_folga, gastos=[Gasto(5_000, data(5, 10))])
    assert com_gasto.resumo(outubro).reserva_invadida == 5_000


def test_rn13_meta_percentual_exata_nao_arredonda():
    assert valor_no_ciclo(cenario.reserva, 300_000) == 30_000


def test_rn13_meta_percentual_arredonda_qualquer_fracao_para_cima():
    assert valor_no_ciclo(cenario.reserva, 1) == 1
    assert valor_no_ciclo(cenario.reserva, 300_001) == 30_001
    assert valor_no_ciclo(cenario.reserva, 0) == 0
