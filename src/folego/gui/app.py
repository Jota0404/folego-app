"""Janela principal do Fôlego (tkinter): uma aba por tela, cada uma em src/folego/gui/tela_*.py.
Cada aba é uma classe ttk.Frame com __init__(self, master, contexto) e atualizar(self)."""
from __future__ import annotations

import importlib
import tkinter as tk
from tkinter import simpledialog, ttk
from typing import Tuple

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


class _EmConstrucao(ttk.Frame):
    """Aba provisória enquanto o arquivo da tela não existe."""

    def __init__(self, master, titulo: str):
        super().__init__(master)
        ttk.Label(self, text=f"{titulo}: em construção").pack(padx=20, pady=20)

    def atualizar(self) -> None:
        pass


def _criar_tela(notebook, contexto: Contexto, modulo: str, classe: str, titulo: str):
    nome = f"src.folego.gui.{modulo}"
    try:
        return getattr(importlib.import_module(nome), classe)(notebook, contexto)
    except ModuleNotFoundError as erro:
        if erro.name != nome:  # um import quebrado dentro da tela não pode virar "em construção"
            raise
        return _EmConstrucao(notebook, titulo)


def construir(raiz: tk.Misc, contexto: Contexto) -> ttk.Notebook:
    """Monta as abas e a barra de status na janela raiz."""
    barra = ttk.Label(raiz, text="", anchor="w", padding=(8, 2))
    barra.pack(side="bottom", fill="x")
    notebook = ttk.Notebook(raiz)
    notebook.pack(fill="both", expand=True)
    contexto.definir_status(lambda texto: barra.config(text=texto))
    abas = {}
    for chave, titulo, modulo, classe in TELAS:
        tela = _criar_tela(notebook, contexto, modulo, classe, titulo)
        notebook.add(tela, text=titulo)
        contexto.registrar(chave, tela)
        abas[chave] = tela
    contexto.definir_navegacao(lambda chave: notebook.select(abas[chave]))
    notebook.bind("<<NotebookTabChanged>>", lambda _: contexto.mudou())
    return notebook


def primeiro_uso(raiz: tk.Misc, contexto: Contexto) -> None:
    """Assistente de primeiro uso: dia do pagamento e salário, com as regras do núcleo."""
    contexto.info("Bem-vindo ao Fôlego!", "Vamos configurar o básico: o dia em que você recebe e o seu salário.")
    while True:
        dia = simpledialog.askinteger("Primeiro uso", "Dia do mês em que você recebe (1 a 31):", parent=raiz)
        if dia is None:
            return  # fechou: o assistente aparece de novo na próxima vez
        if contexto.mostrar_decisao(contexto.configurar.definir_dia_no_primeiro_uso(dia), "Dia definido."):
            break
    while True:
        texto = simpledialog.askstring("Primeiro uso", "Valor do seu salário (ex.: 3.000,00):", parent=raiz)
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


def abrir(repo, hoje=None, agora=None, pasta_exportacao=None, raiz: tk.Misc = None,
          contexto: Contexto = None) -> Tuple[tk.Misc, Contexto]:
    """Cria a janela (ou usa a raiz dada), roda a rotina diária e mostra os alertas.
    Os testes passam um contexto pronto, com diálogos falsos, para nada travar esperando um clique."""
    raiz = raiz or tk.Tk()
    raiz.title("Fôlego")
    raiz.geometry("900x620")
    raiz.minsize(760, 520)
    contexto = contexto or Contexto(repo, hoje, agora, pasta_exportacao)
    construir(raiz, contexto)
    if contexto.configurar.mostrar_primeiro_uso():
        primeiro_uso(raiz, contexto)
    contexto.alertas.rotina_diaria(contexto.hoje, contexto.agora)
    contexto.mudou()
    contexto.exibir_avisos()
    return raiz, contexto
