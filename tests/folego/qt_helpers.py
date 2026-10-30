"""Ajudas para testar as telas Qt sem abrir janela de verdade (QT_QPA_PLATFORM=offscreen).
Se o PySide6 não estiver instalado (CI), os testes de tela pulam sozinhos."""
import os
from datetime import datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.folego.modelos import Configuracoes  # noqa: E402
from src.folego.qt.contexto import Contexto  # noqa: E402
from . import cenario  # noqa: E402
from .cenario import data  # noqa: E402
from .fakes import Ambiente, RepoUnico  # noqa: E402


class Dialogos:
    """Guarda o que a interface mostraria; confirma = resposta fixa de confirmar();
    respostas = textos que perguntar_texto devolve, em ordem (None = cancelou)."""

    def __init__(self, confirma=True, respostas=()):
        self.avisos, self.infos, self.confirma = [], [], confirma
        self._respostas = list(respostas)

    def aviso(self, titulo, texto):
        self.avisos.append((titulo, texto))

    def info(self, titulo, texto):
        self.infos.append((titulo, texto))

    def confirmar(self, titulo, texto):
        return self.confirma

    def perguntar_texto(self, titulo, pergunta):
        return self._respostas.pop(0) if self._respostas else None


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def contexto_de_teste(orcamento=cenario.orcamento, config=None, hoje=data(5, 10), pasta_exportacao=None,
                      confirma=True, respostas=()):
    """(Contexto, Ambiente, Dialogos) com repositórios em memória e diálogos falsos."""
    ambiente = Ambiente(orcamento, config or Configuracoes(primeiro_uso_concluido=True))
    ctx = Contexto(RepoUnico(ambiente), hoje, datetime(2026, 10, 5, 9, 0), pasta_exportacao)
    dialogos = Dialogos(confirma, respostas)
    ctx.aviso, ctx.info, ctx.confirmar = dialogos.aviso, dialogos.info, dialogos.confirmar
    ctx.perguntar_texto = dialogos.perguntar_texto
    return ctx, ambiente, dialogos
