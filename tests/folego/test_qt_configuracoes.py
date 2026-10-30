from dataclasses import replace

from src.folego.modelos import Configuracoes
from src.folego.qt.tela_configuracoes import TelaConfiguracoes
from .qt_helpers import contexto_de_teste, qapp  # noqa: F401

BASE = Configuracoes(primeiro_uso_concluido=True)


def _tela(qapp, **kw):  # noqa: F811
    ctx, _, dlg = contexto_de_teste(**kw)
    return TelaConfiguracoes(ctx), ctx, dlg


def _digitar(tela, *textos):
    for campo, t in zip(tela.campos, textos):
        campo.setText(t)


def test_mostra_valores_gravados(qapp):  # noqa: F811
    tela, _, _ = _tela(qapp, config=replace(BASE, limite_semanal_manual=35000))
    assert tela._atuais() == ("1", "350,00", "70", "90")


def test_salva_limite_e_percentuais(qapp):  # noqa: F811
    tela, ctx, dlg = _tela(qapp)
    _digitar(tela, "1", "400", "60", "80")
    tela.botao_salvar.click()
    c = ctx.repo.configuracoes()
    assert (c.limite_semanal_manual, c.percentual_atencao, c.percentual_critico) == (40000, 6000, 8000)
    assert not dlg.avisos


def test_atencao_maior_que_critico_bloqueada(qapp):  # noqa: F811
    tela, ctx, dlg = _tela(qapp)
    _digitar(tela, "1", "", "95", "90")
    tela.botao_salvar.click()
    assert len(dlg.avisos) == 1
    assert ctx.repo.configuracoes().percentual_atencao == 7000


def test_texto_ilegivel_avisa(qapp):  # noqa: F811
    tela, _, dlg = _tela(qapp)
    _digitar(tela, "1", "abc", "70", "90")
    tela.botao_salvar.click()
    assert dlg.avisos[0][0] == "Dado inválido"


def test_dia_sem_confirmar_nao_grava(qapp):  # noqa: F811
    tela, ctx, _ = _tela(qapp, confirma=False)
    _digitar(tela, "10", "", "70", "90")
    tela.botao_salvar.click()
    assert ctx.repo.configuracoes().dia_pagamento == 1


def test_dia_confirmado_grava(qapp):  # noqa: F811
    tela, ctx, _ = _tela(qapp, confirma=True)
    _digitar(tela, "10", "", "70", "90")
    tela.botao_salvar.click()
    assert ctx.repo.configuracoes().dia_pagamento == 10


def test_desfazer_volta_ao_gravado(qapp):  # noqa: F811
    tela, _, _ = _tela(qapp)
    _digitar(tela, "20", "999", "70", "90")
    tela.botao_desfazer.click()
    assert tela._atuais() == ("1", "", "70", "90")


def test_atualizar_preserva_digitacao(qapp):  # noqa: F811
    tela, _, _ = _tela(qapp)
    tela.campos[1].setText("123")
    tela.atualizar()
    assert tela.campos[1].text() == "123"
