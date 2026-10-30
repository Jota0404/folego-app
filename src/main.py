"""Ponto de entrada: python -m src.main. Os dados ficam em ~/.folego (ou na pasta de FOLEGO_PASTA)."""
import os
import sys
from pathlib import Path

from src.folego.armazenamento import ArmazenamentoCorrompido, RepositorioJson
from src.folego.menu import executar


def main() -> int:
    pasta = Path(os.environ.get("FOLEGO_PASTA", Path.home() / ".folego"))
    try:
        repo = RepositorioJson(pasta)
    except ArmazenamentoCorrompido as erro:
        print(erro, file=sys.stderr)
        return 1
    executar(repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
