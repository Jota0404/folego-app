from dataclasses import replace
from datetime import datetime, time

from src.folego.alertas import CodigoAlerta, ResumoDoCiclo, ResumoSemanal, ReservaInvadida, mensagem
from src.folego.calculadora import Orcamento, ciclo_atual
from src.folego.decisoes import (
    PERMITIDO, Bloqueado, ErroCadastro, PermitidoComAviso, decidir_configuracoes, mostrar_primeiro_uso,
)
from src.folego.modelos import (
    Ciclo, Configuracoes, ContaFixa, Gasto, MetaReserva, TipoMeta,
)
from src.folego.servicos import Configurar
from . import cenario
from .cenario import data
from .fakes import AgendadorDeTeste, Ambiente

outubro = Ciclo(data(1, 10), data(31, 10))
segunda = data(5, 10)
agora = datetime(2026, 10, 5, 12, 0)
padrao = Configuracoes()


def bloqueio(erro):
    return Bloqueado(erro)


# --- Alertas ---------------------------------------------------------------

class TestAlertas:
    def setup_method(self):
        self.amb = Ambiente(cenario.orcamento)

    def gastar(self, centavos, dia=segunda, hoje=None, id=0):
        return self.amb.cadastros.salvar_gasto(Gasto(centavos, dia, id=id), hoje or dia, agora)

    def codigos(self):
        return [a.codigo for a in self.amb.notificador.avisos]

    def test_ca08_a2_dispara_uma_unica_vez_na_semana(self):
        # semana de 05/10, limite 388,88: 272,21 ainda não atinge 70%; 272,22 atinge; depois 300,00
        self.gastar(27_221)
        assert self.codigos() == []
        self.gastar(1)
        assert self.codigos() == [CodigoAlerta.A2]
        self.gastar(2_778)
        assert sum(g.valor_centavos for g in self.amb.orcamento.orcamento().gastos) == 30_000
        assert self.codigos() == [CodigoAlerta.A2]
        msg = mensagem(self.amb.notificador.avisos[0])
        assert msg.titulo == "70% do limite da semana"
        assert msg.texto == "Você já gastou R$ 272,22 de R$ 388,88 nesta semana. Restam R$ 116,66."

    def test_a3_dispara_ao_atingir_90_por_cento_depois_do_a2(self):
        self.gastar(27_222)
        self.gastar(7_778)  # 350,00 de 388,88: 90% é 349,992
        assert self.codigos() == [CodigoAlerta.A2, CodigoAlerta.A3]
        self.gastar(1_000)
        assert self.codigos() == [CodigoAlerta.A2, CodigoAlerta.A3]

    def test_no_salto_direto_para_90_por_cento_so_o_a3_chega_e_o_a2_conta_como_enviado(self):
        # decisão do dono
        self.gastar(37_000)
        assert self.codigos() == [CodigoAlerta.A3]
        assert ("A2", "2026-10-05") in self.amb.historico.alertas

    def test_cada_parte_da_semana_partida_e_um_periodo_separado_para_a2_e_a3(self):
        # 01 a 04/10: limite 193,54; 70% = 135,478
        self.gastar(13_548, dia=data(2, 10))
        assert self.codigos() == [CodigoAlerta.A2]
        # semana de 05/10: limite (1500 - 135,48) x 7 / 27 = 353,75; 70% = 247,62 dispara outro A2
        self.gastar(25_000, dia=segunda)
        assert self.codigos() == [CodigoAlerta.A2, CodigoAlerta.A2]
        assert [a.periodo_ref for a in self.amb.notificador.avisos] == ["2026-10-01", "2026-10-05"]

    def test_com_limite_zero_a2_e_a3_nao_disparam(self):
        # decisão do dono: CA14, o disponível acabou em 02/10
        self.gastar(160_000, dia=data(2, 10), hoje=data(2, 10))
        self.amb.notificador.avisos.clear()
        self.gastar(1_000)
        assert self.codigos() == [CodigoAlerta.A4]

    def test_ca03_gasto_que_invade_a_reserva_dispara_o_a4_uma_vez(self):
        self.gastar(160_000, dia=data(10, 10), hoje=data(10, 10))
        [a4] = [a for a in self.amb.notificador.avisos if isinstance(a, ReservaInvadida)]
        assert a4.reserva_invadida == 10_000
        assert mensagem(a4).texto == "Um gasto invadiu a reserva. A reserva deste ciclo está invadida em R$ 100,00."

    def test_a4_chega_uma_vez_por_gasto_e_tambem_ao_corrigir_um_gasto(self):
        # decisão do dono: corrigir 45,00 para 1.600,00 invade a reserva e dispara o A4
        self.gastar(4_500, dia=data(2, 10), hoje=data(2, 10))
        [gasto] = self.amb.orcamento.orcamento().gastos
        self.gastar(160_000, dia=data(2, 10), hoje=data(2, 10), id=gasto.id)
        assert self.codigos().count(CodigoAlerta.A4) == 1
        # corrigir de novo o mesmo gasto não manda outro A4
        self.gastar(170_000, dia=data(2, 10), hoje=data(2, 10), id=gasto.id)
        assert self.codigos().count(CodigoAlerta.A4) == 1
        # um gasto novo que aprofunda a invasão manda outro
        self.gastar(1_000, dia=data(3, 10), hoje=data(3, 10))
        assert self.codigos().count(CodigoAlerta.A4) == 2

    def test_a1_chega_uma_vez_por_semana_com_o_disponivel_da_semana_e_do_ciclo(self):
        self.amb.alertas.rotina_diaria(segunda, agora)
        self.amb.alertas.rotina_diaria(data(6, 10), agora)
        [a1] = [a for a in self.amb.notificador.avisos if isinstance(a, ResumoSemanal)]
        assert mensagem(a1).texto == (
            "Você pode gastar R$ 388,88 nesta semana (limite de R$ 388,88). No ciclo: R$ 1.500,00.")
        self.amb.alertas.rotina_diaria(data(12, 10), agora)
        assert self.codigos().count(CodigoAlerta.A1) == 2

    def test_rotina_diaria_manda_o_a2_quando_uma_conta_nova_baixa_o_limite_da_semana(self):
        # QA Etapa 6, B3: 200 gastos na semana (51% de 388,88); conta nova de 400 em 05/10 baixa o
        # limite para (1500 - 400) x 7 / 27 = 285,18, e 200 passa a ser 70,1%
        self.gastar(20_000)
        assert self.codigos() == []
        self.amb.cadastros.salvar_conta(
            ContaFixa(40_000, data(1, 10), descricao="Curso", dia_vencimento=10), segunda)
        self.amb.alertas.rotina_diaria(data(6, 10), agora)
        assert CodigoAlerta.A2 in self.codigos()

    def test_a1_atrasado_so_chega_se_ainda_for_a_mesma_semana(self):
        # a rotina de segunda não rodou; na quarta ainda chega o A1 dessa semana, uma vez
        self.amb.alertas.rotina_diaria(data(7, 10), agora)
        a1s = [a for a in self.amb.notificador.avisos if isinstance(a, ResumoSemanal)]
        assert [a.periodo_ref for a in a1s] == ["2026-10-05"]

    def test_a5_fecha_o_ciclo_no_dia_do_pagamento_e_diz_quanto_sobrou_e_guardou(self):
        self.gastar(160_000, dia=data(10, 10), hoje=data(10, 10))  # CA03: reserva invadida em 100
        self.amb.notificador.avisos.clear()
        self.amb.alertas.rotina_diaria(data(1, 11), agora)
        [a5] = [a for a in self.amb.notificador.avisos if isinstance(a, ResumoDoCiclo)]
        assert a5.fechado.ciclo == Ciclo(data(1, 10), data(31, 10))
        assert mensagem(a5).titulo == "Ciclo de 01/10 a 31/10 fechado"
        assert mensagem(a5).texto == "Sobrou R$ 0,00. Reserva não cumprida: guardou R$ 200,00 de R$ 300,00."
        # a rotina do dia seguinte não repete
        self.amb.alertas.rotina_diaria(data(2, 11), agora)
        assert self.codigos().count(CodigoAlerta.A5) == 1

    def test_a5_com_a_reserva_cumprida(self):
        self.gastar(50_000, dia=data(10, 10), hoje=data(10, 10))
        self.amb.alertas.rotina_diaria(data(1, 11), agora)
        [a5] = [a for a in self.amb.notificador.avisos if isinstance(a, ResumoDoCiclo)]
        assert mensagem(a5).texto == "Sobrou R$ 1.000,00. Reserva cumprida: R$ 300,00 guardados."

    def test_com_o_app_parado_na_virada_fecha_tudo_e_manda_um_a5_so_do_ciclo_mais_recente(self):
        # decisão do dono: primeiro gasto em outubro, app volta a rodar em 03/12
        self.gastar(1_000, dia=data(10, 10), hoje=data(10, 10))
        self.amb.alertas.rotina_diaria(data(3, 12), agora)
        assert len(self.amb.historico.fechados) == 2
        [a5] = [a for a in self.amb.notificador.avisos if isinstance(a, ResumoDoCiclo)]
        assert a5.fechado.ciclo == Ciclo(data(1, 11), data(30, 11))

    def test_ca11_ciclo_fechado_de_outubro_continua_com_1000_reais_de_aluguel_depois_da_edicao(self):
        self.gastar(1_000, dia=data(10, 10), hoje=data(10, 10))
        self.amb.alertas.fechar_ciclos(data(1, 11))
        # aluguel editado para 1.100,00 em novembro
        [aluguel] = [c for c in self.amb.orcamento.orcamento().contas if c.valor_centavos == 100_000]
        self.amb.cadastros.salvar_conta(replace(aluguel, valor_centavos=110_000), data(5, 11))
        [fechado] = self.amb.historico.fechados
        assert fechado.resumo.fixas == 120_000  # aluguel 1000 + celular 200
        assert fechado.resumo.disponivel + fechado.resumo.gastos == 150_000

    def test_fechar_duas_vezes_nao_duplica_o_ciclo(self):
        self.gastar(1_000, dia=data(10, 10), hoje=data(10, 10))
        self.amb.alertas.fechar_ciclos(data(1, 11))
        assert self.amb.alertas.fechar_ciclos(data(1, 11)) == []
        assert len(self.amb.historico.fechados) == 1

    def test_rn01_mudar_o_dia_do_pagamento_fecha_o_ciclo_que_termina_ontem(self):
        # QA Etapa 3, B2: 1 -> 15 em 15/10 fecha 01/10 a 14/10 e grava o dia novo
        self.amb.alertas.mudar_dia_pagamento(15, data(15, 10))
        assert [f.ciclo for f in self.amb.historico.fechados] == [Ciclo(data(1, 10), data(14, 10))]
        assert self.amb.configuracoes.dados.dia_pagamento == 15


# --- Configurar ------------------------------------------------------------

class TestConfigurar:
    def setup_method(self):
        self.amb = Ambiente(cenario.orcamento)
        self.agendador = AgendadorDeTeste()
        self.configurar = Configurar(
            self.amb.orcamento, self.amb.configuracoes, self.amb.alertas, self.agendador)

    def test_padroes_do_briefing_sao_validos(self):
        assert decidir_configuracoes(padrao) == PERMITIDO

    def test_dia_do_pagamento_fora_de_1_a_31_e_bloqueado(self):
        assert decidir_configuracoes(replace(padrao, dia_pagamento=0)) == bloqueio(ErroCadastro.DIA_PAGAMENTO_INVALIDO)
        assert decidir_configuracoes(replace(padrao, dia_pagamento=32)) == bloqueio(ErroCadastro.DIA_PAGAMENTO_INVALIDO)
        assert decidir_configuracoes(replace(padrao, dia_pagamento=31)) == PERMITIDO

    def test_rn15_limite_manual_zero_ou_negativo_e_bloqueado_e_vazio_volta_ao_automatico(self):
        zero = bloqueio(ErroCadastro.VALOR_ZERO_OU_NEGATIVO)
        assert decidir_configuracoes(replace(padrao, limite_semanal_manual=0)) == zero
        assert decidir_configuracoes(replace(padrao, limite_semanal_manual=-1)) == zero
        assert decidir_configuracoes(replace(padrao, limite_semanal_manual=50_000)) == PERMITIDO
        assert decidir_configuracoes(replace(padrao, limite_semanal_manual=None)) == PERMITIDO

    def test_percentuais_nas_faixas_e_atencao_menor_que_critico(self):
        # decisão do dono: atenção de 1% a 99%, crítico de 2% a 100%, atenção menor que crítico
        fora = bloqueio(ErroCadastro.PERCENTUAL_FORA_DA_FAIXA)
        ordem = bloqueio(ErroCadastro.ATENCAO_NAO_MENOR_QUE_CRITICO)
        assert decidir_configuracoes(replace(padrao, percentual_atencao=100, percentual_critico=200)) == PERMITIDO
        assert decidir_configuracoes(replace(padrao, percentual_atencao=9_900, percentual_critico=10_000)) == PERMITIDO
        assert decidir_configuracoes(replace(padrao, percentual_atencao=0)) == fora
        assert decidir_configuracoes(replace(padrao, percentual_critico=10_001)) == fora
        assert decidir_configuracoes(replace(padrao, percentual_atencao=9_000, percentual_critico=7_000)) == ordem
        assert decidir_configuracoes(replace(padrao, percentual_atencao=8_000, percentual_critico=8_000)) == ordem

    def test_primeiro_uso_aparece_ate_ser_concluido_e_nao_aparece_para_quem_ja_tem_entradas(self):
        # decisão do dono
        assert mostrar_primeiro_uso(padrao, Orcamento())
        assert not mostrar_primeiro_uso(replace(padrao, primeiro_uso_concluido=True), Orcamento())
        assert not mostrar_primeiro_uso(padrao, cenario.orcamento)

    def test_salvar_grava_as_configuracoes_e_o_horario_novo_reagenda_os_alertas(self):
        nova = replace(padrao, limite_semanal_manual=50_000, percentual_atencao=6_000,
                       percentual_critico=8_500, hora_resumo=time(7, 30))
        assert self.configurar.salvar(nova, data(6, 10)) == PERMITIDO
        assert self.amb.configuracoes.dados == nova
        assert self.agendador.horarios == [time(7, 30)]
        # sem mudar o horário, não reagenda de novo
        self.configurar.salvar(replace(nova, limite_semanal_manual=None), data(6, 10))
        assert len(self.agendador.horarios) == 1
        assert self.amb.configuracoes.dados.limite_semanal_manual is None

    def test_configuracao_bloqueada_nao_e_gravada(self):
        resultado = self.configurar.salvar(replace(padrao, percentual_atencao=9_500), data(6, 10))
        assert resultado == bloqueio(ErroCadastro.ATENCAO_NAO_MENOR_QUE_CRITICO)
        assert self.amb.configuracoes.dados == padrao
        assert self.agendador.horarios == []

    def test_rn01_mudar_o_dia_do_pagamento_nas_configuracoes_fecha_o_ciclo_e_guarda_o_irregular(self):
        # P14: 1 -> 15 em 20/10 deixa o ciclo atual de 01/10 a 14/11; em 15/10, fecha 01/10 a 14/10
        self.configurar.salvar(replace(padrao, dia_pagamento=15), data(20, 10))
        config = self.amb.configuracoes.dados
        assert config.dia_pagamento == 15
        assert ciclo_atual(config, data(25, 10)) == Ciclo(data(1, 10), data(14, 11))

        outro = Ambiente(cenario.orcamento)
        Configurar(outro.orcamento, outro.configuracoes, outro.alertas, AgendadorDeTeste()).salvar(
            replace(padrao, dia_pagamento=15), data(15, 10))
        assert [f.ciclo for f in outro.historico.fechados] == [Ciclo(data(1, 10), data(14, 10))]

    def test_dia_escolhido_no_primeiro_uso_comeca_no_ciclo_normal_sem_ciclo_irregular(self):
        # dia 5 escolhido em 07/10: ciclo de 05/10 a 04/11, e não 01/10 a 04/11 como numa mudança
        vazio = Ambiente()
        configurar = Configurar(vazio.orcamento, vazio.configuracoes, vazio.alertas, AgendadorDeTeste())
        assert configurar.definir_dia_no_primeiro_uso(5) == PERMITIDO
        assert vazio.configuracoes.dados.ciclo_irregular is None
        assert ciclo_atual(vazio.configuracoes.dados, data(7, 10)) == Ciclo(data(5, 10), data(4, 11))
        assert configurar.definir_dia_no_primeiro_uso(0) == bloqueio(ErroCadastro.DIA_PAGAMENTO_INVALIDO)
        assert vazio.historico.fechados == []

    def test_concluir_o_primeiro_uso_grava_que_ele_nao_aparece_mais(self):
        vazio = Ambiente()
        configurar = Configurar(vazio.orcamento, vazio.configuracoes, vazio.alertas, AgendadorDeTeste())
        assert configurar.mostrar_primeiro_uso()
        configurar.concluir_primeiro_uso()
        assert not configurar.mostrar_primeiro_uso()


# --- Cadastros -------------------------------------------------------------

class TestCadastros:
    def setup_method(self):
        # cenário base com ids, como viria do banco
        base = replace(
            cenario.orcamento,
            entradas=[replace(cenario.salario, id=1, descricao="Salário")],
            contas=[replace(cenario.aluguel, id=1, descricao="Aluguel"),
                    replace(cenario.celular, id=2, descricao="Celular")],
            metas=[replace(cenario.reserva, id=1, nome="Reserva")],
        )
        self.hoje = data(6, 10)
        self.agora = datetime(2026, 10, 6, 12, 0)
        self.amb = Ambiente(base)
        self.base = base
        self.conta = ContaFixa(30_000, ciclo_inicio=outubro.inicio, duracao_meses=10,
                               descricao="Financiamento", dia_vencimento=15)
        self.meta = MetaReserva(TipoMeta.VALOR, 10_000, nome="Viagem")

    def test_meta_bloqueada_nao_e_salva_e_meta_que_cabe_e_salva(self):
        cadastros = self.amb.cadastros
        assert cadastros.salvar_meta(replace(self.meta, valor=200_000), self.hoje) == Bloqueado(
            ErroCadastro.METAS_NAO_CABEM, 50_000)
        assert len(self.amb.orcamento.orcamento().metas) == 1
        assert cadastros.salvar_meta(self.meta, self.hoje) == PERMITIDO
        assert len(self.amb.orcamento.orcamento().metas) == 2

    def test_conta_com_aviso_e_salva_mesmo_assim(self):
        cara = replace(self.conta, valor_centavos=170_000, duracao_meses=None)
        assert self.amb.cadastros.salvar_conta(cara, self.hoje) == PermitidoComAviso(20_000)
        assert len(self.amb.orcamento.orcamento().contas) == 3

    def test_rn04_encerrar_a_conta_guarda_o_dia_e_ela_continua_no_ciclo_atual(self):
        cadastros = self.amb.cadastros
        aluguel = self.base.contas[0]
        assert cadastros.excluir_conta(replace(aluguel, ciclo_inicio=data(1, 9)), self.hoje) == bloqueio(
            ErroCadastro.CONTA_JA_DESCONTADA)
        cadastros.encerrar(aluguel, self.hoje)
        [encerrado] = [c for c in self.amb.orcamento.orcamento().contas if c.id == aluguel.id]
        assert encerrado.encerrada_em == self.hoje
        assert self.amb.orcamento.orcamento().resumo(outubro).disponivel == 150_000
        # encerrar de novo não muda a data
        cadastros.encerrar(encerrado, data(20, 10))
        [de_novo] = [c for c in self.amb.orcamento.orcamento().contas if c.id == aluguel.id]
        assert de_novo.encerrada_em == self.hoje

    def test_gasto_bloqueado_nao_e_salvo_e_gasto_valido_e_salvo(self):
        cadastros = self.amb.cadastros
        assert cadastros.salvar_gasto(Gasto(1_000, data(7, 10)), self.hoje, self.agora) == bloqueio(
            ErroCadastro.DATA_FUTURA)
        assert len(self.amb.orcamento.orcamento().gastos) == 0
        assert cadastros.salvar_gasto(Gasto(1_000, self.hoje), self.hoje, self.agora) == PERMITIDO
        assert len(self.amb.orcamento.orcamento().gastos) == 1
