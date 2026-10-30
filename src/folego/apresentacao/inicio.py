"""Textos, cores e avisos da tela Início, prontos e sem GUI (para testar)."""
from typing import List

from ..calculadora import Faixa, Painel
from ..formatos import formatar_data, formatar_dia_mes, formatar_percentual, formatar_reais

CORES = {Faixa.VERDE: "#2e9e4f", Faixa.AMARELA: "#e0a800", Faixa.VERMELHA: "#d32f2f"}


def textos_do_inicio(painel: Painel, ciclo) -> dict:
    """Todos os textos da tela, prontos (sem tela, para testar)."""
    resumo = painel.resumo_do_ciclo
    return {
        "titulo": f"Ciclo: {formatar_data(ciclo.inicio)} a {formatar_data(ciclo.fim)}",
        "semana": f"Semana de {formatar_dia_mes(painel.semana.inicio)} a {formatar_dia_mes(painel.semana.fim)}",
        "disponivel_semana": formatar_reais(painel.disponivel_da_semana),
        "limite": formatar_reais(painel.semana.valor_centavos),
        "disponivel_ciclo": formatar_reais(resumo.disponivel),
        "reserva": formatar_reais(resumo.reserva),
        "consumo": f"{formatar_percentual(painel.consumo_pontos_base)} do limite consumido",
    }


def avisos_do_inicio(painel: Painel) -> List[str]:
    resumo = painel.resumo_do_ciclo
    avisos = []
    if painel.semana.ritmo_nao_fecha_ciclo:
        avisos.append("Nesse ritmo o limite manual não fecha o ciclo.")
    if resumo.reserva_invadida:
        avisos.append(f"Reserva invadida em {formatar_reais(resumo.reserva_invadida)}.")
    if resumo.falta_para_metas:
        avisos.append(f"As metas não cabem: faltam {formatar_reais(resumo.falta_para_metas)}.")
    return avisos
