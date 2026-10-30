"""Repositórios em memória para os testes dos serviços, com o mesmo
comportamento dos de verdade."""
from dataclasses import replace
from datetime import datetime

from src.folego.calculadora import Orcamento
from src.folego.modelos import CATEGORIAS_PADRAO, Configuracoes
from src.folego.servicos import Alertas, Cadastros


class OrcamentoEmMemoria:
    def __init__(self, inicial=None):
        self.dados = inicial or Orcamento()
        self._ultimo_id = 100

    def _salvo(self, campo, item):
        """Troca o item de mesmo id ou acrescenta com um id novo, como o banco."""
        novo_id = item.id
        if novo_id == 0:
            self._ultimo_id += 1
            novo_id = self._ultimo_id
        lista = [i for i in getattr(self.dados, campo) if i.id != novo_id]
        self.dados = replace(self.dados, **{campo: [*lista, replace(item, id=novo_id)]})
        return novo_id

    def _excluido(self, campo, item):
        lista = [i for i in getattr(self.dados, campo) if i.id != item.id]
        self.dados = replace(self.dados, **{campo: lista})

    def orcamento(self):
        return self.dados

    def categorias(self):
        return list(CATEGORIAS_PADRAO)

    def salvar_entrada(self, entrada):
        return self._salvo("entradas", entrada)

    def salvar_conta(self, conta):
        return self._salvo("contas", conta)

    def salvar_meta(self, meta):
        return self._salvo("metas", meta)

    def salvar_gasto(self, gasto):
        return self._salvo("gastos", gasto)

    def excluir_entrada(self, entrada):
        self._excluido("entradas", entrada)

    def excluir_conta(self, conta):
        self._excluido("contas", conta)

    def excluir_meta(self, meta):
        self._excluido("metas", meta)

    def excluir_gasto(self, gasto):
        self._excluido("gastos", gasto)


class ConfiguracoesEmMemoria:
    def __init__(self, inicial=None):
        self.dados = inicial or Configuracoes()

    def configuracoes(self):
        return self.dados

    def atualizar(self, mudanca):
        self.dados = mudanca(self.dados)


class HistoricoEmMemoria:
    """Como o banco: um ciclo só é fechado uma vez, e um alerta só é registrado uma vez por período."""

    def __init__(self):
        self.fechados = []
        self.alertas = set()

    def ciclos_fechados(self):
        return list(self.fechados)

    def salvar_ciclo_fechado(self, ciclo_fechado):
        if any(f.ciclo.inicio == ciclo_fechado.ciclo.inicio for f in self.fechados):
            return -1
        self.fechados.append(ciclo_fechado)
        return len(self.fechados)

    def registrar_alerta(self, codigo: str, periodo_ref: str, disparado_em: datetime) -> bool:
        if (codigo, periodo_ref) in self.alertas:
            return False
        self.alertas.add((codigo, periodo_ref))
        return True


class NotificadorDeTeste:
    """Guarda os avisos que chegariam ao usuário."""

    def __init__(self):
        self.avisos = []

    def avisar(self, alerta):
        self.avisos.append(alerta)


class AgendadorDeTeste:
    def __init__(self):
        self.horarios = []

    def reagendar(self, horario):
        self.horarios.append(horario)


class Ambiente:
    """Tudo o que os casos de uso precisam, em memória."""

    def __init__(self, orcamento=None, configuracoes=None):
        self.orcamento = OrcamentoEmMemoria(orcamento)
        self.configuracoes = ConfiguracoesEmMemoria(configuracoes)
        self.historico = HistoricoEmMemoria()
        self.notificador = NotificadorDeTeste()
        self.alertas = Alertas(self.orcamento, self.configuracoes, self.historico, self.notificador)
        self.cadastros = Cadastros(self.orcamento, self.configuracoes, self.alertas)
