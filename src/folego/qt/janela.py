"""Janela principal do Fôlego (PySide6): uma aba por tela, cada uma em src/folego/qt/tela_*.py.
Cada tela é um QWidget com __init__(self, contexto) e atualizar(self); ela se redesenha quando
o contexto emite `mudou` e quando a aba é aberta."""
from __future__ import annotations

import importlib
from typing import Dict, Tuple

from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from ..formatos import ler_centavos
from ..modelos import Entrada, TipoEntrada
from .contexto import Contexto

# (chave, título da aba, módulo, classe)
TELAS = [
    ("inicio", "Início", "tela_inicio", "TelaInicio"),
    ("gasto", "Novo gasto", "tela_gasto", "TelaGasto"),
    ("historico", "Histórico", "tela_historico", "TelaHistorico"),
    ("cadastros", "Cadastros", "tela_cadastros", "TelaCadastros"),
    ("configuracoes", "Configurações", "tela_configuracoes", "TelaConfiguracoes"),
]


class _EmConstrucao(QWidget):
    """Aba provisória enquanto o arquivo da tela não existe."""

    def __init__(self, titulo: str):
        super().__init__()
        QVBoxLayout(self).addWidget(QLabel(f"{titulo}: em construção"))

    def atualizar(self) -> None:
        pass


def _criar_tela(contexto: Contexto, modulo: str, classe: str, titulo: str) -> QWidget:
    nome = f"src.folego.qt.{modulo}"
    try:
        return getattr(importlib.import_module(nome), classe)(contexto)
    except ModuleNotFoundError as erro:
        if erro.name != nome:  # um import quebrado dentro da tela não pode virar "em construção"
            raise
        return _EmConstrucao(titulo)


class JanelaPrincipal(QMainWindow):
    def __init__(self, contexto: Contexto):
        super().__init__()
        self.contexto = contexto
        contexto.janela = self
        self.setWindowTitle("Fôlego")
        self.resize(980, 680)
        self.setMinimumSize(780, 540)
        # Campos de texto com borda visível também no modo escuro (sem isso somem no fundo)
        self.setStyleSheet(
            "QLineEdit, QComboBox { border: 1px solid palette(mid); border-radius: 4px; padding: 3px 6px; }")
        self.abas = QTabWidget()
        self.setCentralWidget(self.abas)
        self.telas: Dict[str, QWidget] = {}
        for chave, titulo, modulo, classe in TELAS:
            tela = _criar_tela(contexto, modulo, classe, titulo)
            self.telas[chave] = tela
            self.abas.addTab(tela, titulo)
        contexto.definir_status(lambda texto: self.statusBar().showMessage(texto, 8000))
        contexto.definir_navegacao(lambda chave: self.abas.setCurrentWidget(self.telas[chave]))
        contexto.mudou.connect(self.atualizar_todas)
        self.abas.currentChanged.connect(lambda _: self.atualizar_todas())

    def atualizar_todas(self) -> None:
        for tela in self.telas.values():
            tela.atualizar()


def primeiro_uso(contexto: Contexto) -> None:
    """Assistente de primeiro uso: dia do pagamento e salário, com as regras do núcleo."""
    contexto.info("Bem-vindo ao Fôlego!", "Vamos configurar o básico: o dia em que você recebe e o seu salário.")
    while True:
        texto = contexto.perguntar_texto("Primeiro uso", "Dia do mês em que você recebe (1 a 31):")
        if texto is None:
            return  # fechou: o assistente aparece de novo na próxima vez
        try:
            dia = int(texto.strip())
        except ValueError:
            contexto.aviso("Valor inválido", "Digite só o número do dia, por exemplo 5.")
            continue
        if contexto.mostrar_decisao(contexto.configurar.definir_dia_no_primeiro_uso(dia), "Dia definido."):
            break
    while True:
        texto = contexto.perguntar_texto("Primeiro uso", "Valor do seu salário (ex.: 3.000,00):")
        if texto is None:
            return
        valor = ler_centavos(texto)
        if valor is None:
            contexto.aviso("Valor inválido", "Não entendi o valor. Exemplo: 3.000,00")
            continue
        entrada = Entrada(valor, TipoEntrada.RECORRENTE, contexto.ciclo().inicio, descricao="Salário")
        if contexto.mostrar_decisao(contexto.cadastros.salvar_entrada(entrada, contexto.hoje), "Salário cadastrado."):
            break
    contexto.configurar.concluir_primeiro_uso()


def abrir(repo, hoje=None, agora=None, pasta_exportacao=None,
          contexto: Contexto = None) -> Tuple[JanelaPrincipal, Contexto]:
    """Cria a janela, roda o primeiro uso e a rotina diária, e mostra os alertas (sem chamar exec)."""
    contexto = contexto or Contexto(repo, hoje, agora, pasta_exportacao)
    janela = JanelaPrincipal(contexto)
    janela.show()
    if contexto.configurar.mostrar_primeiro_uso():
        primeiro_uso(contexto)
    contexto.alertas.rotina_diaria(contexto.hoje, contexto.agora)
    contexto.mudou.emit()
    contexto.exibir_avisos()
    return janela, contexto
