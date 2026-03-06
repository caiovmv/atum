# Solução de problemas

Problemas mais comuns ao usar o dl-torrent e como resolver.

## Erro de DLL ao importar libtorrent (Windows)

**Sintoma:** Ao usar `--download-direct` ou comandos que dependem do TorrentP, aparece algo como `ImportError: DLL load failed while importing libtorrent` ou "Não foi possível encontrar o módulo especificado".

**Solução:**

1. Instale as DLLs OpenSSL exigidas pelo libtorrent:  
   `pip install libtorrent-windows-dll`
2. Se o erro continuar, instale o [Visual C++ Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe).
3. Se o projeto tiver o script de diagnóstico, rode na pasta do projeto:  
   `python scripts/debug_libtorrent.py`  
   para ver qual dependência está faltando.

Veja também [Instalação](installation.md#windows-e-download-direto).

## Transmission ou uTorrent não conecta

**Sintoma:** Mensagem do tipo "Nenhum torrent foi adicionado ao cliente" ou erro de conexão ao usar o cliente configurado.

**O que verificar:**

- No `.env`, confira `CLIENT_TYPE` e as variáveis do cliente:
  - **Transmission:** `TRANSMISSION_HOST`, `TRANSMISSION_PORT`, `TRANSMISSION_USER`, `TRANSMISSION_PASSWORD`
  - **uTorrent:** `UTORRENT_URL`, `UTORRENT_USER`, `UTORRENT_PASSWORD`
- O cliente (Transmission ou uTorrent) está aberto e acessível na rede?
- Se for em outra máquina, o firewall permite conexão na porta configurada?
- Para uTorrent, a Web UI está habilitada nas configurações do programa?

Consulte [Configuração](configuration.md) para a lista completa de variáveis.

## Nenhum resultado na busca

**Sintoma:** A busca retorna "Nenhum resultado encontrado" ou "Nenhum resultado aceitável".

**O que tentar:**

- Verifique sua conexão com a internet.
- Use **`--no-quality-filter`** para ver todos os resultados (sem filtro de qualidade); às vezes o filtro descarta tudo.
- Troque de indexador com **`--indexer`**:  
  `dl-torrent search "sua busca" --indexer tpb` ou `--indexer 1337x` ou `--indexer 1337x,tpb,tg`
- Os domínios do The Pirate Bay e do TorrentGalaxy podem variar por região ou estar temporariamente indisponíveis. Você pode alterar no `.env`: `TPB_BASE_URL`, `TG_BASE_URL` (veja [Configuração](configuration.md)).

## Download direto falha

**Sintoma:** Ao usar `--download-direct`, o torrent não baixa ou aparece erro.

**O que verificar:**

- A pasta de destino existe e você tem permissão de escrita? Use `--download-dir` para indicar um caminho válido.
- Se aparecer erro de porta em uso (vários terminais com download direto ao mesmo tempo), use **`--listen-port`** com um valor diferente em cada um (ex.: 6882, 6883).
- Confirme que o libtorrent está carregando (veja [Erro de DLL](#erro-de-dll-ao-importar-libtorrent-windows) no Windows).

## Docker: downloads lentos ou poucos peers

**Sintoma:** Em ambiente Docker (ex.: `docker-compose`), os downloads ficam lentos ou não conectam a muitos seeders/peers.

**Causa:** O protocolo BitTorrent precisa receber conexões **de entrada** (além das saídas). Se as portas BitTorrent não forem expostas no container e no host, outros peers não conseguem conectar ao seu cliente.

**Solução:**

1. No `docker-compose.yml`, o serviço **runner** deve expor o range de portas BitTorrent (TCP e UDP), por exemplo:
   ```yaml
   ports:
     - "6881-6889:6881-6889/tcp"
     - "6881-6889:6881-6889/udp"
   ```
2. Em rede atrás de NAT/roteador, encaminhe as portas 6881–6889 (TCP e UDP) para o host que roda o Docker, para melhor descoberta de peers.
3. Para **metadados a partir de magnet**: em Docker o DHT costuma ser menos eficaz. Prefira **torrent_url** (URL do arquivo .torrent) quando o indexador fornecer; assim não é necessário resolver o magnet via DHT dentro do container.

## Notificação do feed não aparece

**Sintoma:** Você configurou `NOTIFY_ENABLED=true` e `NOTIFY_DESKTOP=true` mas não recebe notificação ao rodar `feed poll`.

**O que verificar:**

- No **Windows**, notificação desktop usa a biblioteca `win10toast`. Se não estiver instalada: `pip install win10toast`.
- No **Linux**, o dl-torrent chama o comando `notify-send` (pacote `libnotify-bin` ou similar). Instale se necessário.
- Para **webhook**, confira `NOTIFY_WEBHOOK_URL` no `.env`; o app envia um POST JSON com `title`, `message` e `text`. Veja [Configuração](configuration.md#organização-e-notificação-opcional).

## Outros problemas

- **Comando não encontrado:** Após `pip install -e .`, o `dl-torrent` deve estar no PATH. Se não estiver, use `python -m app` a partir da pasta `src` (veja [Instalação](installation.md)).
- **Dados antigos (feeds, histórico, wishlist):** Ficam no PostgreSQL (DATABASE_URL). Para recomeçar do zero, limpe as tabelas no banco ou use um banco novo.

## Rede e libtorrent / TorrentP

- **Download (worker e CLI):** o dl-torrent usa **libtorrent diretamente** quando disponível (`libtorrent_engine`): sessão com DHT, LSD, trackers públicos e bootstrap, porta configurável. Isso melhora descoberta de peers e velocidade. Se o libtorrent não estiver instalado, o worker e o CLI fazem **fallback** para a biblioteca [TorrentP](https://github.com/iw4p/torrentp) (que também usa libtorrent por baixo).
- Em **Docker**, para melhor velocidade de download é importante expor as portas BitTorrent no serviço que roda os workers (veja [Docker: downloads lentos ou poucos peers](#docker-downloads-lentos-ou-poucos-peers)). Para obter a lista de arquivos a partir de **magnet**, o dl-torrent usa DHT e trackers públicos em uma sessão separada (metadados); em containers essa resolução pode falhar — prefira **torrent_url** (URL do arquivo .torrent) quando o indexador fornecer.
- O **intervalo de atualização do progresso** no banco é configurável via `DOWNLOAD_PROGRESS_INTERVAL_SECONDS` (padrão 1,0 s). As escritas no repositório são limitadas a no máximo uma vez por segundo por download.

Para configuração completa, veja o [README principal](../README.md) e [Configuração](configuration.md).
