"""Aba "Novo gasto" (PySide6): registrar, corrigir e excluir gastos do ciclo atual."""
from __future__ import annotations

from dataclasses import replace
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..apresentacao.gasto import ler_formulario
from ..formatos import formatar_data, formatar_reais
from ..modelos import Gasto, OUTROS


class TelaGasto(QWidget):
    def __init__(self, contexto):
        super().__init__()
        self.contexto = contexto
        self._editando: Optional[Gasto] = None
        self._gastos: List[Gasto] = []  # uma por linha da tabela

        self.formulario = QGroupBox("Novo gasto")
        self.valor = QLineEdit()
        self.data = QLineEdit()
        self.descricao = QLineEdit()
        self.categoria = QComboBox()
        self.valor.setMaximumWidth(200)
        self.data.setMaximumWidth(200)
        self.categoria.setMaximumWidth(260)
        self.valor.setPlaceholderText("1.500,00")
        self.data.setPlaceholderText("dd/mm/aaaa")
        form = QFormLayout(self.formulario)
        form.setSpacing(12)
        form.setContentsMargins(24, 24, 24, 24)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.addRow("Valor", self.valor)
        form.addRow("Data", self.data)
        form.addRow("Descrição (opcional)", self.descricao)
        form.addRow("Categoria", self.categoria)
        for campo in (self.valor, self.data, self.descricao):
            campo.returnPressed.connect(self.salvar)
        self.botao_salvar = QPushButton("Salvar")
        self.botao_salvar.setDefault(True)
        self.botao_limpar = QPushButton("Limpar")
        self.botao_cancelar = QPushButton("Cancelar")
        self.botao_salvar.clicked.connect(self.salvar)
        self.botao_limpar.clicked.connect(self.limpar)
        self.botao_cancelar.clicked.connect(self.limpar)
        botoes = QHBoxLayout()
        botoes.setSpacing(12)
        for b in (self.botao_salvar, self.botao_limpar, self.botao_cancelar):
            botoes.addWidget(b)
        botoes.addStretch()
        form.addRow("", botoes)

        self.lista = QGroupBox("Gastos do ciclo atual")
        self.tabela = QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(["Data", "Descrição", "Categoria", "Valor"])
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.verticalHeader().setVisible(False)
        cab = self.tabela.horizontalHeader()
        cab.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for coluna in (0, 2, 3):
            cab.setSectionResizeMode(coluna, QHeaderView.ResizeMode.ResizeToContents)
        self.botao_corrigir = QPushButton("Corrigir")
        self.botao_excluir = QPushButton("Excluir")
        self.botao_corrigir.clicked.connect(self.corrigir)
        self.botao_excluir.clicked.connect(self.excluir)
        acoes = QHBoxLayout()
        acoes.setSpacing(12)
        acoes.addStretch()
        acoes.addWidget(self.botao_corrigir)
        acoes.addWidget(self.botao_excluir)
        col_lista = QVBoxLayout(self.lista)
        col_lista.setContentsMargins(24, 24, 24, 24)
        col_lista.setSpacing(12)
        col_lista.addWidget(self.tabela)
        col_lista.addLayout(acoes)

        # Coluna central de largura máxima, com espaço elástico dos dois lados.
        coluna = QWidget()
        coluna.setMaximumWidth(760)
        v = QVBoxLayout(coluna)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        v.addWidget(self.formulario)
        v.addWidget(self.lista, 1)
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(24, 24, 24, 24)
        raiz.addStretch(1)
        raiz.addWidget(coluna, 100)
        raiz.addStretch(1)

        self.atualizar()
        self.limpar()

    # --- formulário ----------------------------------------------------------------

    def limpar(self) -> None:
        self._editando = None
        self.formulario.setTitle("Novo gasto")
        self.botao_cancelar.setVisible(False)
        self.valor.clear()
        self.data.setText(formatar_data(self.contexto.hoje))
        self.descricao.clear()
        self.categoria.setCurrentText(self._nome_da(OUTROS))
        self.valor.setFocus()

    def _nome_da(self, categoria_id: int) -> str:
        return next((c.nome for c in self.contexto.repo.categorias() if c.id == categoria_id), "")

    def salvar(self) -> None:
        c = self.contexto
        gasto = ler_formulario(self.valor.text(), self.data.text(), self.descricao.text(),
                               self.categoria.currentText(), c.hoje, c.repo.categorias())
        if isinstance(gasto, str):
            c.aviso("Dado inválido", gasto)
            return
        if self._editando is not None:
            gasto = replace(gasto, id=self._editando.id)
        texto = "Gasto corrigido." if self._editando is not None else "Gasto salvo."
        if c.mostrar_decisao(c.cadastros.salvar_gasto(gasto, c.hoje, c.agora), texto):
            self.limpar()

    # --- lista ---------------------------------------------------------------------

    def _selecionado(self, acao: str) -> Optional[Gasto]:
        linha = self.tabela.currentRow()
        if not self.tabela.selectionModel().hasSelection() or not 0 <= linha < len(self._gastos):
            self.contexto.aviso("Nenhum gasto selecionado", f"Selecione um gasto na lista para {acao}.")
            return None
        return self._gastos[linha]

    def corrigir(self) -> None:
        gasto = self._selecionado("corrigir")
        if gasto is None:
            return
        self._editando = gasto
        self.formulario.setTitle("Corrigir gasto")
        self.botao_cancelar.setVisible(True)
        self.valor.setText(formatar_reais(gasto.valor_centavos).replace("R$ ", ""))
        self.data.setText(formatar_data(gasto.data))
        self.descricao.setText(gasto.descricao)
        self.categoria.setCurrentText(self._nome_da(gasto.categoria_id))
        self.valor.setFocus()

    def excluir(self) -> None:
        gasto = self._selecionado("excluir")
        if gasto is None:
            return
        c = self.contexto
        if c.confirmar("Excluir gasto", f"Excluir o gasto de {formatar_reais(gasto.valor_centavos)} "
                                        f"em {formatar_data(gasto.data)}?"):
            c.mostrar_decisao(c.cadastros.excluir_gasto(gasto, c.hoje), "Gasto excluído.")

    def atualizar(self) -> None:
        """Relê o repositório; o que já foi digitado e a seleção ficam como estão."""
        c = self.contexto
        categorias = c.repo.categorias()
        nomes = {cat.id: cat.nome for cat in categorias}
        atual = self.categoria.currentText()
        self.categoria.blockSignals(True)
        self.categoria.clear()
        self.categoria.addItems([cat.nome for cat in categorias])
        self.categoria.setCurrentText(atual or nomes.get(OUTROS, ""))
        self.categoria.blockSignals(False)
        ciclo = c.ciclo()
        gastos = sorted((g for g in c.repo.orcamento().gastos if g.data in ciclo),
                        key=lambda g: (g.data, g.id), reverse=True)
        antes = self._gastos[self.tabela.currentRow()].id if (
            self.tabela.selectionModel().hasSelection() and 0 <= self.tabela.currentRow() < len(self._gastos)) else None
        self._gastos = gastos
        self.tabela.clearSelection()
        self.tabela.setRowCount(len(gastos))
        for i, g in enumerate(gastos):
            textos = (formatar_data(g.data), g.descricao, nomes.get(g.categoria_id, ""),
                      formatar_reais(g.valor_centavos))
            for j, texto in enumerate(textos):
                item = QTableWidgetItem(texto)
                if j == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tabela.setItem(i, j, item)
            if g.id == antes:
                self.tabela.selectRow(i)
        if self._editando is not None and all(g.id != self._editando.id for g in gastos):
            self.limpar()  # o gasto em correção sumiu (excluído ou fora do ciclo)
