"""Janela do Fôlego: python -m src.gui. Mesmos dados do menu de terminal (dados/ ou FOLEGO_PASTA)."""
import sys
from datetime import datetime

from src.folego.armazenamento import (
    ArmazenamentoCorrompido, PastaEmUso, RepositorioJson, fazer_backup, pasta_padrao, travar,
)
from src.folego.gui.app import abrir


def main() -> int:
    pasta = pasta_padrao()
    try:
        with travar(pasta):
            repo = RepositorioJson(pasta)
            fazer_backup(pasta, datetime.now())
            raiz, _ = abrir(repo, pasta_exportacao=pasta / "exportacoes")
            raiz.mainloop()
    except (PastaEmUso, ArmazenamentoCorrompido) as erro:
        print(erro, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
