from dataclasses import replace

from src.folego.calculadora import Faixa
from src.folego.modelos import Ciclo, Configuracoes, Gasto
from . import cenario
from .cenario import data

outubro = Ciclo(data(1, 10), data(31, 10))
padrao = Configuracoes()


def com_gastos(*gastos):
    return replace(cenario.orcamento, gastos=list(gastos))


def painel_de(gasto, dia=5, config=padrao):
    return com_gastos(Gasto(gasto, data(dia, 10))).painel(outubro, data(5, 10), config)


def test_disponivel_da_semana_e_o_limite_menos_os_gastos_da_propria_semana():
    # gasto de 02/10 é de outra semana e já entrou no limite
    painel = com_gastos(Gasto(10_000, data(2, 10)), Gasto(5_000, data(6, 10))).painel(
        outubro, data(7, 10), padrao
    )
    assert painel.semana.inicio == data(5, 10)
    assert painel.gastos_da_semana == 5_000
    assert painel.disponivel_da_semana == painel.semana.valor_centavos - 5_000


def test_painel_mostra_o_disponivel_do_ciclo_e_a_reserva():
    painel = com_gastos(Gasto(50_000, data(6, 10))).painel(outubro, data(7, 10), padrao)
    assert painel.resumo_do_ciclo.disponivel == 100_000
    assert painel.resumo_do_ciclo.reserva == 30_000
    assert painel.resumo_do_ciclo.reserva_invadida == 0


def test_barra_verde_abaixo_de_70_por_cento_e_amarela_ao_atingir_70():
    # 70% de 388,88 = 272,216: 272,21 ainda é verde, 272,22 já atinge (A2, CA08)
    assert painel_de(27_221).faixa == Faixa.VERDE
    assert painel_de(27_222).faixa == Faixa.AMARELA
    assert cenario.orcamento.painel(outubro, data(5, 10), padrao).faixa == Faixa.VERDE


def test_barra_vermelha_ao_atingir_90_por_cento_e_cheia_ao_passar_do_limite():
    # 90% de 388,88 = 349,992
    assert painel_de(34_999).faixa == Faixa.AMARELA
    assert painel_de(35_000).faixa == Faixa.VERMELHA
    passou = painel_de(50_000)
    assert passou.consumo_pontos_base == 10_000
    assert passou.disponivel_da_semana == 38_888 - 50_000


def test_cores_da_barra_seguem_os_percentuais_configurados():
    config = Configuracoes(percentual_atencao=6000, percentual_critico=8000)
    assert painel_de(23_333, config=config).faixa == Faixa.AMARELA
    assert painel_de(31_111, config=config).faixa == Faixa.VERMELHA


def test_ca14_com_limite_zero_a_barra_fica_cheia_e_vermelha():
    painel = com_gastos(Gasto(160_000, data(2, 10))).painel(outubro, data(5, 10), padrao)
    assert painel.semana.valor_centavos == 0
    assert painel.faixa == Faixa.VERMELHA
    assert painel.consumo_pontos_base == 10_000
    assert painel.resumo_do_ciclo.reserva_invadida == 10_000


def test_consumo_em_pontos_base_para_desenhar_a_barra():
    assert painel_de(19_444).consumo_pontos_base == 5_000


def test_rn12_limite_manual_aparece_no_painel_com_o_aviso_de_ritmo():
    painel = cenario.orcamento.painel(outubro, data(1, 10), Configuracoes(limite_semanal_manual=50_000))
    assert painel.semana.valor_centavos == 28_571
    assert painel.semana.ritmo_nao_fecha_ciclo
