# Instalação

## Pré-requisitos

- **Python 3.10 ou superior**
- Dependências são instaladas automaticamente pelo pip (ver [pyproject.toml](../pyproject.toml) ou `requirements.txt` se existir)

## Instalação padrão

Na pasta do projeto:

```bash
cd dl-torrent
pip install -e .
```

Ou, se existir `requirements.txt`:

```bash
pip install -r requirements.txt
```

Após a instalação, o comando `dl-torrent` fica disponível no terminal.

## Rodar sem instalar

A partir da pasta `src` do projeto:

```bash
cd src
python -m app search "Artist - Song"
```

## Windows e download direto

Para usar a opção **`--download-direct`** (baixar os arquivos diretamente, sem Transmission/uTorrent), o dl-torrent usa a biblioteca libtorrent via TorrentP. No Windows, é comum aparecer erro de DLL ao carregar o libtorrent. Nesse caso:

1. Instale as DLLs OpenSSL exigidas: `pip install libtorrent-windows-dll`
2. Se ainda falhar, instale o [Visual C++ Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe)
3. Para diagnosticar: `python scripts/debug_libtorrent.py` (se o script existir no projeto)

Detalhes em [Solução de problemas](troubleshooting.md#erro-de-dll-ao-importar-libtorrent-windows).

## Verificar a instalação

```bash
dl-torrent --version
```

Deve exibir a versão do pacote (ex.: `0.1.0`).
