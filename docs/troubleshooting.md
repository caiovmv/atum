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

## Notificação do feed não aparece

**Sintoma:** Você configurou `NOTIFY_ENABLED=true` e `NOTIFY_DESKTOP=true` mas não recebe notificação ao rodar `feed poll`.

**O que verificar:**

- No **Windows**, notificação desktop usa a biblioteca `win10toast`. Se não estiver instalada: `pip install win10toast`.
- No **Linux**, o dl-torrent chama o comando `notify-send` (pacote `libnotify-bin` ou similar). Instale se necessário.
- Para **webhook**, confira `NOTIFY_WEBHOOK_URL` no `.env`; o app envia um POST JSON com `title`, `message` e `text`. Veja [Configuração](configuration.md#organização-e-notificação-opcional).

## Outros problemas

- **Comando não encontrado:** Após `pip install -e .`, o `dl-torrent` deve estar no PATH. Se não estiver, use `python -m app` a partir da pasta `src` (veja [Instalação](installation.md)).
- **Dados antigos (feeds, histórico, wishlist):** Ficam em `~/.dl-torrent/feeds.db`. Para recomeçar do zero, você pode renomear ou apagar esse arquivo (e a pasta) quando o programa não estiver em uso.

Para configuração completa, veja o [README principal](../README.md) e [Configuração](configuration.md).
