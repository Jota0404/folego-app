"""Menu interativo no terminal. Só apresenta e aplica: toda decisão de regra
vem de decisoes e servicos. Este é o único lugar que lê o relógio (quando
hoje/agora não são passados)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

from .alertas import mensagem
from .calculadora import ativa_em, ciclo_atual, parcela_em
from .decisoes import inicio_pela_parcela
from .exportacao import exportar_ciclo
from .formatos import (
    formatar_data, formatar_dia_mes, formatar_percentual, formatar_reais, ler_centavos, ler_pontos_base,
)
from .modelos import ContaFixa, Entrada, Gasto, MetaReserva, OUTROS, TipoEntrada, TipoMeta
from .servicos import Alertas, Cadastros, Configurar
from .textos import FAIXAS, linhas_da_decisao


def _reais(texto: str) -> int:
    valor = ler_centavos(texto)
    if valor is None:
        raise ValueError
    return valor


def _pontos_base(texto: str) -> int:
    valor = ler_pontos_base(texto)
    if valor is None:
        raise ValueError
    return valor


class _SemAgendador:
    """Terminal não tem notificação agendada: a rotina roda ao abrir o menu."""

    def reagendar(self, horario) -> None:
        pass


class _Notificador:
    def __init__(self, saida: Callable[[str], None]):
        self._saida = saida

    def avisar(self, alerta) -> None:
        m = mensagem(alerta)
        self._saida(f"*** {m.titulo}: {m.texto}")


class _Menu:
    def __init__(self, repo, entrada, saida, hoje: date, agora: datetime, pasta_exportacao: Optional[Path] = None):
        self.repo = repo
        self.pasta_exportacao = pasta_exportacao
        self.ler = entrada
        self.dizer = saida
        self.hoje = hoje
        self.agora = agora
        self.alertas = Alertas(repo, repo, repo, _Notificador(saida))
        self.cadastros = Cadastros(repo, repo, self.alertas)
        self.configurar = Configurar(repo, repo, self.alertas, _SemAgendador())

    # --- entrada e saída ---------------------------------------------------

    def perguntar(self, texto: str, converter: Callable[[str], object] = str.strip, padrao: object = None,
                  vazio_vale: bool = False):
        """Repergunta até a conversão dar certo. Linha vazia devolve o padrão, se houver."""
        while True:
            linha = self.ler(f"{texto}: ").strip()
            if not linha and (padrao is not None or vazio_vale):
                return padrao
            try:
                return converter(linha)
            except ValueError:
                self.dizer("Não entendi. Tente de novo.")

    def decisao(self, decisao, salvo: str) -> bool:
        """Mostra o resultado de uma decisão do núcleo; devolve True se salvou/aplicou."""
        salvou, linhas = linhas_da_decisao(decisao, salvo)
        if not salvou:
            self.dizer(f"Não foi possível: {linhas[0]}")
            return False
        for linha in linhas:
            self.dizer(linha)
        return True

    def escolher(self, titulo: str, opcoes: list) -> str:
        self.dizer("")
        self.dizer(titulo)
        for numero, rotulo in opcoes:
            self.dizer(f"  {numero} - {rotulo}")
        return self.ler("Opção: ").strip()

    def ciclo(self):
        return ciclo_atual(self.repo.configuracoes(), self.hoje)

    def _data(self, texto: str) -> date:
        """dd/mm/aaaa, ou só dd/mm (no ano de hoje)."""
        if texto.count("/") == 1:
            texto += f"/{self.hoje.year}"
        return datetime.strptime(texto, "%d/%m/%Y").date()

    def _data_ou_sem(self, texto: str) -> Optional[date]:
        return None if texto.lower() == "sem" else self._data(texto)

    @staticmethod
    def _inteiro_ou_sem(texto: str) -> Optional[int]:
        return None if texto.lower() == "sem" else int(texto)

    # --- primeiro uso ------------------------------------------------------

    def primeiro_uso(self) -> None:
        self.dizer("Bem-vindo ao Fôlego! Vamos configurar o básico.")
        while True:
            dia = self.perguntar("Qual o dia do mês em que você recebe? (1 a 31)", int)
            if self.decisao(self.configurar.definir_dia_no_primeiro_uso(dia), "Dia do pagamento definido."):
                break
        while True:
            valor = self.perguntar("Qual o valor do seu salário? (ex.: 3.000,00)", _reais)
            entrada = Entrada(valor, TipoEntrada.RECORRENTE, self.ciclo().inicio, descricao="Salário")
            if self.decisao(self.cadastros.salvar_entrada(entrada, self.hoje), "Salário cadastrado."):
                break
        self.configurar.concluir_primeiro_uso()

    # --- início e novo gasto -----------------------------------------------

    def inicio(self) -> None:
        config = self.repo.configuracoes()
        ciclo = ciclo_atual(config, self.hoje)
        painel = self.repo.orcamento().painel(ciclo, self.hoje, config)
        resumo = painel.resumo_do_ciclo
        self.dizer("")
        self.dizer(f"Ciclo: {formatar_data(ciclo.inicio)} a {formatar_data(ciclo.fim)}")
        self.dizer(f"Disponível da semana ({formatar_dia_mes(painel.semana.inicio)} a "
                   f"{formatar_dia_mes(painel.semana.fim)}): {formatar_reais(painel.disponivel_da_semana)}")
        self.dizer(f"Limite da semana: {formatar_reais(painel.semana.valor_centavos)}")
        self.dizer(f"Disponível do ciclo: {formatar_reais(resumo.disponivel)}")
        self.dizer(f"Reserva do ciclo: {formatar_reais(resumo.reserva)}")
        consumo = formatar_percentual(painel.consumo_pontos_base)
        self.dizer(f"Barra: {FAIXAS[painel.faixa]}, {consumo} do limite consumido")
        if painel.semana.ritmo_nao_fecha_ciclo:
            self.dizer("Aviso: nesse ritmo o limite manual não fecha o ciclo.")
        if resumo.reserva_invadida:
            self.dizer(f"Reserva invadida em {formatar_reais(resumo.reserva_invadida)}.")
        if resumo.falta_para_metas:
            self.dizer(f"As metas não cabem: faltam {formatar_reais(resumo.falta_para_metas)}.")

    def novo_gasto(self) -> None:
        valor = self.perguntar("Valor do gasto", _reais)
        data = self.perguntar(f"Data dd/mm/aaaa (Enter = hoje, {formatar_data(self.hoje)})", self._data, self.hoje)
        descricao = self.perguntar("Descrição (opcional)", str.strip, "", vazio_vale=True)
        categorias = self.repo.categorias()
        self.dizer("Categorias: " + ", ".join(f"{c.id}={c.nome}" for c in categorias))
        ids = {c.id for c in categorias}

        def categoria(texto: str) -> int:
            if int(texto) not in ids:
                raise ValueError
            return int(texto)
        categoria_id = self.perguntar("Categoria (Enter = Outros)", categoria, OUTROS)
        gasto = Gasto(valor, data, descricao, categoria_id)
        self.decisao(self.cadastros.salvar_gasto(gasto, self.hoje, self.agora), "Gasto salvo.")

    def corrigir_gastos(self) -> None:
        """Edita ou exclui um gasto do ciclo atual (gasto de ciclo fechado é recusado pelo núcleo)."""
        ciclo = self.ciclo()
        gastos = sorted((g for g in self.repo.orcamento().gastos if g.data in ciclo),
                        key=lambda g: (g.data, g.id), reverse=True)
        if not gastos:
            self.dizer("Nenhum gasto neste ciclo.")
            return
        nomes = {c.id: c.nome for c in self.repo.categorias()}
        self.dizer("")
        for n, g in enumerate(gastos, 1):
            self.dizer(f"  {n}. {formatar_data(g.data)} - {formatar_reais(g.valor_centavos)} "
                       f"{g.descricao} [{nomes.get(g.categoria_id, '')}]".rstrip())
        numero = self.perguntar("Número do gasto (Enter = voltar)", int, 0)
        if not 1 <= numero <= len(gastos):
            return
        g = gastos[numero - 1]
        acao = self.escolher("O que fazer?", [("1", "Corrigir"), ("2", "Excluir"), ("0", "Voltar")])
        if acao == "2":
            self.decisao(self.cadastros.excluir_gasto(g, self.hoje), "Gasto excluído.")
        elif acao == "1":
            self.dizer("Enter mantém o valor atual.")
            valor = self.perguntar(f"Valor (atual {formatar_reais(g.valor_centavos)})", _reais, g.valor_centavos)
            data = self.perguntar(f"Data (atual {formatar_data(g.data)})", self._data, g.data)
            descricao = self.perguntar("Descrição", str.strip, g.descricao, vazio_vale=True)
            ids = {c.id for c in self.repo.categorias()}

            def categoria(texto: str) -> int:
                if int(texto) not in ids:
                    raise ValueError
                return int(texto)
            self.dizer("Categorias: " + ", ".join(f"{i}={n}" for i, n in nomes.items()))
            categoria_id = self.perguntar("Categoria", categoria, g.categoria_id)
            nova = replace(g, valor_centavos=valor, data=data, descricao=descricao, categoria_id=categoria_id)
            self.decisao(self.cadastros.salvar_gasto(nova, self.hoje, self.agora), "Gasto corrigido.")

    def exportar(self) -> None:
        """Grava o ciclo atual (ou um fechado, pela data) num CSV para planilha."""
        if self.pasta_exportacao is None:
            self.dizer("Exportação indisponível neste modo.")
            return
        config = self.repo.configuracoes()
        data = self.perguntar(f"Data dentro do ciclo a exportar (Enter = hoje, {formatar_data(self.hoje)})",
                              self._data, self.hoje)
        ciclo = ciclo_atual(config, data)
        caminho = exportar_ciclo(self.repo.orcamento(), ciclo, self.repo.categorias(), self.pasta_exportacao)
        self.dizer(f"Ciclo {formatar_data(ciclo.inicio)} a {formatar_data(ciclo.fim)} exportado em: {caminho}")

    # --- cadastros ---------------------------------------------------------

    def cadastros_menu(self) -> None:
        telas = {"1": self.entradas, "2": self.contas, "3": self.metas}
        while True:
            opcao = self.escolher("Cadastros", [("1", "Entradas"), ("2", "Contas fixas"),
                                                ("3", "Metas de reserva"), ("0", "Voltar")])
            if opcao == "0":
                return
            telas.get(opcao, lambda: self.dizer("Opção inválida."))()

    def _submenu(self, titulo: str, listar, adicionar, excluir, *extras) -> None:
        """extras: pares (rótulo, ação), numerados a partir de 4."""
        opcoes = [("1", "Listar"), ("2", "Adicionar"), ("3", "Excluir")]
        acoes = {"1": listar, "2": adicionar, "3": excluir}
        for numero, (rotulo, acao) in enumerate(extras, 4):
            opcoes.append((str(numero), rotulo))
            acoes[str(numero)] = acao
        while True:
            opcao = self.escolher(titulo, opcoes + [("0", "Voltar")])
            if opcao == "0":
                return
            acoes.get(opcao, lambda: self.dizer("Opção inválida."))()

    def _escolher_item(self, itens: list, listar, pergunta: str):
        if not itens:
            listar()
            return None
        listar()
        numero = self.perguntar(f"{pergunta} (Enter = cancelar)", int, 0)
        return itens[numero - 1] if 1 <= numero <= len(itens) else None

    def entradas(self) -> None:
        def itens():
            return self.repo.orcamento().entradas

        def listar():
            if not itens():
                self.dizer("Nenhuma entrada ainda.")
            for n, e in enumerate(itens(), 1):
                tipo = "recorrente" if e.tipo == TipoEntrada.RECORRENTE else "avulsa"
                fim = f" até {formatar_data(e.data_fim)}" if e.data_fim else ""
                self.dizer(f"  {n}. {e.descricao} - {formatar_reais(e.valor_centavos)} ({tipo}, "
                           f"desde {formatar_data(e.data_inicio)}{fim})")

        def adicionar():
            descricao = self.perguntar("Descrição", str.strip, "", vazio_vale=True)
            valor = self.perguntar("Valor", _reais)
            recorrente = self.perguntar("Tipo: 1 = recorrente, 2 = avulsa", self._um_ou_dois) == 1
            inicio = self.ciclo().inicio if recorrente else self.hoje
            data = self.perguntar(f"Data de início dd/mm/aaaa (Enter = {formatar_data(inicio)})", self._data, inicio)
            fim = None
            if recorrente:
                fim = self.perguntar("Data de fim dd/mm/aaaa (Enter = sem fim)", self._data, vazio_vale=True)
            entrada = Entrada(valor, TipoEntrada.RECORRENTE if recorrente else TipoEntrada.AVULSA,
                              data, fim, descricao)
            self.decisao(self.cadastros.salvar_entrada(entrada, self.hoje), "Entrada salva.")

        def excluir():
            e = self._escolher_item(itens(), listar, "Número da entrada a excluir")
            if e:
                self.decisao(self.cadastros.excluir_entrada(e, self.hoje), "Entrada excluída.")

        def editar():
            e = self._escolher_item(itens(), listar, "Número da entrada a editar")
            if not e:
                return
            self.dizer("Enter mantém o valor atual.")
            descricao = self.perguntar("Descrição", str.strip, e.descricao)
            valor = self.perguntar(f"Valor (atual {formatar_reais(e.valor_centavos)})", _reais, e.valor_centavos)
            inicio = self.perguntar(f"Data de início (atual {formatar_data(e.data_inicio)})", self._data,
                                    e.data_inicio)
            fim = e.data_fim
            if e.tipo == TipoEntrada.RECORRENTE:
                atual = formatar_data(e.data_fim) if e.data_fim else "sem fim"
                fim = self.perguntar(f"Data de fim (atual {atual}; 'sem' = sem fim)", self._data_ou_sem,
                                     e.data_fim, vazio_vale=True)
            nova = replace(e, descricao=descricao, valor_centavos=valor, data_inicio=inicio, data_fim=fim)
            self.decisao(self.cadastros.salvar_entrada(nova, self.hoje), "Entrada atualizada.")

        self._submenu("Entradas", listar, adicionar, excluir, ("Editar", editar))

    @staticmethod
    def _um_ou_dois(texto: str) -> int:
        if texto not in ("1", "2"):
            raise ValueError
        return int(texto)

    def contas(self) -> None:
        def itens():
            return self.repo.orcamento().contas

        def listar():
            ciclo = self.ciclo()
            if not itens():
                self.dizer("Nenhuma conta fixa ainda.")
            for n, c in enumerate(itens(), 1):
                if not ativa_em(c, ciclo):
                    situacao = "fora do ciclo atual"
                elif c.duracao_meses is None:
                    situacao = "sem fim"
                else:
                    situacao = f"parcela {parcela_em(c, ciclo)} de {c.duracao_meses}"
                if c.encerrada_em:
                    situacao += f", encerrada em {formatar_data(c.encerrada_em)}"
                self.dizer(f"  {n}. {c.descricao} - {formatar_reais(c.valor_centavos)}, "
                           f"vence dia {c.dia_vencimento} ({situacao})")

        def adicionar():
            descricao = self.perguntar("Descrição", str.strip, "", vazio_vale=True)
            valor = self.perguntar("Valor", _reais)
            vencimento = self.perguntar("Dia do vencimento (1 a 31)", int)
            duracao = self.perguntar("Duração em meses (Enter = sem fim)", int, vazio_vale=True)
            inicio = self.ciclo().inicio
            if duracao is not None:
                parcela = self.perguntar("Parcela atual (Enter = 1)", int, 1)
                inicio = inicio_pela_parcela(self.ciclo(), parcela)
            conta = ContaFixa(valor, inicio, duracao, None, descricao, vencimento)
            self.decisao(self.cadastros.salvar_conta(conta, self.hoje), "Conta salva.")

        def excluir():
            c = self._escolher_item(itens(), listar, "Número da conta a excluir")
            if c:
                self.decisao(self.cadastros.excluir_conta(c, self.hoje), "Conta excluída.")

        def encerrar():
            c = self._escolher_item(itens(), listar, "Número da conta a encerrar")
            if c:
                self.cadastros.encerrar(c, self.hoje)
                self.dizer("Conta encerrada: ela vale até o fim do ciclo atual.")

        def editar():
            c = self._escolher_item(itens(), listar, "Número da conta a editar")
            if not c:
                return
            self.dizer("Enter mantém o valor atual.")
            descricao = self.perguntar("Descrição", str.strip, c.descricao)
            valor = self.perguntar(f"Valor (atual {formatar_reais(c.valor_centavos)})", _reais, c.valor_centavos)
            vencimento = self.perguntar(f"Dia do vencimento (atual {c.dia_vencimento})", int, c.dia_vencimento)
            atual = f"{c.duracao_meses} meses" if c.duracao_meses else "sem fim"
            duracao = self.perguntar(f"Duração em meses (atual {atual}; 'sem' = sem fim)", self._inteiro_ou_sem,
                                     c.duracao_meses, vazio_vale=True)
            nova = replace(c, descricao=descricao, valor_centavos=valor, dia_vencimento=vencimento,
                           duracao_meses=duracao)
            self.decisao(self.cadastros.salvar_conta(nova, self.hoje), "Conta atualizada.")

        self._submenu("Contas fixas", listar, adicionar, excluir, ("Encerrar", encerrar), ("Editar", editar))

    def metas(self) -> None:
        def itens():
            return self.repo.orcamento().metas

        def listar():
            if not itens():
                self.dizer("Nenhuma meta de reserva ainda.")
            for n, m in enumerate(itens(), 1):
                valor = formatar_reais(m.valor) if m.tipo == TipoMeta.VALOR else formatar_percentual(m.valor)
                self.dizer(f"  {n}. {m.nome} - {valor}{'' if m.ativa else ' (pausada)'}")

        def adicionar():
            nome = self.perguntar("Nome", str.strip, "", vazio_vale=True)
            por_valor = self.perguntar("Tipo: 1 = valor em reais, 2 = percentual das entradas", self._um_ou_dois) == 1
            if por_valor:
                meta = MetaReserva(TipoMeta.VALOR, self.perguntar("Valor", _reais), nome=nome)
            else:
                meta = MetaReserva(TipoMeta.PERCENTUAL, self.perguntar("Percentual (ex.: 10)", _pontos_base),
                                   nome=nome)
            self.decisao(self.cadastros.salvar_meta(meta, self.hoje), "Meta salva.")

        def excluir():
            m = self._escolher_item(itens(), listar, "Número da meta a excluir")
            if m:
                self.cadastros.excluir_meta(m)
                self.dizer("Meta excluída.")

        def editar():
            m = self._escolher_item(itens(), listar, "Número da meta a editar")
            if not m:
                return
            self.dizer("Enter mantém o valor atual.")
            nome = self.perguntar("Nome", str.strip, m.nome)
            if m.tipo == TipoMeta.VALOR:
                valor = self.perguntar(f"Valor (atual {formatar_reais(m.valor)})", _reais, m.valor)
            else:
                valor = self.perguntar(f"Percentual (atual {formatar_percentual(m.valor)})", _pontos_base, m.valor)
            self.decisao(self.cadastros.salvar_meta(replace(m, nome=nome, valor=valor), self.hoje), "Meta atualizada.")

        def pausar():
            m = self._escolher_item(itens(), listar, "Número da meta a pausar ou reativar")
            if m:
                texto = "Meta reativada." if not m.ativa else "Meta pausada."
                self.decisao(self.cadastros.salvar_meta(replace(m, ativa=not m.ativa), self.hoje), texto)

        self._submenu("Metas de reserva", listar, adicionar, excluir, ("Editar", editar),
                      ("Pausar ou reativar", pausar))

    # --- histórico e configurações -----------------------------------------

    def historico(self) -> None:
        ciclo = self.ciclo()
        gastos = [g for g in self.repo.orcamento().gastos if g.data in ciclo]
        self.dizer("")
        self.dizer("Gastos do ciclo atual:")
        if not gastos:
            self.dizer("  Nenhum gasto ainda.")
        for dia in sorted({g.data for g in gastos}, reverse=True):
            do_dia = [g for g in gastos if g.data == dia]
            self.dizer(f"  {formatar_data(dia)} - {formatar_reais(sum(g.valor_centavos for g in do_dia))}")
            for g in do_dia:
                self.dizer(f"    {formatar_reais(g.valor_centavos)} {g.descricao}".rstrip())
        self.dizer("Ciclos fechados:")
        fechados = sorted(self.repo.ciclos_fechados(), key=lambda f: f.ciclo.inicio, reverse=True)
        if not fechados:
            self.dizer("  Nenhum ciclo fechado ainda.")
        for f in fechados:
            r = f.resumo
            self.dizer(f"  {formatar_data(f.ciclo.inicio)} a {formatar_data(f.ciclo.fim)}: "
                       f"entradas {formatar_reais(r.entradas)}, gastos {formatar_reais(r.gastos)}, "
                       f"sobrou {formatar_reais(max(0, r.disponivel))}, "
                       f"reserva invadida {formatar_reais(f.reserva_invadida)}")

    def configuracoes(self) -> None:
        atual = self.repo.configuracoes()
        limite = "automático" if atual.limite_semanal_manual is None else formatar_reais(atual.limite_semanal_manual)
        self.dizer("")
        self.dizer(f"Dia do pagamento: {atual.dia_pagamento}")
        self.dizer(f"Limite semanal manual: {limite}")
        self.dizer(f"Atenção em {formatar_percentual(atual.percentual_atencao)} e "
                   f"crítico em {formatar_percentual(atual.percentual_critico)}")
        self.dizer("Enter mantém o valor atual (no limite, Enter volta ao automático).")
        dia = self.perguntar("Novo dia do pagamento", int, atual.dia_pagamento)
        manual = self.perguntar("Limite semanal manual", _reais, vazio_vale=True)
        atencao = self.perguntar("Percentual de atenção", _pontos_base, atual.percentual_atencao)
        critico = self.perguntar("Percentual crítico", _pontos_base, atual.percentual_critico)
        nova = replace(atual, dia_pagamento=dia, limite_semanal_manual=manual,
                       percentual_atencao=atencao, percentual_critico=critico)
        self.decisao(self.configurar.salvar(nova, self.hoje), "Configurações salvas.")

    # --- laço principal ----------------------------------------------------

    def rodar(self) -> None:
        if self.configurar.mostrar_primeiro_uso():
            self.primeiro_uso()
        self.alertas.rotina_diaria(self.hoje, self.agora)
        telas = {"1": self.inicio, "2": self.novo_gasto, "3": self.cadastros_menu,
                 "4": self.historico, "5": self.configuracoes, "6": self.corrigir_gastos, "7": self.exportar}
        while True:
            opcao = self.escolher("Fôlego", [("1", "Início"), ("2", "Novo gasto"), ("3", "Cadastros"),
                                             ("4", "Histórico"), ("5", "Configurações"),
                                             ("6", "Corrigir ou excluir gasto"), ("7", "Exportar ciclo (CSV)"),
                                             ("0", "Sair")])
            if opcao == "0":
                return
            telas.get(opcao, lambda: self.dizer("Opção inválida."))()


def executar(repo, entrada: Callable[[str], str] = input, saida: Callable[[str], None] = print,
             hoje: Optional[date] = None, agora: Optional[datetime] = None,
             pasta_exportacao: Optional[Path] = None) -> None:
    """Roda o menu até o usuário sair. repo implementa os três repositórios de servicos."""
    try:
        _Menu(repo, entrada, saida, hoje or date.today(), agora or datetime.now(), pasta_exportacao).rodar()
    except (EOFError, KeyboardInterrupt):
        saida("")
