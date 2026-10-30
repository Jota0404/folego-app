from src.folego.qt.tela_gasto import TelaGasto
from .qt_helpers import contexto_de_teste, qapp  # noqa: F401  (qapp é uma fixture)


def _tela(**kw):
    ctx, ambiente, dialogos = contexto_de_teste(**kw)
    tela = TelaGasto(ctx)
    ctx.mudou.connect(tela.atualizar)  # a janela faz isso na vida real
    return tela, ctx, ambiente, dialogos


def _preencher(tela, valor, data=None, descricao=""):
    tela.valor.setText(valor)
    if data is not None:
        tela.data.setText(data)
    tela.descricao.setText(descricao)


def _gastos(ambiente):
    return ambiente.orcamento.dados.gastos


def _linhas(tela):
    return [[tela.tabela.item(i, j).text() for j in range(4)] for i in range(tela.tabela.rowCount())]


def test_salvar_gasto_pela_tela(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela()
    assert tela.data.text() == "05/10/2026" and tela.categoria.currentText() == "Outros"
    _preencher(tela, "50,00", descricao="Lanche")
    tela.botao_salvar.click()
    assert [(g.valor_centavos, g.descricao) for g in _gastos(ambiente)] == [(5_000, "Lanche")]
    assert tela.valor.text() == "" and tela.descricao.text() == ""
    assert [linha[1:] for linha in _linhas(tela)] == [["Lanche", "Outros", "R$ 50,00"]]
    assert not dialogos.avisos


def test_valor_invalido_e_zero_nao_gravam(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela()
    _preencher(tela, "abc")
    tela.botao_salvar.click()
    assert dialogos.avisos[-1][0] == "Dado inválido"
    tela.valor.setText("0")
    tela.botao_salvar.click()
    assert len(dialogos.avisos) == 2 and not _gastos(ambiente)
    assert tela.valor.text() == "0"  # o que foi digitado continua lá


def test_ca03_gasto_que_invade_a_reserva(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela()
    _preencher(tela, "1.600,00")
    tela.botao_salvar.click()
    assert len(_gastos(ambiente)) == 1
    assert any("invadiu a reserva em R$ 100,00" in texto for _, texto in dialogos.infos)


def test_data_futura_bloqueada(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela()
    _preencher(tela, "10,00", data="06/10/2026")
    tela.botao_salvar.click()
    assert not _gastos(ambiente) and dialogos.avisos[-1][0] == "Não foi possível"


def test_corrigir_gasto_mantem_o_id(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela()
    _preencher(tela, "50,00", descricao="Lanche")
    tela.botao_salvar.click()
    antigo = _gastos(ambiente)[0]
    tela.botao_corrigir.click()
    assert dialogos.avisos  # nada selecionado
    tela.tabela.selectRow(0)
    tela.botao_corrigir.click()
    assert tela.formulario.title() == "Corrigir gasto" and tela.valor.text() == "50,00"
    assert not tela.botao_cancelar.isHidden()
    tela.valor.setText("70,00")
    tela.botao_salvar.click()
    assert [(g.id, g.valor_centavos) for g in _gastos(ambiente)] == [(antigo.id, 7_000)]
    assert tela.formulario.title() == "Novo gasto" and tela.botao_cancelar.isHidden()


def test_excluir_gasto_pela_tela(qapp):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela()
    _preencher(tela, "50,00")
    tela.botao_salvar.click()
    tela.botao_excluir.click()
    assert len(dialogos.avisos) == 1 and len(_gastos(ambiente)) == 1  # sem seleção
    tela.tabela.selectRow(0)
    dialogos.confirma = False
    tela.botao_excluir.click()
    assert len(_gastos(ambiente)) == 1
    dialogos.confirma = True
    tela.botao_excluir.click()
    assert not _gastos(ambiente) and tela.tabela.rowCount() == 0
