"""Casos de uso com estado: salvar e excluir cadastros, configurar e disparar
os alertas. Síncronos: o repositório devolve o valor atual. hoje e agora vêm de
quem chama, porque o núcleo não lê o relógio."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta
from typing import Callable, List, Protocol

from .alertas import (
    ResumoDoCiclo, ResumoSemanal, alerta_de_invasao, alertas_de_limite,
)
from .calculadora import (
    Orcamento, ciclo_atual, ciclos_para_fechar, com_dia_pagamento,
)
from .decisoes import (
    PERMITIDO, Bloqueado, Permitido, decidir_conta, decidir_configuracoes, decidir_entrada,
    decidir_exclusao_conta, decidir_exclusao_entrada, decidir_exclusao_gasto, decidir_gasto,
    decidir_meta, mostrar_primeiro_uso,
)
from .modelos import (
    Categoria, CicloFechado, Configuracoes, ContaFixa, Entrada, Gasto, MetaReserva,
)


class OrcamentoRepositorio(Protocol):
    """salvar_* cria quando o id é 0 e atualiza nos outros casos, devolvendo o id."""

    def orcamento(self) -> Orcamento: ...

    def categorias(self) -> List[Categoria]: ...

    def salvar_entrada(self, entrada: Entrada) -> int: ...

    def salvar_conta(self, conta: ContaFixa) -> int: ...

    def salvar_meta(self, meta: MetaReserva) -> int: ...

    def salvar_gasto(self, gasto: Gasto) -> int: ...

    def excluir_entrada(self, entrada: Entrada) -> None: ...

    def excluir_conta(self, conta: ContaFixa) -> None: ...

    def excluir_meta(self, meta: MetaReserva) -> None: ...

    def excluir_gasto(self, gasto: Gasto) -> None: ...


class HistoricoRepositorio(Protocol):
    """Ciclos fechados e registro de alertas já disparados."""

    def ciclos_fechados(self) -> List[CicloFechado]: ...

    def salvar_ciclo_fechado(self, ciclo_fechado: CicloFechado) -> int:
        """Devolve -1 quando esse ciclo já tinha sido fechado."""

    def registrar_alerta(self, codigo: str, periodo_ref: str, disparado_em: datetime) -> bool:
        """Registra o alerta e devolve True, ou False se ele já disparou nesse período."""


class ConfiguracoesRepositorio(Protocol):
    def configuracoes(self) -> Configuracoes: ...

    def atualizar(self, mudanca: Callable[[Configuracoes], Configuracoes]) -> None:
        """Altera as configurações de uma vez, ex.: atualizar(lambda c: replace(c, ...))."""


class Notificador(Protocol):
    """Quem mostra o alerta ao usuário."""

    def avisar(self, alerta) -> None: ...


class Agendador(Protocol):
    """Quem agenda a rotina diária dos alertas."""

    def reagendar(self, horario: time) -> None: ...


class Alertas:
    """Fecha ciclos (RN05) e dispara os alertas A1 a A5, cada um no máximo uma
    vez por período (registro de alertas)."""

    def __init__(self, orcamento: OrcamentoRepositorio, configuracoes: ConfiguracoesRepositorio,
                 historico: HistoricoRepositorio, notificador: Notificador):
        self._orcamento = orcamento
        self._configuracoes = configuracoes
        self._historico = historico
        self._notificador = notificador

    def fechar_ciclos(self, hoje: date) -> List[CicloFechado]:
        """Fecha os ciclos que já terminaram e ainda não têm retrato. Devolve os que fechou agora."""
        dados = self._orcamento.orcamento()
        ultimo = max(self._historico.ciclos_fechados(), key=lambda c: c.ciclo.fim, default=None)
        primeiro_gasto = min((g.data for g in dados.gastos), default=None)
        pendentes = ciclos_para_fechar(
            ultimo.ciclo if ultimo else None, primeiro_gasto, self._configuracoes.configuracoes(), hoje)
        # O banco ignora um ciclo repetido, caso dois fechamentos rodem juntos
        fechados = [dados.fechar(c) for c in pendentes]
        return [f for f in fechados if self._historico.salvar_ciclo_fechado(f) != -1]

    def mudar_dia_pagamento(self, novo_dia: int, hoje: date) -> None:
        """RN01: muda o dia do pagamento e fecha, junto, o ciclo que termina ontem (se houver)."""
        self.fechar_ciclos(hoje)
        novo = com_dia_pagamento(self._configuracoes.configuracoes(), novo_dia, hoje)
        if novo.fechado is not None:
            self._historico.salvar_ciclo_fechado(self._orcamento.orcamento().fechar(novo.fechado))
        self._configuracoes.atualizar(lambda _: novo.configuracoes)

    def depois_do_gasto(self, antes: Orcamento, gasto_id: int, hoje: date, agora: datetime) -> None:
        """A2, A3 e A4 depois de salvar um gasto. antes são os dados de antes de salvar."""
        config = self._configuracoes.configuracoes()
        ciclo = ciclo_atual(config, hoje)
        depois = self._orcamento.orcamento()
        painel = depois.painel(ciclo, hoje, config)
        invasao = alerta_de_invasao(antes.resumo(ciclo), depois.resumo(ciclo), gasto_id)
        self._disparar(
            alertas_de_limite(painel, config.percentual_atencao, config.percentual_critico)
            + ([invasao] if invasao else []),
            agora,
        )

    def rotina_diaria(self, hoje: date, agora: datetime) -> None:
        """Rotina de todo dia, por volta do horário do resumo: fecha os ciclos
        que terminaram, manda o A5 do ciclo fechado mais recente (um só, mesmo
        atrasado), o A1 da semana, se ainda não foi, e o A2 ou o A3, se um
        cadastro novo baixou o limite e os gastos já passaram do ponto."""
        self.fechar_ciclos(hoje)
        mais_recente = max(self._historico.ciclos_fechados(), key=lambda c: c.ciclo.fim, default=None)
        config = self._configuracoes.configuracoes()
        painel = self._orcamento.orcamento().painel(ciclo_atual(config, hoje), hoje, config)
        segunda = hoje - timedelta(days=hoje.weekday())
        self._disparar(
            ([ResumoDoCiclo(mais_recente)] if mais_recente else [])
            + [ResumoSemanal(segunda, painel)]
            + alertas_de_limite(painel, config.percentual_atencao, config.percentual_critico),
            agora,
        )

    def _disparar(self, alertas: list, agora: datetime) -> None:
        for a in alertas:
            if self._historico.registrar_alerta(a.codigo.name, a.periodo_ref, agora) and a.avisar:
                self._notificador.avisar(a)


class Cadastros:
    """Salva e exclui cadastros aplicando as decisões: o que é bloqueado não chega ao banco."""

    def __init__(self, orcamento: OrcamentoRepositorio, configuracoes: ConfiguracoesRepositorio, alertas: Alertas):
        self._orcamento = orcamento
        self._configuracoes = configuracoes
        self._alertas = alertas

    def _dados(self) -> Orcamento:
        return self._orcamento.orcamento()

    def _ciclo(self, hoje: date):
        return ciclo_atual(self._configuracoes.configuracoes(), hoje)

    def salvar_conta(self, conta: ContaFixa, hoje: date):
        decisao = decidir_conta(conta, self._dados(), self._ciclo(hoje))
        if not isinstance(decisao, Bloqueado):
            self._orcamento.salvar_conta(conta)
        return decisao

    def salvar_entrada(self, entrada: Entrada, hoje: date):
        decisao = decidir_entrada(entrada, self._dados(), self._ciclo(hoje), hoje)
        if not isinstance(decisao, Bloqueado):
            self._orcamento.salvar_entrada(entrada)
        return decisao

    def salvar_meta(self, meta: MetaReserva, hoje: date):
        decisao = decidir_meta(meta, self._dados(), self._ciclo(hoje))
        if not isinstance(decisao, Bloqueado):
            self._orcamento.salvar_meta(meta)
        return decisao

    def excluir_conta(self, conta: ContaFixa, hoje: date):
        decisao = decidir_exclusao_conta(conta, self._ciclo(hoje))
        if isinstance(decisao, Permitido):
            self._orcamento.excluir_conta(conta)
        return decisao

    def encerrar(self, conta: ContaFixa, hoje: date) -> None:
        """RN04: a conta ainda conta no ciclo de hoje e sai a partir do seguinte."""
        if conta.encerrada_em is None:
            self._orcamento.salvar_conta(replace(conta, encerrada_em=hoje))

    def excluir_entrada(self, entrada: Entrada, hoje: date):
        decisao = decidir_exclusao_entrada(entrada, self._ciclo(hoje))
        if isinstance(decisao, Permitido):
            self._orcamento.excluir_entrada(entrada)
        return decisao

    def excluir_meta(self, meta: MetaReserva) -> None:
        self._orcamento.excluir_meta(meta)

    def salvar_gasto(self, gasto: Gasto, hoje: date, agora: datetime):
        """Salva o gasto e dispara os alertas que ele provocar (A2, A3 e A4)."""
        antes = self._dados()
        decisao = decidir_gasto(gasto, antes, self._ciclo(hoje), hoje)
        if not isinstance(decisao, Bloqueado):
            self._alertas.depois_do_gasto(antes, self._orcamento.salvar_gasto(gasto), hoje, agora)
        return decisao

    def excluir_gasto(self, gasto: Gasto, hoje: date):
        decisao = decidir_exclusao_gasto(gasto, self._ciclo(hoje))
        if isinstance(decisao, Permitido):
            self._orcamento.excluir_gasto(gasto)
        return decisao


class Configurar:
    """Salva as configurações aplicando as decisões e as consequências de cada mudança."""

    def __init__(self, orcamento: OrcamentoRepositorio, configuracoes: ConfiguracoesRepositorio,
                 alertas: Alertas, agendador: Agendador):
        self._orcamento = orcamento
        self._configuracoes = configuracoes
        self._alertas = alertas
        self._agendador = agendador

    def salvar(self, nova: Configuracoes, hoje: date):
        decisao = decidir_configuracoes(nova)
        if decisao != PERMITIDO:
            return decisao
        atual = self._configuracoes.configuracoes()
        # RN01 e P14: mudar o dia fecha o ciclo que termina ontem e guarda o ciclo irregular
        if nova.dia_pagamento != atual.dia_pagamento:
            self._alertas.mudar_dia_pagamento(nova.dia_pagamento, hoje)
        self._configuracoes.atualizar(lambda c: replace(
            c,
            limite_semanal_manual=nova.limite_semanal_manual,
            percentual_atencao=nova.percentual_atencao,
            percentual_critico=nova.percentual_critico,
            hora_resumo=nova.hora_resumo,
        ))
        if nova.hora_resumo != atual.hora_resumo:
            self._agendador.reagendar(nova.hora_resumo)
        return decisao

    def definir_dia_no_primeiro_uso(self, dia: int):
        """Não é uma mudança (RN01): ainda não há ciclos, então o ciclo atual
        já é o normal do dia escolhido, sem ciclo irregular."""
        decisao = decidir_configuracoes(Configuracoes(dia_pagamento=dia))
        if decisao == PERMITIDO:
            self._configuracoes.atualizar(lambda c: replace(c, dia_pagamento=dia, ciclo_irregular=None))
        return decisao

    def concluir_primeiro_uso(self) -> None:
        """Fim do assistente de primeiro uso, concluído ou pulado."""
        self._configuracoes.atualizar(lambda c: replace(c, primeiro_uso_concluido=True))

    def mostrar_primeiro_uso(self) -> bool:
        return mostrar_primeiro_uso(self._configuracoes.configuracoes(), self._orcamento.orcamento())
