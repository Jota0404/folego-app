from dataclasses import replace

from src.folego.gui.tela_configuracoes import TelaConfiguracoes, ler_formulario
from src.folego.modelos import Configuracoes
from .gui_helpers import contexto_de_teste, raiz  # noqa: F401

BASE = Configuracoes(primeiro_uso_concluido=True)


def test_ler_formulario_valido():
    nova = ler_formulario("5", "350,00", "70", "87,5", BASE)
    assert (nova.dia_pagamento, nova.limite_semanal_manual) == (5, 35000)
    assert (nova.percentual_atencao, nova.percentual_critico) == (7000, 8750)
    assert nova.primeiro_uso_concluido


def test_ler_formulario_limite_vazio_e_automatico():
    assert ler_formulario("1", " ", "70", "90", BASE).limite_semanal_manual is None


def test_ler_formulario_erros():
    for args in [("0", "", "70", "90"), ("32", "", "70", "90"), ("x", "", "70", "90"),
                 ("1", "abc", "70", "90"), ("1", "", "abc", "90"), ("1", "", "70", "")]:
        assert isinstance(ler_formulario(*args, BASE), str), args


def _tela(raiz, **kw):  # noqa: F811
    ctx, amb, dlg = contexto_de_teste(**kw)
    tela = TelaConfiguracoes(raiz, ctx)
    return tela, ctx, dlg


def test_tela_mostra_valores_gravados(raiz):  # noqa: F811
    tela, _, _ = _tela(raiz, config=replace(BASE, limite_semanal_manual=35000))
    assert tela._atuais() == ("1", "350,00", "70", "90")


def test_tela_salva_limite_e_percentuais(raiz):  # noqa: F811
    tela, ctx, dlg = _tela(raiz)
    for var, t in zip(tela.vars, ("1", "400", "60", "80")):
        var.set(t)
    tela.salvar()
    c = ctx.repo.configuracoes()
    assert (c.limite_semanal_manual, c.percentual_atencao, c.percentual_critico) == (40000, 6000, 8000)
    assert not dlg.avisos


def test_tela_atencao_maior_que_critico_bloqueada(raiz):  # noqa: F811
    tela, ctx, dlg = _tela(raiz)
    tela.vars[2].set("95")
    tela.vars[3].set("90")
    tela.salvar()
    assert len(dlg.avisos) == 1
    assert ctx.repo.configuracoes().percentual_atencao == 7000


def test_tela_texto_ilegivel_avisa(raiz):  # noqa: F811
    tela, ctx, dlg = _tela(raiz)
    tela.vars[1].set("abc")
    tela.salvar()
    assert dlg.avisos[0][0] == "Dado inválido"


def test_tela_dia_sem_confirmar_nao_grava(raiz):  # noqa: F811
    tela, ctx, dlg = _tela(raiz, confirma=False)
    tela.vars[0].set("10")
    tela.salvar()
    assert ctx.repo.configuracoes().dia_pagamento == 1


def test_tela_dia_confirmado_grava(raiz):  # noqa: F811
    tela, ctx, dlg = _tela(raiz, confirma=True)
    tela.vars[0].set("10")
    tela.salvar()
    assert ctx.repo.configuracoes().dia_pagamento == 10


def test_tela_desfazer_volta_ao_gravado(raiz):  # noqa: F811
    tela, ctx, _ = _tela(raiz)
    tela.vars[0].set("20")
    tela.vars[1].set("999")
    tela.desfazer()
    assert tela._atuais() == ("1", "", "70", "90")


def test_atualizar_preserva_digitacao(raiz):  # noqa: F811
    tela, _, _ = _tela(raiz)
    tela.vars[1].set("123")
    tela.atualizar()
    assert tela.vars[1].get() == "123"
