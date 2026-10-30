"""Ajudas para testar as abas da janela. Sem tela (CI), os testes pulam sozinhos."""
import tkinter as tk
from datetime import datetime

import pytest

from src.folego.gui.contexto import Contexto
from src.folego.modelos import Configuracoes
from . import cenario
from .cenario import data
from .fakes import Ambiente, RepoUnico


class Dialogos:
    """Guarda o que a interface mostraria; confirma = resposta fixa para confirmar()."""

    def __init__(self, confirma=True):
        self.avisos, self.infos, self.confirma = [], [], confirma

    def aviso(self, titulo, texto):
        self.avisos.append((titulo, texto))

    def info(self, titulo, texto):
        self.infos.append((titulo, texto))

    def confirmar(self, titulo, texto):
        return self.confirma


@pytest.fixture
def raiz():
    """Janela raiz escondida; pula o teste se não houver tela."""
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("sem tela para criar janelas")
    r.withdraw()
    yield r
    r.destroy()


def contexto_de_teste(orcamento=cenario.orcamento, config=None, hoje=data(5, 10), pasta_exportacao=None, confirma=True):
    """(Contexto, Ambiente, Dialogos) com repositórios em memória e diálogos falsos."""
    ambiente = Ambiente(orcamento, config or Configuracoes(primeiro_uso_concluido=True))
    ctx = Contexto(RepoUnico(ambiente), hoje, datetime(2026, 10, 5, 9, 0), pasta_exportacao)
    dialogos = Dialogos(confirma)
    ctx.aviso, ctx.info, ctx.confirmar = dialogos.aviso, dialogos.info, dialogos.confirmar
    return ctx, ambiente, dialogos
