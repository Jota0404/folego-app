import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def rodar(pasta, entrada):
    return subprocess.run(
        [sys.executable, "-m", "src.main"], input=entrada, text=True, capture_output=True,
        cwd=RAIZ, env={**os.environ, "FOLEGO_PASTA": str(pasta)},
    )


def test_primeiro_uso_grava_em_disco_e_reabre_com_os_dados(tmp_path):
    primeira = rodar(tmp_path, "1\n3000\n2\n150,50\n\n\n\n0\n")
    assert primeira.returncode == 0 and "Gasto salvo." in primeira.stdout
    segunda = rodar(tmp_path, "1\n0\n")
    assert segunda.returncode == 0 and "Disponível do ciclo: R$ 2.849,50" in segunda.stdout


def test_arquivo_corrompido_aborta_sem_sobrescrever(tmp_path):
    (tmp_path / "orcamento.json").write_text("{ quebrado")
    r = rodar(tmp_path, "0\n")
    assert r.returncode == 1 and "O arquivo não foi alterado" in r.stderr
    assert (tmp_path / "orcamento.json").read_text() == "{ quebrado"
