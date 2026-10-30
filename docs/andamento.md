# Andamento do projeto

Atualizado em 07/10/2026.

**Projeto concluído:** as 7 etapas do roteiro do MVP foram entregues, revisadas pelo QA e aprovadas
pelo dono (a última em 07/10/2026).

A especificação completa está em [`briefing.md`](briefing.md). Este arquivo só registra até onde o projeto chegou.

## Roteiro

| Etapa | Situação |
| --- | --- |
| 1. Setup | ✅ Concluída e aprovada em 05/10/2026 |
| 2. Domínio (só Kotlin puro, RN01 a RN15) | ✅ Concluída e aprovada em 05/10/2026 |
| 3. Persistência (Room, DAOs, DataStore) | ✅ Concluída e aprovada em 06/10/2026 |
| 4. Cadastros | ✅ Concluída e aprovada em 06/10/2026 |
| 5. Gastos e Início | ✅ Concluída e aprovada em 06/10/2026 |
| 6. Alertas e fechamento de ciclo | ✅ Concluída e aprovada em 07/10/2026 |
| 7. Onboarding, configurações e acabamento | ✅ Concluída e aprovada em 07/10/2026 |

## O que já existe (Etapa 1)

- Projeto Android em Kotlin + Jetpack Compose (Material 3), minSdk 26.
- Hilt configurado (`FinancasApplication` e `MainActivity`).
- Dois módulos Gradle:
  - `:app`: o aplicativo Android (telas, dados, alertas, Hilt).
  - `:domain`: as regras de negócio, em Kotlin puro. Ele não enxerga o Android, então o
    compilador recusa qualquer `import android.*` nele. O `:app` depende do `:domain`,
    nunca o contrário.
- Estrutura de pastas da arquitetura criada, ainda vazia (ver README).
- Backup automático do Android ligado (`allowBackup`), conforme a RN16, com um teste no aparelho
  (`BackupTest`) que confere isso.
- GitHub Actions roda, a cada push na `main`, os testes unitários de todos os módulos, gera o APK
  de teste e roda o lint (`./gradlew test assembleDebug lintDebug`).
- Sobras do modelo do Android Studio removidas: itens 1 a 12 da primeira revisão do QA e, no
  começo da Etapa 2, o teste de exemplo, as cores roxas e as bibliotecas de pré-visualização
  (B1, B2 e itens 2, 4 e 5 do Ponytail). O tema usa as cores padrão do Material 3 até a Etapa 7.
- Agentes `qa` e `coder` em `.claude/agents/`, e skills `/verificar`, `/testar-emulador` e
  `/cobertura-rn-ca` em `.claude/skills/`, usadas pelos dois.

**Resultado verificado:** o app compila e abre uma tela vazia num celular físico (Galaxy A56),
seguindo o tema claro ou escuro do aparelho, sem erros.

## O que já existe (Etapa 2)

Os cálculos do app, no módulo `:domain`, sem banco e sem tela (ainda não aparecem no app):

| Arquivo | Calcula | Regras |
| --- | --- | --- |
| `model/Modelos.kt` | Ciclo, Entrada, ContaFixa, MetaReserva e Gasto | — |
| `calculadora/Ciclos.kt` | Ciclo de cada data e mudança do dia do pagamento | RN01, RN02 |
| `calculadora/Orcamento.kt` | Contas ativas, reserva, disponível, quanto falta para as metas e reserva invadida | RN03 a RN09, RN13 |
| `calculadora/LimiteSemanal.kt` | Limite da semana, automático e manual, e o aviso de ritmo | RN10 a RN13 |
| `usecase/Validacoes.kt` | Bloqueio de gasto por data e valor; valor positivo em qualquer cadastro | RN14, RN15 |

## O que já existe (Etapa 3)

Os dados do app passam a ser guardados no celular (ainda sem tela para cadastrar):

| Onde | O que faz |
| --- | --- |
| `domain/.../repository/Repositorios.kt` | O que o domínio precisa dos dados: orçamento, histórico e configurações (P11) |
| `data/local/` | Banco Room com as 7 tabelas do briefing; nasce com as 5 categorias padrão |
| `data/repository/RoomRepositorios.kt` | Salva, exclui e avisa a tela a cada mudança (Flow) |
| `data/datastore/` | Configurações: dia do pagamento, ciclo irregular (P14), limite manual, alertas |
| `di/DadosModule.kt` | Hilt: liga as interfaces do domínio às implementações |
| `app/schemas/1.json` | Esquema da versão 1 do banco, para as migrações futuras |

Os modelos do domínio ganharam os campos que faltavam (id, descrição, nome, vencimento e categoria).
A regra da P14 (qual é o ciclo atual depois de mudar o dia do pagamento) ficou no domínio.

**Backup (RN16), checagem manual no emulador:** com arquivos de teste nas pastas do banco e das
configurações, o backup do Android (`bmgr backupnow`) funcionou, e depois de desinstalar e
reinstalar o app os dois arquivos voltaram com o conteúdo original. Observação: o Android só faz
backup de um app que já foi aberto pelo menos uma vez depois de instalado.

## O que já existe (Etapa 4)

As primeiras telas. O app abre com a navegação de baixo nas quatro abas do briefing; Início,
Histórico e Configurações ainda mostram em que etapa chegam. A aba **Cadastros** tem três telas:

| Tela | O que faz |
| --- | --- |
| Contas fixas | Lista com valor, vencimento e situação ("Parcela 3 de 10", "Sem fim", "Terminou", "Encerrada"). Cadastrar, editar, encerrar (sempre) e excluir (só a conta que começa no ciclo atual, RN04/P17) |
| Entradas | Recorrentes e avulsas separadas. A recorrente vem com o início do ciclo atual; a avulsa, com hoje, e só aceita datas do ciclo atual até hoje |
| Metas de reserva | Valor efetivo no ciclo atual (ex.: "10% das entradas · R$ 300,00 neste ciclo"). Pausar com a chave "Ativa" |

As decisões saem prontas do domínio (`usecase/Cadastros.kt`), e a tela só aplica:
- RN15 em todo cadastro, mais nome obrigatório, vencimento de 1 a 31, duração e parcela válidas;
- RN08: a meta que não cabe é bloqueada com quanto falta (CA04: "faltam R$ 500,00"); a conta ou
  entrada que deixa as metas sem caber é salva com aviso; sem meta ativa, não há aviso.

Valores em reais e percentuais são lidos e mostrados no formato brasileiro, sem `Double`
(`domain/.../formato/Formatos.kt`). Toda lista vazia orienta: "Nenhuma conta fixa ainda. Toque
em + para adicionar."

**Visto no emulador (Android 17), nos temas claro e escuro:** cenário base cadastrado pela tela
(aluguel, celular de 3 meses, salário e reserva de 10%); a meta de R$ 2.000,00 foi bloqueada com
"faltam R$ 500,00"; nenhum travamento no log.

## O que já existe (Etapa 5)

O app já faz o ciclo principal: cadastrar, registrar gastos e ver quanto pode gastar.

| Tela | O que faz |
| --- | --- |
| Início (tela 2) | Disponível da semana em destaque e o limite com as datas da semana. Barra de consumo verde, amarela ou vermelha, nos mesmos pontos dos alertas A2 e A3 (padrão 70% e 90%). Disponível do ciclo, valor protegido na reserva e reserva invadida. Com limite zero, a barra fica cheia e explica que o disponível do ciclo acabou. Botão "+" para novo gasto |
| Novo gasto (tela 3) | O teclado numérico abre direto no valor; data padrão hoje; categoria padrão Outros; descrição opcional. Registrar leva 2 toques ("+" e "Salvar", CA12). Um gasto que invade a reserva é salvo, e o app avisa na hora (RN09) |
| Histórico (tela 7) | Gastos do ciclo atual agrupados por dia, com o total de cada dia. Tocar num gasto corrige ou exclui, com a RN14 e a RN15 também na edição. Avulsas de ciclos fechados aparecem só para consulta (P18). Os ciclos fechados aparecem a partir da Etapa 6 |

O painel do Início é calculado num lugar só, no domínio (`calculadora/Painel.kt`), e as decisões de
gasto também (`decidirGasto` e `decidirExclusao` em `usecase/Cadastros.kt`). A data de hoje se
atualiza sozinha na virada do dia, com o app aberto ou ao voltar para ele.

**Visto no emulador (Android 17):** com o cenário base, o Início mostrou R$ 388,88 na semana de
05/10 a 11/10 (CA05), R$ 1.500,00 no ciclo (CA01) e R$ 300,00 na reserva; o teclado abriu direto no
valor; um gasto de R$ 45,00 em 2 toques; e, com mais R$ 1.555,00 (total de R$ 1.600,00), o aviso
"a reserva deste ciclo está invadida em R$ 100,00" (CA03). Temas claro e escuro sem travamentos.

## O que já existe (Etapa 6)

O app avisa sozinho e guarda o retrato de cada ciclo.

| Alerta | Quando chega |
| --- | --- |
| A1 — Resumo da semana | Uma vez por semana, por volta das 08:00 de segunda; se a rotina de segunda não rodou, chega no primeiro dia em que ela rodar na mesma semana |
| A2 — 70% do limite | Ao registrar um gasto que faz a semana atingir o percentual de atenção; uma vez por parte da semana |
| A3 — 90% do limite | O mesmo, no percentual crítico; num salto direto, só o A3 chega (o A2 conta como enviado). Com limite zero, nem A2 nem A3 |
| A4 — Reserva invadida | Ao registrar ou corrigir um gasto que aumenta a invasão da reserva; uma vez por gasto |
| A5 — Ciclo fechado | No dia do pagamento, por volta das 08:00: quanto sobrou e quanto da reserva foi guardado. Um só, do ciclo mais recente, mesmo atrasado |

- A decisão de cada alerta sai do domínio (`usecase/Alertas.kt`), e o registro de alertas
  (RegistroAlerta) garante que nenhum se repete no mesmo período.
- **Fechamento do ciclo (CicloFechado):** ao abrir o app e na rotina diária, os ciclos que já
  terminaram ganham um retrato com os totais (RN05), inclusive os que terminaram com o app parado,
  a partir do primeiro ciclo com gastos. O retrato guarda a reserva invadida do momento. O banco
  (versão 2, com migração automática) recusa fechar o mesmo ciclo duas vezes.
- **Rotina diária:** o WorkManager roda uma vez por dia, por volta do horário do resumo, e agenda o
  dia seguinte. A permissão de notificação é pedida ao abrir o app (Android 13+); sem ela, os
  alertas ficam registrados, mas não aparecem.

**Visto no emulador (Android 17):** o pedido de permissão ao abrir o app; com salário de R$ 3.000,00
e gastos de R$ 677,77 na semana (limite de R$ 777,77), a notificação "70% do limite da semana"; ao
forçar a rotina diária, a notificação "Resumo da semana", que não se repetiu na segunda rodada.

## O que já existe (Etapa 7)

O app ficou completo, com as oito telas do briefing.

| Tela ou item | O que faz |
| --- | --- |
| Primeiro uso (tela 1) | Assistente em 5 passos: dia do pagamento (padrão 1), salário, contas fixas, metas e permissão de notificação. Os passos 2 a 5 podem ser pulados. Aparece até ser concluído; quem já tem entradas não o vê. O dia escolhido já define o ciclo normal |
| Configurações (tela 8) | Dia do pagamento (com aviso do efeito no ciclo, RN01 e P14), limite manual (vazio = automático), percentuais de atenção e crítico (atenção menor que crítico), horário dos resumos (reagenda a rotina) e o estado das notificações, com atalho para o Android |
| Ícone e cores | Ícone "respiro" (três ondas brancas sobre verde), com versão temática. Verde como cor do app nos celulares sem cor dinâmica. No modo escuro, a abertura já é escura (sem clarão) |
| APK final | Assinado com a chave do Mac do dono, fora do Git (`keystore.properties` e `~/.android/folego-release.jks`). Gerado com `./gradlew assembleRelease` |
| README | Prints, o que o app faz, como rodar, testar e gerar o APK |

**Visto no emulador (Android 17), com o APK final assinado:** primeiro uso completo (dia, salário,
aluguel, reserva de 10% e permissão), Início com R$ 440,74 de limite na semana, gasto de R$ 350,00
com a notificação "70% do limite da semana", rotina diária forçada com o "Resumo da semana" e o
reagendamento, todas as abas abertas, temas claro e escuro, sem travamentos. **Achado nesta etapa:**
desde a Etapa 1, o APK final travava ao abrir por causa de uma configuração do otimizador (R8); foi
corrigido, e o APK final passou a ser conferido no emulador.

## Versões principais

| Item | Versão |
| --- | --- |
| Android Gradle Plugin | 9.4.1 |
| Gradle | 9.8.0 |
| Kotlin | 2.4.20 |
| Compose BOM | 2026.09.00 |
| Hilt | 2.60.1 |
| core-ktx | 1.19.1 |
| activity-compose | 1.13.0 |
| Room | 2.8.5 |
| DataStore | 1.2.1 |
| Lifecycle (Compose) | 2.11.0 |
| Hilt para Compose | 1.4.0 |
| WorkManager | 2.12.0 |
| Hilt para workers | 1.4.0 |
| Robolectric (testes) | 4.17 |
| compileSdk / targetSdk | 37 |

## Testes

- **Domínio:** 155 testes unitários, todos passando, em `domain/src/test/kotlin/.../domain/`. Cada
  RN de RN01 a RN15 tem teste com o código no nome, e os critérios CA01 a CA07, CA09, CA10 e
  CA13 a CA16 estão em `CriteriosDeAceiteTest.kt`, com o cenário base do briefing
  (`CenarioBase.kt`) e os valores exatos em centavos. O CA08 e o CA11 estão em `AlertasTest.kt`.
- **App:** 59 testes em `app/src/test/`: persistência (banco, repositórios, DataStore, migração
  do banco e o CA11 com o banco de verdade), telas (Cadastros, Início, Novo gasto, Histórico, primeiro
  uso e Configurações, entre eles o CA12 e o CA03), virada do dia, notificação e rotina diária. Rodam no computador com
  Robolectric, sem aparelho, e por isso também no GitHub Actions.
- **No aparelho:** 2 testes instrumentados, `BackupTest` (RN16) e `RegistrarGastoTest` (CA12, com o
  app de verdade e o banco em memória, sem ler nem gravar os dados reais). Rodam **só no
  emulador**: `ANDROID_SERIAL=emulator-5554 ./gradlew connectedDebugAndroidTest`. O app continua
  instalado depois dos testes. Não rodam no GitHub Actions, porque precisam de um aparelho.
- Todos os RN e CA do briefing têm teste.

## Pendências e observações

- Revisão completa do QA ([`qa/2026-10-05-etapa-1.md`](qa/2026-10-05-etapa-1.md)): Etapa 1
  aprovada com ressalvas, sem itens Críticos ou Altos. M1 e M2 já resolvidos (Git configurado e
  agente de QA com acesso às skills). B4 resolvido: o app passou a se chamar **Fôlego**.
  B1, B2, B5 a B8 e os itens 2, 4 e 5 do Ponytail foram resolvidos no começo da Etapa 2.
  B3 (clarão branco ao abrir no modo escuro) e o item 3 do Ponytail (ícones `.webp` sem uso)
  foram resolvidos na Etapa 7.
- Mudança no briefing nesta etapa: criada a **RN16** (backup do Android permitido, não conta como
  nuvem do app), e o domínio passou a ser o módulo `:domain`.
- Decisões do dono sobre as propostas do QA (P1 a P10), registradas no briefing: a RN08 soma todas
  as metas (CA04 agora diz R$ 500,00); o limite semanal passa a ser proporcional aos dias que
  faltam no ciclo (RN11; CA05 agora R$ 388,88 e CA08 R$ 272,22); novos CA13 a CA15. Depois, o
  limite manual (RN12) também passou a ser proporcional nas semanas partidas do começo e do fim
  do ciclo (novo CA16: R$ 500,00 viram R$ 285,71 de 01 a 04/10). A P11 (onde
  ficam as interfaces dos repositórios) fica a critério do desenvolvedor na Etapa 3.
- Decisões do dono no começo da Etapa 2, registradas no briefing: mudar o dia do pagamento para o
  próprio dia de hoje fecha o ciclo ontem e abre um novo hoje (RN01); a duração de uma conta fixa
  conta os ciclos pelo mês em que começam (RN03); uma conta encerrada no meio do ciclo ainda é
  descontada nele e sai a partir do seguinte (RN04).
- A RN05 está testada só na parte de cálculo: editar o valor de uma conta muda o ciclo atual e os
  futuros. A parte "nunca muda ciclos já fechados" depende do retrato do ciclo (CicloFechado), que
  é criado na Etapa 6 e testado pelo CA11.
- Revisão do QA da Etapa 2 ([`qa/2026-10-05-etapa-2.md`](qa/2026-10-05-etapa-2.md)): aprovada com
  ressalvas, sem itens Críticos ou Altos. Corrigidos M1 (mudança do dia do pagamento no primeiro
  dia do ciclo agora diz qual ciclo fecha), M2 e M3 (conforme as decisões P12 e P13) e B3. O B1
  (bloquear ou só avisar ao salvar meta, no domínio) fica para a Etapa 4.
- Decisões do dono sobre P12 a P16, registradas no briefing: reserva invadida só por gasto (RN09);
  salário recorrente a partir do primeiro pagamento; `inicioCicloAtual` e `fimCicloAtual` nas
  configurações depois de uma mudança do dia do pagamento (o dono escolheu guardar também o fim,
  porque só o início não identifica o ciclo); limitação aceita da mudança que pula um mês (RN03);
  o que "fixo" quer dizer no limite semanal (RN11).
- Revisão do QA da Etapa 3 ([`qa/2026-10-06-etapa-3.md`](qa/2026-10-06-etapa-3.md)): aprovada com
  ressalvas, sem itens Críticos ou Altos. O M1 (salvar configurações com o arquivo do DataStore
  corrompido) foi resolvido no começo da Etapa 4; B1 e B2 ficam para a Etapa 6. Decisão do dono sobre a P17,
  registrada no briefing (RN04): conta fixa que já foi descontada é encerrada, não excluída;
  excluir só serve para conta cadastrada por engano.
- O B1 da Etapa 2 (o domínio decide se bloqueia ou só avisa ao salvar meta) foi feito na Etapa 4,
  e o CA04 passou a conferir o bloqueio.
- Decisões do dono no começo da Etapa 4, registradas no briefing: conta com duração informa a
  parcela do ciclo atual; entrada recorrente vem com o início do ciclo atual; entrada avulsa só
  aceita datas do ciclo atual até hoje (como a RN14); só se exclui conta que começa no ciclo atual;
  sem meta ativa, salvar conta ou entrada não avisa (RN08).
- Revisão do QA da Etapa 4 ([`qa/2026-10-06-etapa-4.md`](qa/2026-10-06-etapa-4.md)): aprovada com
  ressalvas, sem itens Críticos ou Altos. Corrigidos no começo da Etapa 5: M1 (editar a duração de
  uma conta antiga não pode tirá-la do ciclo atual: "Para tirar a conta deste ciclo, encerre"), M2
  ("1500.50" é aceito, e texto que não é número tem mensagem própria), B1 (formulários sobrevivem a
  girar o celular), B2 (o dia de hoje se atualiza sozinho) e B3 (o + diz o que adiciona). Decisão do dono sobre a P18, registrada no briefing: a lista de Entradas mostra só as
  avulsas do ciclo atual; as de ciclos fechados aparecem no Histórico, só para consulta (resolve o B4).
- Decisões do dono no começo da Etapa 5, registradas no briefing: gastos são corrigidos e excluídos
  tocando no Histórico; com limite zero, a barra fica cheia e vermelha com explicação; o gasto que
  invade a reserva avisa na hora; as cores da barra seguem os percentuais dos alertas; no CA12,
  digitar o valor não conta como toque.
- Revisão do QA da Etapa 5 ([`qa/2026-10-06-etapa-5.md`](qa/2026-10-06-etapa-5.md)): aprovada com
  ressalvas, sem itens Críticos ou Altos. **Atenção:** `connectedDebugAndroidTest` desinstala o app
  no fim e apaga os dados dele. Rodar só no emulador:
  `ANDROID_SERIAL=emulator-5554 ./gradlew connectedDebugAndroidTest`, nunca com o celular do dono
  conectado. Corrigidos no começo da Etapa 6: M1 (o teste do CA12 usa banco em memória, e os testes
  no aparelho não desinstalam mais o app), B1 (sem cadastros, o Início mostra só o convite) e B2
  (ciclos que terminaram antes da Etapa 6 também são fechados). Da Etapa 3, B1 (o retrato guarda a
  reserva invadida) e B2 (mudar o dia do pagamento fecha o ciclo junto).
- Decisões do dono no começo da Etapa 6, registradas no briefing (seção Alertas): permissão na
  primeira abertura; A1 e A5 por volta das 08:00; o A5 diz quanto foi guardado; com o app parado,
  fecha tudo depois e manda um A5 só; só o A3 no salto; sem A2 e A3 com limite zero; A4 também ao
  corrigir um gasto.
- O retrato de um ciclo fechado com atraso usa os cadastros do momento do fechamento. Se uma conta
  for editada antes de o app rodar na virada, a edição entra no retrato do ciclo anterior.
- Atalho do Ponytail que continua: `FinancasDao.kt:30` carrega os gastos de todos os ciclos
  (filtrar por data se o histórico pesar). O de `FolegoApp.kt` ("em breve") saiu na Etapa 7.
- O GitHub avisou que o runner `ubuntu-latest` passa para o Ubuntu 26 a partir de 19/10/2026.
  Não exige ação agora: vale conferir se os testes continuam passando depois dessa data.

- Revisão do QA da Etapa 6 ([`qa/2026-10-07-etapa-6.md`](qa/2026-10-07-etapa-6.md)): reprovada só pelo
  C1 (uma edição do desenvolvedor no `f70d14d` apagou metade do briefing). **C1 resolvido:** o briefing
  foi restaurado (`12e8baa`), com as 10 seções e os critérios CA01 a CA16; comparado com a versão
  anterior ao corte (`a0ea684`), só mudaram a linha da versão, as decisões dos alertas e a P19. Com
  isso, a Etapa 6 ficou aprovada com ressalvas e foi aprovada pelo dono em 07/10/2026. Decisão do dono
  sobre a P19, registrada no briefing (seção Alertas): o A1 chega na primeira rotina da semana; o A4
  dispara quando a reserva fica mais invadida; um ciclo fechado com atraso usa os cadastros do
  momento do fechamento. Corrigidos no começo da Etapa 7: M1 (o fechamento ao abrir o app fica
  protegido, e a rotina é agendada mesmo se ele falhar) e B3 (a rotina diária também confere A2 e A3).
  O B1 é do script de cobertura, que é do QA.
- Decisões do dono no começo da Etapa 7, registradas no briefing: passos do primeiro uso podem ser
  pulados; o dia escolhido no primeiro uso define o ciclo normal; ícone "respiro" verde; chave de
  assinatura e senha só no Mac; APK só no Mac, sem publicar; atenção menor que crítico. O DataStore
  ganhou `primeiroUsoConcluido`, registrado no modelo de dados.
- **Antes de instalar o APK final no celular:** o app instalado pelo botão Run (versão de teste) tem
  outra assinatura, e o Android só aceita a troca desinstalando, o que apaga os dados. Guarde também
  uma cópia da chave (`~/.android/folego-release.jks`) e do `keystore.properties` num lugar seguro.
- Revisão do QA da Etapa 7 ([`qa/2026-10-07-etapa-7.md`](qa/2026-10-07-etapa-7.md)): aprovada com
  ressalvas, sem itens Críticos, Altos ou Médios. O APK final assinado foi conferido no emulador. As
  duas ressalvas foram resolvidas depois da aprovação: o script de cobertura conta só as RN e os CA
  definidos no briefing e avisa se não achar nenhum (B1 das Etapas 6 e 7), e o GitHub Actions também
  gera o APK final, sem assinatura (B2).

## Próximo passo

O roteiro do MVP terminou. Ficam com o dono: guardar a cópia da chave e da senha fora do Mac e
instalar o APK final no celular antes de começar a usar o app de verdade. Melhorias depois do MVP
(as "versões futuras" do briefing) começam por uma conversa no chat do Briefing.
