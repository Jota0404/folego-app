import subprocess
from dataclasses import replace
from datetime import datetime

from src.folego.armazenamento import ARQUIVOS, RepositorioJson, travar
from src.lembrete import escapar_applescript, executar, notificar_real

from .folego import cenario

AGORA = datetime(2026, 10, 14, 8, 0)  # quarta-feira


class Chamadas:
    def __init__(self):
        self.itens = []

    def __call__(self, titulo, texto):
        self.itens.append((titulo, texto))


def gravar_cenario(pasta):
    repo = RepositorioJson(pasta)
    repo.salvar_entrada(cenario.salario)
    repo.salvar_conta(cenario.aluguel)
    repo.salvar_meta(cenario.reserva)
    repo.atualizar(lambda c: replace(c, primeiro_uso_concluido=True))


def rodar(pasta, notificar):
    return executar(pasta, notificar, AGORA.date(), AGORA)


def test_pasta_sem_dados_nao_notifica_nem_cria_nada(tmp_path):
    chamadas = Chamadas()
    assert rodar(tmp_path / "nao_existe", chamadas) == 0
    assert rodar(tmp_path, chamadas) == 0
    assert chamadas.itens == [] and not (tmp_path / "nao_existe").exists() and list(tmp_path.iterdir()) == []


def test_primeiro_uso_nao_concluido_nao_notifica(tmp_path):
    RepositorioJson(tmp_path).atualizar(lambda c: c)  # só a configuração padrão em disco
    chamadas = Chamadas()
    assert rodar(tmp_path, chamadas) == 0 and chamadas.itens == []


def test_resumo_da_semana_vai_uma_vez_so(tmp_path):
    gravar_cenario(tmp_path)
    chamadas = Chamadas()
    assert rodar(tmp_path, chamadas) == 0
    assert [t for t, _ in chamadas.itens] == ["Resumo da semana"]
    assert rodar(tmp_path, chamadas) == 0
    assert len(chamadas.itens) == 1


def test_pasta_travada_sai_em_silencio(tmp_path):
    gravar_cenario(tmp_path)
    chamadas = Chamadas()
    with travar(tmp_path):
        assert rodar(tmp_path, chamadas) == 0
    assert chamadas.itens == []


def test_arquivo_corrompido_retorna_1_sem_alterar(tmp_path, capsys):
    gravar_cenario(tmp_path)
    (tmp_path / "orcamento.json").write_text("{ quebrado")
    antes = {n: (tmp_path / n).read_bytes() for n in ARQUIVOS if (tmp_path / n).exists()}
    chamadas = Chamadas()
    assert rodar(tmp_path, chamadas) == 1
    assert chamadas.itens[0][0] == "Fôlego: dados com problema"
    assert "O arquivo não foi alterado" in capsys.readouterr().err
    assert antes == {n: (tmp_path / n).read_bytes() for n in antes}


def test_falha_ao_notificar_nao_derruba_a_rotina(tmp_path, capsys):
    gravar_cenario(tmp_path)

    def quebrado(titulo, texto):
        raise RuntimeError("sem permissão")

    assert rodar(tmp_path, quebrado) == 0
    assert "sem permissão" in capsys.readouterr().err


def test_escape_do_applescript():
    assert escapar_applescript('a "b" \\ c\nd') == 'a \\"b\\" \\\\ c d'


def test_notificador_real_escapa_e_chama_osascript(monkeypatch):
    chamadas = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: chamadas.append(args))
    notificar_real('T"', 'x" & (do shell script "ls") & "')
    script = chamadas[0][2]
    assert chamadas[0][:2] == ["osascript", "-e"]
    assert script == 'display notification "x\\" & (do shell script \\"ls\\") & \\"" with title "T\\""'


def test_sem_osascript_imprime_no_terminal(monkeypatch, capsys):
    def sem_osascript(*args, **kw):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", sem_osascript)
    notificar_real("Título", "texto")
    assert capsys.readouterr().out == "Título: texto\n"
