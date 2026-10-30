"""Funções puras da tela de Configurações (sem GUI): ler o formulário e formatar os campos."""
from __future__ import annotations

from dataclasses import replace
from typing import Tuple, Union

from ..formatos import formatar_percentual, formatar_reais, ler_centavos, ler_pontos_base
from ..modelos import Configuracoes


def ler_formulario(dia: str, limite: str, atencao: str, critico: str,
                   atual: Configuracoes) -> Union[Configuracoes, str]:
    """Converte os textos do formulário; devolve as novas configurações ou a mensagem de erro.
    Só lê: quem decide se pode salvar (faixas, atenção < crítico) é o núcleo."""
    try:
        novo_dia = int(dia.strip())
    except ValueError:
        return "Dia do pagamento: use um número de 1 a 31."
    if not 1 <= novo_dia <= 31:
        return "Dia do pagamento: use um número de 1 a 31."
    novo_limite = None
    if limite.strip():
        novo_limite = ler_centavos(limite)
        if novo_limite is None:
            return "Limite semanal: não entendi o valor. Exemplo: 350,00 (vazio = automático)."
    nova_atencao, novo_critico = ler_pontos_base(atencao), ler_pontos_base(critico)
    if nova_atencao is None or novo_critico is None:
        return "Percentuais: não entendi. Exemplo: 70 ou 87,5."
    return replace(atual, dia_pagamento=novo_dia, limite_semanal_manual=novo_limite,
                   percentual_atencao=nova_atencao, percentual_critico=novo_critico)


def textos_do_formulario(c: Configuracoes) -> Tuple[str, str, str, str]:
    """Textos dos 4 campos (dia, limite, atenção, crítico) para as configurações gravadas."""
    limite = "" if c.limite_semanal_manual is None else formatar_reais(c.limite_semanal_manual).replace("R$ ", "")
    return (str(c.dia_pagamento), limite,
            formatar_percentual(c.percentual_atencao).rstrip("%"),
            formatar_percentual(c.percentual_critico).rstrip("%"))
