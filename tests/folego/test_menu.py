"""Menu do terminal, com entrada simulada e repositórios em memória."""
from datetime import datetime

from src.folego.calculadora import Orcamento
from src.folego.menu import executar
from src.folego.modelos import Configuracoes, ContaFixa, TipoEntrada
from . import cenario
from .cenario import data
from .fakes import Ambiente


class RepoUnico:
    """Junta os três repositórios do Ambiente em um objeto só, como o repositório em disco."""

    def __init__(self, ambiente):
        self._partes = [ambiente.orcamento, ambiente.historico, ambiente.configuracoes]

    def __getattr__(self, nome):
        for parte in self._partes:
            if hasattr(parte, nome):
                return getattr(parte, nome)
        raise AttributeError(nome)


def rodar(linhas, orcamento=cenario.orcamento, config=None, hoje=data(5, 10)):
    """Roda o menu com as linhas digitadas e devolve (ambiente, texto da saída)."""
    ambiente = Ambiente(orcamento, config or Configuracoes(primeiro_uso_concluido=True))
    fila = iter(linhas)
    saida = []
    executar(RepoUnico(ambiente), entrada=lambda _: next(fila), saida=saida.append,
             hoje=hoje, agora=datetime(2026, 10, 5, 9, 0))
    return ambiente, "\n".join(saida)


def test_sair_com_0_encerra_o_menu():
    _, texto = rodar(["0"])
    assert "Fôlego" in texto


def test_opcao_invalida_no_menu_e_avisada_e_o_menu_continua():
    _, texto = rodar(["9", "0"])
    assert "Opção inválida." in texto


def test_primeiro_uso_define_o_dia_cadastra_o_salario_e_conclui():
    ambiente, texto = rodar(["5", "3.000,00", "0"], orcamento=Orcamento(), config=Configuracoes())
    config = ambiente.configuracoes.configuracoes()
    assert config.dia_pagamento == 5 and config.primeiro_uso_concluido
    [salario] = ambiente.orcamento.orcamento().entradas
    assert salario.valor_centavos == 300_000 and salario.tipo == TipoEntrada.RECORRENTE
    assert "Salário cadastrado." in texto


def test_primeiro_uso_repergunta_dia_invalido_e_valor_invalido():
    ambiente, texto = rodar(["40", "10", "abc", "1.000,00", "0"], orcamento=Orcamento(), config=Configuracoes())
    assert ambiente.configuracoes.configuracoes().dia_pagamento == 10
    assert ambiente.orcamento.orcamento().entradas[0].valor_centavos == 100_000
    assert "entre 1 e 31" in texto and "Não entendi" in texto


def test_inicio_mostra_disponivel_da_semana_ca05_e_do_ciclo():
    _, texto = rodar(["1", "0"])
    assert "R$ 388,88" in texto
    assert "R$ 1.500,00" in texto
    assert "verde" in texto and "0%" in texto


def test_novo_gasto_valido_usa_data_de_hoje_e_categoria_outros():
    ambiente, texto = rodar(["2", "50,00", "", "Almoço", "", "0"])
    [gasto] = ambiente.orcamento.orcamento().gastos
    assert (gasto.valor_centavos, gasto.data, gasto.descricao, gasto.categoria_id) == (5_000, data(5, 10), "Almoço", 5)
    assert "Gasto salvo." in texto


def test_novo_gasto_com_valor_zero_e_bloqueado():
    ambiente, texto = rodar(["2", "0", "", "", "", "0"])
    assert ambiente.orcamento.orcamento().gastos == []
    assert "maior que zero" in texto


def test_novo_gasto_com_data_futura_e_bloqueado():
    ambiente, texto = rodar(["2", "10,00", "06/10/2026", "", "", "0"])
    assert ambiente.orcamento.orcamento().gastos == []
    assert "no futuro" in texto


def test_ca03_gasto_de_1600_reais_salva_e_avisa_que_invadiu_100_da_reserva():
    ambiente, texto = rodar(["2", "1600", "", "", "", "0"], hoje=data(10, 10))
    assert len(ambiente.orcamento.orcamento().gastos) == 1
    assert "invadiu a reserva em R$ 100,00" in texto


def test_entrada_invalida_e_reperguntada():
    ambiente, texto = rodar(["2", "abc", "-5", "12,50", "31/02/2026", "", "", "", "0"])
    assert ambiente.orcamento.orcamento().gastos[0].valor_centavos == 1_250
    assert texto.count("Não entendi") == 3


def test_cadastrar_e_excluir_conta_nova():
    ambiente, texto = rodar(["3", "2", "2", "Academia", "99,90", "10", "", "3", "3", "0", "0", "0"])
    # a conta nova começa no ciclo atual, então pode ser excluída (RN04)
    assert ambiente.orcamento.orcamento().contas == [cenario.aluguel, cenario.celular]
    assert "Conta salva." in texto and "Conta excluída." in texto


def test_conta_parcelada_na_parcela_2_comeca_no_ciclo_anterior():
    ambiente, _ = rodar(["3", "2", "2", "Sofá", "300", "5", "4", "2", "0", "0", "0"])
    conta = next(c for c in ambiente.orcamento.orcamento().contas if c.descricao == "Sofá")
    assert conta.duracao_meses == 4 and conta.ciclo_inicio == data(1, 9)


def test_conta_com_parcela_fora_da_duracao_e_bloqueada():
    ambiente, texto = rodar(["3", "2", "2", "Sofá", "300", "5", "4", "9", "0", "0", "0"])
    assert len(ambiente.orcamento.orcamento().contas) == 2
    assert "parcela atual" in texto


def test_conta_antiga_nao_pode_ser_excluida_mas_pode_ser_encerrada():
    antiga = ContaFixa(5_000, data(1, 8), descricao="Antiga", id=7)
    base = Orcamento(entradas=[cenario.salario], contas=[antiga])
    ambiente, texto = rodar(["3", "2", "3", "1", "4", "1", "0", "0", "0"], orcamento=base)
    assert "já foi descontada" in texto
    assert ambiente.orcamento.orcamento().contas[0].encerrada_em == data(5, 10)


def test_cadastrar_e_excluir_meta():
    ambiente, texto = rodar(["3", "3", "2", "Viagem", "1", "100", "3", "2", "0", "0", "0"])
    assert ambiente.orcamento.orcamento().metas == [cenario.reserva]
    assert "Meta salva." in texto and "Meta excluída." in texto


def test_ca04_meta_que_nao_cabe_e_bloqueada_dizendo_quanto_falta():
    ambiente, texto = rodar(["3", "3", "2", "Viagem", "1", "2000", "0", "0", "0"])
    assert len(ambiente.orcamento.orcamento().metas) == 1
    assert "Faltam R$ 500,00" in texto


def test_entrada_avulsa_futura_e_bloqueada_e_recorrente_e_salva():
    linhas = ["3", "1", "2", "Bônus", "100", "2", "07/10/2026", "2", "Extra", "50", "1", "", "", "0", "0", "0"]
    ambiente, texto = rodar(linhas)
    assert "no futuro" in texto
    assert [e.descricao for e in ambiente.orcamento.orcamento().entradas] == ["", "Extra"]


def test_historico_mostra_gastos_do_ciclo_por_dia():
    _, texto = rodar(["4", "0"])
    assert "Nenhum gasto ainda." in texto
    _, texto = rodar(["2", "10", "", "Pão", "", "4", "0"])
    assert "05/10/2026 - R$ 10,00" in texto and "Pão" in texto


def test_configuracoes_salva_limite_e_percentuais_e_reaplica_validacao():
    ambiente, texto = rodar(["5", "", "500", "50", "80", "0"])
    config = ambiente.configuracoes.configuracoes()
    assert (config.limite_semanal_manual, config.percentual_atencao, config.percentual_critico) == (50_000, 5000, 8000)
    assert "Configurações salvas." in texto
    _, texto = rodar(["5", "", "", "90", "80", "0"])
    assert "menor que o crítico" in texto
