from src.folego.qt.janela import TELAS, JanelaPrincipal, abrir, primeiro_uso
from src.folego.calculadora import Orcamento
from src.folego.modelos import Configuracoes, TipoEntrada
from .qt_helpers import contexto_de_teste, qapp  # noqa: F401  (qapp é uma fixture)


def test_a_janela_abre_com_todas_as_abas_e_navega(qapp):  # noqa: F811
    ctx, ambiente, dialogos = contexto_de_teste()
    janela, contexto = abrir(ctx.repo, contexto=ctx)
    assert isinstance(janela, JanelaPrincipal)
    assert set(janela.telas) == {chave for chave, *_ in TELAS}
    contexto.ir_para("gasto")
    assert janela.abas.currentWidget() is janela.telas["gasto"]
    assert dialogos.infos  # a rotina diária mostrou o resumo da semana por diálogo falso
    janela.close()


def test_primeiro_uso_define_o_dia_cadastra_o_salario_e_conclui(qapp):  # noqa: F811
    ctx, ambiente, dialogos = contexto_de_teste(Orcamento(), Configuracoes(), respostas=["5", "3.000,00"])
    primeiro_uso(ctx)
    config = ambiente.configuracoes.configuracoes()
    assert config.dia_pagamento == 5 and config.primeiro_uso_concluido
    [salario] = ambiente.orcamento.orcamento().entradas
    assert salario.valor_centavos == 300_000 and salario.tipo == TipoEntrada.RECORRENTE


def test_primeiro_uso_repergunta_valor_invalido_e_cancelar_nao_conclui(qapp):  # noqa: F811
    respostas = ["40", "abc", "10", "xyz", "1.000,00"]
    ctx, ambiente, dialogos = contexto_de_teste(Orcamento(), Configuracoes(), respostas=respostas)
    primeiro_uso(ctx)
    assert ambiente.configuracoes.configuracoes().dia_pagamento == 10
    assert ambiente.orcamento.orcamento().entradas[0].valor_centavos == 100_000
    assert len(dialogos.avisos) == 3
    ctx2, amb2, _ = contexto_de_teste(Orcamento(), Configuracoes(), respostas=[None])
    primeiro_uso(ctx2)
    assert not amb2.configuracoes.configuracoes().primeiro_uso_concluido
