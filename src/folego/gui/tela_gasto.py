"""Aba "Novo gasto": registrar, corrigir e excluir gastos do ciclo atual."""
from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from datetime import date
from tkinter import ttk
from typing import List, Optional, Union

from ..formatos import formatar_data, formatar_reais, ler_centavos
from ..modelos import Categoria, Gasto, OUTROS


def _ler_data(texto: str, hoje: date) -> Optional[date]:
    """Lê dd/mm/aaaa ou dd/mm (ano de hoje); None se não for uma data."""
    partes = texto.strip().split("/")
    if len(partes) not in (2, 3) or not all(p.isdigit() for p in partes):
        return None
    try:
        ano = int(partes[2]) if len(partes) == 3 else hoje.year
        return date(ano, int(partes[1]), int(partes[0]))
    except ValueError:
        return None


def ler_formulario(valor: str, data: str, descricao: str, categoria: str, hoje: date,
                   categorias: List[Categoria]) -> Union[Gasto, str]:
    """Converte o que foi digitado em Gasto, ou devolve a mensagem de erro."""
    centavos = ler_centavos(valor)
    if centavos is None:
        return "Não entendi o valor. Exemplo: 1.500,00 ou 150,50"
    dia = _ler_data(data, hoje) if data.strip() else hoje
    if dia is None:
        return "Não entendi a data. Use dd/mm/aaaa ou dd/mm."
    ids = {c.nome: c.id for c in categorias}
    if categoria not in ids:
        return "Escolha uma categoria da lista."
    return Gasto(centavos, dia, descricao.strip(), ids[categoria])


class TelaGasto(ttk.Frame):
    def __init__(self, master, contexto):
        super().__init__(master, padding=12)
        self.contexto = contexto
        self._editando: Optional[Gasto] = None
        self._gastos = {}  # iid da linha -> Gasto

        self.formulario = ttk.LabelFrame(self, text="Novo gasto", padding=10)
        self.formulario.pack(fill="x")
        self.formulario.columnconfigure(1, weight=1)
        self.valor = tk.StringVar()
        self.data = tk.StringVar()
        self.descricao = tk.StringVar()
        self.categoria = tk.StringVar()
        self.entrada_valor = self._campo(0, "Valor", ttk.Entry(self.formulario, textvariable=self.valor))
        self.entrada_data = self._campo(1, "Data", ttk.Entry(self.formulario, textvariable=self.data))
        self.entrada_descricao = self._campo(2, "Descrição (opcional)",
                                             ttk.Entry(self.formulario, textvariable=self.descricao))
        self.combo = self._campo(3, "Categoria", ttk.Combobox(self.formulario, textvariable=self.categoria,
                                                              state="readonly"))
        for entrada in (self.entrada_valor, self.entrada_data, self.entrada_descricao):
            entrada.bind("<Return>", lambda _: self.salvar())
        botoes = ttk.Frame(self.formulario)
        botoes.grid(row=4, column=1, sticky="w", pady=(8, 0))
        self.botao_salvar = ttk.Button(botoes, text="Salvar", command=self.salvar)
        self.botao_salvar.pack(side="left")
        self.botao_limpar = ttk.Button(botoes, text="Limpar", command=self.limpar)
        self.botao_limpar.pack(side="left", padx=6)
        self.botao_cancelar = ttk.Button(botoes, text="Cancelar", command=self.limpar)  # só aparece ao corrigir

        lista = ttk.LabelFrame(self, text="Gastos do ciclo atual", padding=10)
        lista.pack(fill="both", expand=True, pady=(12, 0))
        self.arvore = ttk.Treeview(lista, columns=("data", "descricao", "categoria", "valor"),
                                   show="headings", selectmode="browse", height=8)
        for coluna, titulo, largura, ancora in (("data", "Data", 90, "w"), ("descricao", "Descrição", 280, "w"),
                                                ("categoria", "Categoria", 130, "w"), ("valor", "Valor", 110, "e")):
            self.arvore.heading(coluna, text=titulo)
            self.arvore.column(coluna, width=largura, anchor=ancora)
        rolagem = ttk.Scrollbar(lista, orient="vertical", command=self.arvore.yview)
        self.arvore.configure(yscrollcommand=rolagem.set)
        rolagem.pack(side="right", fill="y")
        self.arvore.pack(side="top", fill="both", expand=True)
        acoes = ttk.Frame(lista)
        acoes.pack(side="bottom", anchor="e", pady=(8, 0))
        self.botao_corrigir = ttk.Button(acoes, text="Corrigir", command=self.corrigir)
        self.botao_corrigir.pack(side="left")
        self.botao_excluir = ttk.Button(acoes, text="Excluir", command=self.excluir)
        self.botao_excluir.pack(side="left", padx=(6, 0))

        self.atualizar()
        self.limpar()

    def _campo(self, linha: int, rotulo: str, widget):
        ttk.Label(self.formulario, text=rotulo).grid(row=linha, column=0, sticky="w", padx=(0, 10), pady=3)
        widget.grid(row=linha, column=1, sticky="ew", pady=3)
        return widget

    # --- formulário ----------------------------------------------------------------

    def limpar(self) -> None:
        self._editando = None
        self.formulario.config(text="Novo gasto")
        self.botao_cancelar.pack_forget()
        self.valor.set("")
        self.data.set(formatar_data(self.contexto.hoje))
        self.descricao.set("")
        self.categoria.set(self._nome_da(OUTROS))
        self.entrada_valor.focus_set()

    def _nome_da(self, categoria_id: int) -> str:
        return next((c.nome for c in self.contexto.repo.categorias() if c.id == categoria_id), "")

    def salvar(self) -> None:
        c = self.contexto
        gasto = ler_formulario(self.valor.get(), self.data.get(), self.descricao.get(), self.categoria.get(),
                               c.hoje, c.repo.categorias())
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
        selecao = self.arvore.selection()
        if not selecao or selecao[0] not in self._gastos:
            self.contexto.aviso("Nenhum gasto selecionado", f"Selecione um gasto na lista para {acao}.")
            return None
        return self._gastos[selecao[0]]

    def corrigir(self) -> None:
        gasto = self._selecionado("corrigir")
        if gasto is None:
            return
        self._editando = gasto
        self.formulario.config(text="Corrigir gasto")
        self.botao_cancelar.pack(side="left")
        self.valor.set(formatar_reais(gasto.valor_centavos).replace("R$ ", ""))
        self.data.set(formatar_data(gasto.data))
        self.descricao.set(gasto.descricao)
        self.categoria.set(self._nome_da(gasto.categoria_id))
        self.entrada_valor.focus_set()

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
        self.combo.config(values=[cat.nome for cat in categorias])
        if not self.categoria.get():
            self.categoria.set(nomes.get(OUTROS, ""))
        ciclo = c.ciclo()
        gastos = sorted((g for g in c.repo.orcamento().gastos if g.data in ciclo),
                        key=lambda g: (g.data, g.id), reverse=True)
        selecao = self.arvore.selection()
        self.arvore.delete(*self.arvore.get_children())
        self._gastos = {str(g.id): g for g in gastos}
        for g in gastos:
            self.arvore.insert("", "end", iid=str(g.id), values=(
                formatar_data(g.data), g.descricao, nomes.get(g.categoria_id, ""), formatar_reais(g.valor_centavos)))
        if selecao and selecao[0] in self._gastos:
            self.arvore.selection_set(selecao[0])
        if self._editando is not None and str(self._editando.id) not in self._gastos:
            self.limpar()  # o gasto em correção sumiu (excluído ou fora do ciclo)
