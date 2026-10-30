"""Funções puras da tela de gasto (sem GUI): leitura do formulário."""
from __future__ import annotations

from datetime import date
from typing import List, Optional, Union

from ..formatos import ler_centavos
from ..modelos import Categoria, Gasto


def _ler_data(texto: str, hoje: date) -> Optional[date]:
    """Lê dd/mm/aaaa ou dd/mm (ano de hoje); None se não for uma data."""
    partes = texto.strip().split("/")
    if len(partes) not in (2, 3) or not all(p.isdigit() for p in partes):
        return None
    try:
        ano = int(partes[2]) if len(partes) == 3 else hoje.year
        return date(ano, int(partes[1]), int(partes[0]))
    except ValueError:
        return None


def ler_formulario(valor: str, data: str, descricao: str, categoria: str, hoje: date,
                   categorias: List[Categoria]) -> Union[Gasto, str]:
    """Converte o que foi digitado em Gasto, ou devolve a mensagem de erro."""
    centavos = ler_centavos(valor)
    if centavos is None:
        return "Não entendi o valor. Exemplo: 1.500,00 ou 150,50"
    dia = _ler_data(data, hoje) if data.strip() else hoje
    if dia is None:
        return "Não entendi a data. Use dd/mm/aaaa ou dd/mm."
    ids = {c.nome: c.id for c in categorias}
    if categoria not in ids:
        return "Escolha uma categoria da lista."
    return Gasto(centavos, dia, descricao.strip(), ids[categoria])
