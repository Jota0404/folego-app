"""O app Fôlego (janela de desktop): python -m src.app. Dados em dados/ (ou FOLEGO_PASTA)."""
import sys
from datetime import datetime

from src.folego.armazenamento import (
    ArmazenamentoCorrompido, PastaEmUso, RepositorioJson, fazer_backup, pasta_padrao, travar,
)


def main() -> int:
    from PySide6.QtWidgets import QApplication, QMessageBox

    from src.folego.qt.janela import abrir

    app = QApplication(sys.argv)
    app.setApplicationName("Fôlego")
    pasta = pasta_padrao()
    try:
        with travar(pasta):
            repo = RepositorioJson(pasta)
            fazer_backup(pasta, datetime.now())
            janela, _ = abrir(repo, pasta_exportacao=pasta / "exportacoes")
            return app.exec()
    except (PastaEmUso, ArmazenamentoCorrompido) as erro:
        QMessageBox.critical(None, "Fôlego", str(erro))
        return 1


if __name__ == "__main__":
    sys.exit(main())
