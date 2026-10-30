from dataclasses import replace

from src.folego.apresentacao.cadastros import (
    ler_conta, ler_data, ler_entrada, ler_meta, linha_conta, linha_entrada, linha_meta, situacao_conta,
)
from src.folego.calculadora import ciclo_atual
from src.folego.modelos import ContaFixa, Configuracoes, Entrada, MetaReserva, TipoEntrada, TipoMeta
from . import cenario
from .cenario import data

HOJE = data(5, 10)
CICLO = ciclo_atual(Configuracoes(dia_pagamento=1), HOJE)


def test_ler_data_aceita_dia_e_mes_ou_data_completa():
    assert ler_data("06/10/2026", HOJE) == data(6, 10)
    assert ler_data("06/10", HOJE) == data(6, 10)
    assert ler_data("31/02", HOJE) is None and ler_data("abc", HOJE) is None


def test_ler_entrada_recorrente_usa_o_inicio_do_ciclo_e_avulsa_usa_hoje():
    rec = ler_entrada(" Salário ", "3.000,00", TipoEntrada.RECORRENTE, "", "sem", HOJE, CICLO)
    assert rec == Entrada(300_000, TipoEntrada.RECORRENTE, data(1, 10), None, "Salário")
    avulsa = ler_entrada("Bico", "150,50", TipoEntrada.AVULSA, "", "31/12/2026", HOJE, CICLO)
    assert avulsa == Entrada(15_050, TipoEntrada.AVULSA, HOJE, None, "Bico")  # avulsa não tem fim


def test_ler_entrada_com_fim_e_edicao_mantem_o_id():
    base = Entrada(100, TipoEntrada.RECORRENTE, data(1, 9), None, "Velho", id=7)
    nova = ler_entrada("Novo", "10", TipoEntrada.RECORRENTE, "01/10", "31/12", HOJE, CICLO, base)
    assert nova == Entrada(1_000, TipoEntrada.RECORRENTE, data(1, 10), data(31, 12), "Novo", id=7)


def test_ler_entrada_devolve_mensagem_para_valor_e_datas_invalidos():
    assert "valor" in ler_entrada("A", "abc", TipoEntrada.AVULSA, "", "", HOJE, CICLO)
    assert "início" in ler_entrada("A", "10", TipoEntrada.AVULSA, "32/01", "", HOJE, CICLO)
    assert "fim" in ler_entrada("A", "10", TipoEntrada.RECORRENTE, "", "xx", HOJE, CICLO)


def test_ler_conta_sem_fim_e_com_parcela_atual():
    sem_fim = ler_conta("Aluguel", "1.000,00", "5", "", "", CICLO)
    assert sem_fim == ContaFixa(100_000, data(1, 10), None, None, "Aluguel", 5)
    parcela = ler_conta("Carro", "500,00", "10", "10", "3", CICLO)
    assert parcela.ciclo_inicio == data(1, 8) and parcela.duracao_meses == 10
    assert ler_conta("Carro", "500,00", "10", "10", "", CICLO).ciclo_inicio == data(1, 10)


def test_ler_conta_devolve_mensagem_para_valor_dia_duracao_e_parcela():
    assert "valor" in ler_conta("A", "x", "5", "", "", CICLO)
    assert "vencimento" in ler_conta("A", "10", "cinco", "", "", CICLO)
    assert "duração" in ler_conta("A", "10", "5", "muitos", "", CICLO)
    assert "duração" in ler_conta("A", "10", "5", "0", "", CICLO)
    assert "parcela" in ler_conta("A", "10", "5", "10", "11", CICLO)
    assert "parcela" in ler_conta("A", "10", "5", "10", "0", CICLO)
    assert "parcela" in ler_conta("A", "10", "5", "10", "x", CICLO)


def test_ler_conta_editando_ignora_a_parcela_e_aceita_sem_fim():
    base = replace(cenario.celular, id=2, descricao="Celular")
    nova = ler_conta("Celular", "250,00", "7", "sem", "99", CICLO, base)
    assert nova == replace(base, valor_centavos=25_000, dia_vencimento=7, duracao_meses=None)


def test_ler_meta_por_valor_e_por_percentual():
    assert ler_meta(" Viagem ", TipoMeta.VALOR, "500,00") == MetaReserva(TipoMeta.VALOR, 50_000, nome="Viagem")
    assert ler_meta("Reserva", TipoMeta.PERCENTUAL, "10,5") == MetaReserva(TipoMeta.PERCENTUAL, 1_050, nome="Reserva")
    base = MetaReserva(TipoMeta.VALOR, 100, False, "Velha", id=3)
    assert ler_meta("Nova", TipoMeta.VALOR, "2", base) == MetaReserva(TipoMeta.VALOR, 200, False, "Nova", id=3)
    assert "valor" in ler_meta("A", TipoMeta.VALOR, "x") and "percentual" in ler_meta("A", TipoMeta.PERCENTUAL, "x")


def test_situacao_da_conta_parcela_fora_do_ciclo_e_encerrada():
    celular = replace(cenario.celular, descricao="Celular")
    assert situacao_conta(replace(celular, ciclo_inicio=data(1, 8)), CICLO) == "parcela 3 de 3"
    assert situacao_conta(replace(celular, ciclo_inicio=data(1, 5)), CICLO) == "fora do ciclo atual"
    encerrada = replace(cenario.aluguel, encerrada_em=data(3, 10))
    assert situacao_conta(encerrada, CICLO) == "sem fim, encerrada em 03/10/2026"


def test_linhas_das_listas():
    salario = replace(cenario.salario, descricao="Salário")
    assert linha_entrada(salario) == ("Salário", "R$ 3.000,00", "recorrente", "01/10/2026", "sem fim")
    bico = Entrada(15_000, TipoEntrada.AVULSA, HOJE, None, "Bico")
    assert linha_entrada(bico)[2:] == ("avulsa", "05/10/2026", "")
    celular = replace(cenario.celular, descricao="Celular", dia_vencimento=7)
    assert linha_conta(celular, CICLO) == ("Celular", "R$ 200,00", "dia 7", "parcela 1 de 3")
    assert linha_meta(replace(cenario.reserva, nome="Reserva")) == ("Reserva", "10%", "ativa")
    pausada = MetaReserva(TipoMeta.VALOR, 20_000, False, "Viagem")
    assert linha_meta(pausada) == ("Viagem", "R$ 200,00", "pausada")
