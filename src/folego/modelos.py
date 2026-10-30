"""Modelos do núcleo. Dinheiro em centavos (int), percentuais em pontos-base
(1000 = 10%). Nos modelos, id 0 quer dizer "ainda não foi salvo"."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional


@dataclass(frozen=True)
class Ciclo:
    """Período entre dois pagamentos, de inicio a fim, os dois inclusive (RN01)."""
    inicio: date
    fim: date

    def __contains__(self, data: date) -> bool:
        return self.inicio <= data <= self.fim


class TipoEntrada(enum.Enum):
    RECORRENTE = "RECORRENTE"
    AVULSA = "AVULSA"


@dataclass(frozen=True)
class Entrada:
    """Recorrente entra nos ciclos cujo primeiro dia cai entre data_inicio e
    data_fim (None = sem fim). Avulsa entra só no ciclo de data_inicio."""
    valor_centavos: int
    tipo: TipoEntrada
    data_inicio: date
    data_fim: Optional[date] = None
    descricao: str = ""
    id: int = 0


@dataclass(frozen=True)
class ContaFixa:
    """ciclo_inicio é o primeiro dia do primeiro ciclo da conta. duracao_meses
    None é "sem fim" (RN04). encerrada_em é o dia em que o usuário encerrou a
    conta. dia_vencimento é só informativo: não entra nos cálculos."""
    valor_centavos: int
    ciclo_inicio: date
    duracao_meses: Optional[int] = None
    encerrada_em: Optional[date] = None
    descricao: str = ""
    dia_vencimento: int = 1
    id: int = 0


class TipoMeta(enum.Enum):
    VALOR = "VALOR"
    PERCENTUAL = "PERCENTUAL"


@dataclass(frozen=True)
class MetaReserva:
    """valor em centavos (VALOR) ou em pontos-base (PERCENTUAL) (RN06)."""
    tipo: TipoMeta
    valor: int
    ativa: bool = True
    nome: str = ""
    id: int = 0


@dataclass(frozen=True)
class Categoria:
    id: int
    nome: str
    icone: str


OUTROS = 5
CATEGORIAS_PADRAO = [
    Categoria(1, "Alimentação", "🍽️"),
    Categoria(2, "Transporte", "🚌"),
    Categoria(3, "Lazer", "🎉"),
    Categoria(4, "Saúde", "💊"),
    Categoria(OUTROS, "Outros", "📦"),
]


@dataclass(frozen=True)
class Gasto:
    """Descrição opcional e categoria padrão Outros (CA12)."""
    valor_centavos: int
    data: date
    descricao: str = ""
    categoria_id: int = OUTROS
    id: int = 0


@dataclass(frozen=True)
class Resumo:
    """Totais de um ciclo, em centavos."""
    entradas: int
    fixas: int
    reserva: int
    gastos: int

    @property
    def disponivel(self) -> int:
        """RN07: a reserva sai antes dos gastos e nunca aparece como disponível."""
        return self.entradas - self.fixas - self.reserva - self.gastos

    @property
    def reserva_invadida(self) -> int:
        """RN09: quanto os gastos tiraram da reserva: o quanto o disponível
        ficou negativo, até o total de gastos."""
        return min(self.gastos, max(0, -self.disponivel))

    @property
    def falta_para_metas(self) -> int:
        """RN08: quanto falta para as metas caberem em Entradas − Contas fixas."""
        return max(0, self.reserva - (self.entradas - self.fixas))


@dataclass(frozen=True)
class CicloFechado:
    """Retrato de um ciclo no fechamento (RN05): editar um cadastro depois não
    muda os totais. reserva_invadida é o valor gravado no fechamento."""
    ciclo: Ciclo
    resumo: Resumo
    reserva_invadida: Optional[int] = None
    id: int = 0

    def __post_init__(self):
        if self.reserva_invadida is None:
            object.__setattr__(self, "reserva_invadida", self.resumo.reserva_invadida)


@dataclass(frozen=True)
class Configuracoes:
    """ciclo_irregular guarda o ciclo atual quando uma mudança do dia do
    pagamento o deixou diferente do normal (P14). Percentuais em pontos-base."""
    dia_pagamento: int = 1
    ciclo_irregular: Optional[Ciclo] = None
    limite_semanal_manual: Optional[int] = None
    percentual_atencao: int = 7000
    percentual_critico: int = 9000
    hora_resumo: time = field(default_factory=lambda: time(8, 0))
    primeiro_uso_concluido: bool = False
