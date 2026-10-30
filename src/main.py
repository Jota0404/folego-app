"""Ponto de entrada: python -m src.main. Os dados ficam em dados/ (ou na pasta de FOLEGO_PASTA)."""
import sys
from datetime import datetime

from src.folego.armazenamento import (
    ArmazenamentoCorrompido, PastaEmUso, RepositorioJson, fazer_backup, pasta_padrao, travar,
)
from src.folego.menu import executar


def main() -> int:
    pasta = pasta_padrao()
    try:
        with travar(pasta):
            repo = RepositorioJson(pasta)
            fazer_backup(pasta, datetime.now())
            executar(repo, pasta_exportacao=pasta / "exportacoes")
    except (PastaEmUso, ArmazenamentoCorrompido) as erro:
        print(erro, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
