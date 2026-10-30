from dataclasses import replace

from src.folego.calculadora import ciclo_atual
from src.folego.gui.formularios import (
    FormularioConta, FormularioEntrada, FormularioMeta, ler_conta, ler_data, ler_entrada, ler_meta,
)
from src.folego.gui.tela_cadastros import TelaCadastros, situacao_conta
from src.folego.modelos import ContaFixa, Configuracoes, Entrada, MetaReserva, TipoEntrada, TipoMeta
from . import cenario
from .cenario import data
from .gui_helpers import contexto_de_teste, raiz  # noqa: F401  (raiz é uma fixture)

HOJE = data(5, 10)
CICLO = ciclo_atual(Configuracoes(dia_pagamento=1), HOJE)


def com_ids(**mudancas):
    """Cenário base com ids e descrições, como viria do banco."""
    base = replace(
        cenario.orcamento,
        entradas=[replace(cenario.salario, id=1, descricao="Salário")],
        contas=[replace(cenario.aluguel, id=1, descricao="Aluguel"),
                replace(cenario.celular, id=2, descricao="Celular")],
        metas=[replace(cenario.reserva, id=1, nome="Reserva")],
    )
    return replace(base, **mudancas)


def montar(raiz, **kwargs):  # noqa: F811
    ctx, ambiente, dialogos = contexto_de_teste(orcamento=kwargs.pop("orcamento", com_ids()), **kwargs)
    tela = TelaCadastros(raiz, ctx)
    ctx.registrar("cadastros", tela)
    tela.atualizar()
    return tela, ctx, ambiente, dialogos


def itens(ambiente):
    return ambiente.orcamento.orcamento()


def por_id(lista, id):
    return next(i for i in lista if i.id == id)  # o repositório falso pode reordenar ao salvar


def linhas(arvore):
    return [arvore.item(i, "values") for i in arvore.get_children()]


# --- funções puras --------------------------------------------------------------

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


# --- listas ---------------------------------------------------------------------

def test_listas_mostram_entradas_contas_e_metas(raiz):  # noqa: F811
    tela, *_ = montar(raiz)
    assert linhas(tela.entradas.arvore) == [("Salário", "R$ 3.000,00", "recorrente", "01/10/2026", "sem fim")]
    assert linhas(tela.contas.arvore) == [("Aluguel", "R$ 1.000,00", "dia 1", "sem fim"),
                                          ("Celular", "R$ 200,00", "dia 1", "parcela 1 de 3")]
    assert linhas(tela.metas.arvore) == [("Reserva", "10%", "ativa")]


def test_situacao_da_conta_parcela_fora_do_ciclo_e_encerrada():
    celular = replace(cenario.celular, descricao="Celular")
    assert situacao_conta(replace(celular, ciclo_inicio=data(1, 8)), CICLO) == "parcela 3 de 3"
    assert situacao_conta(replace(celular, ciclo_inicio=data(1, 5)), CICLO) == "fora do ciclo atual"
    encerrada = replace(cenario.aluguel, encerrada_em=data(3, 10))
    assert situacao_conta(encerrada, CICLO) == "sem fim, encerrada em 03/10/2026"


def test_atualizar_mantem_a_subaba_e_a_selecao(raiz):  # noqa: F811
    tela, ctx, ambiente, _ = montar(raiz)
    tela.abas.select(tela.metas)
    tela.metas.arvore.selection_set("1")
    ctx.mudou()
    assert tela.abas.select() == str(tela.metas) and tela.metas.arvore.selection() == ("1",)


# --- adicionar ------------------------------------------------------------------

def test_adicionar_entrada_avulsa(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar(raiz)
    f = FormularioEntrada(tela.entradas, ctx)
    f.descricao.set("Bico")
    f.valor.set("150,00")
    f.tipo.set("Avulsa")
    f._tipo_mudou()
    assert f.inicio.get() == "05/10/2026"  # o padrão do início acompanha o tipo
    assert f.salvar()
    nova = itens(ambiente).entradas[-1]
    assert (nova.descricao, nova.valor_centavos, nova.tipo, nova.data_inicio) == (
        "Bico", 15_000, TipoEntrada.AVULSA, HOJE)
    assert len(tela.entradas.arvore.get_children()) == 2 and not f.janela.winfo_exists() == 1


def test_adicionar_entrada_invalida_nao_fecha_o_formulario(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar(raiz)
    f = FormularioEntrada(tela.entradas, ctx)
    f.descricao.set("X")
    f.valor.set("abc")
    assert not f.salvar() and dialogos.avisos and f.janela.winfo_exists()
    f.valor.set("0")
    assert not f.salvar() and "maior que zero" in dialogos.avisos[-1][1]
    assert len(itens(ambiente).entradas) == 1
    f.janela.destroy()


def test_adicionar_conta_na_parcela_3_de_10(raiz):  # noqa: F811
    tela, ctx, ambiente, _ = montar(raiz)
    f = FormularioConta(tela.contas, ctx)
    f.descricao.set("Carro")
    f.valor.set("300,00")
    f.vencimento.set("10")
    f.duracao.set("10")
    f.parcela.set("3")
    assert f.salvar()
    carro = itens(ambiente).contas[-1]
    assert carro.ciclo_inicio == data(1, 8) and carro.duracao_meses == 10 and carro.dia_vencimento == 10
    assert ("Carro", "R$ 300,00", "dia 10", "parcela 3 de 10") in linhas(tela.contas.arvore)


def test_adicionar_meta_por_valor_e_por_percentual(raiz):  # noqa: F811
    tela, ctx, ambiente, _ = montar(raiz)
    f = FormularioMeta(tela.metas, ctx)
    f.nome.set("Viagem")
    f.valor.set("200,00")
    assert f.salvar()
    g = FormularioMeta(tela.metas, ctx)
    g.nome.set("Estudos")
    g.tipo.set("Percentual das entradas")
    g.valor.set("5")
    assert g.salvar()
    assert [(m.nome, m.tipo, m.valor) for m in itens(ambiente).metas[1:]] == [
        ("Viagem", TipoMeta.VALOR, 20_000), ("Estudos", TipoMeta.PERCENTUAL, 500)]


def test_meta_que_nao_cabe_e_bloqueada_com_quanto_falta(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar(raiz)
    f = FormularioMeta(tela.metas, ctx)
    f.nome.set("Grande")
    f.valor.set("2.000,00")
    assert not f.salvar()
    assert "Faltam R$ 500,00" in dialogos.avisos[-1][1]  # CA04
    assert len(itens(ambiente).metas) == 1 and f.janela.winfo_exists()
    f.janela.destroy()


# --- editar ---------------------------------------------------------------------

def test_editar_valor_da_conta_vem_preenchido_e_mantem_o_id(raiz):  # noqa: F811
    tela, ctx, ambiente, _ = montar(raiz)
    aluguel = itens(ambiente).contas[0]
    f = FormularioConta(tela.contas, ctx, aluguel)
    assert (f.descricao.get(), f.valor.get(), f.vencimento.get(), f.duracao.get()) == (
        "Aluguel", "R$ 1.000,00", "1", "")
    f.valor.set("1.100,00")
    assert f.salvar()
    assert por_id(itens(ambiente).contas, 1) == replace(aluguel, valor_centavos=110_000)
    assert [v[1] for v in linhas(tela.contas.arvore) if v[0] == "Aluguel"] == ["R$ 1.100,00"]


def test_editar_entrada(raiz):  # noqa: F811
    tela, ctx, ambiente, _ = montar(raiz)
    f = FormularioEntrada(tela.entradas, ctx, itens(ambiente).entradas[0])
    assert f.inicio.get() == "01/10/2026"
    f.valor.set("3.500,00")
    f.fim.set("31/12/2026")
    assert f.salvar()
    e = itens(ambiente).entradas[0]
    assert (e.id, e.valor_centavos, e.data_fim) == (1, 350_000, data(31, 12))


def test_botao_editar_sem_selecao_avisa(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar(raiz)
    tela.contas.editar_selecionado(FormularioConta)
    tela.contas.encerrar()
    tela.metas.excluir()
    tela.entradas.excluir()
    assert len(dialogos.avisos) == 4 and len(itens(ambiente).contas) == 2


# --- excluir, encerrar, pausar --------------------------------------------------

def test_excluir_conta_ja_descontada_e_bloqueado(raiz):  # noqa: F811
    antiga = replace(cenario.aluguel, id=1, descricao="Aluguel", ciclo_inicio=data(1, 8))
    tela, ctx, ambiente, dialogos = montar(raiz, orcamento=com_ids(contas=[antiga]))
    tela.contas.arvore.selection_set("1")
    tela.contas.excluir()
    assert "já foi descontada" in dialogos.avisos[-1][1] and itens(ambiente).contas == [antiga]


def test_excluir_conta_nova_pede_confirmacao(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar(raiz, confirma=False)
    tela.contas.arvore.selection_set("2")
    tela.contas.excluir()
    assert len(itens(ambiente).contas) == 2  # respondeu não
    dialogos.confirma = True
    tela.contas.excluir()
    assert [c.id for c in itens(ambiente).contas] == [1]
    assert not dialogos.avisos


def test_excluir_entrada_e_meta(raiz):  # noqa: F811
    tela, ctx, ambiente, _ = montar(raiz)
    tela.metas.arvore.selection_set("1")
    tela.metas.excluir()
    assert itens(ambiente).metas == [] and linhas(tela.metas.arvore) == []
    tela.entradas.arvore.selection_set("1")
    tela.entradas.excluir()
    assert itens(ambiente).entradas == []


def test_encerrar_conta(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar(raiz)
    tela.contas.arvore.selection_set("1")
    tela.contas.encerrar()
    assert por_id(itens(ambiente).contas, 1).encerrada_em == HOJE
    assert ('Aluguel', 'R$ 1.000,00', 'dia 1', 'sem fim, encerrada em 05/10/2026') in linhas(tela.contas.arvore)
    tela.contas.encerrar()  # segunda vez: só avisa
    assert dialogos.avisos[-1][0] == "Já encerrada"


def test_pausar_e_reativar_meta(raiz):  # noqa: F811
    tela, ctx, ambiente, _ = montar(raiz)
    tela.metas.arvore.selection_set("1")
    tela.metas.pausar()
    assert not itens(ambiente).metas[0].ativa and linhas(tela.metas.arvore)[0][2] == "pausada"
    tela.metas.pausar()
    assert itens(ambiente).metas[0].ativa and linhas(tela.metas.arvore)[0][2] == "ativa"


def test_editar_meta_mantem_o_tipo(raiz):  # noqa: F811
    tela, ctx, ambiente, _ = montar(raiz)
    f = FormularioMeta(tela.metas, ctx, itens(ambiente).metas[0])
    assert f.valor.get() == "10%"
    f.valor.set("15")
    assert f.salvar()
    assert itens(ambiente).metas[0] == replace(cenario.reserva, id=1, nome="Reserva", valor=1_500)
