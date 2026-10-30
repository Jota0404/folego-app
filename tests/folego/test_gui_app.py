from src.folego.gui.app import TELAS, abrir
from .gui_helpers import contexto_de_teste, raiz  # noqa: F401  (raiz é uma fixture)


def test_a_janela_abre_com_todas_as_abas_e_navega(raiz):  # noqa: F811
    ctx, ambiente, dialogos = contexto_de_teste()
    janela, contexto = abrir(ctx.repo, raiz=raiz, contexto=ctx)
    assert set(contexto._telas) == {chave for chave, *_ in TELAS}
    contexto.ir_para("gasto")
    contexto.mudou()
    assert janela.title() == "Fôlego"
    assert dialogos.infos  # a rotina diária mostrou o resumo da semana por diálogo falso
