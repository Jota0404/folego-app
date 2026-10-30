"""Exporta um ciclo para CSV (Excel/Numbers em português). Dinheiro em centavos."""
import csv
from pathlib import Path
from typing import List

from .calculadora import Orcamento, ativa_em, entra_em, parcela_em
from .modelos import Categoria, Ciclo


def _reais(centavos: int) -> str:
    """Centavos em texto de reais com vírgula, sem R$ nem milhar (ex.: -1500,00)."""
    reais, cents = divmod(abs(centavos), 100)
    return "%s%d,%02d" % ("-" if centavos < 0 else "", reais, cents)


def _data(d) -> str:
    return d.strftime("%d/%m/%Y")


def _seguro(texto: str) -> str:
    """Evita que o Excel trate texto digitado como fórmula."""
    return "'" + texto if texto[:1] in ("=", "+", "-", "@") else texto


def exportar_ciclo(orcamento: Orcamento, ciclo: Ciclo, categorias: List[Categoria], pasta: Path) -> Path:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / ("folego-%s_a_%s.csv" % (ciclo.inicio.isoformat(), ciclo.fim.isoformat()))
    nomes = {c.id: c.nome for c in categorias}
    linhas = [["Tipo", "Data", "Descrição", "Categoria", "Valor"]]
    for e in orcamento.entradas:
        if entra_em(e, ciclo):
            linhas.append(["Entrada", _data(e.data_inicio), _seguro(e.descricao), "", _reais(e.valor_centavos)])
    for c in orcamento.contas:
        if ativa_em(c, ciclo):
            desc = _seguro(c.descricao)
            parcela = parcela_em(c, ciclo)
            if parcela is not None:
                desc += " (parcela %d de %d)" % (parcela, c.duracao_meses)
            linhas.append(["Conta fixa", "", desc, "", _reais(c.valor_centavos)])
    for g in sorted((g for g in orcamento.gastos if g.data in ciclo), key=lambda g: g.data):
        linhas.append(["Gasto", _data(g.data), _seguro(g.descricao), nomes.get(g.categoria_id, ""),
                       _reais(g.valor_centavos)])
    r = orcamento.resumo(ciclo)
    linhas.append([])
    for nome, valor in (("Entradas", r.entradas), ("Contas fixas", r.fixas), ("Reserva", r.reserva),
                        ("Gastos", r.gastos), ("Disponível", r.disponivel)):
        linhas.append(["Resumo", "", nome, "", _reais(valor)])
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f, delimiter=";").writerows(linhas)
    return caminho
