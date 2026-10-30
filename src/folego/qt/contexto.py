"""Contexto compartilhado pelas telas do app (PySide6): repositório, serviços, data de hoje e diálogos.
Os diálogos (aviso, info, confirmar) são atributos para os testes trocarem por funções falsas."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget

from ..alertas import mensagem
from ..calculadora import ciclo_atual
from ..servicos import Alertas, Cadastros, Configurar
from ..textos import linhas_da_decisao


class _SemAgendador:
    def reagendar(self, horario) -> None:
        pass


class _Notificador:
    """Os alertas ficam numa fila e aparecem juntos em exibir_avisos()."""

    def __init__(self, contexto: "Contexto"):
        self._contexto = contexto

    def avisar(self, alerta) -> None:
        m = mensagem(alerta)
        self._contexto.avisos_pendentes.append(f"{m.titulo}\n{m.texto}")


class Contexto(QObject):
    mudou = Signal()  # emitido depois de gravar qualquer dado: as telas se redesenham

    def __init__(self, repo, hoje: Optional[date] = None, agora: Optional[datetime] = None,
                 pasta_exportacao: Optional[Path] = None, janela: Optional[QWidget] = None):
        super().__init__()
        self.repo = repo
        self.pasta_exportacao = pasta_exportacao
        self.janela = janela  # pai dos diálogos
        self._hoje = hoje
        self._agora = agora
        self.avisos_pendentes: List[str] = []
        self.alertas = Alertas(repo, repo, repo, _Notificador(self))
        self.cadastros = Cadastros(repo, repo, self.alertas)
        self.configurar = Configurar(repo, repo, self.alertas, _SemAgendador())
        self._status: Callable[[str], None] = lambda texto: None
        self._ir_para: Callable[[str], None] = lambda chave: None
        # Diálogos reais; os testes trocam por falsos para nada travar esperando um clique.
        self.aviso: Callable[[str, str], None] = lambda t, x: QMessageBox.warning(self.janela, t, x)
        self.info: Callable[[str, str], None] = lambda t, x: QMessageBox.information(self.janela, t, x)
        self.confirmar: Callable[[str, str], bool] = lambda t, x: (
            QMessageBox.question(self.janela, t, x) == QMessageBox.StandardButton.Yes)
        self.perguntar_texto: Callable[[str, str], Optional[str]] = self._perguntar_texto

    def _perguntar_texto(self, titulo: str, pergunta: str) -> Optional[str]:
        """Texto digitado, ou None se o usuário cancelou."""
        texto, ok = QInputDialog.getText(self.janela, titulo, pergunta)
        return texto if ok else None

    # --- tempo: o app é a borda do sistema, então é aqui que o relógio é lido ---

    @property
    def hoje(self) -> date:
        return self._hoje or date.today()

    @property
    def agora(self) -> datetime:
        return self._agora or datetime.now()

    def ciclo(self):
        return ciclo_atual(self.repo.configuracoes(), self.hoje)

    # --- ligação com a janela ----------------------------------------------------

    def definir_status(self, funcao: Callable[[str], None]) -> None:
        self._status = funcao

    def definir_navegacao(self, funcao: Callable[[str], None]) -> None:
        self._ir_para = funcao

    def status(self, texto: str) -> None:
        """Texto curto na barra de baixo da janela."""
        self._status(texto)

    def ir_para(self, chave: str) -> None:
        """Troca de aba: 'inicio', 'gasto', 'historico', 'cadastros' ou 'configuracoes'."""
        self._ir_para(chave)

    # --- decisões e alertas ------------------------------------------------------

    def mostrar_decisao(self, decisao, salvo: str) -> bool:
        """Mostra o resultado de uma decisão do núcleo. Devolve True se foi salvo/aplicado.
        Bloqueio vira aviso; aviso de reserva/metas vira info; sucesso simples só vai à barra de status."""
        salvou, linhas = linhas_da_decisao(decisao, salvo)
        if not salvou:
            self.aviso("Não foi possível", linhas[0])
            return False
        self.status(linhas[0])
        if len(linhas) > 1:
            self.info("Atenção", "\n".join(linhas[1:]))
        self.exibir_avisos()
        self.mudou.emit()
        return True

    def exibir_avisos(self) -> None:
        """Mostra de uma vez os alertas (resumo da semana, limite, reserva...) que a fila juntou."""
        if self.avisos_pendentes:
            texto = "\n\n".join(self.avisos_pendentes)
            self.avisos_pendentes.clear()
            self.info("Fôlego", texto)


Telas = Dict[str, QWidget]
