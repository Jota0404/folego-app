from dataclasses import replace

from src.folego.calculadora import Faixa
from src.folego.gui.tela_historico import TelaHistorico, linhas_de_fechados, linhas_de_gastos
from src.folego.gui.tela_inicio import CORES, TelaInicio, avisos_do_inicio, textos_do_inicio
from src.folego.modelos import Ciclo, CicloFechado, Gasto, Resumo
from .cenario import data, orcamento
from .gui_helpers import contexto_de_teste, raiz  # noqa: F401  (raiz é uma fixture)


def _inicio(raiz, gastos=()):  # noqa: F811
    ctx, amb, dialogos = contexto_de_teste(replace(orcamento, gastos=list(gastos)))
    tela = TelaInicio(raiz, ctx)
    return tela, ctx


def test_ca05_textos_do_inicio(raiz):  # noqa: F811
    tela, ctx = _inicio(raiz)
    t = {k: v.get() for k, v in tela.var.items()}
    assert t["titulo"] == "Ciclo: 01/10/2026 a 31/10/2026"
    assert t["disponivel_semana"] == "R$ 388,88"
    assert t["limite"] == "R$ 388,88"
    assert t["disponivel_ciclo"] == "R$ 1.500,00"
    assert t["reserva"] == "R$ 300,00"
    assert t["consumo"] == "0% do limite consumido"
    assert t["semana"].startswith("Semana de ")
    assert avisos_do_inicio(ctx.repo.orcamento().painel(ctx.ciclo(), ctx.hoje, ctx.repo.configuracoes())) == []


def test_ca05_cor_e_faixa_da_barra(raiz):  # noqa: F811
    for valor, faixa, texto in [(0, Faixa.VERDE, "0%"), (29_166, Faixa.AMARELA, "75%"),
                                (36_944, Faixa.VERMELHA, "95%")]:
        gastos = [Gasto(valor, data(5, 10), id=1)] if valor else []
        tela, _ = _inicio(raiz, gastos)
        assert tela.var["consumo"].get().startswith(texto)
        assert tela.barra.itemcget(tela._preenchido, "fill") == CORES[faixa]
        x1 = tela.barra.coords(tela._preenchido)[2]
        assert x1 == 400 * (valor * 10_000 // 38_888) // 10_000


def test_inicio_avisa_reserva_invadida_e_botao_vai_para_gasto(raiz):  # noqa: F811
    tela, ctx = _inicio(raiz, [Gasto(160_000, data(2, 10), id=1)])
    painel = ctx.repo.orcamento().painel(ctx.ciclo(), ctx.hoje, ctx.repo.configuracoes())
    assert avisos_do_inicio(painel) == ["Reserva invadida em R$ 100,00."]
    assert len(tela.quadro_avisos.winfo_children()) == 1
    destinos = []
    ctx.definir_navegacao(destinos.append)
    [b for b in tela.winfo_children() if b.winfo_class() == "TButton"][0].invoke()
    assert destinos == ["gasto"]


def test_inicio_com_limite_zero_nao_quebra():
    from src.folego.modelos import Configuracoes
    ctx, _, _ = contexto_de_teste(replace(orcamento, entradas=[]), Configuracoes(primeiro_uso_concluido=True))
    painel = ctx.repo.orcamento().painel(ctx.ciclo(), ctx.hoje, ctx.repo.configuracoes())
    t = textos_do_inicio(painel, ctx.ciclo())
    assert painel.faixa == Faixa.VERMELHA
    assert t["consumo"] == "100% do limite consumido"


GASTOS = [Gasto(1_000, data(2, 10), "pão", 1, id=1), Gasto(2_500, data(4, 10), "ônibus", 2, id=2),
          Gasto(500, data(4, 10), "", id=3), Gasto(900, data(30, 9), "ciclo anterior", 1, id=4)]


def test_historico_ordem_subtotal_e_categoria():
    ctx, _, _ = contexto_de_teste(replace(orcamento, gastos=GASTOS))
    dias = linhas_de_gastos(ctx.repo.orcamento().gastos, ctx.repo.categorias(), ctx.ciclo())
    assert [d[0] for d in dias] == [("04/10/2026", "Total do dia", "", "R$ 30,00"),
                                    ("02/10/2026", "Total do dia", "", "R$ 10,00")]
    assert dias[0][1] == [("", "", "Outros", "R$ 5,00"), ("", "ônibus", "Transporte", "R$ 25,00")]
    assert dias[1][1] == [("", "pão", "Alimentação", "R$ 10,00")]


def test_historico_ciclos_fechados_do_mais_recente_ao_mais_antigo():
    velho = CicloFechado(Ciclo(data(1, 8), data(31, 8)), Resumo(300_000, 100_000, 30_000, 50_000), 0, 1)
    novo = CicloFechado(Ciclo(data(1, 9), data(30, 9)), Resumo(300_000, 100_000, 30_000, 190_000), 20_000, 2)
    assert linhas_de_fechados([velho, novo]) == [
        ("01/09/2026 a 30/09/2026", "R$ 3.000,00", "R$ 1.900,00", "R$ 0,00", "R$ 200,00"),
        ("01/08/2026 a 31/08/2026", "R$ 3.000,00", "R$ 500,00", "R$ 1.200,00", "R$ 0,00")]


def test_historico_tela_mostra_gastos_e_fechados(raiz):  # noqa: F811
    ctx, amb, _ = contexto_de_teste(replace(orcamento, gastos=GASTOS))
    amb.historico.fechados.append(CicloFechado(Ciclo(data(1, 9), data(30, 9)), Resumo(1, 0, 0, 0), None, 1))
    tela = TelaHistorico(raiz, ctx)
    pais = tela.gastos.get_children()
    assert len(pais) == 2
    assert len(tela.gastos.get_children(pais[0])) == 2
    assert len(tela.fechados.get_children()) == 1


def test_historico_exporta_csv(raiz, tmp_path):  # noqa: F811
    ctx, _, dialogos = contexto_de_teste(replace(orcamento, gastos=GASTOS), pasta_exportacao=tmp_path)
    TelaHistorico(raiz, ctx).exportar()
    arquivos = list(tmp_path.glob("*.csv"))
    assert len(arquivos) == 1
    assert dialogos.infos[-1][0] == "Exportado" and str(arquivos[0]) in dialogos.infos[-1][1]


def test_historico_exportacao_indisponivel_sem_pasta(raiz):  # noqa: F811
    ctx, _, dialogos = contexto_de_teste(replace(orcamento, gastos=GASTOS))
    TelaHistorico(raiz, ctx).exportar()
    assert dialogos.avisos == [("Exportação", "Exportação indisponível.")]
