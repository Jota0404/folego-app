"""Aba Configurações: dia do pagamento, limite semanal manual e percentuais de alerta."""
from __future__ import annotations

from typing import Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
                               QWidget)

from ..apresentacao.configuracoes import ler_formulario, textos_do_formulario
from .contexto import Contexto

_CAMPOS = [
    ("Dia do pagamento", "Dia do mês em que você recebe (1 a 31)."),
    ("Limite semanal manual (R$)", "Deixe vazio para o Fôlego calcular sozinho."),
    ("Percentual de atenção (%)", "Do limite gasto, a partir de quanto avisar."),
    ("Percentual crítico (%)", "Do limite gasto, a partir de quanto o alerta é forte."),
]


class TelaConfiguracoes(QWidget):
    def __init__(self, contexto: Contexto):
        super().__init__()
        self.contexto = contexto
        self._carregado: Tuple[str, ...] = ("", "", "", "")

        coluna = QWidget()
        coluna.setMaximumWidth(560)
        form = QFormLayout(coluna)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.campos = []
        for rotulo, ajuda in _CAMPOS:
            campo = QLineEdit()
            campo.setMaximumWidth(200)
            self.campos.append(campo)
            dica = QLabel(ajuda)
            dica.setEnabled(False)  # cor "desabilitada" do tema: discreta em claro e escuro
            caixa = QVBoxLayout()
            caixa.setSpacing(2)
            caixa.addWidget(campo)
            caixa.addWidget(dica)
            form.addRow(rotulo, caixa)
        self.botao_salvar = QPushButton("Salvar")
        self.botao_salvar.clicked.connect(self.salvar)
        self.botao_desfazer = QPushButton("Desfazer")
        self.botao_desfazer.clicked.connect(self.desfazer)
        botoes = QHBoxLayout()
        botoes.addStretch()
        botoes.addWidget(self.botao_desfazer)
        botoes.addWidget(self.botao_salvar)
        form.addRow(botoes)

        centro = QHBoxLayout(self)
        centro.addStretch()
        centro.addWidget(coluna, 1)
        centro.addStretch()
        self.desfazer()

    def _atuais(self) -> Tuple[str, ...]:
        return tuple(c.text() for c in self.campos)

    def desfazer(self) -> None:
        """Volta os campos aos valores gravados."""
        self._carregado = textos_do_formulario(self.contexto.repo.configuracoes())
        for campo, texto in zip(self.campos, self._carregado):
            campo.setText(texto)

    def atualizar(self) -> None:
        if self._atuais() == self._carregado:  # não apaga o que a pessoa está digitando
            self.desfazer()

    def salvar(self) -> None:
        ctx = self.contexto
        atual = ctx.repo.configuracoes()
        nova = ler_formulario(*self._atuais(), atual)
        if isinstance(nova, str):
            ctx.aviso("Dado inválido", nova)
            return
        if nova.dia_pagamento != atual.dia_pagamento and not ctx.confirmar(
                "Mudar o dia do pagamento",
                "Isso muda o ciclo atual e pode fechar o ciclo anterior. Continuar?"):
            return
        decisao = ctx.configurar.salvar(nova, ctx.hoje)
        if ctx.mostrar_decisao(decisao, "Configurações salvas."):
            self.desfazer()
