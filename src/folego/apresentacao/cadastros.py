"""Cadastros sem interface: leitura dos campos dos formulários (devolve o item pronto ou o texto do erro)
e o texto das linhas das listas. Nenhum import de GUI; toda regra de negócio continua no núcleo."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from typing import Optional, Tuple, Union

from ..calculadora import ativa_em, parcela_em
from ..decisoes import ErroCadastro, inicio_pela_parcela
from ..formatos import formatar_data, formatar_percentual, formatar_reais, ler_centavos, ler_pontos_base
from ..modelos import ContaFixa, Entrada, MetaReserva, TipoEntrada, TipoMeta
from ..textos import ERROS

MSG_VALOR = "Não entendi o valor. Exemplo: 1.500,00"
MSG_PERCENTUAL = "Não entendi o percentual. Exemplo: 10 ou 10,5"
MSG_VENCIMENTO = "O dia do vencimento precisa ser um número. Exemplo: 5"
MSG_DURACAO = "A duração precisa ser um número de meses, ou ficar vazia (sem fim)."
MSG_PARCELA = "A parcela atual precisa ser um número. Exemplo: 3"

ROTULO_ENTRADA = {TipoEntrada.RECORRENTE: "Recorrente", TipoEntrada.AVULSA: "Avulsa"}
ROTULO_META = {TipoMeta.VALOR: "Valor em reais", TipoMeta.PERCENTUAL: "Percentual das entradas"}


def ler_data(texto: str, hoje: date) -> Optional[date]:
    """dd/mm/aaaa, ou só dd/mm (no ano de hoje); None se não for uma data."""
    texto = texto.strip()
    if texto.count("/") == 1:
        texto += f"/{hoje.year}"
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        return None


def ler_entrada(descricao: str, valor: str, tipo: TipoEntrada, inicio: str, fim: str, hoje: date, ciclo,
                base: Optional[Entrada] = None) -> Union[Entrada, str]:
    """Início vazio = começo do ciclo (recorrente) ou hoje (avulsa). Fim vazio ou 'sem' = sem fim (avulsa não tem)."""
    centavos = ler_centavos(valor)
    if centavos is None:
        return MSG_VALOR
    recorrente = tipo == TipoEntrada.RECORRENTE
    data_inicio = ler_data(inicio, hoje) if inicio.strip() else (ciclo.inicio if recorrente else hoje)
    if data_inicio is None:
        return "Não entendi a data de início. Exemplo: 01/10/2026"
    data_fim = None
    if recorrente and fim.strip().lower() not in ("", "sem"):
        data_fim = ler_data(fim, hoje)
        if data_fim is None:
            return "Não entendi a data de fim. Exemplo: 31/12/2026"
    return replace(base or Entrada(0, tipo, data_inicio), valor_centavos=centavos, tipo=tipo,
                   data_inicio=data_inicio, data_fim=data_fim, descricao=descricao.strip())


def ler_conta(descricao: str, valor: str, vencimento: str, duracao: str, parcela: str, ciclo,
              base: Optional[ContaFixa] = None) -> Union[ContaFixa, str]:
    """Duração vazia ou 'sem' = sem fim. A parcela atual só vale para conta nova com duração (vazia = 1)."""
    centavos = ler_centavos(valor)
    if centavos is None:
        return MSG_VALOR
    try:
        dia = int(vencimento)
    except ValueError:
        return MSG_VENCIMENTO
    meses = None
    if duracao.strip().lower() not in ("", "sem"):
        try:
            meses = int(duracao)
        except ValueError:
            return MSG_DURACAO
        if meses < 1:
            return ERROS[ErroCadastro.DURACAO_INVALIDA]
    inicio = base.ciclo_inicio if base else ciclo.inicio
    if base is None and meses is not None:
        try:
            numero = int(parcela) if parcela.strip() else 1
        except ValueError:
            return MSG_PARCELA
        if not 1 <= numero <= meses:
            return ERROS[ErroCadastro.PARCELA_INVALIDA]
        inicio = inicio_pela_parcela(ciclo, numero)
    return replace(base or ContaFixa(0, inicio), valor_centavos=centavos, ciclo_inicio=inicio, duracao_meses=meses,
                   descricao=descricao.strip(), dia_vencimento=dia)


def ler_meta(nome: str, tipo: TipoMeta, valor: str, base: Optional[MetaReserva] = None) -> Union[MetaReserva, str]:
    """Valor em reais (VALOR) ou percentual em pontos-base (PERCENTUAL)."""
    numero = ler_centavos(valor) if tipo == TipoMeta.VALOR else ler_pontos_base(valor)
    if numero is None:
        return MSG_VALOR if tipo == TipoMeta.VALOR else MSG_PERCENTUAL
    return replace(base or MetaReserva(tipo, numero), tipo=tipo, valor=numero, nome=nome.strip())


def situacao_conta(conta: ContaFixa, ciclo) -> str:
    """Mesmo texto do menu: 'parcela 2 de 3', 'sem fim' ou 'fora do ciclo atual', mais 'encerrada em ...'."""
    if not ativa_em(conta, ciclo):
        situacao = "fora do ciclo atual"
    elif conta.duracao_meses is None:
        situacao = "sem fim"
    else:
        situacao = f"parcela {parcela_em(conta, ciclo)} de {conta.duracao_meses}"
    if conta.encerrada_em:
        situacao += f", encerrada em {formatar_data(conta.encerrada_em)}"
    return situacao


def linha_entrada(e: Entrada) -> Tuple[str, str, str, str, str]:
    """Descrição, valor, tipo, início e fim."""
    tipo = "recorrente" if e.tipo == TipoEntrada.RECORRENTE else "avulsa"
    fim = formatar_data(e.data_fim) if e.data_fim else ("sem fim" if e.tipo == TipoEntrada.RECORRENTE else "")
    return e.descricao, formatar_reais(e.valor_centavos), tipo, formatar_data(e.data_inicio), fim


def linha_conta(c: ContaFixa, ciclo) -> Tuple[str, str, str, str]:
    """Descrição, valor, vencimento e situação."""
    return (c.descricao, formatar_reais(c.valor_centavos), f"dia {c.dia_vencimento}", situacao_conta(c, ciclo))


def linha_meta(m: MetaReserva) -> Tuple[str, str, str]:
    """Nome, valor ou percentual e situação."""
    valor = formatar_reais(m.valor) if m.tipo == TipoMeta.VALOR else formatar_percentual(m.valor)
    return m.nome, valor, "ativa" if m.ativa else "pausada"
