"""Decisões de cadastro: o que pode ser salvo, bloqueado ou salvo com aviso.
A tela só aplica a decisão (RN04 a RN09, RN14, RN15)."""
from __future__ import annotations

import enum
from dataclasses import dataclass, replace
from datetime import date
from typing import Optional

from .calculadora import Orcamento, ativa_em, menos_meses
from .modelos import (
    Ciclo, Configuracoes, ContaFixa, Entrada, Gasto, MetaReserva,
    TipoEntrada, TipoMeta,
)


class ErroGasto(enum.Enum):
    VALOR_ZERO_OU_NEGATIVO = "VALOR_ZERO_OU_NEGATIVO"
    DATA_EM_CICLO_FECHADO = "DATA_EM_CICLO_FECHADO"
    DATA_FUTURA = "DATA_FUTURA"


class ErroCadastro(enum.Enum):
    DESCRICAO_VAZIA = "DESCRICAO_VAZIA"
    VALOR_ZERO_OU_NEGATIVO = "VALOR_ZERO_OU_NEGATIVO"
    PERCENTUAL_ACIMA_DE_100 = "PERCENTUAL_ACIMA_DE_100"
    DIA_VENCIMENTO_INVALIDO = "DIA_VENCIMENTO_INVALIDO"
    DURACAO_INVALIDA = "DURACAO_INVALIDA"
    PARCELA_INVALIDA = "PARCELA_INVALIDA"
    DATA_EM_CICLO_FECHADO = "DATA_EM_CICLO_FECHADO"
    DATA_FUTURA = "DATA_FUTURA"
    FIM_ANTES_DO_INICIO = "FIM_ANTES_DO_INICIO"
    METAS_NAO_CABEM = "METAS_NAO_CABEM"
    CONTA_JA_DESCONTADA = "CONTA_JA_DESCONTADA"
    CONTA_SAIRIA_DO_CICLO = "CONTA_SAIRIA_DO_CICLO"
    DIA_PAGAMENTO_INVALIDO = "DIA_PAGAMENTO_INVALIDO"
    PERCENTUAL_FORA_DA_FAIXA = "PERCENTUAL_FORA_DA_FAIXA"
    ATENCAO_NAO_MENOR_QUE_CRITICO = "ATENCAO_NAO_MENOR_QUE_CRITICO"


@dataclass(frozen=True)
class Permitido:
    pass


@dataclass(frozen=True)
class PermitidoComAviso:
    """RN08: salva, mas avisa quanto falta para as metas caberem."""
    falta_para_metas: int


@dataclass(frozen=True)
class PermitidoComReservaInvadida:
    """RN09: o gasto é salvo, mas a reserva do ciclo fica invadida."""
    reserva_invadida: int


@dataclass(frozen=True)
class Bloqueado:
    """falta_para_metas só é preenchido no erro METAS_NAO_CABEM (RN08)."""
    erro: ErroCadastro
    falta_para_metas: int = 0


PERMITIDO = Permitido()


def valor_valido(valor: int) -> bool:
    """RN15: valor zero ou negativo é bloqueado em qualquer cadastro."""
    return valor > 0


def validar_gasto(gasto: Gasto, ciclo_atual: Ciclo, hoje: date) -> Optional[ErroGasto]:
    """RN14 e RN15: o motivo do bloqueio, ou None quando o gasto pode ser salvo."""
    if not valor_valido(gasto.valor_centavos):
        return ErroGasto.VALOR_ZERO_OU_NEGATIVO
    if gasto.data < ciclo_atual.inicio:
        return ErroGasto.DATA_EM_CICLO_FECHADO
    if gasto.data > hoje:
        return ErroGasto.DATA_FUTURA
    return None


def _com_item(itens: list, item) -> list:
    """Troca o item de mesmo id, ou acrescenta quando ele é novo (id 0)."""
    if item.id != 0:
        itens = [i for i in itens if i.id != item.id]
    return [*itens, item]


def _aviso_de_metas(depois: Orcamento, ciclo: Ciclo):
    """RN08: avisa se as metas deixaram de caber. Sem meta ativa, não avisa."""
    if not any(m.ativa for m in depois.metas):
        return PERMITIDO
    falta = depois.resumo(ciclo).falta_para_metas
    return PermitidoComAviso(falta) if falta > 0 else PERMITIDO


def inicio_pela_parcela(ciclo_atual: Ciclo, parcela: int) -> date:
    """Primeiro dia do ciclo em que começa uma conta que está na parcela."""
    return menos_meses(ciclo_atual.inicio, parcela - 1)


def decidir_conta(conta: ContaFixa, orcamento: Orcamento, ciclo_atual: Ciclo):
    """RN15, RN03 e RN08 para salvar uma conta fixa."""
    duracao = conta.duracao_meses
    erro = None
    if not conta.descricao.strip():
        erro = ErroCadastro.DESCRICAO_VAZIA
    elif not valor_valido(conta.valor_centavos):
        erro = ErroCadastro.VALOR_ZERO_OU_NEGATIVO
    elif not 1 <= conta.dia_vencimento <= 31:
        erro = ErroCadastro.DIA_VENCIMENTO_INVALIDO
    elif duracao is not None and duracao < 1:
        erro = ErroCadastro.DURACAO_INVALIDA
    # RN04 e P17 também ao editar: diminuir a duração não pode tirar a conta do ciclo atual
    elif (any(c.id == conta.id and c.id != 0 and ativa_em(c, ciclo_atual) for c in orcamento.contas)
          and not ativa_em(conta, ciclo_atual)):
        erro = ErroCadastro.CONTA_SAIRIA_DO_CICLO
    # conta nova: a parcela do ciclo atual vai de 1 até a duração
    elif (conta.id == 0 and duracao is not None
          and not inicio_pela_parcela(ciclo_atual, duracao) <= conta.ciclo_inicio <= ciclo_atual.inicio):
        erro = ErroCadastro.PARCELA_INVALIDA
    if erro:
        return Bloqueado(erro)
    novo = replace(orcamento, contas=_com_item(orcamento.contas, conta))
    return _aviso_de_metas(novo, ciclo_atual)


def decidir_entrada(entrada: Entrada, orcamento: Orcamento, ciclo_atual: Ciclo, hoje: date):
    """RN15, data da avulsa como nos gastos (RN14) e aviso da RN08."""
    fim = entrada.data_fim
    avulsa = entrada.tipo == TipoEntrada.AVULSA
    erro = None
    if not entrada.descricao.strip():
        erro = ErroCadastro.DESCRICAO_VAZIA
    elif not valor_valido(entrada.valor_centavos):
        erro = ErroCadastro.VALOR_ZERO_OU_NEGATIVO
    elif avulsa and entrada.data_inicio < ciclo_atual.inicio:
        erro = ErroCadastro.DATA_EM_CICLO_FECHADO
    elif avulsa and entrada.data_inicio > hoje:
        erro = ErroCadastro.DATA_FUTURA
    elif fim is not None and fim < entrada.data_inicio:
        erro = ErroCadastro.FIM_ANTES_DO_INICIO
    if erro:
        return Bloqueado(erro)
    novo = replace(orcamento, entradas=_com_item(orcamento.entradas, entrada))
    return _aviso_de_metas(novo, ciclo_atual)


def decidir_meta(meta: MetaReserva, orcamento: Orcamento, ciclo_atual: Ciclo):
    """RN15 e RN08: se as metas ativas não cabem, bloqueia e diz quanto falta."""
    erro = None
    if not meta.nome.strip():
        erro = ErroCadastro.DESCRICAO_VAZIA
    elif not valor_valido(meta.valor):
        erro = ErroCadastro.VALOR_ZERO_OU_NEGATIVO
    elif meta.tipo == TipoMeta.PERCENTUAL and meta.valor > 10_000:
        erro = ErroCadastro.PERCENTUAL_ACIMA_DE_100
    if erro:
        return Bloqueado(erro)
    # Uma meta pausada não entra na soma, então pausar sempre é permitido
    if not meta.ativa:
        return PERMITIDO
    novo = replace(orcamento, metas=_com_item(orcamento.metas, meta))
    falta = novo.resumo(ciclo_atual).falta_para_metas
    return Bloqueado(ErroCadastro.METAS_NAO_CABEM, falta) if falta > 0 else PERMITIDO


def decidir_exclusao_conta(conta: ContaFixa, ciclo_atual: Ciclo):
    """RN04 e P17: só exclui conta que ainda não foi descontada."""
    if conta.ciclo_inicio >= ciclo_atual.inicio:
        return PERMITIDO
    return Bloqueado(ErroCadastro.CONTA_JA_DESCONTADA)


def decidir_gasto(gasto: Gasto, orcamento: Orcamento, ciclo_atual: Ciclo, hoje: date):
    """RN14, RN15 e RN09 para salvar um gasto, novo ou editado. Um gasto de
    ciclo fechado não pode ser mudado. Se a reserva fica invadida, salva e avisa."""
    original = next(
        (g for g in orcamento.gastos if gasto.id != 0 and g.id == gasto.id), None
    )
    if original is not None and original.data < ciclo_atual.inicio:
        return Bloqueado(ErroCadastro.DATA_EM_CICLO_FECHADO)
    erro = validar_gasto(gasto, ciclo_atual, hoje)
    if erro is not None:
        return Bloqueado(ErroCadastro[erro.name])
    novo = replace(orcamento, gastos=_com_item(orcamento.gastos, gasto))
    invadida = novo.resumo(ciclo_atual).reserva_invadida
    return PermitidoComReservaInvadida(invadida) if invadida > 0 else PERMITIDO


def decidir_exclusao_gasto(gasto: Gasto, ciclo_atual: Ciclo):
    """Um gasto de ciclo fechado não pode ser excluído (RN05)."""
    if gasto.data < ciclo_atual.inicio:
        return Bloqueado(ErroCadastro.DATA_EM_CICLO_FECHADO)
    return PERMITIDO


def decidir_exclusao_entrada(entrada: Entrada, ciclo_atual: Ciclo):
    """P18: uma avulsa de ciclo fechado é só para consulta."""
    if entrada.tipo == TipoEntrada.AVULSA and entrada.data_inicio < ciclo_atual.inicio:
        return Bloqueado(ErroCadastro.DATA_EM_CICLO_FECHADO)
    return PERMITIDO


def decidir_configuracoes(config: Configuracoes):
    """Dia de 1 a 31, limite manual positivo ou vazio (RN15), atenção de 1% a
    99%, crítico de 2% a 100% e atenção menor que crítico."""
    limite = config.limite_semanal_manual
    erro = None
    if not 1 <= config.dia_pagamento <= 31:
        erro = ErroCadastro.DIA_PAGAMENTO_INVALIDO
    elif limite is not None and not valor_valido(limite):
        erro = ErroCadastro.VALOR_ZERO_OU_NEGATIVO
    elif (not 100 <= config.percentual_atencao <= 9_900
          or not 200 <= config.percentual_critico <= 10_000):
        erro = ErroCadastro.PERCENTUAL_FORA_DA_FAIXA
    elif config.percentual_atencao >= config.percentual_critico:
        erro = ErroCadastro.ATENCAO_NAO_MENOR_QUE_CRITICO
    return Bloqueado(erro) if erro else PERMITIDO


def mostrar_primeiro_uso(config: Configuracoes, orcamento: Orcamento) -> bool:
    """O assistente aparece até ser concluído; quem já tem entradas não o vê."""
    return not config.primeiro_uso_concluido and not orcamento.entradas
