# dl-torrent

CLI em Python para buscar e baixar torrents de música por nome ou álbum, com preferência de qualidade (FLAC, ALAC, MP3 320, MP3 até 198 kbps) e suporte a feeds RSS.

## Instalação

```bash
cd dl-torrent
pip install -e .
```

No **Windows**, se for usar download direto (`--download-direct`), pode ser necessário instalar as DLLs do libtorrent: `pip install libtorrent-windows-dll`. Se ainda falhar, veja [Solução de problemas](docs/troubleshooting.md).

## Primeiros passos

1. Copie o arquivo de exemplo e edite com seu cliente de torrent e pastas:  
   `cp .env.example .env`  
   Defina pelo menos `CLIENT_TYPE` (`transmission`, `utorrent` ou `folder`) e as variáveis do cliente escolhido.

2. Faça uma busca:  
   `dl-torrent search "Artist - Album"`  
   Use setas + Espaço para marcar os resultados e Enter para confirmar; os selecionados serão enviados ao cliente configurado.

3. Para mais opções e configuração, veja a [documentação em /docs](docs/README.md).

## O que o dl-torrent faz

- **Busca** em 1337x, The Pirate Bay, YTS, EZTV, NYAA e Limetorrents, com filtro por qualidade (FLAC, ALAC, MP3 320, MP3 até 198 kbps).
- **Envio** do magnet para Transmission, uTorrent ou para uma pasta (ex.: FrostWire).
- **Download direto** dos arquivos (sem cliente externo) com `--download-direct`; opção **`--organize`** para criar subpastas Artist/Album.
- **Batch:** comando `batch` para processar uma lista (arquivo ou stdin): cada linha vira uma busca e baixa o melhor resultado — ideal para listas do Spotify, Last.fm ou “Radar de Trend”.
- **Histórico** de buscas e **wishlist** para repetir ou buscar em lote.
- **Feeds RSS** de torrents de música: inscrever, verificar novidades (com auto-download), filtros **`--include`** e **`--exclude`**, e **`feed daemon`** para poll em loop (alternativa ao cron).
- **Notificação** ao detectar novo item no feed (webhook ou desktop), via variáveis no `.env`.
- **Resolução de álbum** via Last.fm (opcional) para buscar por nome de álbum.
- **Status dos indexadores:** o comando `indexers daemon` testa periodicamente cada fonte com um **probe de busca** (mesmo código da API); fontes que falham são desativadas na busca até voltarem.

## Clientes suportados

| Cliente      | `CLIENT_TYPE`  | Observação |
|--------------|----------------|------------|
| Transmission | `transmission` | Recomendado; API estável. |
| uTorrent     | `utorrent`     | Web UI ativa. |
| FrostWire    | `folder`       | Sem API; usa `WATCH_FOLDER` e grava magnets em `magnets.txt`. |

## Requisitos

- Python 3.10+  
- Detalhes de instalação (incl. Windows e download direto): [docs/installation.md](docs/installation.md)

## Documentação

Toda a documentação está em **[docs/](docs/README.md)**:

- [Instalação](docs/installation.md)
- [Configuração](docs/configuration.md)
- [Comandos](docs/commands.md)
- [Feeds RSS e agendamento](docs/feeds-and-scheduling.md)
- [Fontes de RSS para música](docs/rss-sources.md)
- [Arquitetura Netflix self-hosted (música)](docs/arquitetura-netflix-self-hosted.md)
- [Solução de problemas](docs/troubleshooting.md)

## Testes

Para rodar os testes: `pip install -e ".[dev]"` e `pytest tests`. Com cobertura: `pytest tests --cov=app --cov-report=term-missing`.
