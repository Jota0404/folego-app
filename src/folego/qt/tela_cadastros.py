"""Aba Cadastros: entradas, contas fixas e metas de reserva, cada uma numa sub-aba com tabela e botões.
Toda gravação passa por contexto.cadastros e o resultado das regras vai para contexto.mostrar_decisao.
Os formulários abrem sem bloquear (dialog.open()) e ficam em self.dialogo."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget,
)

from ..apresentacao.cadastros import linha_conta, linha_entrada, linha_meta
from .formularios import FormularioConta, FormularioEntrada, FormularioMeta

ESQUERDA = Qt.AlignLeft | Qt.AlignVCenter
DIREITA = Qt.AlignRight | Qt.AlignVCenter
CENTRO = Qt.AlignHCenter | Qt.AlignVCenter


class _Lista(QWidget):
    """Tabela com botões. As subclasses dizem colunas, itens, linhas, formulário e ações extras."""
    colunas = ()  # (título, largura, alinhamento); a primeira coluna estica e a largura dela é ignorada
    nome_do_item = "um item"
    formulario = None

    def __init__(self, contexto):
        super().__init__()
        self.contexto = contexto
        self.dialogo = None
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(12)
        self.tabela = QTableWidget(0, len(self.colunas))
        self.tabela.setHorizontalHeaderLabels([c[0] for c in self.colunas])
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setShowGrid(False)
        # respiro entre as colunas (o texto não cola na borda nem no vizinho)
        self.tabela.setStyleSheet("QTableWidget::item { padding: 0 8px; } QHeaderView::section { padding: 4px 8px; }")
        self.tabela.verticalHeader().hide()
        self.tabela.verticalHeader().setDefaultSectionSize(34)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setMinimumSectionSize(60)
        cabecalho.setHighlightSections(False)
        for n, (titulo, largura, alinhamento) in enumerate(self.colunas):
            self.tabela.horizontalHeaderItem(n).setTextAlignment(alinhamento)
            if n == 0:
                cabecalho.setSectionResizeMode(n, QHeaderView.Stretch)
            else:
                cabecalho.setSectionResizeMode(n, QHeaderView.Fixed)
                self.tabela.setColumnWidth(n, largura)
        self.tabela.cellDoubleClicked.connect(lambda *_: self.editar())
        raiz.addWidget(self.tabela, 1)
        botoes = QHBoxLayout()
        botoes.setSpacing(12)
        self.botao_adicionar = self._botao(botoes, "Adicionar", self.adicionar)
        self.botao_editar = self._botao(botoes, "Editar", self.editar)
        self.botoes_extras(botoes)
        botoes.addStretch(1)
        self.botao_excluir = self._botao(botoes, "Excluir", self.excluir)
        raiz.addLayout(botoes)

    def _botao(self, linha, texto: str, acao) -> QPushButton:
        botao = QPushButton(texto)
        botao.setMinimumWidth(110)
        botao.clicked.connect(lambda _marcado=False: acao())
        linha.addWidget(botao)
        return botao

    def botoes_extras(self, linha) -> None:
        pass

    def itens(self) -> list:
        raise NotImplementedError

    def textos(self, item) -> tuple:
        raise NotImplementedError

    def excluir(self) -> None:
        raise NotImplementedError

    @staticmethod
    def _chave(posicao: int, item) -> str:
        return str(item.id) if item.id else f"n{posicao}"  # id 0 = ainda sem id (não vem do banco)

    def atualizar(self) -> None:
        """Relê o repositório e redesenha, mantendo o item selecionado."""
        escolhida = self._chave_selecionada()
        self.tabela.setRowCount(0)
        for n, item in enumerate(self.itens()):
            self.tabela.insertRow(n)
            for coluna, texto in enumerate(self.textos(item)):
                celula = QTableWidgetItem(texto)
                celula.setTextAlignment(self.colunas[coluna][2])
                if coluna == 0:
                    celula.setData(Qt.UserRole, self._chave(n, item))
                self.tabela.setItem(n, coluna, celula)
            if self._chave(n, item) == escolhida:
                self.tabela.selectRow(n)

    def _chave_selecionada(self):
        linhas = self.tabela.selectionModel().selectedRows()
        return self.tabela.item(linhas[0].row(), 0).data(Qt.UserRole) if linhas else None

    def selecionado(self):
        """O item escolhido na tabela, ou None (depois de avisar)."""
        escolhida = self._chave_selecionada()
        for n, item in enumerate(self.itens()):
            if escolhida is not None and self._chave(n, item) == escolhida:
                return item
        self.contexto.aviso("Nada selecionado", f"Escolha {self.nome_do_item} na lista primeiro.")
        return None

    def _abrir(self, item=None) -> None:
        """Mostra o formulário sem esperar ele fechar."""
        if self.dialogo is not None:
            self.dialogo.deleteLater()
        self.dialogo = self.formulario(self.contexto, item, self.window())
        self.dialogo.finished.connect(lambda _resultado: setattr(self, "dialogo", None))
        self.dialogo.open()

    def adicionar(self) -> None:
        self._abrir()

    def editar(self) -> None:
        item = self.selecionado()
        if item:
            self._abrir(item)

    def excluir_selecionado(self, pergunta: str, excluir) -> None:
        """excluir(item) aplica a exclusão e mostra o resultado."""
        item = self.selecionado()
        if item and self.contexto.confirmar("Excluir", pergunta.format(item)):
            excluir(item)


class ListaEntradas(_Lista):
    nome_do_item = "uma entrada"
    formulario = FormularioEntrada
    colunas = (("Descrição", 0, ESQUERDA), ("Valor", 130, DIREITA), ("Tipo", 110, ESQUERDA),
               ("Início", 110, CENTRO), ("Fim", 110, CENTRO))

    def itens(self):
        return self.contexto.repo.orcamento().entradas

    def textos(self, entrada):
        return linha_entrada(entrada)

    def excluir(self):
        ctx = self.contexto
        self.excluir_selecionado("Excluir a entrada '{.descricao}'?",
                                 lambda e: ctx.mostrar_decisao(ctx.cadastros.excluir_entrada(e, ctx.hoje),
                                                               "Entrada excluída."))


class ListaContas(_Lista):
    nome_do_item = "uma conta"
    formulario = FormularioConta
    colunas = (("Descrição", 0, ESQUERDA), ("Valor", 130, DIREITA), ("Vencimento", 110, CENTRO),
               ("Situação", 240, ESQUERDA))

    def botoes_extras(self, linha):
        self.botao_encerrar = self._botao(linha, "Encerrar", self.encerrar)

    def itens(self):
        return self.contexto.repo.orcamento().contas

    def textos(self, conta):
        return linha_conta(conta, self.contexto.ciclo())

    def excluir(self):
        ctx = self.contexto
        self.excluir_selecionado("Excluir a conta '{.descricao}'?",
                                 lambda c: ctx.mostrar_decisao(ctx.cadastros.excluir_conta(c, ctx.hoje),
                                                               "Conta excluída."))

    def encerrar(self):
        ctx, conta = self.contexto, self.selecionado()
        if conta is None:
            return
        if conta.encerrada_em:
            ctx.aviso("Já encerrada", "Essa conta já foi encerrada.")
        elif ctx.confirmar("Encerrar", f"Encerrar a conta '{conta.descricao}'? Ela vale até o fim do ciclo atual."):
            ctx.cadastros.encerrar(conta, ctx.hoje)
            ctx.status("Conta encerrada: ela vale até o fim do ciclo atual.")
            ctx.mudou.emit()


class ListaMetas(_Lista):
    nome_do_item = "uma meta"
    formulario = FormularioMeta
    colunas = (("Nome", 0, ESQUERDA), ("Valor ou %", 140, DIREITA), ("Situação", 120, ESQUERDA))

    def botoes_extras(self, linha):
        self.botao_pausar = self._botao(linha, "Pausar/reativar", self.pausar)

    def itens(self):
        return self.contexto.repo.orcamento().metas

    def textos(self, meta):
        return linha_meta(meta)

    def pausar(self):
        ctx, meta = self.contexto, self.selecionado()
        if meta:
            texto = "Meta pausada." if meta.ativa else "Meta reativada."
            ctx.mostrar_decisao(ctx.cadastros.salvar_meta(replace(meta, ativa=not meta.ativa), ctx.hoje), texto)

    def excluir(self):
        def apagar(meta):
            self.contexto.cadastros.excluir_meta(meta)
            self.contexto.status("Meta excluída.")
            self.contexto.mudou.emit()
        self.excluir_selecionado("Excluir a meta '{.nome}'?", apagar)


class TelaCadastros(QWidget):
    def __init__(self, contexto):
        super().__init__()
        self.contexto = contexto
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 24, 24, 24)
        self.abas = QTabWidget()
        raiz.addWidget(self.abas)
        self.entradas = ListaEntradas(contexto)
        self.contas = ListaContas(contexto)
        self.metas = ListaMetas(contexto)
        for lista, titulo in ((self.entradas, "Entradas"), (self.contas, "Contas fixas"),
                              (self.metas, "Metas de reserva")):
            self.abas.addTab(lista, titulo)

    def atualizar(self) -> None:
        for lista in (self.entradas, self.contas, self.metas):
            lista.atualizar()
