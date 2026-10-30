"""Armazenamento em disco: um único RepositorioJson implementa os três
repositórios de servicos.py, com um arquivo JSON por assunto dentro de uma pasta:

    orcamento.json       entradas, contas, metas e gastos (e o último id usado)
    historico.json       ciclos fechados e alertas já disparados (e o último id usado)
    configuracoes.json   as configurações

Dinheiro em centavos (int), datas em ISO (2026-10-05), horas em HH:MM e enums
pelo nome. Cada operação lê o arquivo e grava de volta inteiro, num arquivo
temporário trocado com os.replace: uma queda no meio da gravação não estraga
os dados. Um arquivo ilegível nunca é sobrescrito: levanta ArmazenamentoCorrompido.

shortcut: sem trava entre processos, vale um app aberto por pasta; upgrade: trava de arquivo ou SQLite.
"""
from __future__ import annotations

import enum
import json
import os
import tempfile
from dataclasses import dataclass, field, fields, is_dataclass, replace
from datetime import date, datetime, time
from pathlib import Path
from typing import Callable, List, Union, get_args, get_origin, get_type_hints

from .calculadora import Orcamento
from .modelos import (
    CATEGORIAS_PADRAO, Categoria, CicloFechado, Configuracoes, ContaFixa, Entrada, Gasto, MetaReserva,
)

ORCAMENTO = "orcamento.json"
HISTORICO = "historico.json"
CONFIGURACOES = "configuracoes.json"


class ArmazenamentoCorrompido(Exception):
    """Arquivo de dados existe mas não pode ser lido. Ele fica como está."""


@dataclass(frozen=True)
class _Alerta:
    codigo: str
    periodo_ref: str
    disparado_em: datetime


@dataclass(frozen=True)
class _ArquivoOrcamento:
    ultimo_id: int = 0  # nunca volta atrás, nem depois de excluir
    orcamento: Orcamento = field(default_factory=Orcamento)


@dataclass(frozen=True)
class _ArquivoHistorico:
    ultimo_id: int = 0
    ciclos_fechados: List[CicloFechado] = field(default_factory=list)
    alertas: List[_Alerta] = field(default_factory=list)


def _codificar(valor):
    if isinstance(valor, (date, datetime)):  # datetime é um date
        return valor.isoformat()
    if isinstance(valor, time):
        return valor.strftime("%H:%M")
    if isinstance(valor, enum.Enum):
        return valor.name
    if is_dataclass(valor):
        return {f.name: _codificar(getattr(valor, f.name)) for f in fields(valor)}
    if isinstance(valor, list):
        return [_codificar(i) for i in valor]
    return valor


def _decodificar(tipo, valor):
    """Monta o objeto de tipo a partir do JSON; qualquer valor fora do tipo levanta erro."""
    origem = get_origin(tipo)
    if origem is Union:  # Optional[X]
        interno = next(t for t in get_args(tipo) if t is not type(None))
        return None if valor is None else _decodificar(interno, valor)
    if origem is list:
        if not isinstance(valor, list):
            raise TypeError("esperava uma lista")
        return [_decodificar(get_args(tipo)[0], i) for i in valor]
    if tipo in (int, str, bool):
        if type(valor) is not tipo:  # recusa float no lugar de centavos, e bool no lugar de int
            raise TypeError(f"esperava {tipo.__name__}, veio {valor!r}")
        return valor
    if tipo is datetime:
        return datetime.fromisoformat(valor)
    if tipo is date:
        return date.fromisoformat(valor)
    if tipo is time:
        return datetime.strptime(valor, "%H:%M").time()
    if issubclass(tipo, enum.Enum):
        return tipo[valor]
    if not isinstance(valor, dict):
        raise TypeError("esperava um objeto")
    dicas = get_type_hints(tipo)
    return tipo(**{f.name: _decodificar(dicas[f.name], valor[f.name]) for f in fields(tipo) if f.name in valor})


class RepositorioJson:
    """OrcamentoRepositorio, HistoricoRepositorio e ConfiguracoesRepositorio num só objeto."""

    def __init__(self, pasta: Path):
        self._pasta = Path(pasta)
        self._pasta.mkdir(parents=True, exist_ok=True)
        # Um arquivo estragado aparece já na abertura, não no meio do uso
        for nome, tipo in ((ORCAMENTO, _ArquivoOrcamento), (HISTORICO, _ArquivoHistorico),
                           (CONFIGURACOES, Configuracoes)):
            self._ler(nome, tipo)

    # --- arquivos ----------------------------------------------------------

    def _ler(self, nome: str, tipo):
        """Lê o arquivo; se ele ainda não existe (primeira execução), devolve tipo() com os padrões."""
        caminho = self._pasta / nome
        try:
            with open(caminho, encoding="utf-8") as arquivo:
                return _decodificar(tipo, json.load(arquivo))
        except FileNotFoundError:
            return tipo()
        except (OSError, ValueError, KeyError, TypeError) as erro:
            raise ArmazenamentoCorrompido(
                f"Não consegui ler {caminho} ({erro!r}). O arquivo não foi alterado: "
                "corrija-o ou mova-o para outro lugar e abra o app de novo."
            ) from erro

    def _gravar(self, nome: str, dados) -> None:
        descritor, temporario = tempfile.mkstemp(dir=self._pasta, prefix=nome, suffix=".tmp")
        try:
            with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
                json.dump(_codificar(dados), arquivo, ensure_ascii=False, indent=2)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, self._pasta / nome)
        except BaseException:
            os.unlink(temporario)
            raise

    # --- OrcamentoRepositorio ----------------------------------------------

    def orcamento(self) -> Orcamento:
        return self._ler(ORCAMENTO, _ArquivoOrcamento).orcamento

    def categorias(self) -> List[Categoria]:
        return list(CATEGORIAS_PADRAO)

    def _salvo(self, campo: str, item) -> int:
        """Troca o item de mesmo id ou acrescenta com um id novo, como o banco."""
        arquivo = self._ler(ORCAMENTO, _ArquivoOrcamento)
        novo_id = item.id or arquivo.ultimo_id + 1
        lista = [i for i in getattr(arquivo.orcamento, campo) if i.id != novo_id]
        orcamento = replace(arquivo.orcamento, **{campo: [*lista, replace(item, id=novo_id)]})
        self._gravar(ORCAMENTO, _ArquivoOrcamento(max(arquivo.ultimo_id, novo_id), orcamento))
        return novo_id

    def _excluido(self, campo: str, item) -> None:
        arquivo = self._ler(ORCAMENTO, _ArquivoOrcamento)
        lista = [i for i in getattr(arquivo.orcamento, campo) if i.id != item.id]
        self._gravar(ORCAMENTO, replace(arquivo, orcamento=replace(arquivo.orcamento, **{campo: lista})))

    def salvar_entrada(self, entrada: Entrada) -> int:
        return self._salvo("entradas", entrada)

    def salvar_conta(self, conta: ContaFixa) -> int:
        return self._salvo("contas", conta)

    def salvar_meta(self, meta: MetaReserva) -> int:
        return self._salvo("metas", meta)

    def salvar_gasto(self, gasto: Gasto) -> int:
        return self._salvo("gastos", gasto)

    def excluir_entrada(self, entrada: Entrada) -> None:
        self._excluido("entradas", entrada)

    def excluir_conta(self, conta: ContaFixa) -> None:
        self._excluido("contas", conta)

    def excluir_meta(self, meta: MetaReserva) -> None:
        self._excluido("metas", meta)

    def excluir_gasto(self, gasto: Gasto) -> None:
        self._excluido("gastos", gasto)

    # --- HistoricoRepositorio ----------------------------------------------

    def ciclos_fechados(self) -> List[CicloFechado]:
        return self._ler(HISTORICO, _ArquivoHistorico).ciclos_fechados

    def salvar_ciclo_fechado(self, ciclo_fechado: CicloFechado) -> int:
        arquivo = self._ler(HISTORICO, _ArquivoHistorico)
        if any(f.ciclo.inicio == ciclo_fechado.ciclo.inicio for f in arquivo.ciclos_fechados):
            return -1
        novo_id = arquivo.ultimo_id + 1
        self._gravar(HISTORICO, replace(
            arquivo, ultimo_id=novo_id,
            ciclos_fechados=[*arquivo.ciclos_fechados, replace(ciclo_fechado, id=novo_id)]))
        return novo_id

    def registrar_alerta(self, codigo: str, periodo_ref: str, disparado_em: datetime) -> bool:
        arquivo = self._ler(HISTORICO, _ArquivoHistorico)
        if any(a.codigo == codigo and a.periodo_ref == periodo_ref for a in arquivo.alertas):
            return False
        self._gravar(HISTORICO, replace(
            arquivo, alertas=[*arquivo.alertas, _Alerta(codigo, periodo_ref, disparado_em)]))
        return True

    # --- ConfiguracoesRepositorio ------------------------------------------

    def configuracoes(self) -> Configuracoes:
        return self._ler(CONFIGURACOES, Configuracoes)

    def atualizar(self, mudanca: Callable[[Configuracoes], Configuracoes]) -> None:
        self._gravar(CONFIGURACOES, mudanca(self.configuracoes()))
