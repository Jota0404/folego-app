from dataclasses import replace

import pytest

from src.folego.calculadora import Orcamento, ciclo_de
from src.folego.modelos import Ciclo, Entrada, Gasto, TipoEntrada
from . import cenario
from .cenario import data

base = cenario.orcamento
outubro = Ciclo(data(1, 10), data(31, 10))


def ciclo_do_dia(dia, mes, ano=2026):
    return ciclo_de(data(dia, mes, ano), cenario.DIA_PAGAMENTO)


def test_rn10_semana_vai_de_segunda_a_domingo():
    quarta = base.limite_semanal(outubro, data(7, 10))
    assert quarta.inicio == data(5, 10)
    assert quarta.fim == data(11, 10)
    assert base.limite_semanal(outubro, data(11, 10)) == quarta
    assert base.limite_semanal(outubro, data(12, 10)).inicio == data(12, 10)


def test_rn10_semana_que_cruza_o_inicio_do_ciclo_comeca_no_primeiro_dia():
    sabado = base.limite_semanal(outubro, data(3, 10))
    assert sabado.inicio == data(1, 10)
    assert sabado.fim == data(4, 10)


def test_rn11_ultima_semana_do_ciclo_libera_todo_o_disponivel():
    limite = base.limite_semanal(outubro, data(28, 10))
    assert limite.inicio == data(26, 10)
    assert limite.fim == data(31, 10)
    assert limite.valor_centavos == 150_000


def test_rn11_semana_que_cruza_a_virada_do_ciclo_tem_um_limite_em_cada_ciclo():
    # domingo 01/11 é o primeiro dia do ciclo de novembro: 1500 x 1 / 30
    limite = base.limite_semanal(ciclo_do_dia(1, 11), data(1, 11))
    assert limite.inicio == data(1, 11)
    assert limite.fim == data(1, 11)
    assert limite.valor_centavos == 5_000


def test_rn11_semana_que_cruza_a_virada_do_ano():
    dezembro = base.limite_semanal(ciclo_do_dia(28, 12), data(28, 12))
    assert dezembro.fim == data(31, 12)
    assert dezembro.valor_centavos == 150_000
    # janeiro, sem o celular: 1700 x 3 / 31 = 164,516...
    janeiro = base.limite_semanal(ciclo_do_dia(1, 1, 2027), data(3, 1, 2027))
    assert janeiro.inicio == data(1, 1, 2027)
    assert janeiro.valor_centavos == 16_451


def test_rn11_gastos_da_propria_semana_nao_mudam_o_limite():
    com_gastos = replace(base, gastos=[Gasto(10_000, data(5, 10)), Gasto(20_000, data(6, 10))])
    assert com_gastos.limite_semanal(outubro, data(7, 10)).valor_centavos == 38_888


def test_rn11_disponivel_zerado_da_limite_zero():
    sem_sobra = replace(base, gastos=[Gasto(150_000, data(2, 10))])
    assert sem_sobra.limite_semanal(outubro, data(5, 10)).valor_centavos == 0


def test_rn11_limite_sobe_com_uma_entrada_nova_na_semana():
    # freela de 270 em 07/10: entradas 3270, reserva 327, disponível 1743; 1743 x 7 / 27
    freela = Entrada(27_000, TipoEntrada.AVULSA, data_inicio=data(7, 10))
    orc = replace(base, entradas=[*base.entradas, freela])
    assert orc.limite_semanal(outubro, data(7, 10)).valor_centavos == 45_188


def test_rn11_data_fora_do_ciclo_e_recusada():
    with pytest.raises(ValueError):
        base.limite_semanal(outubro, data(1, 11))


def test_rn12_limite_manual_vale_inteiro_na_semana_cheia_e_avisa():
    limite = base.limite_semanal(outubro, data(5, 10), limite_manual=50_000)
    assert limite.valor_centavos == 50_000
    assert limite.ritmo_nao_fecha_ciclo


def test_rn12_limite_manual_menor_ou_igual_ao_automatico_nao_avisa():
    menor = base.limite_semanal(outubro, data(5, 10), limite_manual=30_000)
    assert menor.valor_centavos == 30_000
    assert not menor.ritmo_nao_fecha_ciclo
    assert not base.limite_semanal(outubro, data(5, 10), limite_manual=38_888).ritmo_nao_fecha_ciclo


def test_rn12_limite_manual_e_proporcional_na_semana_partida_do_fim_do_ciclo():
    # 26 a 31/10: 500 x 6 / 7 = 428,57...
    limite = base.limite_semanal(outubro, data(28, 10), limite_manual=50_000)
    assert limite.valor_centavos == 42_857
    assert not limite.ritmo_nao_fecha_ciclo


def test_rn12_limite_manual_numa_semana_de_um_dia_so():
    # domingo 01/11: 500 x 1 / 7 = 71,42...; o automático é 50,00
    limite = base.limite_semanal(ciclo_do_dia(1, 11), data(1, 11), limite_manual=50_000)
    assert limite.valor_centavos == 7_142
    assert limite.ritmo_nao_fecha_ciclo


def test_rn12_limite_manual_vale_mesmo_com_a_reserva_invadida_e_avisa():
    invadido = replace(base, gastos=[Gasto(160_000, data(2, 10))])
    limite = invadido.limite_semanal(outubro, data(5, 10), limite_manual=50_000)
    assert limite.valor_centavos == 50_000
    assert limite.ritmo_nao_fecha_ciclo


def test_rn13_divisao_do_limite_arredonda_para_baixo():
    # disponível de 1,00 numa segunda com 27 dias restantes: 1,00 x 7 / 27 = 0,259...
    um_real = Orcamento(entradas=[Entrada(100, TipoEntrada.AVULSA, data_inicio=data(2, 10))])
    assert um_real.limite_semanal(outubro, data(5, 10)).valor_centavos == 25
    # limite manual de 0,01 em 4 dias: 0,01 x 4 / 7 = 0,005...
    assert base.limite_semanal(outubro, data(1, 10), limite_manual=1).valor_centavos == 0


def test_rn14_gasto_retroativo_de_semana_anterior_recalcula_o_limite_da_atual():
    assert base.limite_semanal(outubro, data(7, 10)).valor_centavos == 38_888
    # gasto de 150 lançado na quarta 07/10 com data de 02/10: 1350 x 7 / 27 = 350,00
    retroativo = replace(base, gastos=[Gasto(15_000, data(2, 10))])
    assert retroativo.limite_semanal(outubro, data(7, 10)).valor_centavos == 35_000
