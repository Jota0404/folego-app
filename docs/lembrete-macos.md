# Lembrete diário no macOS

Hoje os alertas só aparecem quando você abre o Fôlego. O `src/lembrete.py` faz o
mesmo trabalho sozinho: fecha ciclos, e manda o resumo da semana e os avisos de
limite como notificação do macOS. Se o Fôlego estiver aberto na hora, o lembrete
não faz nada (o app já mostra os alertas). Cada aviso sai uma vez só por período,
então abrir o app depois não repete.

**Nada é instalado automaticamente.** Você copia o arquivo abaixo e roda os comandos.

## Testar à mão

Na pasta do projeto:

```
python3 -m src.lembrete
```

Sem erro, o código de saída é 0. Dados com problema dão saída 1 e uma mensagem
no terminal. Para usar outra pasta de dados: `FOLEGO_PASTA=/caminho python -m src.lembrete`.
A primeira vez que o macOS mostrar uma notificação, pode ser preciso permitir
notificações do "Script Editor" ou do terminal em Ajustes do Sistema > Notificações.

## Agendar todo dia com o launchd

Crie o arquivo `~/Library/LaunchAgents/com.folego.lembrete.plist`. Troque
`SEU_USUARIO` pelo seu usuário e confira os caminhos:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.folego.lembrete</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>src.lembrete</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/SEU_USUARIO/Documents/Projetos/folego-app</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/SEU_USUARIO/.folego/lembrete.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/SEU_USUARIO/.folego/lembrete.log</string>
</dict>
</plist>
```

O launchd não entende `~`: use sempre o caminho completo. A pasta `~/.folego`
precisa existir (ela é criada na primeira vez que você usa o Fôlego).

### Ligar

```
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.folego.lembrete.plist
```

Para rodar agora, sem esperar as 8h:

```
launchctl kickstart gui/$(id -u)/com.folego.lembrete
```

### Desligar

```
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.folego.lembrete.plist
```

Depois, se quiser, apague o arquivo `.plist`. Se mudar o plist, desligue e ligue de novo.

## O que saber

- O horário do plist é fixo (8h00). A configuração "hora do resumo" do menu **não** muda o
  agendamento hoje. Para outro horário, edite `Hour` e `Minute` e religue.
- O Mac precisa estar ligado nessa hora. Se estiver dormindo, o launchd roda o lembrete
  quando ele acordar; se estiver desligado, o dia é pulado.
- Erros e mensagens ficam em `~/.folego/lembrete.log`.
