# 💰 Fôlego app

<img src="docs/prints/icone.png" width="72" align="right" alt="Ícone do Fôlego" />

Controle financeiro pessoal que responde, toda semana: **quanto posso gastar sem comprometer as contas fixas e a reserva?**

O Fôlego nasceu como app Android (Kotlin) e agora vive aqui em Python. O núcleo de regras já está pronto e testado; a interface (menu no terminal) e a gravação em disco ainda não existem.

| Início | Novo gasto | Histórico | Cadastros |
| --- | --- | --- | --- |
| <img src="docs/prints/inicio.png" width="200" alt="Início" /> | <img src="docs/prints/novo-gasto.png" width="200" alt="Novo gasto" /> | <img src="docs/prints/historico.png" width="200" alt="Histórico" /> | <img src="docs/prints/cadastros.png" width="200" alt="Cadastros" /> |

*Telas da primeira versão (Android), que servem de referência para a interface.*

## O que o Fôlego calcula
- **Ciclo do salário:** o mês financeiro vai de um pagamento até a véspera do próximo, no dia que você escolher.
- **Reserva antes de tudo:** metas em reais ou em percentual das entradas saem antes de qualquer gasto e nunca aparecem como disponível.
- **Limite da semana:** o que sobra do ciclo é dividido pelos dias que faltam; a barra fica verde, amarela ou vermelha.
- **Contas fixas com parcelas** ("parcela 3 de 10"), entradas recorrentes e avulsas.
- **Alertas** (resumo da semana, 70% e 90% do limite, reserva invadida, fechamento do ciclo), cada um no máximo uma vez por período.
- **Retrato de cada ciclo:** ao fechar, os totais ficam guardados; editar uma conta depois não muda o passado.

A especificação completa (regras RN01 a RN16 e critérios CA01 a CA16) está em [`docs/briefing.md`](docs/briefing.md).

## Núcleo de regras (`src/folego/`)
| Módulo | O que faz |
| --- | --- |
| `modelos.py` | Estruturas de dados: ciclo, entradas, gastos, contas fixas, metas, configurações |
| `calculadora.py` | Ciclo, orçamento, limite semanal, painel e fechamento |
| `decisoes.py` | O que pode ser salvo, bloqueado ou salvo com aviso |
| `alertas.py` | Alertas A1 a A5: quando disparam e o texto de cada um |
| `servicos.py` | Salvar cadastros, configurar e disparar alertas (repositórios são `Protocol`; hoje só em memória, nos testes) |
| `formatos.py` | Reais e percentuais no formato brasileiro, sem `float` |

Dinheiro é sempre em **centavos** (`int`). Os testes em `tests/folego/` são a melhor documentação das regras: o nome de cada teste traz o código da regra (RN) ou do critério (CA).

## Como rodar
Requer Python 3.10+ (testado também em 3.9).
```bash
git clone https://github.com/Jota0404/folego-app.git
cd folego-app
python -m venv .venv
source .venv/bin/activate      # macOS/Linux  (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
pytest tests/                  # testes
flake8 src/ tests/             # estilo (config em .flake8)
```

## Próximos passos
1. Menu no terminal que use `Cadastros`, `Configurar` e `Alertas`.
2. Repositórios que gravem em disco (JSON ou SQLite).

## Histórico
[`docs/andamento.md`](docs/andamento.md) e [`docs/qa/`](docs/qa/) registram a construção da versão Android (7 etapas, 05 a 07/10/2026), que foi concluída e depois substituída por esta versão Python (o código Kotlin não está mais em nenhum repositório).
