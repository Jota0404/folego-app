from dataclasses import replace

from src.folego.alertas import (
    CodigoAlerta, ResumoDoCiclo, ResumoSemanal,
    alerta_de_invasao, alertas_de_limite, mensagem,
)
from src.folego.modelos import Ciclo, Configuracoes, Gasto
from . import cenario
from .cenario import data

outubro = Ciclo(data(1, 10), data(31, 10))
padrao = Configuracoes()


def painel_com(gasto_centavos, dia=5):
    orc = replace(cenario.orcamento, gastos=[Gasto(gasto_centavos, data(dia, 10))])
    return orc.painel(outubro, data(5, 10), padrao)


def alertas(painel):
    return alertas_de_limite(painel, padrao.percentual_atencao, padrao.percentual_critico)


def test_ca08_a2_so_a_partir_de_70_por_cento_do_limite():
    # semana de 05/10, limite 388,88: 272,21 ainda não atinge 70%; 272,22 atinge
    assert alertas(painel_com(27_221)) == []
    [a2] = alertas(painel_com(27_222))
    assert a2.codigo == CodigoAlerta.A2
    assert a2.periodo_ref == "2026-10-05"
    msg = mensagem(a2)
    assert msg.titulo == "70% do limite da semana"
    assert msg.texto == "Você já gastou R$ 272,22 de R$ 388,88 nesta semana. Restam R$ 116,66."


def test_a3_chega_ao_atingir_90_por_cento_e_o_a2_junto_nao_avisa():
    # decisão do dono: no salto direto para o A3, o A2 só é registrado
    a2, a3 = alertas(painel_com(35_000))
    assert (a2.codigo, a2.avisar) == (CodigoAlerta.A2, False)
    assert (a3.codigo, a3.avisar) == (CodigoAlerta.A3, True)


def test_com_limite_zero_a2_e_a3_nao_disparam():
    assert alertas(painel_com(160_000, dia=2)) == []


def test_cada_parte_da_semana_partida_e_um_periodo_separado():
    parte1 = replace(cenario.orcamento, gastos=[Gasto(13_548, data(2, 10))]).painel(
        outubro, data(2, 10), padrao
    )
    [a2] = alertas(parte1)
    assert a2.periodo_ref == "2026-10-01"


def test_ca03_a4_dispara_so_quando_a_reserva_fica_mais_invadida():
    antes = cenario.orcamento.resumo(outubro)
    depois = replace(cenario.orcamento, gastos=[Gasto(160_000, data(10, 10))]).resumo(outubro)
    a4 = alerta_de_invasao(antes, depois, gasto_id=9)
    assert a4.reserva_invadida == 10_000
    assert a4.periodo_ref == "gasto-9"
    assert mensagem(a4).texto == (
        "Um gasto invadiu a reserva. A reserva deste ciclo está invadida em R$ 100,00."
    )
    assert alerta_de_invasao(depois, depois, gasto_id=9) is None
    assert alerta_de_invasao(antes, antes, gasto_id=9) is None


def test_a1_diz_o_disponivel_da_semana_e_do_ciclo():
    painel = cenario.orcamento.painel(outubro, data(5, 10), padrao)
    a1 = ResumoSemanal(data(5, 10), painel)
    assert a1.periodo_ref == "2026-10-05"
    assert mensagem(a1).texto == (
        "Você pode gastar R$ 388,88 nesta semana (limite de R$ 388,88). "
        "No ciclo: R$ 1.500,00."
    )


def test_a5_reserva_nao_cumprida_diz_quanto_sobrou_e_quanto_guardou():
    orc = replace(cenario.orcamento, gastos=[Gasto(160_000, data(10, 10))])
    a5 = ResumoDoCiclo(orc.fechar(outubro))
    msg = mensagem(a5)
    assert msg.titulo == "Ciclo de 01/10 a 31/10 fechado"
    assert msg.texto == "Sobrou R$ 0,00. Reserva não cumprida: guardou R$ 200,00 de R$ 300,00."
    assert a5.periodo_ref == "2026-10-01"


def test_a5_com_a_reserva_cumprida():
    orc = replace(cenario.orcamento, gastos=[Gasto(50_000, data(10, 10))])
    msg = mensagem(ResumoDoCiclo(orc.fechar(outubro)))
    assert msg.texto == "Sobrou R$ 1.000,00. Reserva cumprida: R$ 300,00 guardados."


def test_a5_sem_meta_de_reserva():
    orc = replace(cenario.orcamento, metas=[])
    msg = mensagem(ResumoDoCiclo(orc.fechar(outubro)))
    assert msg.texto == "Sobrou R$ 1.800,00. Sem meta de reserva."
