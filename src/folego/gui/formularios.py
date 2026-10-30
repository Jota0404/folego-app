"""Formulários de entrada, conta fixa e meta (tk.Toplevel). A leitura dos campos fica em funções puras
(ler_entrada, ler_conta, ler_meta: devolvem o item ou a mensagem de erro); toda regra de negócio vem do núcleo.
O formulário nunca espera a janela fechar: o botão Salvar chama salvar(), que só fecha se salvou."""
from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from datetime import date, datetime
from tkinter import ttk
from typing import Optional, Union

from ..decisoes import ErroCadastro, inicio_pela_parcela
from ..formatos import formatar_data, formatar_percentual, formatar_reais, ler_centavos, ler_pontos_base
from ..modelos import ContaFixa, Entrada, MetaReserva, TipoEntrada, TipoMeta
from ..textos import ERROS

MSG_VALOR = "Não entendi o valor. Exemplo: 1.500,00"
MSG_PERCENTUAL = "Não entendi o percentual. Exemplo: 10 ou 10,5"
MSG_VENCIMENTO = "O dia do vencimento precisa ser um número. Exemplo: 5"
MSG_DURACAO = "A duração precisa ser um número de meses, ou ficar vazia (sem fim)."
MSG_PARCELA = "A parcela atual precisa ser um número. Exemplo: 3"

ROTULO_ENTRADA = {TipoEntrada.RECORRENTE: "Recorrente", TipoEntrada.AVULSA: "Avulsa"}
ROTULO_META = {TipoMeta.VALOR: "Valor em reais", TipoMeta.PERCENTUAL: "Percentual das entradas"}


def ler_data(texto: str, hoje: date) -> Optional[date]:
    """dd/mm/aaaa, ou só dd/mm (no ano de hoje); None se não for uma data."""
    texto = texto.strip()
    if texto.count("/") == 1:
        texto += f"/{hoje.year}"
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        return None


def ler_entrada(descricao: str, valor: str, tipo: TipoEntrada, inicio: str, fim: str, hoje: date, ciclo,
                base: Optional[Entrada] = None) -> Union[Entrada, str]:
    """Início vazio = começo do ciclo (recorrente) ou hoje (avulsa). Fim vazio ou 'sem' = sem fim (avulsa não tem)."""
    centavos = ler_centavos(valor)
    if centavos is None:
        return MSG_VALOR
    recorrente = tipo == TipoEntrada.RECORRENTE
    data_inicio = ler_data(inicio, hoje) if inicio.strip() else (ciclo.inicio if recorrente else hoje)
    if data_inicio is None:
        return "Não entendi a data de início. Exemplo: 01/10/2026"
    data_fim = None
    if recorrente and fim.strip().lower() not in ("", "sem"):
        data_fim = ler_data(fim, hoje)
        if data_fim is None:
            return "Não entendi a data de fim. Exemplo: 31/12/2026"
    return replace(base or Entrada(0, tipo, data_inicio), valor_centavos=centavos, tipo=tipo,
                   data_inicio=data_inicio, data_fim=data_fim, descricao=descricao.strip())


def ler_conta(descricao: str, valor: str, vencimento: str, duracao: str, parcela: str, ciclo,
              base: Optional[ContaFixa] = None) -> Union[ContaFixa, str]:
    """Duração vazia ou 'sem' = sem fim. A parcela atual só vale para conta nova com duração (vazia = 1)."""
    centavos = ler_centavos(valor)
    if centavos is None:
        return MSG_VALOR
    try:
        dia = int(vencimento)
    except ValueError:
        return MSG_VENCIMENTO
    meses = None
    if duracao.strip().lower() not in ("", "sem"):
        try:
            meses = int(duracao)
        except ValueError:
            return MSG_DURACAO
        if meses < 1:
            return ERROS[ErroCadastro.DURACAO_INVALIDA]
    inicio = base.ciclo_inicio if base else ciclo.inicio
    if base is None and meses is not None:
        try:
            numero = int(parcela) if parcela.strip() else 1
        except ValueError:
            return MSG_PARCELA
        if not 1 <= numero <= meses:
            return ERROS[ErroCadastro.PARCELA_INVALIDA]
        inicio = inicio_pela_parcela(ciclo, numero)
    return replace(base or ContaFixa(0, inicio), valor_centavos=centavos, ciclo_inicio=inicio, duracao_meses=meses,
                   descricao=descricao.strip(), dia_vencimento=dia)


def ler_meta(nome: str, tipo: TipoMeta, valor: str, base: Optional[MetaReserva] = None) -> Union[MetaReserva, str]:
    """Valor em reais (VALOR) ou percentual em pontos-base (PERCENTUAL)."""
    numero = ler_centavos(valor) if tipo == TipoMeta.VALOR else ler_pontos_base(valor)
    if numero is None:
        return MSG_VALOR if tipo == TipoMeta.VALOR else MSG_PERCENTUAL
    return replace(base or MetaReserva(tipo, numero), tipo=tipo, valor=numero, nome=nome.strip())


class _Formulario:
    """Janela com campos em grade. As subclasses montam os campos, leem e gravam."""
    titulo = ""
    salvo = ""

    def __init__(self, master, contexto, item=None):
        self.contexto, self.item = contexto, item
        self.janela = tk.Toplevel(master)
        self.janela.title(self.titulo + (" (editar)" if item else " (novo)"))
        self.janela.transient(master.winfo_toplevel())
        self.janela.resizable(False, False)
        self.corpo = ttk.Frame(self.janela, padding=14)
        self.corpo.pack(fill="both", expand=True)
        self.corpo.columnconfigure(1, weight=1)
        self.campos()
        botoes = ttk.Frame(self.corpo)
        botoes.grid(column=0, columnspan=2, pady=(12, 0), sticky="e")
        ttk.Button(botoes, text="Cancelar", command=self.janela.destroy).pack(side="right")
        ttk.Button(botoes, text="Salvar", command=self.salvar).pack(side="right", padx=(0, 6))
        try:
            self.janela.grab_set()
        except tk.TclError:  # janela ainda não visível (por exemplo, nos testes)
            pass

    def _linha(self, rotulo: str, variavel: tk.StringVar, tipo=ttk.Entry, **opcoes):
        linha = self.corpo.grid_size()[1]
        ttk.Label(self.corpo, text=rotulo).grid(row=linha, column=0, sticky="w", padx=(0, 10), pady=3)
        campo = tipo(self.corpo, textvariable=variavel, width=28, **opcoes)
        campo.grid(row=linha, column=1, sticky="ew", pady=3)
        return campo

    def campos(self) -> None:
        raise NotImplementedError

    def ler(self):
        """O item pronto, ou o texto do erro."""
        raise NotImplementedError

    def gravar(self, item):
        """Chama o serviço e devolve a decisão do núcleo."""
        raise NotImplementedError

    def salvar(self) -> bool:
        item = self.ler()
        if isinstance(item, str):
            self.contexto.aviso("Confira os dados", item)
            return False
        if not self.contexto.mostrar_decisao(self.gravar(item), self.salvo):
            return False
        self.janela.destroy()
        return True


class FormularioEntrada(_Formulario):
    titulo = "Entrada"
    salvo = "Entrada salva."

    def campos(self) -> None:
        e, ctx = self.item, self.contexto
        self.descricao = tk.StringVar(self.janela, e.descricao if e else "")
        self.valor = tk.StringVar(self.janela, formatar_reais(e.valor_centavos) if e else "")
        self.tipo = tk.StringVar(self.janela, ROTULO_ENTRADA[e.tipo if e else TipoEntrada.RECORRENTE])
        self.inicio = tk.StringVar(self.janela, formatar_data(e.data_inicio if e else ctx.ciclo().inicio))
        self.fim = tk.StringVar(self.janela, formatar_data(e.data_fim) if e and e.data_fim else "")
        self._linha("Descrição", self.descricao).focus_set()
        self._linha("Valor", self.valor)
        combo = self._linha("Tipo", self.tipo, ttk.Combobox, values=list(ROTULO_ENTRADA.values()),
                            state="disabled" if e else "readonly")
        combo.bind("<<ComboboxSelected>>", self._tipo_mudou)
        self._linha("Início (dd/mm/aaaa)", self.inicio)
        self.campo_fim = self._linha("Fim (vazio = sem fim)", self.fim)
        self._tipo_mudou()

    def _tipo(self) -> TipoEntrada:
        recorrente = self.tipo.get() == ROTULO_ENTRADA[TipoEntrada.RECORRENTE]
        return TipoEntrada.RECORRENTE if recorrente else TipoEntrada.AVULSA

    def _tipo_mudou(self, _evento=None) -> None:
        recorrente = self._tipo() == TipoEntrada.RECORRENTE
        if self.item is None:  # só troca o padrão do início se o usuário não mexeu nele
            padrao_recorrente = formatar_data(self.contexto.ciclo().inicio)
            padrao_avulsa = formatar_data(self.contexto.hoje)
            antigo, novo = (padrao_avulsa, padrao_recorrente) if recorrente else (padrao_recorrente, padrao_avulsa)
            if self.inicio.get() == antigo:
                self.inicio.set(novo)
        self.campo_fim.config(state="normal" if recorrente else "disabled")

    def ler(self):
        return ler_entrada(self.descricao.get(), self.valor.get(), self._tipo(), self.inicio.get(), self.fim.get(),
                           self.contexto.hoje, self.contexto.ciclo(), self.item)

    def gravar(self, item):
        return self.contexto.cadastros.salvar_entrada(item, self.contexto.hoje)


class FormularioConta(_Formulario):
    titulo = "Conta fixa"
    salvo = "Conta salva."

    def campos(self) -> None:
        c = self.item
        self.descricao = tk.StringVar(self.janela, c.descricao if c else "")
        self.valor = tk.StringVar(self.janela, formatar_reais(c.valor_centavos) if c else "")
        self.vencimento = tk.StringVar(self.janela, str(c.dia_vencimento) if c else "")
        self.duracao = tk.StringVar(self.janela, str(c.duracao_meses) if c and c.duracao_meses else "")
        self.parcela = tk.StringVar(self.janela, "")
        self._linha("Descrição", self.descricao).focus_set()
        self._linha("Valor", self.valor)
        self._linha("Dia do vencimento (1 a 31)", self.vencimento)
        self._linha("Duração em meses (vazio = sem fim)", self.duracao)
        if c is None:
            self._linha("Parcela atual (vazio = 1)", self.parcela)

    def ler(self):
        return ler_conta(self.descricao.get(), self.valor.get(), self.vencimento.get(), self.duracao.get(),
                         self.parcela.get(), self.contexto.ciclo(), self.item)

    def gravar(self, item):
        return self.contexto.cadastros.salvar_conta(item, self.contexto.hoje)


class FormularioMeta(_Formulario):
    titulo = "Meta de reserva"
    salvo = "Meta salva."

    def campos(self) -> None:
        m = self.item
        self.nome = tk.StringVar(self.janela, m.nome if m else "")
        self.tipo = tk.StringVar(self.janela, ROTULO_META[m.tipo if m else TipoMeta.VALOR])
        texto = ""
        if m:
            texto = formatar_reais(m.valor) if m.tipo == TipoMeta.VALOR else formatar_percentual(m.valor)
        self.valor = tk.StringVar(self.janela, texto)
        self._linha("Nome", self.nome).focus_set()
        self._linha("Tipo", self.tipo, ttk.Combobox, values=list(ROTULO_META.values()),
                    state="disabled" if m else "readonly")
        self._linha("Valor (reais ou %)", self.valor)

    def ler(self):
        tipo = TipoMeta.VALOR if self.tipo.get() == ROTULO_META[TipoMeta.VALOR] else TipoMeta.PERCENTUAL
        return ler_meta(self.nome.get(), tipo, self.valor.get(), self.item)

    def gravar(self, item):
        return self.contexto.cadastros.salvar_meta(item, self.contexto.hoje)
