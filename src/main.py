"""Ponto de entrada: python -m src.main. Os dados ficam em ~/.folego (ou na pasta de FOLEGO_PASTA)."""
import os
import sys
from datetime import datetime
from pathlib import Path

from src.folego.armazenamento import ArmazenamentoCorrompido, PastaEmUso, RepositorioJson, fazer_backup, travar
from src.folego.menu import executar


def main() -> int:
    pasta = Path(os.environ.get("FOLEGO_PASTA", Path.home() / ".folego"))
    try:
        with travar(pasta):
            repo = RepositorioJson(pasta)
            fazer_backup(pasta, datetime.now())
            executar(repo)
    except (PastaEmUso, ArmazenamentoCorrompido) as erro:
        print(erro, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
