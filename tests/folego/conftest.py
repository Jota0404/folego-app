"""Sem o PySide6 (como no CI), os testes das telas Qt são ignorados em vez de quebrar a coleta."""
try:
    import PySide6  # noqa: F401
except ImportError:
    collect_ignore_glob = ["test_qt_*.py"]
