"""Formulários de entrada, conta fixa e meta (QDialog). A leitura dos campos fica em
src/folego/apresentacao/cadastros.py; toda regra de negócio vem do núcleo.
O botão Salvar chama salvar(), que só fecha o diálogo se salvou; erros viram contexto.aviso."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QSizePolicy, QVBoxLayout,
)

from ..apresentacao.cadastros import ROTULO_ENTRADA, ROTULO_META, ler_conta, ler_entrada, ler_meta
from ..formatos import formatar_data, formatar_percentual, formatar_reais
from ..modelos import TipoEntrada, TipoMeta


class _Formulario(QDialog):
    """Diálogo com campos em QFormLayout. As subclasses montam os campos, leem e gravam."""
    titulo = ""
    salvo = ""

    def __init__(self, contexto, item=None, parent=None):
        super().__init__(parent)
        self.contexto, self.item = contexto, item
        self.setWindowTitle(self.titulo + (" (editar)" if item else " (novo)"))
        self.setModal(True)
        self.setMinimumWidth(480)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 24, 24, 24)
        raiz.setSpacing(18)
        self.form = QFormLayout()
        self.form.setHorizontalSpacing(16)
        self.form.setVerticalSpacing(12)
        self.form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        raiz.addLayout(self.form)
        self.campos()
        botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botoes.button(QDialogButtonBox.Save).setText("Salvar")
        botoes.button(QDialogButtonBox.Save).setDefault(True)
        botoes.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botoes.accepted.connect(self.salvar)
        botoes.rejected.connect(self.reject)
        raiz.addWidget(botoes)

    def _texto(self, rotulo: str, valor: str = "", dica: str = "") -> QLineEdit:
        campo = QLineEdit(valor)
        campo.setPlaceholderText(dica)
        self.form.addRow(rotulo, campo)
        return campo

    def _escolha(self, rotulo: str, rotulos: dict, atual, travado: bool) -> QComboBox:
        combo = QComboBox()
        for tipo, texto in rotulos.items():
            combo.addItem(texto, tipo)
        combo.setCurrentIndex(combo.findData(atual))
        combo.setEnabled(not travado)
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # mesma largura dos campos de texto
        self.form.addRow(rotulo, combo)
        return combo

    def campos(self) -> None:
        raise NotImplementedError

    def ler(self):
        """O item pronto, ou o texto do erro."""
        raise NotImplementedError

    def gravar(self, item):
        """Chama o serviço e devolve a decisão do núcleo."""
        raise NotImplementedError

    def salvar(self) -> bool:
        item = self.ler()
        if isinstance(item, str):
            self.contexto.aviso("Confira os dados", item)
            return False
        if not self.contexto.mostrar_decisao(self.gravar(item), self.salvo):
            return False
        self.accept()
        return True


class FormularioEntrada(_Formulario):
    titulo = "Entrada"
    salvo = "Entrada salva."

    def campos(self) -> None:
        e = self.item
        self.descricao = self._texto("Descrição", e.descricao if e else "")
        self.valor = self._texto("Valor", formatar_reais(e.valor_centavos) if e else "", "Exemplo: 3.000,00")
        self.tipo = self._escolha("Tipo", ROTULO_ENTRADA, e.tipo if e else TipoEntrada.RECORRENTE, travado=bool(e))
        self.inicio = self._texto("Início", formatar_data(e.data_inicio if e else self.contexto.ciclo().inicio),
                                  "dd/mm/aaaa")
        self.fim = self._texto("Fim", formatar_data(e.data_fim) if e and e.data_fim else "", "Vazio = sem fim")
        self.tipo.currentIndexChanged.connect(self._tipo_mudou)
        self._tipo_mudou()
        self.descricao.setFocus()

    def _tipo_mudou(self, _indice=None) -> None:
        recorrente = self.tipo.currentData() == TipoEntrada.RECORRENTE
        if self.item is None:  # só troca o padrão do início se o usuário não mexeu nele
            padrao_recorrente = formatar_data(self.contexto.ciclo().inicio)
            padrao_avulsa = formatar_data(self.contexto.hoje)
            antigo, novo = (padrao_avulsa, padrao_recorrente) if recorrente else (padrao_recorrente, padrao_avulsa)
            if self.inicio.text() == antigo:
                self.inicio.setText(novo)
        self.fim.setEnabled(recorrente)

    def ler(self):
        return ler_entrada(self.descricao.text(), self.valor.text(), self.tipo.currentData(), self.inicio.text(),
                           self.fim.text(), self.contexto.hoje, self.contexto.ciclo(), self.item)

    def gravar(self, item):
        return self.contexto.cadastros.salvar_entrada(item, self.contexto.hoje)


class FormularioConta(_Formulario):
    titulo = "Conta fixa"
    salvo = "Conta salva."

    def campos(self) -> None:
        c = self.item
        self.descricao = self._texto("Descrição", c.descricao if c else "")
        self.valor = self._texto("Valor", formatar_reais(c.valor_centavos) if c else "", "Exemplo: 1.000,00")
        self.vencimento = self._texto("Dia do vencimento", str(c.dia_vencimento) if c else "", "1 a 31")
        self.duracao = self._texto("Duração em meses", str(c.duracao_meses) if c and c.duracao_meses else "",
                                   "Vazio = sem fim")
        self.parcela = None
        if c is None:  # a parcela atual só existe ao adicionar uma conta com duração
            self.parcela = self._texto("Parcela atual", "", "Vazio = 1")
            self.duracao.textChanged.connect(self._duracao_mudou)
            self._duracao_mudou()
        self.descricao.setFocus()

    def _duracao_mudou(self, _texto=None) -> None:
        self.parcela.setEnabled(self.duracao.text().strip().lower() not in ("", "sem"))

    def ler(self):
        parcela = self.parcela.text() if self.parcela else ""
        return ler_conta(self.descricao.text(), self.valor.text(), self.vencimento.text(), self.duracao.text(),
                         parcela, self.contexto.ciclo(), self.item)

    def gravar(self, item):
        return self.contexto.cadastros.salvar_conta(item, self.contexto.hoje)


class FormularioMeta(_Formulario):
    titulo = "Meta de reserva"
    salvo = "Meta salva."

    def campos(self) -> None:
        m = self.item
        self.nome = self._texto("Nome", m.nome if m else "")
        self.tipo = self._escolha("Tipo", ROTULO_META, m.tipo if m else TipoMeta.VALOR, travado=bool(m))
        texto = ""
        if m:
            texto = formatar_reais(m.valor) if m.tipo == TipoMeta.VALOR else formatar_percentual(m.valor)
        self.valor = self._texto("Valor ou %", texto, "Exemplo: 500,00 ou 10")
        self.nome.setFocus()

    def ler(self):
        return ler_meta(self.nome.text(), self.tipo.currentData(), self.valor.text(), self.item)

    def gravar(self, item):
        return self.contexto.cadastros.salvar_meta(item, self.contexto.hoje)
