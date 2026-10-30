"""Aba Início (PySide6): disponível da semana, barra de consumo e avisos."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
                               QWidget)

from ..apresentacao.inicio import CORES, avisos_do_inicio, textos_do_inicio

LARGURA_MAXIMA = 760
COR_AVISO = "#e05252"  # legível em fundo claro e escuro


class TelaInicio(QWidget):
    def __init__(self, contexto):
        super().__init__()
        self.contexto = contexto
        coluna = QWidget()
        coluna.setMaximumWidth(LARGURA_MAXIMA)
        lay = QVBoxLayout(coluna)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        self.rotulos = {k: QLabel() for k in
                        ("titulo", "semana", "disponivel_semana", "limite", "disponivel_ciclo", "reserva", "consumo")}
        r = self.rotulos
        r["titulo"].setStyleSheet("font-size: 18px; font-weight: bold;")
        r["disponivel_semana"].setStyleSheet("font-size: 40px; font-weight: bold;")
        lay.addWidget(r["titulo"])
        lay.addWidget(QLabel("Disponível da semana"))
        lay.addWidget(r["disponivel_semana"])
        lay.addWidget(r["semana"])

        grade = QGridLayout()
        grade.setHorizontalSpacing(12)
        grade.setVerticalSpacing(8)
        grade.setColumnStretch(0, 1)
        for linha, (rotulo, chave) in enumerate([("Limite da semana", "limite"),
                                                 ("Disponível do ciclo", "disponivel_ciclo"),
                                                 ("Reserva do ciclo", "reserva")]):
            grade.addWidget(QLabel(rotulo), linha, 0)
            r[chave].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grade.addWidget(r[chave], linha, 1)
        lay.addLayout(grade)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(22)
        lay.addWidget(self.barra)
        lay.addWidget(r["consumo"])

        self.quadro_avisos = QVBoxLayout()
        self.quadro_avisos.setSpacing(6)
        lay.addLayout(self.quadro_avisos)

        self.botao_gasto = QPushButton("+ Novo gasto")
        self.botao_gasto.clicked.connect(lambda: contexto.ir_para("gasto"))
        lay.addWidget(self.botao_gasto, alignment=Qt.AlignLeft)
        lay.addStretch()

        externo = QHBoxLayout(self)
        externo.setContentsMargins(24, 24, 24, 24)
        externo.addStretch()
        externo.addWidget(coluna, 1)
        externo.addStretch()
        self.atualizar()

    def atualizar(self) -> None:
        ctx = self.contexto
        ciclo = ctx.ciclo()
        painel = ctx.repo.orcamento().painel(ciclo, ctx.hoje, ctx.repo.configuracoes())
        for chave, texto in textos_do_inicio(painel, ciclo).items():
            self.rotulos[chave].setText(texto)
        self.barra.setValue(min(100, painel.consumo_pontos_base // 100))
        self.barra.setStyleSheet(
            "QProgressBar { border: none; border-radius: 4px; background: rgba(128,128,128,70); }"
            "QProgressBar::chunk { border-radius: 4px; background: %s; }" % CORES[painel.faixa])
        while self.quadro_avisos.count():
            self.quadro_avisos.takeAt(0).widget().deleteLater()
        for aviso in avisos_do_inicio(painel):
            w = QLabel(aviso)
            w.setWordWrap(True)
            w.setStyleSheet("color: %s; font-weight: bold;" % COR_AVISO)
            self.quadro_avisos.addWidget(w)
