"""Textos em português que a interface mostra para as decisões do núcleo (menu e janela usam os mesmos)."""
from __future__ import annotations

from typing import List, Tuple

from .calculadora import Faixa
from .decisoes import Bloqueado, ErroCadastro, PermitidoComAviso, PermitidoComReservaInvadida
from .formatos import formatar_reais

ERROS = {
    ErroCadastro.DESCRICAO_VAZIA: "A descrição não pode ficar vazia.",
    ErroCadastro.VALOR_ZERO_OU_NEGATIVO: "O valor precisa ser maior que zero.",
    ErroCadastro.PERCENTUAL_ACIMA_DE_100: "O percentual não pode passar de 100%.",
    ErroCadastro.DIA_VENCIMENTO_INVALIDO: "O dia do vencimento precisa estar entre 1 e 31.",
    ErroCadastro.DURACAO_INVALIDA: "A duração precisa ser de pelo menos 1 mês.",
    ErroCadastro.PARCELA_INVALIDA: "A parcela atual precisa estar entre 1 e a duração da conta.",
    ErroCadastro.DATA_EM_CICLO_FECHADO: "Essa data é de um ciclo já fechado.",
    ErroCadastro.DATA_FUTURA: "A data não pode ser no futuro.",
    ErroCadastro.FIM_ANTES_DO_INICIO: "O fim não pode ser antes do início.",
    ErroCadastro.METAS_NAO_CABEM: "As metas de reserva não cabem nas entradas menos as contas fixas.",
    ErroCadastro.CONTA_JA_DESCONTADA: "Essa conta já foi descontada em um ciclo: encerre em vez de excluir.",
    ErroCadastro.CONTA_SAIRIA_DO_CICLO: "Essa mudança tiraria a conta do ciclo atual.",
    ErroCadastro.DIA_PAGAMENTO_INVALIDO: "O dia do pagamento precisa estar entre 1 e 31.",
    ErroCadastro.PERCENTUAL_FORA_DA_FAIXA: "Atenção vai de 1% a 99% e crítico de 2% a 100%.",
    ErroCadastro.ATENCAO_NAO_MENOR_QUE_CRITICO: "O percentual de atenção precisa ser menor que o crítico.",
}
FAIXAS = {Faixa.VERDE: "verde", Faixa.AMARELA: "amarela", Faixa.VERMELHA: "vermelha"}


def linhas_da_decisao(decisao, salvo: str) -> Tuple[bool, List[str]]:
    """(salvou?, linhas a mostrar): o motivo do bloqueio, ou a mensagem de sucesso mais os avisos."""
    if isinstance(decisao, Bloqueado):
        texto = ERROS[decisao.erro]
        if decisao.falta_para_metas:
            texto += f" Faltam {formatar_reais(decisao.falta_para_metas)}."
        return False, [texto]
    linhas = [salvo]
    if isinstance(decisao, PermitidoComAviso):
        falta = formatar_reais(decisao.falta_para_metas)
        linhas.append(f"Atenção: as metas de reserva não cabem mais. Faltam {falta}.")
    elif isinstance(decisao, PermitidoComReservaInvadida):
        linhas.append(f"Atenção: este gasto invadiu a reserva em {formatar_reais(decisao.reserva_invadida)}.")
    return True, linhas
