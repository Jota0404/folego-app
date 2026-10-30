from dataclasses import replace

import pytest

from src.folego.calculadora import Orcamento
from src.folego.decisoes import (
    PERMITIDO, Bloqueado, ErroCadastro, ErroGasto, PermitidoComAviso,
    PermitidoComReservaInvadida, decidir_configuracoes, decidir_conta,
    decidir_entrada, decidir_exclusao_conta, decidir_exclusao_entrada,
    decidir_exclusao_gasto, decidir_gasto, decidir_meta, inicio_pela_parcela,
    mostrar_primeiro_uso, valor_valido, validar_gasto,
)
from src.folego.calculadora import parcela_em
from src.folego.modelos import (
    Ciclo, Configuracoes, ContaFixa, Entrada, Gasto, MetaReserva, TipoEntrada,
    TipoMeta,
)
from . import cenario
from .cenario import data

# cenário base com ids, como viria do banco
base = replace(
    cenario.orcamento,
    entradas=[replace(cenario.salario, id=1, descricao="Salário")],
    contas=[replace(cenario.aluguel, id=1, descricao="Aluguel"),
            replace(cenario.celular, id=2, descricao="Celular")],
    metas=[replace(cenario.reserva, id=1, nome="Reserva")],
)
outubro = Ciclo(data(1, 10), data(31, 10))
hoje = data(6, 10)
conta = ContaFixa(30_000, ciclo_inicio=outubro.inicio, duracao_meses=10,
                  descricao="Financiamento", dia_vencimento=15)
freela = Entrada(50_000, TipoEntrada.AVULSA, data_inicio=hoje, descricao="Freela")
meta = MetaReserva(TipoMeta.VALOR, 10_000, nome="Viagem")
padrao = Configuracoes()


def bloqueio(erro):
    return Bloqueado(erro)


# --- Validações (RN14, RN15) ------------------------------------------------

def validar(valor, dia, mes, ano=2026):
    return validar_gasto(Gasto(valor, data(dia, mes, ano)), outubro, data(15, 10))


def test_rn14_gasto_retroativo_dentro_do_ciclo_atual_e_permitido():
    assert validar(5_000, 1, 10) is None
    assert validar(5_000, 14, 10) is None
    assert validar(5_000, 15, 10) is None


def test_rn14_gasto_em_ciclo_fechado_e_bloqueado():
    assert validar(5_000, 30, 9) == ErroGasto.DATA_EM_CICLO_FECHADO
    assert validar(5_000, 31, 12, 2025) == ErroGasto.DATA_EM_CICLO_FECHADO


def test_rn14_gasto_com_data_futura_e_bloqueado():
    assert validar(5_000, 16, 10) == ErroGasto.DATA_FUTURA
    assert validar(5_000, 1, 11) == ErroGasto.DATA_FUTURA


def test_rn15_gasto_de_valor_zero_ou_negativo_e_bloqueado():
    assert validar(0, 10, 10) == ErroGasto.VALOR_ZERO_OU_NEGATIVO
    assert validar(-100, 10, 10) == ErroGasto.VALOR_ZERO_OU_NEGATIVO
    assert validar(1, 10, 10) is None


def test_rn15_valor_zero_ou_negativo_e_invalido_em_qualquer_cadastro():
    assert not valor_valido(0)
    assert not valor_valido(-1)
    assert valor_valido(1)


# --- Cadastros --------------------------------------------------------------

@pytest.mark.parametrize("valor", [0, -1])
def test_rn15_valor_zero_ou_negativo_bloqueia_conta_entrada_e_meta(valor):
    esperado = bloqueio(ErroCadastro.VALOR_ZERO_OU_NEGATIVO)
    assert decidir_conta(replace(conta, valor_centavos=valor), base, outubro) == esperado
    assert decidir_entrada(replace(freela, valor_centavos=valor), base, outubro, hoje) == esperado
    assert decidir_meta(replace(meta, valor=valor), base, outubro) == esperado
    investimento = MetaReserva(TipoMeta.PERCENTUAL, valor, nome="Investimento")
    assert decidir_meta(investimento, base, outubro) == esperado


def test_cadastro_sem_descricao_e_bloqueado():
    esperado = bloqueio(ErroCadastro.DESCRICAO_VAZIA)
    assert decidir_conta(replace(conta, descricao=" "), base, outubro) == esperado
    assert decidir_entrada(replace(freela, descricao=""), base, outubro, hoje) == esperado
    assert decidir_meta(replace(meta, nome=""), base, outubro) == esperado


def test_conta_com_vencimento_duracao_ou_parcela_fora_do_lugar_e_bloqueada():
    invalido = bloqueio(ErroCadastro.DIA_VENCIMENTO_INVALIDO)
    assert decidir_conta(replace(conta, dia_vencimento=0), base, outubro) == invalido
    assert decidir_conta(replace(conta, dia_vencimento=32), base, outubro) == invalido
    assert decidir_conta(replace(conta, duracao_meses=0), base, outubro) == bloqueio(ErroCadastro.DURACAO_INVALIDA)
    parcela = bloqueio(ErroCadastro.PARCELA_INVALIDA)
    # parcela 11 de 10 e conta que começaria num ciclo futuro
    assert decidir_conta(replace(conta, ciclo_inicio=inicio_pela_parcela(outubro, 11)), base, outubro) == parcela
    assert decidir_conta(replace(conta, ciclo_inicio=data(1, 11)), base, outubro) == parcela


def test_rn04_editar_conta_antiga_para_duracao_menor_que_a_parcela_atual_e_bloqueado():
    # na parcela 3 de 10, encurtar para 1 ou 2 meses tiraria a conta de outubro
    antiga = replace(conta, id=7, ciclo_inicio=inicio_pela_parcela(outubro, 3))
    com_antiga = replace(base, contas=[*base.contas, antiga])
    sairia = bloqueio(ErroCadastro.CONTA_SAIRIA_DO_CICLO)
    assert decidir_conta(replace(antiga, duracao_meses=1), com_antiga, outubro) == sairia
    assert decidir_conta(replace(antiga, duracao_meses=2), com_antiga, outubro) == sairia
    # encurtar até a parcela atual (3) mantém a conta em outubro
    assert decidir_conta(replace(antiga, duracao_meses=3), com_antiga, outubro) == PERMITIDO


def test_rn04_editar_conta_que_ja_terminou_continua_permitido():
    terminada = replace(conta, id=8, duracao_meses=2, ciclo_inicio=data(1, 8))
    com_terminada = replace(base, contas=[*base.contas, terminada])
    assert decidir_conta(replace(terminada, descricao="Curso"), com_terminada, outubro) == PERMITIDO


def test_p18_avulsa_de_ciclo_fechado_nao_pode_ser_excluida():
    fechada = replace(freela, data_inicio=data(30, 9))
    assert decidir_exclusao_entrada(fechada, outubro) == bloqueio(ErroCadastro.DATA_EM_CICLO_FECHADO)
    assert decidir_exclusao_entrada(freela, outubro) == PERMITIDO
    antiga = replace(base.entradas[0], data_inicio=data(1, 1, 2020))
    assert decidir_exclusao_entrada(antiga, outubro) == PERMITIDO


def test_rn03_conta_na_parcela_3_de_10_comeca_2_ciclos_antes():
    na_terceira = replace(conta, ciclo_inicio=inicio_pela_parcela(outubro, 3))
    assert na_terceira.ciclo_inicio == data(1, 8)
    assert parcela_em(na_terceira, outubro) == 3
    assert parcela_em(na_terceira, Ciclo(data(1, 5, 2027), data(31, 5, 2027))) == 10
    assert decidir_conta(na_terceira, base, outubro) == PERMITIDO
    assert parcela_em(cenario.aluguel, outubro) is None


def test_inicio_pela_parcela_com_dia_31_vai_para_o_ultimo_dia_do_mes():
    # como o minusMonths do Java: 31/05 menos 1 mês é 30/04
    assert inicio_pela_parcela(Ciclo(data(31, 5), data(29, 6)), 2) == data(30, 4)


def test_rn08_conta_que_deixa_as_metas_sem_caber_salva_com_aviso():
    cara = replace(conta, valor_centavos=170_000, duracao_meses=None)
    assert decidir_conta(cara, base, outubro) == PermitidoComAviso(20_000)
    assert decidir_conta(conta, base, outubro) == PERMITIDO


def test_rn08_editar_a_conta_conta_o_valor_novo_e_nao_soma_duas_vezes():
    mais_caro = replace(base.contas[0], valor_centavos=250_000)
    assert decidir_conta(mais_caro, base, outubro) == PERMITIDO
    assert decidir_conta(replace(mais_caro, valor_centavos=250_001), base, outubro) == PermitidoComAviso(1)


def test_rn08_sem_meta_ativa_a_conta_e_salva_sem_aviso():
    sem_fim = replace(conta, duracao_meses=None)
    assert decidir_conta(sem_fim, Orcamento(), outubro) == PERMITIDO
    so_pausada = Orcamento(metas=[replace(meta, ativa=False)])
    assert decidir_conta(sem_fim, so_pausada, outubro) == PERMITIDO
    um_centavo = Orcamento(metas=[replace(meta, valor=1)])
    assert decidir_conta(sem_fim, um_centavo, outubro) == PermitidoComAviso(30_001)


def test_rn08_entrada_que_deixa_as_metas_sem_caber_salva_com_aviso():
    assert decidir_entrada(replace(base.entradas[0], valor_centavos=150_000), base, outubro, hoje) == PERMITIDO
    r = decidir_entrada(replace(base.entradas[0], valor_centavos=130_000), base, outubro, hoje)
    assert r == PermitidoComAviso(3_000)


def test_rn08_meta_que_nao_cabe_e_bloqueada_com_quanto_falta():
    assert decidir_meta(replace(meta, valor=150_000), base, outubro) == PERMITIDO
    assert decidir_meta(replace(meta, valor=150_001), base, outubro) == Bloqueado(ErroCadastro.METAS_NAO_CABEM, 1)


def test_rn08_meta_pausada_nao_entra_na_soma_e_pode_ser_salva():
    assert decidir_meta(replace(meta, valor=500_000, ativa=False), base, outubro) == PERMITIDO


def test_rn08_editar_a_meta_troca_o_valor_antigo_em_vez_de_somar():
    reserva = base.metas[0]
    assert decidir_meta(replace(reserva, valor=6000), base, outubro) == PERMITIDO
    assert decidir_meta(replace(reserva, valor=6100), base, outubro) == Bloqueado(ErroCadastro.METAS_NAO_CABEM, 3_000)


def test_meta_percentual_acima_de_100_por_cento_e_bloqueada():
    tudo = MetaReserva(TipoMeta.PERCENTUAL, 10_001, nome="Tudo")
    assert decidir_meta(tudo, Orcamento(), outubro) == bloqueio(ErroCadastro.PERCENTUAL_ACIMA_DE_100)


def test_rn14_entrada_avulsa_so_vale_do_inicio_do_ciclo_ate_hoje():
    assert decidir_entrada(replace(freela, data_inicio=data(1, 10)), base, outubro, hoje) == PERMITIDO
    assert decidir_entrada(replace(freela, data_inicio=hoje), base, outubro, hoje) == PERMITIDO
    fechado = bloqueio(ErroCadastro.DATA_EM_CICLO_FECHADO)
    futura = bloqueio(ErroCadastro.DATA_FUTURA)
    assert decidir_entrada(replace(freela, data_inicio=data(30, 9)), base, outubro, hoje) == fechado
    assert decidir_entrada(replace(freela, data_inicio=data(7, 10)), base, outubro, hoje) == futura


def test_entrada_recorrente_aceita_inicio_no_passado_ou_futuro_mas_nao_fim_antes_do_inicio():
    salario = Entrada(300_000, TipoEntrada.RECORRENTE, data_inicio=data(1, 11), descricao="Emprego novo")
    fim_antes = bloqueio(ErroCadastro.FIM_ANTES_DO_INICIO)
    assert decidir_entrada(salario, base, outubro, hoje) == PERMITIDO
    assert decidir_entrada(replace(salario, data_inicio=data(1, 1, 2020)), base, outubro, hoje) == PERMITIDO
    assert decidir_entrada(replace(salario, data_fim=data(31, 10)), base, outubro, hoje) == fim_antes


def test_rn04_conta_que_comeca_no_ciclo_atual_pode_ser_excluida():
    assert decidir_exclusao_conta(conta, outubro) == PERMITIDO


def test_rn04_conta_ja_descontada_em_ciclo_anterior_so_pode_ser_encerrada():
    antiga = replace(conta, ciclo_inicio=inicio_pela_parcela(outubro, 3))
    assert decidir_exclusao_conta(antiga, outubro) == bloqueio(ErroCadastro.CONTA_JA_DESCONTADA)


def test_ca03_gasto_que_invade_a_reserva_e_salvo_com_aviso_de_quanto():
    assert decidir_gasto(Gasto(160_000, data(5, 10)), base, outubro, hoje) == PermitidoComReservaInvadida(10_000)
    assert decidir_gasto(Gasto(150_000, data(5, 10)), base, outubro, hoje) == PERMITIDO


def test_rn14_e_rn15_valem_ao_criar_e_ao_editar_um_gasto():
    almoco = Gasto(4_500, data(6, 10), descricao="Almoço", id=3)
    com_almoco = replace(base, gastos=[almoco])
    assert decidir_gasto(replace(almoco, valor_centavos=5_400), com_almoco, outubro, hoje) == PERMITIDO
    zero = bloqueio(ErroCadastro.VALOR_ZERO_OU_NEGATIVO)
    assert decidir_gasto(replace(almoco, valor_centavos=0), com_almoco, outubro, hoje) == zero
    futura = bloqueio(ErroCadastro.DATA_FUTURA)
    assert decidir_gasto(replace(almoco, data=data(7, 10)), com_almoco, outubro, hoje) == futura
    fechado = bloqueio(ErroCadastro.DATA_EM_CICLO_FECHADO)
    assert decidir_gasto(replace(almoco, data=data(30, 9)), com_almoco, outubro, hoje) == fechado
    assert decidir_gasto(Gasto(0, hoje), base, outubro, hoje) == zero


def test_rn05_gasto_de_ciclo_fechado_nao_pode_ser_editado_nem_excluido():
    antigo = Gasto(2_000, data(28, 9), id=4)
    com_antigo = replace(base, gastos=[antigo])
    fechado = bloqueio(ErroCadastro.DATA_EM_CICLO_FECHADO)
    # mesmo mudando a data para o ciclo atual
    assert decidir_gasto(replace(antigo, data=hoje), com_antigo, outubro, hoje) == fechado
    assert decidir_exclusao_gasto(antigo, outubro) == fechado
    assert decidir_exclusao_gasto(replace(antigo, data=data(1, 10)), outubro) == PERMITIDO


# --- Configurações ----------------------------------------------------------

def test_padroes_do_briefing_sao_validos():
    assert decidir_configuracoes(padrao) == PERMITIDO


def test_dia_do_pagamento_fora_de_1_a_31_e_bloqueado():
    invalido = bloqueio(ErroCadastro.DIA_PAGAMENTO_INVALIDO)
    assert decidir_configuracoes(replace(padrao, dia_pagamento=0)) == invalido
    assert decidir_configuracoes(replace(padrao, dia_pagamento=32)) == invalido
    assert decidir_configuracoes(replace(padrao, dia_pagamento=31)) == PERMITIDO


def test_rn15_limite_manual_zero_ou_negativo_e_bloqueado_e_vazio_volta_ao_automatico():
    erro = bloqueio(ErroCadastro.VALOR_ZERO_OU_NEGATIVO)
    assert decidir_configuracoes(replace(padrao, limite_semanal_manual=0)) == erro
    assert decidir_configuracoes(replace(padrao, limite_semanal_manual=-1)) == erro
    assert decidir_configuracoes(replace(padrao, limite_semanal_manual=50_000)) == PERMITIDO
    assert decidir_configuracoes(replace(padrao, limite_semanal_manual=None)) == PERMITIDO


def test_percentuais_nas_faixas_e_atencao_menor_que_critico():
    assert decidir_configuracoes(replace(padrao, percentual_atencao=100, percentual_critico=200)) == PERMITIDO
    assert decidir_configuracoes(replace(padrao, percentual_atencao=9_900, percentual_critico=10_000)) == PERMITIDO
    fora = bloqueio(ErroCadastro.PERCENTUAL_FORA_DA_FAIXA)
    assert decidir_configuracoes(replace(padrao, percentual_atencao=0)) == fora
    assert decidir_configuracoes(replace(padrao, percentual_critico=10_001)) == fora
    maior = bloqueio(ErroCadastro.ATENCAO_NAO_MENOR_QUE_CRITICO)
    assert decidir_configuracoes(replace(padrao, percentual_atencao=9_000, percentual_critico=7_000)) == maior
    assert decidir_configuracoes(replace(padrao, percentual_atencao=8_000, percentual_critico=8_000)) == maior


def test_primeiro_uso_aparece_ate_ser_concluido_e_nao_para_quem_ja_tem_entradas():
    assert mostrar_primeiro_uso(padrao, Orcamento())
    assert not mostrar_primeiro_uso(replace(padrao, primeiro_uso_concluido=True), Orcamento())
    assert not mostrar_primeiro_uso(padrao, cenario.orcamento)
