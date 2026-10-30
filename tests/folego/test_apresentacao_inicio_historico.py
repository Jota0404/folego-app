from dataclasses import replace

from src.folego.calculadora import Faixa
from src.folego.apresentacao.historico import linhas_de_fechados, linhas_de_gastos
from src.folego.apresentacao.inicio import CORES, avisos_do_inicio, textos_do_inicio
from src.folego.modelos import Ciclo, CicloFechado, Configuracoes, Gasto, Resumo
from .cenario import data, orcamento
from .fakes import Ambiente, RepoUnico


def _painel(gastos=(), orc=None, config=None):
    config = config or Configuracoes(primeiro_uso_concluido=True)
    repo = RepoUnico(Ambiente(orc or replace(orcamento, gastos=list(gastos)), config))
    from src.folego.calculadora import ciclo_atual
    ciclo = ciclo_atual(config, data(5, 10))
    return repo.orcamento().painel(ciclo, data(5, 10), config), ciclo


def test_ca05_textos_do_inicio():
    painel, ciclo = _painel()
    t = textos_do_inicio(painel, ciclo)
    assert t["titulo"] == "Ciclo: 01/10/2026 a 31/10/2026"
    assert t["disponivel_semana"] == "R$ 388,88"
    assert t["limite"] == "R$ 388,88"
    assert t["disponivel_ciclo"] == "R$ 1.500,00"
    assert t["reserva"] == "R$ 300,00"
    assert t["consumo"] == "0% do limite consumido"
    assert t["semana"].startswith("Semana de ")
    assert avisos_do_inicio(painel) == []


def test_ca05_faixa_da_cor():
    for valor, faixa, texto in [(0, Faixa.VERDE, "0%"), (29_166, Faixa.AMARELA, "75%"),
                                (36_944, Faixa.VERMELHA, "95%")]:
        painel, ciclo = _painel([Gasto(valor, data(5, 10), id=1)] if valor else [])
        assert textos_do_inicio(painel, ciclo)["consumo"].startswith(texto)
        assert painel.faixa == faixa and CORES[faixa].startswith("#")


def test_inicio_avisa_reserva_invadida():
    painel, _ = _painel([Gasto(160_000, data(2, 10), id=1)])
    assert avisos_do_inicio(painel) == ["Reserva invadida em R$ 100,00."]


def test_inicio_com_limite_zero_nao_quebra():
    painel, ciclo = _painel(orc=replace(orcamento, entradas=[]))
    assert painel.faixa == Faixa.VERMELHA
    assert textos_do_inicio(painel, ciclo)["consumo"] == "100% do limite consumido"


GASTOS = [Gasto(1_000, data(2, 10), "pão", 1, id=1), Gasto(2_500, data(4, 10), "ônibus", 2, id=2),
          Gasto(500, data(4, 10), "", id=3), Gasto(900, data(30, 9), "ciclo anterior", 1, id=4)]


def test_historico_ordem_subtotal_e_categoria():
    repo = RepoUnico(Ambiente(replace(orcamento, gastos=GASTOS), Configuracoes(primeiro_uso_concluido=True)))
    ciclo = Ciclo(data(1, 10), data(31, 10))
    dias = linhas_de_gastos(repo.orcamento().gastos, repo.categorias(), ciclo)
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
