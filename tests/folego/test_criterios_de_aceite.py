"""Critérios de aceite de cálculo do briefing, com o cenário base."""
from dataclasses import replace

from src.folego.calculadora import ativa_em, ciclo_de
from src.folego.decisoes import (
    Bloqueado, ErroCadastro, ErroGasto, decidir_meta, validar_gasto,
)
from src.folego.modelos import Gasto, MetaReserva, TipoMeta
from . import cenario
from .cenario import DIA_PAGAMENTO, data

base = cenario.orcamento
outubro = ciclo_de(data(1, 10), DIA_PAGAMENTO)


def test_ca01_outubro_sem_gastos_tem_1500_reais_disponiveis():
    assert base.resumo(outubro).disponivel == 150_000


def test_ca02_em_janeiro_de_2027_o_celular_acabou_e_sobram_1700_reais():
    janeiro = ciclo_de(data(1, 1, 2027), DIA_PAGAMENTO)
    assert not ativa_em(cenario.celular, janeiro)
    assert base.resumo(janeiro).disponivel == 170_000


def test_ca03_gasto_de_1600_reais_em_outubro_invade_a_reserva_em_100_reais():
    gasto = Gasto(160_000, data(10, 10))
    assert validar_gasto(gasto, outubro, hoje=data(10, 10)) is None
    resumo = replace(base, gastos=[gasto]).resumo(outubro)
    assert resumo.disponivel == -10_000
    assert resumo.reserva_invadida == 10_000


def test_ca04_meta_de_2000_reais_em_outubro_e_bloqueada_porque_faltam_500():
    meta_nova = MetaReserva(TipoMeta.VALOR, 200_000, nome="Viagem")
    assert decidir_meta(meta_nova, base, outubro) == Bloqueado(ErroCadastro.METAS_NAO_CABEM, 50_000)


def test_ca05_segunda_05_10_sem_gastos_tem_limite_semanal_de_388_88():
    limite = base.limite_semanal(outubro, data(5, 10))
    assert limite.fim == data(11, 10)
    assert limite.valor_centavos == 38_888


def test_ca06_limite_de_1000_reais_numa_segunda_com_21_dias_restantes_e_333_33():
    # segunda 11/01/2027: 1700 disponíveis - 700 de gastos = 1000
    janeiro = ciclo_de(data(11, 1, 2027), DIA_PAGAMENTO)
    orcamento = replace(base, gastos=[Gasto(70_000, data(4, 1, 2027))])
    assert orcamento.resumo(janeiro, gastos_antes_de=data(11, 1, 2027)).disponivel == 100_000
    assert orcamento.limite_semanal(janeiro, data(11, 1, 2027)).valor_centavos == 33_333


def test_ca07_dia_do_pagamento_31_faz_o_ciclo_de_abril_comecar_em_30_04():
    assert ciclo_de(data(30, 4, 2027), 31).inicio == data(30, 4, 2027)
    assert ciclo_de(data(15, 5, 2027), 31).inicio == data(30, 4, 2027)


def test_ca09_gasto_de_0_reais_e_bloqueado():
    erro = validar_gasto(Gasto(0, data(5, 10)), outubro, hoje=data(5, 10))
    assert erro == ErroGasto.VALOR_ZERO_OU_NEGATIVO


def test_ca10_gasto_com_data_em_ciclo_ja_fechado_e_bloqueado():
    erro = validar_gasto(Gasto(5_000, data(30, 9)), outubro, hoje=data(5, 10))
    assert erro == ErroGasto.DATA_EM_CICLO_FECHADO


def test_ca13_quinta_01_10_sem_gastos_tem_limite_de_193_54_ate_domingo_04_10():
    limite = base.limite_semanal(outubro, data(1, 10))
    assert limite.inicio == data(1, 10)
    assert limite.fim == data(4, 10)
    assert limite.valor_centavos == 19_354


def test_ca14_segunda_05_10_com_a_reserva_invadida_tem_limite_zero():
    invadido = replace(base, gastos=[Gasto(160_000, data(2, 10))])
    assert invadido.limite_semanal(outubro, data(5, 10)).valor_centavos == 0


def test_ca15_salario_de_3000_05_com_meta_de_10_por_cento_reserva_300_01():
    salario = replace(cenario.salario, valor_centavos=300_005)
    assert replace(base, entradas=[salario]).resumo(outubro).reserva == 30_001


def test_ca16_limite_manual_de_500_reais_vira_285_71_e_avisa_do_ritmo():
    limite = base.limite_semanal(outubro, data(1, 10), limite_manual=50_000)
    assert limite.valor_centavos == 28_571
    assert limite.ritmo_nao_fecha_ciclo
    assert base.limite_semanal(outubro, data(1, 10)).valor_centavos == 19_354
