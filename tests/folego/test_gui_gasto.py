from datetime import date

from src.folego.gui.tela_gasto import TelaGasto, ler_formulario
from src.folego.modelos import CATEGORIAS_PADRAO, Gasto
from .gui_helpers import contexto_de_teste, raiz  # noqa: F401  (raiz é uma fixture)

HOJE = date(2026, 10, 5)


def _tela(raiz, **kw):  # noqa: F811
    ctx, ambiente, dialogos = contexto_de_teste(**kw)
    tela = TelaGasto(raiz, ctx)
    ctx.registrar("gasto", tela)
    return tela, ctx, ambiente, dialogos


def _preencher(tela, valor, data=None, descricao=""):
    tela.entrada_valor.delete(0, "end")
    tela.entrada_valor.insert(0, valor)
    if data is not None:
        tela.entrada_data.delete(0, "end")
        tela.entrada_data.insert(0, data)
    tela.entrada_descricao.insert(0, descricao)


def _gastos(ambiente):
    return ambiente.orcamento.dados.gastos


def test_ler_formulario_valor_e_categoria():
    g = ler_formulario("1.500,00", "03/10/2026", " Mercado ", "Outros", HOJE, CATEGORIAS_PADRAO)
    assert g == Gasto(150_000, date(2026, 10, 3), "Mercado", 5)
    assert ler_formulario("150,5", "", "", "Outros", HOJE, CATEGORIAS_PADRAO).valor_centavos == 15_050
    assert isinstance(ler_formulario("abc", "", "", "Outros", HOJE, CATEGORIAS_PADRAO), str)
    assert isinstance(ler_formulario("10", "", "", "Inexistente", HOJE, CATEGORIAS_PADRAO), str)


def test_ler_formulario_data_dd_mm_e_ilegivel():
    assert ler_formulario("10", "03/10", "", "Outros", HOJE, CATEGORIAS_PADRAO).data == date(2026, 10, 3)
    assert ler_formulario("10", "", "", "Outros", HOJE, CATEGORIAS_PADRAO).data == HOJE
    for ruim in ("31/02", "ontem", "1/2/3/4", "10-10-2026"):
        assert isinstance(ler_formulario("10", ruim, "", "Outros", HOJE, CATEGORIAS_PADRAO), str)


def test_salvar_gasto_pela_tela(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela(raiz)
    assert tela.data.get() == "05/10/2026" and tela.categoria.get() == "Outros"
    _preencher(tela, "50,00", descricao="Lanche")
    tela.botao_salvar.invoke()
    assert [(g.valor_centavos, g.descricao) for g in _gastos(ambiente)] == [(5_000, "Lanche")]
    assert tela.valor.get() == "" and tela.descricao.get() == ""
    assert [tela.arvore.item(i, "values")[1:] for i in tela.arvore.get_children()] == [("Lanche", "Outros", "R$ 50,00")]
    assert not dialogos.avisos


def test_valor_invalido_e_zero_nao_gravam(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela(raiz)
    _preencher(tela, "abc")
    tela.botao_salvar.invoke()
    assert dialogos.avisos[-1][0] == "Dado inválido"
    tela.valor.set("0")
    tela.botao_salvar.invoke()
    assert len(dialogos.avisos) == 2 and not _gastos(ambiente)
    assert tela.valor.get() == "0"  # o que foi digitado continua lá


def test_ca03_gasto_que_invade_a_reserva(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela(raiz)
    _preencher(tela, "1.600,00")
    tela.botao_salvar.invoke()
    assert len(_gastos(ambiente)) == 1
    assert any("invadiu a reserva em R$ 100,00" in texto for _, texto in dialogos.infos)


def test_data_futura_bloqueada(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela(raiz)
    _preencher(tela, "10,00", data="06/10/2026")
    tela.botao_salvar.invoke()
    assert not _gastos(ambiente) and dialogos.avisos[-1][0] == "Não foi possível"


def test_corrigir_gasto_mantem_o_id(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela(raiz)
    _preencher(tela, "50,00", descricao="Lanche")
    tela.botao_salvar.invoke()
    antigo = _gastos(ambiente)[0]
    tela.botao_corrigir.invoke()
    assert dialogos.avisos  # nada selecionado
    tela.arvore.selection_set(tela.arvore.get_children()[0])
    tela.botao_corrigir.invoke()
    assert tela.formulario.cget("text") == "Corrigir gasto" and tela.valor.get() == "50,00"
    tela.valor.set("70,00")
    tela.botao_salvar.invoke()
    assert [(g.id, g.valor_centavos) for g in _gastos(ambiente)] == [(antigo.id, 7_000)]
    assert tela.formulario.cget("text") == "Novo gasto"


def test_excluir_gasto_pela_tela(raiz):  # noqa: F811
    tela, ctx, ambiente, dialogos = _tela(raiz)
    _preencher(tela, "50,00")
    tela.botao_salvar.invoke()
    tela.botao_excluir.invoke()
    assert len(dialogos.avisos) == 1 and len(_gastos(ambiente)) == 1  # sem seleção
    tela.arvore.selection_set(tela.arvore.get_children()[0])
    dialogos.confirma = False
    tela.botao_excluir.invoke()
    assert len(_gastos(ambiente)) == 1
    dialogos.confirma = True
    tela.botao_excluir.invoke()
    assert not _gastos(ambiente) and not tela.arvore.get_children()
