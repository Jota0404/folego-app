"""Aba Configurações: dia do pagamento, limite semanal manual e percentuais de alerta."""
from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from tkinter import ttk
from typing import Tuple, Union

from ..formatos import ler_centavos, ler_pontos_base, formatar_percentual, formatar_reais
from ..modelos import Configuracoes
from .contexto import Contexto


def ler_formulario(dia: str, limite: str, atencao: str, critico: str,
                   atual: Configuracoes) -> Union[Configuracoes, str]:
    """Converte os textos do formulário; devolve as novas configurações ou a mensagem de erro.
    Só lê: quem decide se pode salvar (faixas, atenção < crítico) é o núcleo."""
    try:
        novo_dia = int(dia.strip())
    except ValueError:
        return "Dia do pagamento: use um número de 1 a 31."
    if not 1 <= novo_dia <= 31:
        return "Dia do pagamento: use um número de 1 a 31."
    novo_limite = None
    if limite.strip():
        novo_limite = ler_centavos(limite)
        if novo_limite is None:
            return "Limite semanal: não entendi o valor. Exemplo: 350,00 (vazio = automático)."
    nova_atencao, novo_critico = ler_pontos_base(atencao), ler_pontos_base(critico)
    if nova_atencao is None or novo_critico is None:
        return "Percentuais: não entendi. Exemplo: 70 ou 87,5."
    return replace(atual, dia_pagamento=novo_dia, limite_semanal_manual=novo_limite,
                   percentual_atencao=nova_atencao, percentual_critico=novo_critico)


def _textos(c: Configuracoes) -> Tuple[str, str, str, str]:
    limite = "" if c.limite_semanal_manual is None else formatar_reais(c.limite_semanal_manual).replace("R$ ", "")
    return (str(c.dia_pagamento), limite,
            formatar_percentual(c.percentual_atencao).rstrip("%"),
            formatar_percentual(c.percentual_critico).rstrip("%"))


_CAMPOS = [
    ("Dia do pagamento", "Dia do mês em que você recebe (1 a 31)."),
    ("Limite semanal manual (R$)", "Deixe vazio para o Fôlego calcular sozinho."),
    ("Percentual de atenção (%)", "Do limite gasto, a partir de quanto avisar."),
    ("Percentual crítico (%)", "Do limite gasto, a partir de quanto o alerta é forte."),
]


class TelaConfiguracoes(ttk.Frame):
    def __init__(self, master, contexto: Contexto):
        super().__init__(master, padding=20)
        self.contexto = contexto
        self._carregado: Tuple[str, ...] = ("", "", "", "")
        self.vars = [tk.StringVar() for _ in _CAMPOS]
        self.entradas = []
        for i, ((rotulo, ajuda), var) in enumerate(zip(_CAMPOS, self.vars)):
            ttk.Label(self, text=rotulo).grid(row=2 * i, column=0, sticky="w", padx=(0, 12), pady=(8, 0))
            entrada = ttk.Entry(self, textvariable=var, width=18)
            entrada.grid(row=2 * i, column=1, sticky="w", pady=(8, 0))
            self.entradas.append(entrada)
            ttk.Label(self, text=ajuda, foreground="gray40").grid(row=2 * i + 1, column=1, sticky="w")
        botoes = ttk.Frame(self)
        botoes.grid(row=2 * len(_CAMPOS), column=1, sticky="w", pady=(16, 0))
        self.botao_salvar = ttk.Button(botoes, text="Salvar", command=self.salvar)
        self.botao_salvar.pack(side="left")
        self.botao_desfazer = ttk.Button(botoes, text="Desfazer", command=self.desfazer)
        self.botao_desfazer.pack(side="left", padx=(8, 0))
        self.desfazer()

    def _atuais(self) -> Tuple[str, ...]:
        return tuple(v.get() for v in self.vars)

    def desfazer(self) -> None:
        """Volta os campos aos valores gravados."""
        self._carregado = _textos(self.contexto.repo.configuracoes())
        for var, texto in zip(self.vars, self._carregado):
            var.set(texto)

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
