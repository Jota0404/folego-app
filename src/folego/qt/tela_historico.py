"""Aba Histórico (PySide6): gastos do ciclo atual (agrupados por dia), ciclos fechados e exportação."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from ..apresentacao.historico import linhas_de_fechados, linhas_de_gastos
from ..exportacao import exportar_ciclo

LARGURA_MAXIMA = 760


def _tabela(colunas, numericas) -> QTreeWidget:
    """Tabela só de leitura; as colunas numéricas ficam alinhadas à direita; a 1ª ou 2ª estica."""
    t = QTreeWidget()
    t.setColumnCount(len(colunas))
    t.setHeaderLabels(colunas)
    t.setRootIsDecorated(False)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setAlternatingRowColors(True)
    t.setStyleSheet("QTreeView::item { padding: 3px 8px; } QHeaderView::section { padding: 3px 8px; }")
    cab = t.header()
    cab.setStretchLastSection(False)
    esticar = 1 if colunas[1] == "Descrição" else 0
    for i in range(len(colunas)):
        cab.setSectionResizeMode(i, QHeaderView.Stretch if i == esticar else QHeaderView.ResizeToContents)
        if i in numericas:
            t.headerItem().setTextAlignment(i, Qt.AlignRight | Qt.AlignVCenter)
    return t


def _item(valores, numericas, negrito=False) -> QTreeWidgetItem:
    item = QTreeWidgetItem(list(valores))
    for i in range(len(valores)):
        if i in numericas:
            item.setTextAlignment(i, Qt.AlignRight | Qt.AlignVCenter)
        if negrito:
            fonte = item.font(i)
            fonte.setBold(True)
            item.setFont(i, fonte)
    return item


class TelaHistorico(QWidget):
    def __init__(self, contexto):
        super().__init__()
        self.contexto = contexto
        coluna = QWidget()
        coluna.setMaximumWidth(LARGURA_MAXIMA)
        lay = QVBoxLayout(coluna)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        topo = QHBoxLayout()
        titulo = QLabel("Gastos do ciclo atual")
        titulo.setStyleSheet("font-weight: bold;")
        topo.addWidget(titulo)
        topo.addStretch()
        self.botao_exportar = QPushButton("Exportar ciclo (CSV)")
        self.botao_exportar.clicked.connect(self.exportar)
        topo.addWidget(self.botao_exportar)
        lay.addLayout(topo)

        self.gastos = _tabela(("Data", "Descrição", "Categoria", "Valor"), {3})
        lay.addWidget(self.gastos, 3)
        titulo2 = QLabel("Ciclos fechados")
        titulo2.setStyleSheet("font-weight: bold;")
        lay.addWidget(titulo2)
        self.fechados = _tabela(("Período", "Entradas", "Gastos", "Sobrou", "Reserva invadida"), {1, 2, 3, 4})
        lay.addWidget(self.fechados, 2)

        externo = QHBoxLayout(self)
        externo.setContentsMargins(24, 24, 24, 24)
        externo.addStretch()
        externo.addWidget(coluna, 1)
        externo.addStretch()
        self.atualizar()

    def atualizar(self) -> None:
        ctx = self.contexto
        self.gastos.clear()
        self.fechados.clear()
        for pai, filhos in linhas_de_gastos(ctx.repo.orcamento().gastos, ctx.repo.categorias(), ctx.ciclo()):
            item = _item(pai, {3}, negrito=True)
            self.gastos.addTopLevelItem(item)
            for filho in filhos:
                item.addChild(_item(filho, {3}))
            item.setExpanded(True)
        self.gastos.setRootIsDecorated(True)
        for linha in linhas_de_fechados(ctx.repo.ciclos_fechados()):
            self.fechados.addTopLevelItem(_item(linha, {1, 2, 3, 4}))

    def exportar(self) -> None:
        ctx = self.contexto
        if ctx.pasta_exportacao is None:
            ctx.aviso("Exportação", "Exportação indisponível.")
            return
        caminho = exportar_ciclo(ctx.repo.orcamento(), ctx.ciclo(), ctx.repo.categorias(), ctx.pasta_exportacao)
        ctx.info("Exportado", f"Ciclo exportado em:\n{caminho}")
