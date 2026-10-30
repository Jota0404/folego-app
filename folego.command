#!/bin/zsh
# Abre o Fôlego com duplo clique (dados em dados/, nesta pasta).
cd "$(dirname "$0")" && python3 -m src.gui
