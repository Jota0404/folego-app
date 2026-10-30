#!/bin/zsh
# Abre o Fôlego com duplo clique (dados em dados/, nesta pasta).
cd "$(dirname "$0")" && .venv/bin/python -m src.app
