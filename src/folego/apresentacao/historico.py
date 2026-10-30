"""Linhas das tabelas da tela Histórico, prontas e sem GUI (para testar)."""
from typing import List, Tuple

from ..formatos import formatar_data, formatar_reais


def linhas_de_gastos(gastos, categorias, ciclo) -> List[Tuple[tuple, List[tuple]]]:
    """Um item por dia (mais recente primeiro): (linha do dia com subtotal, linhas dos gastos).
    Linha = (Data, Descrição, Categoria, Valor)."""
    nomes = {c.id: c.nome for c in categorias}
    do_ciclo = sorted((g for g in gastos if g.data in ciclo), key=lambda g: (g.data, g.id), reverse=True)
    dias = []
    for dia in sorted({g.data for g in do_ciclo}, reverse=True):
        do_dia = [g for g in do_ciclo if g.data == dia]
        pai = (formatar_data(dia), "Total do dia", "", formatar_reais(sum(g.valor_centavos for g in do_dia)))
        filhos = [("", g.descricao, nomes.get(g.categoria_id, ""), formatar_reais(g.valor_centavos)) for g in do_dia]
        dias.append((pai, filhos))
    return dias


def linhas_de_fechados(fechados) -> List[tuple]:
    """(Período, Entradas, Gastos, Sobrou, Reserva invadida), do mais recente ao mais antigo."""
    linhas = []
    for f in sorted(fechados, key=lambda f: f.ciclo.inicio, reverse=True):
        r = f.resumo
        linhas.append((f"{formatar_data(f.ciclo.inicio)} a {formatar_data(f.ciclo.fim)}",
                       formatar_reais(r.entradas), formatar_reais(r.gastos),
                       formatar_reais(max(0, r.disponivel)), formatar_reais(f.reserva_invadida or 0)))
    return linhas
