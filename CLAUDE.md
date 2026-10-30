# CLAUDE.md — Regras do projeto

Fôlego app: controle financeiro pessoal por ciclo de salário, em Python (`src/folego/`).
Nasceu como app Android (Kotlin); a versão Python é a que continua.

## Comunicação
- Responder em **português**, em linguagem simples.

## Fonte da verdade
- Ler `docs/briefing.md` antes de qualquer tarefa: as regras RN e os critérios CA valem.
- Regra ambígua: perguntar ao dono antes de implementar e registrar a decisão no briefing.
- Nunca mudar uma regra de negócio sem atualizar o briefing na mesma entrega.
  Depois de editar o briefing, conferir com `git diff --stat docs/briefing.md`.
- `docs/andamento.md` e `docs/qa/` são o histórico da versão Android; só leitura.

## Regras técnicas
- Dinheiro sempre em **centavos (`int`)**, nunca `float`. Percentuais em pontos-base (1000 = 10%).
- Divisão de centavos com `//` (arredonda para baixo, RN13), nunca `int(a / b)`.
- O núcleo (`src/folego/`) nunca lê o relógio: `hoje` e `agora` chegam como parâmetro.
- Decisões de regra (bloquear, avisar, fechar ciclo) saem prontas do núcleo, com teste;
  interface e repositórios só aplicam o resultado. Vale também para **editar**.

## Testes
- Cada RN e CA tem teste automatizado com o código no nome (`test_rn13_...`, `test_ca06_...`).
- Rodar antes de cada push: `pytest tests/` e `flake8 src/ tests/` (config em `.flake8`).
- Compatível com Python 3.9+ (o CI usa 3.10).
