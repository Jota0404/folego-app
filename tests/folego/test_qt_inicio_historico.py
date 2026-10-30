from dataclasses import replace

from src.folego.apresentacao.inicio import CORES
from src.folego.calculadora import Faixa
from src.folego.modelos import Ciclo, CicloFechado, Gasto, Resumo
from src.folego.qt.tela_historico import TelaHistorico
from src.folego.qt.tela_inicio import TelaInicio
from .cenario import data, orcamento
from .qt_helpers import contexto_de_teste, qapp  # noqa: F401  (qapp é uma fixture)


def _inicio(gastos=()):
    ctx, _, _ = contexto_de_teste(replace(orcamento, gastos=list(gastos)))
    return TelaInicio(ctx), ctx


def test_ca05_inicio_mostra_textos(qapp):  # noqa: F811
    tela, _ = _inicio()
    t = {k: v.text() for k, v in tela.rotulos.items()}
    assert t["titulo"] == "Ciclo: 01/10/2026 a 31/10/2026"
    assert t["disponivel_semana"] == "R$ 388,88"
    assert t["reserva"] == "R$ 300,00"
    assert t["consumo"] == "0% do limite consumido"
    assert tela.quadro_avisos.count() == 0


def test_ca05_barra_cor_e_valor(qapp):  # noqa: F811
    for valor, faixa, pct in [(0, Faixa.VERDE, 0), (29_166, Faixa.AMARELA, 75), (36_944, Faixa.VERMELHA, 95)]:
        tela, _ = _inicio([Gasto(valor, data(5, 10), id=1)] if valor else [])
        assert tela.barra.value() == pct
        assert CORES[faixa] in tela.barra.styleSheet()
        assert tela.rotulos["consumo"].text().startswith("%d%%" % pct)


def test_inicio_avisa_reserva_invadida_e_botao_vai_para_gasto(qapp):  # noqa: F811
    tela, ctx = _inicio([Gasto(160_000, data(2, 10), id=1)])
    assert tela.quadro_avisos.count() == 1
    destinos = []
    ctx.definir_navegacao(destinos.append)
    tela.botao_gasto.click()
    assert destinos == ["gasto"]


GASTOS = [Gasto(1_000, data(2, 10), "pão", 1, id=1), Gasto(2_500, data(4, 10), "ônibus", 2, id=2),
          Gasto(500, data(4, 10), "", id=3), Gasto(900, data(30, 9), "ciclo anterior", 1, id=4)]


def test_historico_tela_mostra_gastos_e_fechados(qapp):  # noqa: F811
    ctx, amb, _ = contexto_de_teste(replace(orcamento, gastos=GASTOS))
    amb.historico.fechados.append(CicloFechado(Ciclo(data(1, 9), data(30, 9)), Resumo(1, 0, 0, 0), None, 1))
    tela = TelaHistorico(ctx)
    assert tela.gastos.topLevelItemCount() == 2
    assert tela.gastos.topLevelItem(0).childCount() == 2
    assert tela.gastos.topLevelItem(0).text(3) == "R$ 30,00"
    assert tela.fechados.topLevelItemCount() == 1
    ctx.mudou.emit()
    tela.atualizar()
    assert tela.gastos.topLevelItemCount() == 2


def test_historico_exporta_csv(qapp, tmp_path):  # noqa: F811
    ctx, _, dialogos = contexto_de_teste(replace(orcamento, gastos=GASTOS), pasta_exportacao=tmp_path)
    TelaHistorico(ctx).exportar()
    arquivos = list(tmp_path.glob("*.csv"))
    assert len(arquivos) == 1
    assert dialogos.infos[-1][0] == "Exportado" and str(arquivos[0]) in dialogos.infos[-1][1]


def test_historico_exportacao_indisponivel_sem_pasta(qapp):  # noqa: F811
    ctx, _, dialogos = contexto_de_teste(replace(orcamento, gastos=GASTOS))
    TelaHistorico(ctx).exportar()
    assert dialogos.avisos == [("Exportação", "Exportação indisponível.")]
