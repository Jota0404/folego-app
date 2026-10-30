import json
import subprocess
import sys
from pathlib import Path
from dataclasses import replace
from datetime import date, datetime, time

import pytest

from src.folego.alertas import CodigoAlerta
from src.folego.armazenamento import (
    CONFIGURACOES, HISTORICO, ORCAMENTO, ArmazenamentoCorrompido, PastaEmUso, RepositorioJson, fazer_backup, travar,
)
from src.folego.calculadora import Orcamento
from src.folego.modelos import (
    CATEGORIAS_PADRAO, Ciclo, CicloFechado, Configuracoes, ContaFixa, Entrada, Gasto, MetaReserva,
    Resumo, TipoEntrada, TipoMeta,
)
from src.folego.servicos import Alertas, Cadastros, Configurar
from . import cenario
from .cenario import data
from .fakes import AgendadorDeTeste, NotificadorDeTeste

agora = datetime(2026, 10, 5, 12, 0)
outubro = Ciclo(data(1, 10), data(31, 10))


def reabrir(pasta):
    return RepositorioJson(pasta)


def retrato(inicio=data(1, 10), fim=data(31, 10), **resumo):
    totais = dict(entradas=300_000, fixas=120_000, reserva=30_000, gastos=50_000)
    return CicloFechado(Ciclo(inicio, fim), Resumo(**{**totais, **resumo}))


# --- Primeira execução -------------------------------------------------------

def test_primeira_execucao_devolve_tudo_vazio_e_configuracoes_padrao(tmp_path):
    repo = RepositorioJson(tmp_path / "dados" / "folego")  # a pasta (e as de cima) é criada
    assert repo.orcamento() == Orcamento()
    assert repo.configuracoes() == Configuracoes()
    assert repo.ciclos_fechados() == []
    assert repo.categorias() == CATEGORIAS_PADRAO


# --- Orçamento: ida e volta --------------------------------------------------

def test_ida_e_volta_de_cada_tipo_de_cadastro(tmp_path):
    repo = RepositorioJson(tmp_path)
    recorrente = Entrada(300_000, TipoEntrada.RECORRENTE, data(1, 10), data_fim=data(1, 12), descricao="Salário")
    avulsa = Entrada(5_050, TipoEntrada.AVULSA, data(7, 10), descricao="Venda")
    conta = ContaFixa(20_000, data(1, 10), duracao_meses=3, encerrada_em=data(15, 11),
                      descricao="Celular", dia_vencimento=12)
    sem_fim = ContaFixa(100_000, data(1, 10), descricao="Aluguel")
    meta = MetaReserva(TipoMeta.PERCENTUAL, 1000, ativa=False, nome="Viagem")
    gasto = Gasto(1_999, data(5, 10), descricao="Café ☕", categoria_id=1)
    ids = [
        repo.salvar_entrada(recorrente), repo.salvar_entrada(avulsa), repo.salvar_conta(conta),
        repo.salvar_conta(sem_fim), repo.salvar_meta(meta), repo.salvar_gasto(gasto),
    ]
    assert len(set(ids)) == 6 and 0 not in ids

    lido = reabrir(tmp_path).orcamento()
    assert lido == Orcamento(
        entradas=[replace(recorrente, id=ids[0]), replace(avulsa, id=ids[1])],
        contas=[replace(conta, id=ids[2]), replace(sem_fim, id=ids[3])],
        metas=[replace(meta, id=ids[4])],
        gastos=[replace(gasto, id=ids[5])],
    )
    assert lido.contas[0].duracao_meses == 3 and lido.contas[0].encerrada_em == data(15, 11)
    assert lido.contas[1].duracao_meses is None and lido.entradas[1].data_fim is None


def test_salvar_com_id_existente_substitui_e_nao_duplica(tmp_path):
    repo = RepositorioJson(tmp_path)
    id_gasto = repo.salvar_gasto(Gasto(1_000, data(5, 10)))
    assert repo.salvar_gasto(Gasto(2_500, data(5, 10), descricao="corrigido", id=id_gasto)) == id_gasto
    gastos = reabrir(tmp_path).orcamento().gastos
    assert gastos == [Gasto(2_500, data(5, 10), descricao="corrigido", id=id_gasto)]


def test_ids_sao_autoincrementais_e_nao_voltam_depois_de_excluir(tmp_path):
    repo = RepositorioJson(tmp_path)
    primeiro = repo.salvar_gasto(Gasto(100, data(5, 10)))
    segundo = repo.salvar_gasto(Gasto(200, data(5, 10)))
    assert segundo > primeiro
    repo.excluir_gasto(replace(Gasto(200, data(5, 10)), id=segundo))
    # Mesmo depois de reabrir, o id do gasto excluído não é reaproveitado
    terceiro = reabrir(tmp_path).salvar_gasto(Gasto(300, data(5, 10)))
    assert terceiro > segundo
    assert [g.id for g in reabrir(tmp_path).orcamento().gastos] == [primeiro, terceiro]


def test_excluir_cada_tipo_tira_so_o_item_certo(tmp_path):
    repo = RepositorioJson(tmp_path)
    e1 = replace(cenario.salario, id=repo.salvar_entrada(cenario.salario))
    e2 = replace(cenario.salario, id=repo.salvar_entrada(cenario.salario))
    c = replace(cenario.aluguel, id=repo.salvar_conta(cenario.aluguel))
    m = replace(cenario.reserva, id=repo.salvar_meta(cenario.reserva))
    g = replace(Gasto(100, data(5, 10)), id=repo.salvar_gasto(Gasto(100, data(5, 10))))
    repo.excluir_entrada(e1)
    repo.excluir_conta(c)
    repo.excluir_meta(m)
    repo.excluir_gasto(g)
    assert reabrir(tmp_path).orcamento() == Orcamento(entradas=[e2])


def test_dinheiro_fica_em_centavos_inteiros_no_arquivo(tmp_path):
    repo = RepositorioJson(tmp_path)
    repo.salvar_entrada(cenario.salario)
    repo.salvar_gasto(Gasto(1_999, data(5, 10)))
    texto = (tmp_path / ORCAMENTO).read_text(encoding="utf-8")
    gravado = json.loads(texto)["orcamento"]
    assert gravado["entradas"][0]["valor_centavos"] == 300_000
    assert type(gravado["gastos"][0]["valor_centavos"]) is int
    assert gravado["gastos"][0]["data"] == "2026-10-05"
    assert gravado["entradas"][0]["tipo"] == "RECORRENTE"


# --- Configurações -----------------------------------------------------------

def test_configuracoes_ida_e_volta_com_ciclo_irregular_e_limite_manual(tmp_path):
    repo = RepositorioJson(tmp_path)
    nova = Configuracoes(
        dia_pagamento=15, ciclo_irregular=Ciclo(data(1, 10), data(14, 11)), limite_semanal_manual=25_000,
        percentual_atencao=6000, percentual_critico=8500, hora_resumo=time(7, 30), primeiro_uso_concluido=True,
    )
    repo.atualizar(lambda _: nova)
    assert reabrir(tmp_path).configuracoes() == nova
    gravado = json.loads((tmp_path / CONFIGURACOES).read_text(encoding="utf-8"))
    assert gravado["hora_resumo"] == "07:30"
    assert gravado["ciclo_irregular"] == {"inicio": "2026-10-01", "fim": "2026-11-14"}


def test_atualizar_recebe_o_valor_atual_e_guarda_o_novo(tmp_path):
    repo = RepositorioJson(tmp_path)
    repo.atualizar(lambda c: replace(c, dia_pagamento=5))
    repo.atualizar(lambda c: replace(c, limite_semanal_manual=10_000))
    assert reabrir(tmp_path).configuracoes() == Configuracoes(dia_pagamento=5, limite_semanal_manual=10_000)


# --- Histórico ---------------------------------------------------------------

def test_ciclo_fechado_ida_e_volta(tmp_path):
    repo = RepositorioJson(tmp_path)
    fechado = replace(retrato(), reserva_invadida=1_234)
    id_novo = repo.salvar_ciclo_fechado(fechado)
    assert id_novo > 0
    assert reabrir(tmp_path).ciclos_fechados() == [replace(fechado, id=id_novo)]


def test_ciclo_ja_fechado_devolve_menos_um_e_nao_duplica(tmp_path):
    repo = RepositorioJson(tmp_path)
    assert repo.salvar_ciclo_fechado(retrato()) > 0
    assert reabrir(tmp_path).salvar_ciclo_fechado(retrato(gastos=1)) == -1
    assert len(repo.ciclos_fechados()) == 1
    assert repo.ciclos_fechados()[0].resumo.gastos == 50_000  # o retrato original não muda
    assert repo.salvar_ciclo_fechado(retrato(data(1, 11), data(30, 11))) > 0


def test_alerta_repetido_no_mesmo_periodo_devolve_false_mesmo_depois_de_reabrir(tmp_path):
    repo = RepositorioJson(tmp_path)
    assert repo.registrar_alerta("A2", "2026-10-05", agora) is True
    assert repo.registrar_alerta("A2", "2026-10-05", agora) is False
    reaberto = reabrir(tmp_path)
    assert reaberto.registrar_alerta("A2", "2026-10-05", agora) is False
    assert reaberto.registrar_alerta("A2", "2026-10-12", agora) is True
    assert reaberto.registrar_alerta("A3", "2026-10-05", agora) is True


# --- Arquivo corrompido ------------------------------------------------------

CORROMPIDOS = [
    (ORCAMENTO, "{ isto não é json"),
    (HISTORICO, ""),
    (CONFIGURACOES, "[]"),
    (CONFIGURACOES, '{"dia_pagamento": 1.5}'),
    (ORCAMENTO, '{"orcamento": {"gastos": [{"valor_centavos": 10.5, "data": "2026-10-05"}]}}'),
    (ORCAMENTO, '{"orcamento": {"gastos": [{"valor_centavos": 10, "data": "05/10/2026"}]}}'),
    (HISTORICO, '{"alertas": [{"codigo": "A2"}]}'),
]


@pytest.mark.parametrize("nome, conteudo", CORROMPIDOS)
def test_arquivo_corrompido_levanta_erro_claro_e_nao_e_sobrescrito(tmp_path, nome, conteudo):
    (tmp_path / nome).write_text(conteudo, encoding="utf-8")
    with pytest.raises(ArmazenamentoCorrompido, match=nome):
        RepositorioJson(tmp_path)
    assert (tmp_path / nome).read_text(encoding="utf-8") == conteudo


def test_arquivo_que_estraga_depois_de_aberto_nao_e_sobrescrito_por_uma_gravacao(tmp_path):
    repo = RepositorioJson(tmp_path)
    repo.salvar_gasto(Gasto(100, data(5, 10)))
    (tmp_path / ORCAMENTO).write_text("lixo", encoding="utf-8")
    with pytest.raises(ArmazenamentoCorrompido):
        repo.salvar_gasto(Gasto(200, data(5, 10)))
    assert (tmp_path / ORCAMENTO).read_text(encoding="utf-8") == "lixo"


def test_nenhum_arquivo_temporario_sobra_na_pasta(tmp_path):
    repo = RepositorioJson(tmp_path)
    repo.salvar_gasto(Gasto(100, data(5, 10)))
    repo.atualizar(lambda c: replace(c, dia_pagamento=5))
    repo.registrar_alerta("A2", "2026-10-05", agora)
    assert sorted(p.name for p in tmp_path.iterdir()) == [CONFIGURACOES, HISTORICO, ORCAMENTO]


def test_falha_na_gravacao_mantem_o_arquivo_anterior(tmp_path, monkeypatch):
    repo = RepositorioJson(tmp_path)
    repo.salvar_gasto(Gasto(100, data(5, 10)))
    antes = (tmp_path / ORCAMENTO).read_text(encoding="utf-8")

    def falha(origem, destino):
        raise OSError("disco cheio")
    monkeypatch.setattr("src.folego.armazenamento.os.replace", falha)
    with pytest.raises(OSError):
        repo.salvar_gasto(Gasto(200, data(5, 10)))
    assert (tmp_path / ORCAMENTO).read_text(encoding="utf-8") == antes
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


# --- Os serviços sobre o RepositorioJson -------------------------------------

def servicos(pasta):
    """Tudo o que o app monta, com um só RepositorioJson no lugar dos três repositórios."""
    repo = RepositorioJson(pasta)
    notificador, agendador = NotificadorDeTeste(), AgendadorDeTeste()
    alertas = Alertas(repo, repo, repo, notificador)
    return (repo, notificador, agendador, alertas,
            Cadastros(repo, repo, alertas), Configurar(repo, repo, alertas, agendador))


def semear_cenario(repo):
    """Grava o cenário base direto no repositório (as entradas dele não têm descrição, que o Cadastros exige)."""
    for entrada in cenario.orcamento.entradas:
        repo.salvar_entrada(entrada)
    for conta in cenario.orcamento.contas:
        repo.salvar_conta(conta)
    repo.salvar_meta(cenario.reserva)


def test_fluxo_de_cadastros_alertas_e_configurar_reabrindo_no_meio(tmp_path):
    segunda = data(5, 10)
    repo, notificador, _, _, cadastros, _ = servicos(tmp_path)
    semear_cenario(repo)
    cadastros.salvar_gasto(Gasto(27_221, segunda), segunda, agora)
    assert notificador.avisos == []

    # O app fecha e abre de novo: os cadastros e o gasto continuam lá
    repo, notificador, _, _, cadastros, _ = servicos(tmp_path)
    dados = repo.orcamento()
    assert [e.valor_centavos for e in dados.entradas] == [300_000]
    assert [c.valor_centavos for c in dados.contas] == [100_000, 20_000]
    assert [g.valor_centavos for g in dados.gastos] == [27_221]

    cadastros.salvar_gasto(Gasto(1, segunda), segunda, agora)  # passa de 70% do limite semanal: A2
    assert [a.codigo for a in notificador.avisos] == [CodigoAlerta.A2]

    # Outra reabertura: o registro do A2 vale, então mais um gasto não avisa de novo
    repo, notificador, _, _, cadastros, _ = servicos(tmp_path)
    cadastros.salvar_gasto(Gasto(2_778, segunda), segunda, agora)
    assert notificador.avisos == []
    assert sum(g.valor_centavos for g in repo.orcamento().gastos) == 30_000

    # Excluir pelo serviço também chega ao disco
    gasto = repo.orcamento().gastos[0]
    cadastros.excluir_gasto(gasto, segunda)
    assert gasto.id not in [g.id for g in reabrir(tmp_path).orcamento().gastos]


def test_configurar_mudando_o_dia_do_pagamento_guarda_o_ciclo_irregular(tmp_path):
    hoje = data(20, 10)
    repo, _, agendador, _, cadastros, configurar = servicos(tmp_path)
    configurar.definir_dia_no_primeiro_uso(1)
    semear_cenario(repo)

    repo, _, agendador, _, _, configurar = servicos(tmp_path)
    configurar.salvar(Configuracoes(dia_pagamento=15, limite_semanal_manual=20_000, hora_resumo=time(7, 0)), hoje)
    assert agendador.horarios == [time(7, 0)]

    config = reabrir(tmp_path).configuracoes()
    assert config.dia_pagamento == 15
    assert config.limite_semanal_manual == 20_000
    assert config.hora_resumo == time(7, 0)
    assert config.ciclo_irregular == Ciclo(data(1, 10), data(14, 11))
    assert reabrir(tmp_path).ciclos_fechados() == []  # mudar em 20/10 não deixa ciclo terminado ontem


def test_rotina_diaria_fecha_ciclos_e_o_historico_sobrevive_a_reabertura(tmp_path):
    repo, notificador, _, alertas, cadastros, _ = servicos(tmp_path)
    semear_cenario(repo)
    cadastros.salvar_gasto(Gasto(10_000, data(5, 10)), data(5, 10), agora)

    novembro = datetime(2026, 11, 2, 8, 0)
    alertas.rotina_diaria(novembro.date(), novembro)
    fechados = repo.ciclos_fechados()
    assert [f.ciclo for f in fechados] == [outubro]
    assert fechados[0].resumo == Resumo(entradas=300_000, fixas=120_000, reserva=30_000, gastos=10_000)
    assert CodigoAlerta.A5 in [a.codigo for a in notificador.avisos]

    # Reabrindo e rodando a rotina de novo no mesmo dia, nada fecha nem avisa outra vez
    repo, notificador, _, alertas, _, _ = servicos(tmp_path)
    alertas.rotina_diaria(novembro.date(), novembro)
    assert len(repo.ciclos_fechados()) == 1
    assert notificador.avisos == []


def test_formato_de_data_no_arquivo_e_iso(tmp_path):
    repo = RepositorioJson(tmp_path)
    repo.salvar_ciclo_fechado(retrato())
    repo.registrar_alerta("A1", "2026-10-05", agora)
    gravado = json.loads((tmp_path / HISTORICO).read_text(encoding="utf-8"))
    assert gravado["ciclos_fechados"][0]["ciclo"] == {"inicio": "2026-10-01", "fim": "2026-10-31"}
    assert gravado["alertas"][0]["disparado_em"] == agora.isoformat()
    assert date.fromisoformat(gravado["ciclos_fechados"][0]["ciclo"]["inicio"]) == data(1, 10)


# --- trava e backup ----------------------------------------------------------

def test_travar_recusa_segunda_trava_e_libera_depois(tmp_path):
    with travar(tmp_path):
        with pytest.raises(PastaEmUso, match="Feche o outro Fôlego"):
            with travar(tmp_path):
                pass
    with travar(tmp_path):  # liberou
        pass


def test_travar_recusa_trava_de_outro_processo(tmp_path):
    codigo = ("import sys, time\nfrom src.folego.armazenamento import travar\n"
              "with travar(sys.argv[1]):\n    print('ok', flush=True)\n    time.sleep(30)")
    filho = subprocess.Popen([sys.executable, "-c", codigo, str(tmp_path)], stdout=subprocess.PIPE, text=True,
                             cwd=Path(__file__).resolve().parents[2])
    try:
        assert filho.stdout.readline().strip() == "ok"
        with pytest.raises(PastaEmUso):
            with travar(tmp_path):
                pass
    finally:
        filho.kill()
        filho.wait()
    with travar(tmp_path):  # processo morto, trava solta sozinha
        pass


def _dados(pasta, **arquivos):
    for nome, texto in arquivos.items():
        (pasta / f"{nome}.json").write_text(texto)


def test_backup_copia_so_o_que_existe_e_nao_duplica_sem_mudanca(tmp_path):
    _dados(tmp_path, orcamento="a", configuracoes="c")
    copia = fazer_backup(tmp_path, datetime(2026, 10, 5, 12, 0, 0))
    assert copia.name == "2026-10-05-120000"
    assert sorted(p.name for p in copia.iterdir()) == ["configuracoes.json", "orcamento.json"]
    assert fazer_backup(tmp_path, datetime(2026, 10, 6, 12, 0, 0)) is None
    assert len(list((tmp_path / "backups").iterdir())) == 1


def test_backup_duplica_quando_mudou_e_nunca_altera_os_originais(tmp_path):
    _dados(tmp_path, orcamento="a", historico="h")
    fazer_backup(tmp_path, datetime(2026, 10, 5, 12, 0, 0))
    _dados(tmp_path, orcamento="b")
    fazer_backup(tmp_path, datetime(2026, 10, 6, 12, 0, 0))
    assert [p.name for p in sorted((tmp_path / "backups").iterdir())] == ["2026-10-05-120000", "2026-10-06-120000"]
    assert (tmp_path / "backups/2026-10-05-120000/orcamento.json").read_text() == "a"
    assert (tmp_path / "backups/2026-10-06-120000/orcamento.json").read_text() == "b"
    assert (tmp_path / "orcamento.json").read_text() == "b" and (tmp_path / "historico.json").read_text() == "h"


def test_backup_poda_alem_de_manter_e_sem_dados_nao_cria_copia(tmp_path):
    assert fazer_backup(tmp_path, agora) is None
    for dia in range(1, 6):
        _dados(tmp_path, orcamento=str(dia))
        fazer_backup(tmp_path, datetime(2026, 10, dia, 12, 0, 0), manter=3)
    assert [p.name for p in sorted((tmp_path / "backups").iterdir())] == [
        "2026-10-03-120000", "2026-10-04-120000", "2026-10-05-120000"]
