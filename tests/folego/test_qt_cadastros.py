from dataclasses import replace

from PySide6.QtCore import Qt

from src.folego.modelos import TipoEntrada, TipoMeta
from src.folego.qt.formularios import FormularioConta, FormularioEntrada, FormularioMeta
from src.folego.qt.tela_cadastros import TelaCadastros
from . import cenario
from .cenario import data
from .qt_helpers import contexto_de_teste, qapp  # noqa: F401  (qapp é uma fixture)

HOJE = data(5, 10)


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


def montar(**kwargs):
    ctx, ambiente, dialogos = contexto_de_teste(orcamento=kwargs.pop("orcamento", com_ids()), **kwargs)
    tela = TelaCadastros(ctx)
    ctx.mudou.connect(tela.atualizar)  # a janela faz isso no app
    tela.atualizar()
    return tela, ctx, ambiente, dialogos


def itens(ambiente):
    return ambiente.orcamento.orcamento()


def por_id(lista, id):
    return next(i for i in lista if i.id == id)  # o repositório falso pode reordenar ao salvar


def linhas(lista):
    t = lista.tabela
    return [tuple(t.item(r, c).text() for c in range(t.columnCount())) for r in range(t.rowCount())]


# --- listas ---------------------------------------------------------------------

def test_listas_mostram_entradas_contas_e_metas(qapp):  # noqa: F811
    tela, *_ = montar()
    assert linhas(tela.entradas) == [("Salário", "R$ 3.000,00", "recorrente", "01/10/2026", "sem fim")]
    assert linhas(tela.contas) == [("Aluguel", "R$ 1.000,00", "dia 1", "sem fim"),
                                   ("Celular", "R$ 200,00", "dia 1", "parcela 1 de 3")]
    assert linhas(tela.metas) == [("Reserva", "10%", "ativa")]
    assert tela.contas.tabela.item(0, 1).textAlignment() & Qt.AlignRight  # valores à direita


def test_conta_com_parcela_avancada_mostra_a_situacao(qapp):  # noqa: F811
    celular = replace(cenario.celular, id=2, descricao="Celular", ciclo_inicio=data(1, 8))
    tela, *_ = montar(orcamento=com_ids(contas=[celular]))
    assert linhas(tela.contas) == [("Celular", "R$ 200,00", "dia 1", "parcela 3 de 3")]


def test_itens_sem_id_nao_quebram_a_aba(qapp):  # noqa: F811
    tela, *_ = montar(orcamento=cenario.orcamento)
    assert len(linhas(tela.contas)) == 2
    tela.contas.tabela.selectRow(1)
    tela.atualizar()
    assert tela.contas.selecionado() is cenario.celular


def test_atualizar_mantem_a_subaba_e_a_selecao(qapp):  # noqa: F811
    tela, ctx, ambiente, _ = montar()
    tela.abas.setCurrentWidget(tela.contas)
    tela.contas.tabela.selectRow(1)
    ctx.mudou.emit()
    assert tela.abas.currentWidget() is tela.contas and tela.contas.selecionado().id == 2


# --- adicionar ------------------------------------------------------------------

def test_adicionar_entrada_avulsa_pelo_botao(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar()
    tela.entradas.botao_adicionar.click()
    f = tela.entradas.dialogo
    assert isinstance(f, FormularioEntrada) and f.isVisible()
    f.descricao.setText("Bico")
    f.valor.setText("150,00")
    f.tipo.setCurrentIndex(f.tipo.findData(TipoEntrada.AVULSA))
    assert f.inicio.text() == "05/10/2026" and not f.fim.isEnabled()  # o padrão do início acompanha o tipo
    assert f.salvar()
    nova = itens(ambiente).entradas[-1]
    assert (nova.descricao, nova.valor_centavos, nova.tipo, nova.data_inicio) == (
        "Bico", 15_000, TipoEntrada.AVULSA, HOJE)
    assert len(linhas(tela.entradas)) == 2 and not f.isVisible() and tela.entradas.dialogo is None


def test_adicionar_entrada_invalida_nao_fecha_o_formulario(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar()
    f = FormularioEntrada(ctx)
    f.descricao.setText("X")
    f.valor.setText("abc")
    assert not f.salvar() and dialogos.avisos
    f.valor.setText("0")
    assert not f.salvar() and "maior que zero" in dialogos.avisos[-1][1]
    assert len(itens(ambiente).entradas) == 1


def test_adicionar_conta_na_parcela_3_de_10(qapp):  # noqa: F811
    tela, ctx, ambiente, _ = montar()
    tela.abas.setCurrentWidget(tela.contas)
    tela.contas.botao_adicionar.click()
    f = tela.contas.dialogo
    assert isinstance(f, FormularioConta) and not f.parcela.isEnabled()  # parcela só com duração
    f.descricao.setText("Carro")
    f.valor.setText("300,00")
    f.vencimento.setText("10")
    f.duracao.setText("10")
    assert f.parcela.isEnabled()
    f.parcela.setText("3")
    assert f.salvar()
    carro = itens(ambiente).contas[-1]
    assert carro.ciclo_inicio == data(1, 8) and carro.duracao_meses == 10 and carro.dia_vencimento == 10
    assert ("Carro", "R$ 300,00", "dia 10", "parcela 3 de 10") in linhas(tela.contas)


def test_adicionar_meta_por_valor_e_por_percentual(qapp):  # noqa: F811
    tela, ctx, ambiente, _ = montar()
    f = FormularioMeta(ctx)
    f.nome.setText("Viagem")
    f.valor.setText("200,00")
    assert f.salvar()
    g = FormularioMeta(ctx)
    g.nome.setText("Estudos")
    g.tipo.setCurrentIndex(g.tipo.findData(TipoMeta.PERCENTUAL))
    g.valor.setText("5")
    assert g.salvar()
    assert [(m.nome, m.tipo, m.valor) for m in itens(ambiente).metas[1:]] == [
        ("Viagem", TipoMeta.VALOR, 20_000), ("Estudos", TipoMeta.PERCENTUAL, 500)]


def test_ca04_meta_que_nao_cabe_e_bloqueada_com_quanto_falta(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar()
    f = FormularioMeta(ctx)
    f.nome.setText("Grande")
    f.valor.setText("2.000,00")
    assert not f.salvar()
    assert "Faltam R$ 500,00" in dialogos.avisos[-1][1]
    assert len(itens(ambiente).metas) == 1


# --- editar ---------------------------------------------------------------------

def test_editar_conta_vem_preenchida_e_mantem_o_id(qapp):  # noqa: F811
    tela, ctx, ambiente, _ = montar()
    aluguel = itens(ambiente).contas[0]
    f = FormularioConta(ctx, aluguel)
    assert (f.descricao.text(), f.valor.text(), f.vencimento.text(), f.duracao.text()) == (
        "Aluguel", "R$ 1.000,00", "1", "")
    assert f.parcela is None
    f.valor.setText("1.100,00")
    assert f.salvar()
    assert por_id(itens(ambiente).contas, 1) == replace(aluguel, valor_centavos=110_000)
    assert [v[1] for v in linhas(tela.contas) if v[0] == "Aluguel"] == ["R$ 1.100,00"]


def test_duplo_clique_edita_a_linha(qapp):  # noqa: F811
    tela, *_ = montar()
    tela.contas.tabela.selectRow(1)
    tela.contas.tabela.cellDoubleClicked.emit(1, 0)
    assert tela.contas.dialogo.item.id == 2 and tela.contas.dialogo.descricao.text() == "Celular"


def test_editar_entrada_trava_o_tipo(qapp):  # noqa: F811
    tela, ctx, ambiente, _ = montar()
    f = FormularioEntrada(ctx, itens(ambiente).entradas[0])
    assert f.inicio.text() == "01/10/2026" and not f.tipo.isEnabled()
    f.valor.setText("3.500,00")
    f.fim.setText("31/12/2026")
    assert f.salvar()
    e = itens(ambiente).entradas[0]
    assert (e.id, e.valor_centavos, e.data_fim) == (1, 350_000, data(31, 12))


def test_editar_meta_mantem_o_tipo(qapp):  # noqa: F811
    tela, ctx, ambiente, _ = montar()
    f = FormularioMeta(ctx, itens(ambiente).metas[0])
    assert f.valor.text() == "10%" and not f.tipo.isEnabled()
    f.valor.setText("15")
    assert f.salvar()
    assert itens(ambiente).metas[0] == replace(cenario.reserva, id=1, nome="Reserva", valor=1_500)


def test_botoes_sem_selecao_avisam(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar()
    tela.contas.botao_editar.click()
    tela.contas.botao_encerrar.click()
    tela.contas.botao_excluir.click()
    tela.metas.botao_pausar.click()
    tela.entradas.botao_excluir.click()
    assert len(dialogos.avisos) == 5 and len(itens(ambiente).contas) == 2
    assert tela.contas.dialogo is None


# --- excluir, encerrar, pausar --------------------------------------------------

def test_excluir_conta_ja_descontada_e_bloqueado(qapp):  # noqa: F811
    antiga = replace(cenario.aluguel, id=1, descricao="Aluguel", ciclo_inicio=data(1, 8))
    tela, ctx, ambiente, dialogos = montar(orcamento=com_ids(contas=[antiga]))
    tela.contas.tabela.selectRow(0)
    tela.contas.excluir()
    assert "já foi descontada" in dialogos.avisos[-1][1] and itens(ambiente).contas == [antiga]


def test_excluir_conta_nova_pede_confirmacao(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar(confirma=False)
    tela.contas.tabela.selectRow(1)
    tela.contas.excluir()
    assert len(itens(ambiente).contas) == 2  # respondeu não
    dialogos.confirma = True
    tela.contas.excluir()
    assert [c.id for c in itens(ambiente).contas] == [1]
    assert not dialogos.avisos


def test_excluir_entrada_e_meta(qapp):  # noqa: F811
    tela, ctx, ambiente, _ = montar()
    tela.metas.tabela.selectRow(0)
    tela.metas.excluir()
    assert itens(ambiente).metas == [] and linhas(tela.metas) == []
    tela.entradas.tabela.selectRow(0)
    tela.entradas.excluir()
    assert itens(ambiente).entradas == []


def test_encerrar_conta(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = montar()
    tela.contas.tabela.selectRow(0)
    tela.contas.encerrar()
    assert por_id(itens(ambiente).contas, 1).encerrada_em == HOJE
    assert ("Aluguel", "R$ 1.000,00", "dia 1", "sem fim, encerrada em 05/10/2026") in linhas(tela.contas)
    tela.contas.encerrar()  # segunda vez: só avisa
    assert dialogos.avisos[-1][0] == "Já encerrada"


def test_pausar_e_reativar_meta(qapp):  # noqa: F811
    tela, ctx, ambiente, _ = montar()
    tela.metas.tabela.selectRow(0)
    tela.metas.botao_pausar.click()
    assert not itens(ambiente).metas[0].ativa and linhas(tela.metas)[0][2] == "pausada"
    tela.metas.botao_pausar.click()  # a seleção sobrevive ao redesenho
    assert itens(ambiente).metas[0].ativa and linhas(tela.metas)[0][2] == "ativa"
