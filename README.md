# 💰 Finanças CLI - Gestão Simples de Fluxo de Caixa

Este projeto é uma ferramenta de linha de comando (CLI) desenvolvida para auxiliar no controle financeiro pessoal, permitindo o registro de salários e despesas para cálculo imediato de saldo.

## 🎯 Visão Geral e Problema Real
Muitos profissionais autônomos, estagiários e cidadãos enfrentam dificuldades na organização financeira básica por não possuírem ferramentas leves e rápidas que funcionem offline. A falta de controle sobre entradas (salários) e saídas (despesas) é um dos principais fatores de endividamento. 

O **Finanças CLI** resolve essa "dor" oferecendo uma interface minimalista para cálculos rápidos, garantindo que o usuário tenha clareza sobre sua saúde financeira sem a complexidade de planilhas robustas.

### 👥 Público-Alvo
* Estudantes e estagiários.
* Microempreendedores que precisam de um controle de caixa rápido.
* Usuários que preferem ferramentas de terminal (CLI).

## 🛠️ Tecnologias Utilizadas
* **Linguagem:** Python 3.10+
* **Testes:** Pytest
* **Linting:** Flake8
* **Automação:** GitHub Actions (CI)
* **Versionamento Semântico:** 1.0.0

## 🚀 Como Executar o Projeto

### Pré-requisitos
* Python instalado (versão 3.10 ou superior).
* Gerenciador de pacotes `pip`.

### Instalação
1. Clone o repositório e entre na pasta:
   ```bash
   git clone https://github.com/Jota0404/financas-cli.git
   cd financas-cli
   ```
2. Crie um ambiente virtual (uma "caixinha" só para as dependências deste projeto):
   ```bash
   python -m venv .venv
   ```
3. Ative o ambiente virtual:
   ```bash
   source .venv/bin/activate      # macOS/Linux
   .venv\Scripts\activate         # Windows
   ```
4. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

### Como rodar o CLI antigo
```bash
python src/main.py
```
Obs.: `python -m src.main` não funciona hoje, porque o import em `src/main.py` é `from financas import ...`.

### Testes e lint
```bash
pytest tests/            # roda os testes
flake8 src/ tests/       # confere o estilo (configuração em .flake8)
```

## 🧩 Núcleo de regras (src/folego)
É o port em Python das regras do app Android Fôlego (repositório `financas-app`). Módulos de `src/folego/`:
* `modelos.py`: as estruturas de dados (ciclo, entradas, gastos, contas fixas, metas, configurações).
* `calculadora.py`: cálculos de ciclo, orçamento, limite semanal, painel e fechamento.
* `decisoes.py`: decide o que pode ser salvo, bloqueado ou salvo com aviso.
* `alertas.py`: alertas A1 a A5, quando disparam e o texto de cada um.
* `formatos.py`: valores no formato brasileiro (reais e percentuais), sem usar float.

Dinheiro é sempre em **centavos** (`int`), nunca `float`. Os testes em `tests/folego/` são a melhor documentação das regras (RN e CA).
