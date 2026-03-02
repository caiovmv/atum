# Feeds RSS e agendamento

## O que são feeds no dl-torrent

O dl-torrent permite inscrever-se em **feeds RSS de torrents de música**. Cada feed é uma URL que retorna uma lista de torrents (geralmente as últimas adições de um site ou categoria). O comando `feed poll` lê esses feeds, filtra por qualidade (igual à busca), opcionalmente por palavras-chave (`--include` e `--exclude`) e pode listar ou baixar automaticamente os itens novos.

## Comandos de feed

- **`dl-torrent feed add "URL"`** — Inscreve em um feed (a URL do RSS).
- **`dl-torrent feed list`** — Lista os feeds inscritos.
- **`dl-torrent feed poll`** — Verifica todos os feeds, mostra itens novos que passam no filtro de qualidade. Itens já vistos não são mostrados de novo.
- **`dl-torrent feed poll --auto-download`** — Igual ao `poll`, mas envia os novos itens aceitáveis para o cliente configurado (Transmission/uTorrent/pasta) ou para download direto, conforme sua configuração.
- **`dl-torrent feed poll --auto-download --format flac,320`** — Restringe a FLAC e MP3 320 (ou outros formatos listados).
- **`dl-torrent feed poll --include "FLAC" --exclude "bootleg,mix"`** — Só itens cujo título contém alguma palavra de `--include` e não contém nenhuma de `--exclude` (palavras separadas por vírgula).
- **`dl-torrent feed daemon --interval 30 --auto-download`** — Fica em loop fazendo poll a cada 30 minutos (Ctrl+C para sair). Alternativa ao cron ou Agendador de Tarefas quando você quer deixar o dl-torrent rodando.

Se **notificação** estiver habilitada no `.env` (`NOTIFY_ENABLED`, `NOTIFY_WEBHOOK_URL` e/ou `NOTIFY_DESKTOP`), ao detectar um item novo o dl-torrent envia um POST para o webhook e/ou mostra notificação na área de trabalho. Veja [Configuração](configuration.md#organização-e-notificação-opcional).

## Agendamento do poll

Para verificar os feeds periodicamente sem deixar o dl-torrent rodando o tempo todo, use o agendador do sistema.

### Windows (Agendador de Tarefas)

1. Abra o **Agendador de Tarefas**.
2. Criar Tarefa Básica: nome "dl-torrent feeds", disparo "Diariamente" (ou a cada X horas, conforme quiser).
3. Ação: "Iniciar um programa".
4. **Se instalou com `pip install -e .`:**
   - Programa: `dl-torrent` (ou o caminho completo do executável, ex.: `C:\...\Scripts\dl-torrent.exe`).
   - Argumentos: `feed poll --auto-download`.
   - Em "Iniciar em", pode deixar em branco ou colocar a pasta do projeto.
5. **Se roda com Python sem instalar:**
   - Programa: `python` (ou caminho completo do `python.exe`).
   - Argumentos: `-m app feed poll --auto-download`.
   - Em "Iniciar em", coloque a pasta `src` do projeto (ex.: `D:\workspace\Caio\dl-torrent\src`).

### Linux / macOS (cron)

Edite o crontab:

```bash
crontab -e
```

Exemplo: verificar a cada 30 minutos (com instalação via pip, comando `dl-torrent` no PATH):

```bash
*/30 * * * * dl-torrent feed poll --auto-download
```

Se usar `python -m app` a partir da pasta `src`:

```bash
*/30 * * * * cd /caminho/para/dl-torrent/src && python -m app feed poll --auto-download
```

Ajuste `/caminho/para/dl-torrent` para o seu diretório do projeto.

**Alternativa ao cron/Agendador:** use o comando **`feed daemon`** para o próprio dl-torrent fazer o poll em loop (ex.: `dl-torrent feed daemon --interval 30 --auto-download`). Útil quando você prefere deixar um terminal ou serviço rodando em vez de configurar o agendador do sistema.
