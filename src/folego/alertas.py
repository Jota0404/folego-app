"""Alertas A1 a A5: quando disparam e o texto de cada um. O mesmo código só
dispara uma vez por periodo_ref."""
from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date
from typing import Optional

from .calculadora import Faixa, Painel
from .formatos import formatar_dia_mes, formatar_percentual, formatar_reais
from .modelos import CicloFechado, Resumo


class CodigoAlerta(enum.Enum):
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A5 = "A5"


@dataclass(frozen=True)
class ResumoSemanal:
    """A1: resumo da semana que começa na segunda."""
    segunda: date
    painel: Painel
    codigo = CodigoAlerta.A1
    avisar = True

    @property
    def periodo_ref(self) -> str:
        return self.segunda.isoformat()


@dataclass(frozen=True)
class LimiteDaSemana:
    """A2 ou A3: os gastos da semana atingiram percentual do limite.
    avisar=False só registra o alerta, sem avisar (o A2 quando o A3 dispara junto)."""
    codigo: CodigoAlerta
    percentual: int
    painel: Painel
    avisar: bool = True

    @property
    def periodo_ref(self) -> str:
        return self.painel.semana.inicio.isoformat()


@dataclass(frozen=True)
class ReservaInvadida:
    """A4: o gasto invadiu a reserva (um alerta por gasto)."""
    gasto_id: int
    reserva_invadida: int
    codigo = CodigoAlerta.A4
    avisar = True

    @property
    def periodo_ref(self) -> str:
        return f"gasto-{self.gasto_id}"


@dataclass(frozen=True)
class ResumoDoCiclo:
    """A5: resumo do ciclo que fechou."""
    fechado: CicloFechado
    codigo = CodigoAlerta.A5
    avisar = True

    @property
    def periodo_ref(self) -> str:
        return self.fechado.ciclo.inicio.isoformat()


def alertas_de_limite(painel: Painel, percentual_atencao: int, percentual_critico: int) -> list:
    """A2 e A3 da semana do painel. No salto direto para o A3, o A2 só é
    registrado, sem aviso; com limite zero, nenhum dos dois."""
    if painel.semana.valor_centavos <= 0 or painel.faixa == Faixa.VERDE:
        return []
    if painel.faixa == Faixa.AMARELA:
        return [LimiteDaSemana(CodigoAlerta.A2, percentual_atencao, painel)]
    return [
        LimiteDaSemana(CodigoAlerta.A2, percentual_atencao, painel, avisar=False),
        LimiteDaSemana(CodigoAlerta.A3, percentual_critico, painel),
    ]


def alerta_de_invasao(antes: Resumo, depois: Resumo, gasto_id: int) -> Optional[ReservaInvadida]:
    """A4 (RN09): o gasto invadiu a reserva se ela ficou mais invadida depois dele."""
    if depois.reserva_invadida > antes.reserva_invadida:
        return ReservaInvadida(gasto_id, depois.reserva_invadida)
    return None


@dataclass(frozen=True)
class Mensagem:
    titulo: str
    texto: str


def mensagem(alerta) -> Mensagem:
    """Título e texto da notificação."""
    if isinstance(alerta, ResumoSemanal):
        p = alerta.painel
        return Mensagem(
            "Resumo da semana",
            f"Você pode gastar {formatar_reais(p.disponivel_da_semana)} nesta semana "
            f"(limite de {formatar_reais(p.semana.valor_centavos)}). "
            f"No ciclo: {formatar_reais(p.resumo_do_ciclo.disponivel)}.",
        )
    if isinstance(alerta, LimiteDaSemana):
        p = alerta.painel
        return Mensagem(
            f"{formatar_percentual(alerta.percentual)} do limite da semana",
            f"Você já gastou {formatar_reais(p.gastos_da_semana)} de "
            f"{formatar_reais(p.semana.valor_centavos)} nesta semana. "
            f"Restam {formatar_reais(max(0, p.disponivel_da_semana))}.",
        )
    if isinstance(alerta, ReservaInvadida):
        return Mensagem(
            "Reserva invadida",
            "Um gasto invadiu a reserva. A reserva deste ciclo está invadida em "
            f"{formatar_reais(alerta.reserva_invadida)}.",
        )
    fechado = alerta.fechado
    resumo = fechado.resumo
    guardado = max(0, resumo.reserva - fechado.reserva_invadida)
    if resumo.reserva == 0:
        reserva = "Sem meta de reserva."
    elif fechado.reserva_invadida == 0:
        reserva = f"Reserva cumprida: {formatar_reais(resumo.reserva)} guardados."
    else:
        reserva = (f"Reserva não cumprida: guardou {formatar_reais(guardado)} "
                   f"de {formatar_reais(resumo.reserva)}.")
    return Mensagem(
        f"Ciclo de {formatar_dia_mes(fechado.ciclo.inicio)} a "
        f"{formatar_dia_mes(fechado.ciclo.fim)} fechado",
        f"Sobrou {formatar_reais(max(0, resumo.disponivel))}. {reserva}",
    )
