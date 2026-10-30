"""Valores no formato brasileiro, sem float: dinheiro em centavos e
percentuais em pontos-base."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

_FORMATO_REAIS = re.compile(r"\d{1,3}(\.\d{3}){0,4}(,\d{1,2})?|\d{1,13}(,\d{1,2})?", re.ASCII)
# Ponto seguido de 1 ou 2 dígitos no fim é centavo ("1500.50"); com 3 é milhar ("1.500")
_CENTAVOS_COM_PONTO = re.compile(r"\d{1,13}\.\d{1,2}", re.ASCII)
_FORMATO_PERCENTUAL = re.compile(r"\d{1,3}(,\d{1,2})?", re.ASCII)


def formatar_reais(centavos: int) -> str:
    """150000 vira "R$ 1.500,00"; -10000 vira "-R$ 100,00"."""
    sinal = "-" if centavos < 0 else ""
    reais, cents = divmod(abs(centavos), 100)
    return f"{sinal}R$ {reais:,}".replace(",", ".") + f",{cents:02d}"


def _partes_para_inteiro(limpo: str) -> int:
    partes = limpo.split(",")
    fracao = partes[1] if len(partes) > 1 else ""
    return int(partes[0]) * 100 + int(fracao.ljust(2, "0"))


def ler_centavos(texto: str) -> Optional[int]:
    """Lê "1.500,00", "1500", "1500,5", "1500.50" ou "R$ 0,01" em centavos;
    None quando o texto não é um valor."""
    limpo = texto.replace("R$", "").strip()
    if _CENTAVOS_COM_PONTO.fullmatch(limpo):
        limpo = limpo.replace(".", ",")
    if not _FORMATO_REAIS.fullmatch(limpo):
        return None
    return _partes_para_inteiro(limpo.replace(".", ""))


def formatar_percentual(pontos_base: int) -> str:
    """1000 vira "10%"; 1050 vira "10,5%"; 1025 vira "10,25%"."""
    inteiro, resto = divmod(pontos_base, 100)
    fracao = f"{resto:02d}".rstrip("0")
    return f"{inteiro},{fracao}%" if fracao else f"{inteiro}%"


def ler_pontos_base(texto: str) -> Optional[int]:
    """Lê "10", "10,5", "10.5" ou "10,25%" em pontos-base; None se inválido."""
    limpo = texto.replace("%", "").strip().replace(".", ",")
    if not _FORMATO_PERCENTUAL.fullmatch(limpo):
        return None
    return _partes_para_inteiro(limpo)


def formatar_data(data: date) -> str:
    """2026-10-06 vira "06/10/2026"."""
    return f"{data.day:02d}/{data.month:02d}/{data.year:04d}"


def formatar_dia_mes(data: date) -> str:
    """2026-10-06 vira "06/10"."""
    return f"{data.day:02d}/{data.month:02d}"
