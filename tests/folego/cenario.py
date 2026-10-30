"""Cenário base dos critérios de aceite do briefing. Valores em centavos."""
from datetime import date

from src.folego.calculadora import Orcamento
from src.folego.modelos import ContaFixa, Entrada, MetaReserva, TipoEntrada, TipoMeta


def data(dia: int, mes: int, ano: int = 2026) -> date:
    """Data na ordem do briefing: dia, mês e ano (padrão: 2026)."""
    return date(ano, mes, dia)


DIA_PAGAMENTO = 1

# Salário recorrente de R$ 3.000,00
salario = Entrada(300_000, TipoEntrada.RECORRENTE, data_inicio=data(1, 10))
# Aluguel de R$ 1.000,00, sem fim
aluguel = ContaFixa(100_000, ciclo_inicio=data(1, 10))
# Celular de R$ 200,00 por 3 meses a partir do ciclo de outubro/2026
celular = ContaFixa(20_000, ciclo_inicio=data(1, 10), duracao_meses=3)
# Reserva de 10% das entradas
reserva = MetaReserva(TipoMeta.PERCENTUAL, 1000)

orcamento = Orcamento(entradas=[salario], contas=[aluguel, celular], metas=[reserva])
