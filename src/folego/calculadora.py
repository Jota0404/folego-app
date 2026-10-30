"""Cálculos de ciclo, orçamento, limite semanal, painel e fechamento."""
from __future__ import annotations

import calendar
import enum
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import List, Optional

from .modelos import (
    Ciclo, CicloFechado, Configuracoes, ContaFixa, Entrada, Gasto,
    MetaReserva, Resumo, TipoEntrada, TipoMeta,
)

UM_DIA = timedelta(days=1)


def _dias_no_mes(ano: int, mes: int) -> int:
    return calendar.monthrange(ano, mes)[1]


def _somar_meses(ano: int, mes: int, n: int):
    total = ano * 12 + (mes - 1) + n
    return total // 12, total % 12 + 1


def menos_meses(data: date, n: int) -> date:
    """Como o minusMonths do Java: se o dia não existe no mês, vai para o último."""
    ano, mes = _somar_meses(data.year, data.month, -n)
    return date(ano, mes, min(data.day, _dias_no_mes(ano, mes)))


def _meses_entre(de: date, ate: date) -> int:
    return (ate.year - de.year) * 12 + (ate.month - de.month)


def data_de_pagamento(ano: int, mes: int, dia_pagamento: int) -> date:
    """Data do pagamento no mês. Se o dia não existe, é o último dia (RN02)."""
    if not 1 <= dia_pagamento <= 31:
        raise ValueError(f"Dia do pagamento fora de 1 a 31: {dia_pagamento}")
    return date(ano, mes, min(dia_pagamento, _dias_no_mes(ano, mes)))


def ciclo_de(data: date, dia_pagamento: int) -> Ciclo:
    """Ciclo que contém data: começa no dia do pagamento e termina na véspera
    do próximo (RN01, RN02)."""
    ano, mes = data.year, data.month
    if data_de_pagamento(ano, mes, dia_pagamento) > data:
        ano, mes = _somar_meses(ano, mes, -1)
    prox_ano, prox_mes = _somar_meses(ano, mes, 1)
    return Ciclo(
        inicio=data_de_pagamento(ano, mes, dia_pagamento),
        fim=data_de_pagamento(prox_ano, prox_mes, dia_pagamento) - UM_DIA,
    )


@dataclass(frozen=True)
class MudancaDiaPagamento:
    """O ciclo que contém hoje e, se houver, o que fecha ontem."""
    atual: Ciclo
    fechado: Optional[Ciclo]


def mudar_dia_pagamento(atual: Ciclo, novo_dia: int, hoje: date) -> MudancaDiaPagamento:
    """RN01: o dia do pagamento muda para novo_dia em hoje. Em geral, o ciclo
    atual passa a terminar na véspera da próxima ocorrência do novo dia. Se o
    novo dia é hoje, o atual fecha ontem e um ciclo novo começa hoje; se o
    atual também começou hoje, não há o que fechar."""
    if hoje not in atual:
        raise ValueError(f"{hoje} fora do ciclo atual {atual}")
    novo = ciclo_de(hoje, novo_dia)
    if novo.inicio != hoje:
        return MudancaDiaPagamento(Ciclo(atual.inicio, novo.fim), None)
    if atual.inicio == hoje:
        return MudancaDiaPagamento(novo, None)
    return MudancaDiaPagamento(novo, Ciclo(atual.inicio, hoje - UM_DIA))


def ciclo_atual(config: Configuracoes, hoje: date) -> Ciclo:
    """O irregular guardado depois de uma mudança do dia (P14) ou o normal."""
    irregular = config.ciclo_irregular
    if irregular is not None and hoje in irregular:
        return irregular
    return ciclo_de(hoje, config.dia_pagamento)


@dataclass(frozen=True)
class NovoDiaPagamento:
    configuracoes: Configuracoes
    fechado: Optional[Ciclo]


def com_dia_pagamento(config: Configuracoes, novo_dia: int, hoje: date) -> NovoDiaPagamento:
    """RN01 e P14: muda o dia do pagamento. O ciclo atual fica guardado
    enquanto for diferente do normal do novo dia, e o ciclo que fecha vem junto."""
    mudanca = mudar_dia_pagamento(ciclo_atual(config, hoje), novo_dia, hoje)
    irregular = None if mudanca.atual == ciclo_de(hoje, novo_dia) else mudanca.atual
    nova = replace(config, dia_pagamento=novo_dia, ciclo_irregular=irregular)
    return NovoDiaPagamento(nova, mudanca.fechado)


# --- Orçamento -------------------------------------------------------------

def entra_em(entrada: Entrada, ciclo: Ciclo) -> bool:
    """Recorrente: ciclos cujo primeiro dia cai entre data_inicio e data_fim.
    Avulsa: só o ciclo da data."""
    if entrada.tipo == TipoEntrada.AVULSA:
        return entrada.data_inicio in ciclo
    return ciclo.inicio >= entrada.data_inicio and (
        entrada.data_fim is None or ciclo.inicio <= entrada.data_fim
    )


def _meses_desde_o_inicio(conta: ContaFixa, ciclo: Ciclo) -> int:
    return _meses_entre(conta.ciclo_inicio, ciclo.inicio)


def ativa_em(conta: ContaFixa, ciclo: Ciclo) -> bool:
    """RN03: vale nos duracao_meses ciclos a partir de ciclo_inicio, contados
    pelo mês em que cada ciclo começa. RN04: sem duração, vale até ser
    encerrada; encerrada no meio de um ciclo, ainda vale nele."""
    meses = _meses_desde_o_inicio(conta, ciclo)
    return (
        meses >= 0
        and (conta.duracao_meses is None or meses < conta.duracao_meses)
        and (conta.encerrada_em is None or conta.encerrada_em >= ciclo.inicio)
    )


def parcela_em(conta: ContaFixa, ciclo: Ciclo) -> Optional[int]:
    """RN03: número da parcela em ciclo (1 no ciclo de início), ou None se sem fim."""
    if conta.duracao_meses is None:
        return None
    return _meses_desde_o_inicio(conta, ciclo) + 1


def valor_no_ciclo(meta: MetaReserva, entradas_centavos: int) -> int:
    """RN06: valor que a meta reserva no ciclo. O percentual arredonda para
    cima (exceção da RN13)."""
    if meta.tipo == TipoMeta.VALOR:
        return meta.valor
    return -((-entradas_centavos * meta.valor) // 10_000)


@dataclass(frozen=True)
class Orcamento:
    """Tudo o que foi cadastrado. Cada cálculo filtra o que vale no ciclo."""
    entradas: List[Entrada] = field(default_factory=list)
    contas: List[ContaFixa] = field(default_factory=list)
    metas: List[MetaReserva] = field(default_factory=list)
    gastos: List[Gasto] = field(default_factory=list)

    def resumo(self, ciclo: Ciclo, gastos_antes_de: Optional[date] = None) -> Resumo:
        """Totais de ciclo. Só entram os gastos com data antes de
        gastos_antes_de (padrão: o ciclo todo)."""
        if gastos_antes_de is None:
            gastos_antes_de = ciclo.fim + UM_DIA
        total_entradas = sum(e.valor_centavos for e in self.entradas if entra_em(e, ciclo))
        return Resumo(
            entradas=total_entradas,
            fixas=sum(c.valor_centavos for c in self.contas if ativa_em(c, ciclo)),
            reserva=sum(valor_no_ciclo(m, total_entradas) for m in self.metas if m.ativa),
            gastos=sum(
                g.valor_centavos for g in self.gastos
                if g.data in ciclo and g.data < gastos_antes_de
            ),
        )

    def fechar(self, ciclo: Ciclo) -> CicloFechado:
        """RN05: o retrato do ciclo, com os totais de agora."""
        return CicloFechado(ciclo, self.resumo(ciclo))

    def limite_semanal(self, ciclo: Ciclo, data: date, limite_manual: Optional[int] = None) -> "LimiteSemanal":
        """Limite da semana que contém data (RN10 a RN13). limite_manual vale
        para uma semana cheia. Usa o disponível do primeiro dia da semana dentro
        do ciclo: os gastos da própria semana não mudam o limite, mas um gasto
        retroativo de uma semana anterior muda (RN14)."""
        if data not in ciclo:
            raise ValueError(f"{data} fora do ciclo {ciclo}")
        segunda = data - timedelta(days=data.weekday())
        domingo = segunda + timedelta(days=6)
        inicio = max(segunda, ciclo.inicio)
        fim = min(domingo, ciclo.fim)
        dias = (fim - inicio).days + 1
        dias_restantes = (ciclo.fim - inicio).days + 1

        disponivel = self.resumo(ciclo, gastos_antes_de=inicio).disponivel
        # RN11: multiplica antes de dividir, e a divisão arredonda para baixo (RN13)
        automatico = 0 if disponivel <= 0 else disponivel * dias // dias_restantes
        # RN12: proporcional aos dias da semana dentro do ciclo
        manual = None if limite_manual is None else limite_manual * dias // 7
        valor = automatico if manual is None else manual
        return LimiteSemanal(inicio, fim, valor, manual is not None and manual > automatico)

    def painel(self, ciclo: Ciclo, hoje: date, config: Configuracoes) -> "Painel":
        """Painel da semana de hoje. A barra fica amarela quando os gastos
        atingem o percentual de atenção e vermelha no crítico, os mesmos pontos
        dos alertas A2 e A3. Com limite zero, fica vermelha."""
        semana = self.limite_semanal(ciclo, hoje, config.limite_semanal_manual)
        gastos_da_semana = sum(
            g.valor_centavos for g in self.gastos if semana.inicio <= g.data <= semana.fim
        )
        limite = semana.valor_centavos
        # compara gastos/limite com o percentual sem dividir
        if limite <= 0:
            faixa = Faixa.VERMELHA
        elif gastos_da_semana * 10_000 < limite * config.percentual_atencao:
            faixa = Faixa.VERDE
        elif gastos_da_semana * 10_000 < limite * config.percentual_critico:
            faixa = Faixa.AMARELA
        else:
            faixa = Faixa.VERMELHA
        return Painel(semana, gastos_da_semana, self.resumo(ciclo), faixa)


@dataclass(frozen=True)
class LimiteSemanal:
    """Limite de uma semana (RN10) recortada pelo ciclo, de inicio a fim.
    ritmo_nao_fecha_ciclo: o limite manual passou do automático (RN12)."""
    inicio: date
    fim: date
    valor_centavos: int
    ritmo_nao_fecha_ciclo: bool = False


class Faixa(enum.Enum):
    VERDE = "VERDE"
    AMARELA = "AMARELA"
    VERMELHA = "VERMELHA"


@dataclass(frozen=True)
class Painel:
    """Tudo o que a tela Início mostra, calculado num lugar só."""
    semana: LimiteSemanal
    gastos_da_semana: int
    resumo_do_ciclo: Resumo
    faixa: Faixa

    @property
    def disponivel_da_semana(self) -> int:
        """Fica negativo quando passa do limite."""
        return self.semana.valor_centavos - self.gastos_da_semana

    @property
    def consumo_pontos_base(self) -> int:
        """Parte do limite já gasta (10000 = barra cheia). Limite zero enche a barra."""
        if self.semana.valor_centavos <= 0:
            return 10_000
        return min(10_000, self.gastos_da_semana * 10_000 // self.semana.valor_centavos)


# --- Fechamento ------------------------------------------------------------

def ciclos_para_fechar(
    ultimo_fechado: Optional[Ciclo],
    primeiro_gasto: Optional[date],
    config: Configuracoes,
    hoje: date,
) -> List[Ciclo]:
    """Ciclos que já terminaram antes de hoje e ainda não foram fechados: a
    partir do ciclo seguinte ao ultimo_fechado ou, sem nenhum, a partir do
    ciclo do primeiro_gasto."""
    if ultimo_fechado is not None:
        dia = ultimo_fechado.fim + UM_DIA
    elif primeiro_gasto is not None:
        dia = primeiro_gasto
    else:
        return []
    ciclos = []
    while True:
        ciclo = ciclo_atual(config, dia)
        if ciclo.fim >= hoje:
            return ciclos
        ciclos.append(ciclo)
        dia = ciclo.fim + UM_DIA
