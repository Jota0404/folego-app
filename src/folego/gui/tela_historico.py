"""Aba Histórico: gastos do ciclo atual (agrupados por dia), ciclos fechados e exportação."""
from __future__ import annotations

from tkinter import font as tkfont, ttk
from typing import List, Tuple

from ..exportacao import exportar_ciclo
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


def _tabela(master, colunas, larguras, altura):
    quadro = ttk.Frame(master)
    arvore = ttk.Treeview(quadro, columns=colunas, show="headings", height=altura)
    for nome, largura in zip(colunas, larguras):
        valor = nome in ("Valor", "Entradas", "Gastos", "Sobrou", "Reserva invadida")
        arvore.heading(nome, text=nome)
        arvore.column(nome, width=largura, anchor="e" if valor else "w")
    rolagem = ttk.Scrollbar(quadro, orient="vertical", command=arvore.yview)
    arvore.configure(yscrollcommand=rolagem.set)
    arvore.pack(side="left", fill="both", expand=True)
    rolagem.pack(side="right", fill="y")
    return quadro, arvore


class TelaHistorico(ttk.Frame):
    def __init__(self, master, contexto):
        super().__init__(master, padding=16)
        self.contexto = contexto
        negrito = tkfont.Font(weight="bold")
        topo = ttk.Frame(self)
        topo.pack(fill="x")
        ttk.Label(topo, text="Gastos do ciclo atual", font=negrito).pack(side="left")
        ttk.Button(topo, text="Exportar ciclo (CSV)", command=self.exportar).pack(side="right")
        quadro, self.gastos = _tabela(self, ("Data", "Descrição", "Categoria", "Valor"), (90, 260, 140, 110), 9)
        quadro.pack(fill="both", expand=True, pady=(4, 12))
        ttk.Label(self, text="Ciclos fechados", font=negrito).pack(anchor="w")
        quadro, self.fechados = _tabela(
            self, ("Período", "Entradas", "Gastos", "Sobrou", "Reserva invadida"), (190, 110, 110, 110, 130), 6)
        quadro.pack(fill="both", expand=True, pady=(4, 0))
        self.atualizar()

    def atualizar(self) -> None:
        ctx = self.contexto
        self.gastos.delete(*self.gastos.get_children())
        self.fechados.delete(*self.fechados.get_children())
        for pai, filhos in linhas_de_gastos(ctx.repo.orcamento().gastos, ctx.repo.categorias(), ctx.ciclo()):
            item = self.gastos.insert("", "end", values=pai, open=True)
            for filho in filhos:
                self.gastos.insert(item, "end", values=filho)
        for linha in linhas_de_fechados(ctx.repo.ciclos_fechados()):
            self.fechados.insert("", "end", values=linha)

    def exportar(self) -> None:
        ctx = self.contexto
        if ctx.pasta_exportacao is None:
            ctx.aviso("Exportação", "Exportação indisponível.")
            return
        caminho = exportar_ciclo(ctx.repo.orcamento(), ctx.ciclo(), ctx.repo.categorias(), ctx.pasta_exportacao)
        ctx.info("Exportado", f"Ciclo exportado em:\n{caminho}")
