"""Aba Início: disponível da semana, barra de consumo e avisos."""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont, ttk
from typing import List

from ..calculadora import Faixa, Painel
from ..formatos import formatar_data, formatar_dia_mes, formatar_percentual, formatar_reais

CORES = {Faixa.VERDE: "#2e9e4f", Faixa.AMARELA: "#e0a800", Faixa.VERMELHA: "#d32f2f"}
ALTURA_BARRA = 22


def textos_do_inicio(painel: Painel, ciclo) -> dict:
    """Todos os textos da tela, prontos (sem tela, para testar)."""
    resumo = painel.resumo_do_ciclo
    return {
        "titulo": f"Ciclo: {formatar_data(ciclo.inicio)} a {formatar_data(ciclo.fim)}",
        "semana": f"Semana de {formatar_dia_mes(painel.semana.inicio)} a {formatar_dia_mes(painel.semana.fim)}",
        "disponivel_semana": formatar_reais(painel.disponivel_da_semana),
        "limite": formatar_reais(painel.semana.valor_centavos),
        "disponivel_ciclo": formatar_reais(resumo.disponivel),
        "reserva": formatar_reais(resumo.reserva),
        "consumo": f"{formatar_percentual(painel.consumo_pontos_base)} do limite consumido",
    }


def avisos_do_inicio(painel: Painel) -> List[str]:
    resumo = painel.resumo_do_ciclo
    avisos = []
    if painel.semana.ritmo_nao_fecha_ciclo:
        avisos.append("Nesse ritmo o limite manual não fecha o ciclo.")
    if resumo.reserva_invadida:
        avisos.append(f"Reserva invadida em {formatar_reais(resumo.reserva_invadida)}.")
    if resumo.falta_para_metas:
        avisos.append(f"As metas não cabem: faltam {formatar_reais(resumo.falta_para_metas)}.")
    return avisos


class TelaInicio(ttk.Frame):
    def __init__(self, master, contexto):
        super().__init__(master, padding=20)
        self.contexto = contexto
        grande = tkfont.Font(size=34, weight="bold")
        titulo = tkfont.Font(size=16, weight="bold")
        self.var = {k: tk.StringVar() for k in
                    ("titulo", "semana", "disponivel_semana", "limite", "disponivel_ciclo", "reserva", "consumo")}
        ttk.Label(self, textvariable=self.var["titulo"], font=titulo).pack(anchor="w")
        ttk.Label(self, text="Disponível da semana").pack(anchor="w", pady=(16, 0))
        ttk.Label(self, textvariable=self.var["disponivel_semana"], font=grande).pack(anchor="w")
        ttk.Label(self, textvariable=self.var["semana"]).pack(anchor="w")

        grade = ttk.Frame(self)
        grade.pack(fill="x", pady=16)
        grade.columnconfigure(1, weight=1)
        for linha, (rotulo, chave) in enumerate([("Limite da semana", "limite"),
                                                 ("Disponível do ciclo", "disponivel_ciclo"),
                                                 ("Reserva do ciclo", "reserva")]):
            ttk.Label(grade, text=rotulo).grid(row=linha, column=0, sticky="w", pady=2)
            ttk.Label(grade, textvariable=self.var[chave], anchor="e").grid(row=linha, column=1, sticky="e", pady=2)

        self.barra = tk.Canvas(self, height=ALTURA_BARRA, highlightthickness=0, bg="#dddddd")
        self.barra.pack(fill="x")
        self._fundo = self.barra.create_rectangle(0, 0, 0, ALTURA_BARRA, width=0)
        self._preenchido = self.barra.create_rectangle(0, 0, 0, ALTURA_BARRA, width=0)
        self.barra.bind("<Configure>", lambda _: self._desenhar_barra())
        ttk.Label(self, textvariable=self.var["consumo"]).pack(anchor="w", pady=(4, 0))

        self.quadro_avisos = ttk.Frame(self)
        self.quadro_avisos.pack(fill="x", pady=12)
        ttk.Button(self, text="+ Novo gasto", command=lambda: contexto.ir_para("gasto")).pack(anchor="w")
        self._consumo = 0
        self._cor = CORES[Faixa.VERDE]
        self.atualizar()

    def _desenhar_barra(self) -> None:
        largura = self.barra.winfo_width()
        if largura <= 1:
            largura = 400
        self.barra.coords(self._fundo, 0, 0, largura, ALTURA_BARRA)
        self.barra.itemconfigure(self._fundo, fill="#dddddd")
        self.barra.coords(self._preenchido, 0, 0, largura * self._consumo // 10_000, ALTURA_BARRA)
        self.barra.itemconfigure(self._preenchido, fill=self._cor)

    def atualizar(self) -> None:
        ctx = self.contexto
        config = ctx.repo.configuracoes()
        ciclo = ctx.ciclo()
        painel = ctx.repo.orcamento().painel(ciclo, ctx.hoje, config)
        for chave, texto in textos_do_inicio(painel, ciclo).items():
            self.var[chave].set(texto)
        self._consumo = painel.consumo_pontos_base
        self._cor = CORES[painel.faixa]
        self._desenhar_barra()
        for w in self.quadro_avisos.winfo_children():
            w.destroy()
        for aviso in avisos_do_inicio(painel):
            tk.Label(self.quadro_avisos, text=aviso, fg="#b71c1c", anchor="w",
                     font=tkfont.Font(weight="bold")).pack(fill="x")
