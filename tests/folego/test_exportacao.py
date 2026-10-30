from dataclasses import replace

from src.folego.calculadora import ciclo_de
from src.folego.exportacao import exportar_ciclo
from src.folego.modelos import CATEGORIAS_PADRAO, ContaFixa, Gasto
from .cenario import data, orcamento

CICLO = ciclo_de(data(15, 10), 1)


def _ler(caminho):
    texto = caminho.read_text(encoding="utf-8-sig")
    return [linha.split(";") for linha in texto.splitlines()]


def _com(*gastos, contas=None):
    return replace(orcamento, gastos=list(gastos), contas=contas or orcamento.contas)


def test_cenario_base_nome_linhas_e_resumo(tmp_path):
    contas = [ContaFixa(100_000, data(1, 10), descricao="Aluguel"),
              ContaFixa(20_000, data(1, 10), duracao_meses=3, descricao="Celular")]
    caminho = exportar_ciclo(_com(contas=contas), CICLO, CATEGORIAS_PADRAO, tmp_path / "novo")
    assert caminho.name == "folego-2026-10-01_a_2026-10-31.csv"
    linhas = _ler(caminho)
    assert linhas[0] == ["Tipo", "Data", "Descrição", "Categoria", "Valor"]
    assert ["Entrada", "01/10/2026", "", "", "3000,00"] in linhas
    assert ["Conta fixa", "", "Aluguel", "", "1000,00"] in linhas
    assert ["Conta fixa", "", "Celular (parcela 1 de 3)", "", "200,00"] in linhas
    assert linhas[-5:] == [
        ["Resumo", "", "Entradas", "", "3000,00"], ["Resumo", "", "Contas fixas", "", "1200,00"],
        ["Resumo", "", "Reserva", "", "300,00"], ["Resumo", "", "Gastos", "", "0,00"],
        ["Resumo", "", "Disponível", "", "1500,00"],
    ]
    assert linhas[-6] == [""]


def test_gasto_aparece_com_categoria_e_de_outro_ciclo_nao(tmp_path):
    o = _com(Gasto(2_550, data(5, 10), "Pizza", 1), Gasto(9_900, data(5, 11), "Outro mês", 1))
    texto = exportar_ciclo(o, CICLO, CATEGORIAS_PADRAO, tmp_path).read_text(encoding="utf-8-sig")
    assert "Gasto;05/10/2026;Pizza;Alimentação;25,50" in texto
    assert "Outro mês" not in texto


def test_descricao_com_formula_e_protegida(tmp_path):
    o = _com(Gasto(100, data(5, 10), "=SOMA(A1)", 1))
    texto = exportar_ciclo(o, CICLO, CATEGORIAS_PADRAO, tmp_path).read_text(encoding="utf-8-sig")
    assert "'=SOMA(A1)" in texto


def test_exportar_de_novo_recomeca_limpo(tmp_path):
    exportar_ciclo(_com(Gasto(100, data(5, 10), "Velho", 1)), CICLO, CATEGORIAS_PADRAO, tmp_path)
    caminho = exportar_ciclo(orcamento, CICLO, CATEGORIAS_PADRAO, tmp_path)
    assert "Velho" not in caminho.read_text(encoding="utf-8-sig")


def test_bom_e_separador_ponto_e_virgula(tmp_path):
    caminho = exportar_ciclo(orcamento, CICLO, CATEGORIAS_PADRAO, tmp_path)
    assert caminho.read_bytes().startswith(b"\xef\xbb\xbf")
    assert caminho.read_text(encoding="utf-8-sig").startswith("Tipo;Data;Descrição;Categoria;Valor")
