"""Aba Cadastros: entradas, contas fixas e metas de reserva, cada uma numa sub-aba com tabela e botões.
Toda gravação passa por contexto.cadastros e o resultado das regras vai para contexto.mostrar_decisao."""
from __future__ import annotations

from dataclasses import replace
from tkinter import ttk

from ..calculadora import ativa_em, parcela_em
from ..formatos import formatar_data, formatar_percentual, formatar_reais
from ..modelos import TipoEntrada, TipoMeta
from .formularios import FormularioConta, FormularioEntrada, FormularioMeta


def situacao_conta(conta, ciclo) -> str:
    """Mesmo texto do menu: 'parcela 2 de 3', 'sem fim' ou 'fora do ciclo atual', mais 'encerrada em ...'."""
    if not ativa_em(conta, ciclo):
        situacao = "fora do ciclo atual"
    elif conta.duracao_meses is None:
        situacao = "sem fim"
    else:
        situacao = f"parcela {parcela_em(conta, ciclo)} de {conta.duracao_meses}"
    if conta.encerrada_em:
        situacao += f", encerrada em {formatar_data(conta.encerrada_em)}"
    return situacao


class _Lista(ttk.Frame):
    """Tabela com botões. As subclasses dizem colunas, itens, linhas e ações."""
    colunas = ()  # (chave, título, largura, âncora)
    nome_do_item = "item"

    def __init__(self, master, contexto):
        super().__init__(master, padding=10)
        self.contexto = contexto
        topo = ttk.Frame(self)
        topo.pack(fill="both", expand=True)
        self.arvore = ttk.Treeview(topo, columns=[c[0] for c in self.colunas], show="headings", selectmode="browse")
        for n, (chave, titulo, largura, ancora) in enumerate(self.colunas):
            self.arvore.heading(chave, text=titulo, anchor=ancora)
            self.arvore.column(chave, width=largura, anchor=ancora, stretch=n == 0)
        rolagem = ttk.Scrollbar(topo, orient="vertical", command=self.arvore.yview)
        self.arvore.configure(yscrollcommand=rolagem.set)
        self.arvore.pack(side="left", fill="both", expand=True)
        rolagem.pack(side="right", fill="y")
        botoes = ttk.Frame(self)
        botoes.pack(fill="x", pady=(10, 0))
        for rotulo, acao in self.acoes():
            ttk.Button(botoes, text=rotulo, command=acao).pack(side="left", padx=(0, 6))

    def itens(self) -> list:
        raise NotImplementedError

    def linha(self, item) -> tuple:
        raise NotImplementedError

    def acoes(self) -> list:
        raise NotImplementedError

    @staticmethod
    def _iid(posicao: int, item) -> str:
        return str(item.id) if item.id else f"n{posicao}"  # id 0 = ainda sem id (não vem do banco)

    def atualizar(self) -> None:
        """Relê o repositório e redesenha, mantendo o item selecionado."""
        selecionado = self.arvore.selection()
        self.arvore.delete(*self.arvore.get_children())
        for n, item in enumerate(self.itens()):
            self.arvore.insert("", "end", iid=self._iid(n, item), values=self.linha(item))
        if selecionado and self.arvore.exists(selecionado[0]):
            self.arvore.selection_set(selecionado[0])

    def selecionado(self):
        """O item escolhido na tabela, ou None (depois de avisar)."""
        escolhida = self.arvore.selection()
        for n, item in enumerate(self.itens()):
            if escolhida and self._iid(n, item) == escolhida[0]:
                return item
        self.contexto.aviso("Nada selecionado", f"Escolha {self.nome_do_item} na lista primeiro.")
        return None

    def editar_selecionado(self, formulario) -> None:
        item = self.selecionado()
        if item:
            formulario(self, self.contexto, item)

    def excluir_selecionado(self, pergunta: str, excluir) -> None:
        """excluir(item) devolve a decisão do núcleo (ou None, quando o serviço não decide)."""
        item = self.selecionado()
        if item and self.contexto.confirmar("Excluir", pergunta.format(item)):
            excluir(item)


class ListaEntradas(_Lista):
    nome_do_item = "uma entrada"
    colunas = (("descricao", "Descrição", 220, "w"), ("valor", "Valor", 110, "e"), ("tipo", "Tipo", 100, "w"),
               ("inicio", "Início", 100, "center"), ("fim", "Fim", 100, "center"))

    def itens(self):
        return self.contexto.repo.orcamento().entradas

    def linha(self, e):
        tipo = "recorrente" if e.tipo == TipoEntrada.RECORRENTE else "avulsa"
        fim = formatar_data(e.data_fim) if e.data_fim else ("sem fim" if e.tipo == TipoEntrada.RECORRENTE else "")
        return e.descricao, formatar_reais(e.valor_centavos), tipo, formatar_data(e.data_inicio), fim

    def acoes(self):
        return [("Adicionar", lambda: FormularioEntrada(self, self.contexto)),
                ("Editar", lambda: self.editar_selecionado(FormularioEntrada)),
                ("Excluir", self.excluir)]

    def excluir(self):
        ctx = self.contexto
        self.excluir_selecionado("Excluir a entrada '{.descricao}'?",
                                 lambda e: ctx.mostrar_decisao(ctx.cadastros.excluir_entrada(e, ctx.hoje),
                                                               "Entrada excluída."))


class ListaContas(_Lista):
    nome_do_item = "uma conta"
    colunas = (("descricao", "Descrição", 200, "w"), ("valor", "Valor", 110, "e"),
               ("vencimento", "Vencimento", 90, "center"), ("situacao", "Situação", 220, "w"))

    def itens(self):
        return self.contexto.repo.orcamento().contas

    def linha(self, c):
        return (c.descricao, formatar_reais(c.valor_centavos), f"dia {c.dia_vencimento}",
                situacao_conta(c, self.contexto.ciclo()))

    def acoes(self):
        return [("Adicionar", lambda: FormularioConta(self, self.contexto)),
                ("Editar", lambda: self.editar_selecionado(FormularioConta)),
                ("Encerrar", self.encerrar), ("Excluir", self.excluir)]

    def excluir(self):
        ctx = self.contexto
        self.excluir_selecionado("Excluir a conta '{.descricao}'?",
                                 lambda c: ctx.mostrar_decisao(ctx.cadastros.excluir_conta(c, ctx.hoje),
                                                               "Conta excluída."))

    def encerrar(self):
        ctx, conta = self.contexto, self.selecionado()
        if conta is None:
            return
        if conta.encerrada_em:
            ctx.aviso("Já encerrada", "Essa conta já foi encerrada.")
        elif ctx.confirmar("Encerrar", f"Encerrar a conta '{conta.descricao}'? Ela vale até o fim do ciclo atual."):
            ctx.cadastros.encerrar(conta, ctx.hoje)
            ctx.status("Conta encerrada: ela vale até o fim do ciclo atual.")
            ctx.mudou()


class ListaMetas(_Lista):
    nome_do_item = "uma meta"
    colunas = (("nome", "Nome", 240, "w"), ("valor", "Valor ou %", 120, "e"), ("situacao", "Situação", 100, "w"))

    def itens(self):
        return self.contexto.repo.orcamento().metas

    def linha(self, m):
        valor = formatar_reais(m.valor) if m.tipo == TipoMeta.VALOR else formatar_percentual(m.valor)
        return m.nome, valor, "ativa" if m.ativa else "pausada"

    def acoes(self):
        return [("Adicionar", lambda: FormularioMeta(self, self.contexto)),
                ("Editar", lambda: self.editar_selecionado(FormularioMeta)),
                ("Pausar/reativar", self.pausar), ("Excluir", self.excluir)]

    def pausar(self):
        ctx, meta = self.contexto, self.selecionado()
        if meta:
            texto = "Meta pausada." if meta.ativa else "Meta reativada."
            ctx.mostrar_decisao(ctx.cadastros.salvar_meta(replace(meta, ativa=not meta.ativa), ctx.hoje), texto)

    def excluir(self):
        def apagar(meta):
            self.contexto.cadastros.excluir_meta(meta)
            self.contexto.status("Meta excluída.")
            self.contexto.mudou()
        self.excluir_selecionado("Excluir a meta '{.nome}'?", apagar)


class TelaCadastros(ttk.Frame):
    def __init__(self, master, contexto):
        super().__init__(master)
        self.contexto = contexto
        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True, padx=6, pady=6)
        self.entradas = ListaEntradas(self.abas, contexto)
        self.contas = ListaContas(self.abas, contexto)
        self.metas = ListaMetas(self.abas, contexto)
        for lista, titulo in ((self.entradas, "Entradas"), (self.contas, "Contas fixas"),
                              (self.metas, "Metas de reserva")):
            self.abas.add(lista, text=titulo)

    def atualizar(self) -> None:
        for lista in (self.entradas, self.contas, self.metas):
            lista.atualizar()
