"""Lembrete diário: python -m src.lembrete. Roda a rotina diária de alertas fora do menu
(feito para ser agendado, ver docs/lembrete-macos.md). Usa a mesma pasta do main.py."""
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

from src.folego.alertas import mensagem
from src.folego.armazenamento import ARQUIVOS, ArmazenamentoCorrompido, PastaEmUso, RepositorioJson, travar
from src.folego.decisoes import mostrar_primeiro_uso
from src.folego.servicos import Alertas

Notificar = Callable[[str, str], None]


def escapar_applescript(texto: str) -> str:
    """Texto seguro para ficar entre aspas num script do AppleScript."""
    return texto.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")


def notificar_real(titulo: str, texto: str) -> None:
    """Notificação do macOS; sem osascript (outras plataformas), escreve no terminal."""
    try:
        script = f'display notification "{escapar_applescript(texto)}" with title "{escapar_applescript(titulo)}"'
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=30)
    except FileNotFoundError:
        print(f"{titulo}: {texto}")
    except (subprocess.SubprocessError, OSError) as erro:
        print(f"Não foi possível notificar: {erro}", file=sys.stderr)


class _Notificador:
    def __init__(self, notificar: Notificar):
        self._notificar = notificar

    def avisar(self, alerta) -> None:
        m = mensagem(alerta)
        try:
            self._notificar(m.titulo, m.texto)
        except Exception as erro:  # falhar ao avisar não derruba a rotina
            print(f"Não foi possível notificar: {erro}", file=sys.stderr)


def executar(pasta, notificar: Notificar, hoje: Optional[date] = None, agora: Optional[datetime] = None) -> int:
    pasta = Path(pasta)
    if not any((pasta / nome).is_file() for nome in ARQUIVOS):
        return 0  # sem dados (e sem criar a pasta)
    hoje = hoje or date.today()
    agora = agora or datetime.now()
    try:
        with travar(pasta):
            repo = RepositorioJson(pasta)
            if mostrar_primeiro_uso(repo.configuracoes(), repo.orcamento()):
                return 0
            Alertas(repo, repo, repo, _Notificador(notificar)).rotina_diaria(hoje, agora)
    except PastaEmUso:
        return 0  # o Fôlego está aberto e já mostra os alertas
    except ArmazenamentoCorrompido as erro:
        print(erro, file=sys.stderr)
        try:
            notificar("Fôlego: dados com problema", "Abra o Fôlego no terminal para ver o que aconteceu.")
        except Exception as falha:
            print(f"Não foi possível notificar: {falha}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    pasta = Path(os.environ.get("FOLEGO_PASTA", Path.home() / ".folego"))
    return executar(pasta, notificar_real, date.today(), datetime.now())


if __name__ == "__main__":
    sys.exit(main())
