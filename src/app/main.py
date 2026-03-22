"""CLI principal: subcomandos search e feed."""

import http.server
import logging
import re
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import typer

logger = logging.getLogger(__name__)

from . import __version__


app = typer.Typer(
    name="dl-torrent",
    help="Buscar e baixar torrents: música (FLAC, ALAC, MP3), filmes e séries (1080p, 720p, etc.).",
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Mostrar versão.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    pass


@app.command()
def search(
    query: str | None = typer.Argument(None, help="Nome da música, filme ou série (ou artista para música)."),
    album: str | None = typer.Option(None, "--album", "-a", help="Nome do álbum."),
    best: bool = typer.Option(False, "--best", "-b", help="Baixar o melhor resultado automaticamente (alias de --auto-download-best-result)."),
    auto_download_best_result: bool = typer.Option(
        False,
        "--auto-download-best-result",
        help="Baixar apenas o melhor resultado, sem abrir a lista de seleção.",
    ),
    index: int | None = typer.Option(None, "--index", "-i", help="Número do resultado para baixar (1-based)."),
    limit: int = typer.Option(1000, "--limit", "-n", help="Máximo de resultados buscados (lista paginada)."),
    page_size: int = typer.Option(20, "--page-size", help="Itens por página (navegação com n=próxima, p=anterior)."),
    sort_by: str = typer.Option("seeders", "--sort", "-s", help="Ordenar por: seeders (Se/Le) ou size (tamanho)."),
    format_filter: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Subfiltro opcional: só mostrar formatos listados (ex: flac,alac,320 ou flac,alac,mp3_320,mp3).",
    ),
    no_quality_filter: bool = typer.Option(
        False,
        "--no-quality-filter",
        help="Mostrar todos os resultados, sem filtrar por qualidade.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-V",
        help="Mostrar detalhes da busca (erros, quantidade de resultados do 1337x).",
    ),
    all_categories: bool = typer.Option(
        False,
        "--all-categories",
        help="Buscar em todas as categorias do 1337x (não só Music).",
    ),
    save_to_watch_folder: bool = typer.Option(
        False,
        "--save-to-watch-folder",
        help="Salvar magnets na pasta (WATCH_FOLDER ou --watch-folder), sem usar Transmission/uTorrent.",
    ),
    watch_folder: str | None = typer.Option(
        None,
        "--watch-folder",
        help="Pasta onde salvar os magnets (usado com --save-to-watch-folder). Se omitido, usa WATCH_FOLDER do .env.",
    ),
    download_direct: bool = typer.Option(
        False,
        "--download-direct",
        help="Baixar os arquivos diretamente com libtorrent (sem Transmission/uTorrent).",
    ),
    download_dir: str | None = typer.Option(
        None,
        "--download-dir",
        help="Pasta de destino do download direto (usado com --download-direct). Padrão: DOWNLOAD_DIR ou ./downloads.",
    ),
    listen_port: int | None = typer.Option(
        None,
        "--listen-port",
        help="Porta para download direto (padrão: automática por processo; use se der conflito com outro terminal).",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        help="Com --download-direct: enfileirar na fila de downloads e baixar em background (use 'download list' para acompanhar).",
    ),
    indexer: str = typer.Option(
        None,
        "--indexer",
        help="Indexadores separados por vírgula (padrão: todos). Ex: 1337x,tpb,yts,eztv,nyaa,limetorrents.",
    ),
    organize: bool = typer.Option(
        False,
        "--organize",
        help="Com download direto: criar subpastas conforme o tipo (Artist/Album, Filme, Show/Season).",
    ),
    content_type: str = typer.Option(
        "music",
        "--type",
        "-t",
        help="Tipo de conteúdo: music (música), movies (filmes), tv (séries). Afeta categoria do indexador e organização.",
    ),
) -> None:
    """Buscar torrents por nome (música, filme ou série). Lista paginada: n=próxima, p=anterior."""
    from .config import get_settings
    from .organize import ContentType
    from .search import run_search

    ct: ContentType = content_type if content_type in ("music", "movies", "tv") else "music"

    query = (query or "").strip()
    api_key = (get_settings().lastfm_api_key or "").strip()
    if api_key and album:
        from .lastfm import resolve_album, resolve_artist_album
        if query and album:
            resolved = resolve_artist_album(query, album, api_key)
            if resolved:
                query = resolved
                album = None
        else:
            results = resolve_album(album, api_key, limit=1)
            if results:
                query = f"{results[0]['artist']} - {results[0]['name']}"
                typer.echo(f"Last.fm: buscando como '{query}'")
                album = None
            else:
                query = album
                album = None
    elif album and not query:
        query = album
        album = None
    if not query or not str(query).strip():
        typer.echo("Informe o termo de busca.")
        raise typer.Exit(1)
    query = str(query).strip()

    from .search import ALL_INDEXERS, DEFAULT_INDEXERS
    default_indexer_str = ",".join(DEFAULT_INDEXERS)
    indexers_raw = [x.strip().lower() for x in (indexer or default_indexer_str).split(",") if x.strip()]
    indexers_list = [x for x in indexers_raw if x in ALL_INDEXERS]
    if not indexers_list:
        indexers_list = list(DEFAULT_INDEXERS)

    run_search(
        query=query.strip(),
        album=album,
        best=best,
        index=index,
        limit=limit,
        format_filter=format_filter,
        no_quality_filter=no_quality_filter,
        verbose=verbose,
        music_category_only=not all_categories,
        content_type=ct,
        auto_download_best_result=auto_download_best_result or best,
        save_to_watch_folder=save_to_watch_folder,
        watch_folder_path=watch_folder,
        download_direct=download_direct,
        download_direct_path=download_dir,
        download_direct_port=listen_port,
        download_background=background,
        organize_by_artist_album=organize,
        indexers=indexers_list,
        sort_by=sort_by if sort_by in ("seeders", "size") else "seeders",
        page_size=max(1, min(100, page_size)),
    )


download_app = typer.Typer(help="Gerenciar downloads em background: listar, iniciar, parar, deletar.")
app.add_typer(download_app, name="download")


@app.command()
def runner(
    port: int = typer.Option(9092, "--port", "-p", help="Porta do Download Runner."),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host para escutar."),
) -> None:
    """Inicia o Download Runner (API HTTP da fila de downloads). Use com dl-torrent serve e DOWNLOAD_RUNNER_URL."""
    import uvicorn
    uvicorn.run(
        "app.runner.app:app",
        host=host,
        port=port,
        reload=False,
    )


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Porta da API Web."),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host para escutar (0.0.0.0 = todos)."),
) -> None:
    """Inicia a API Web (busca + proxy para o Runner). Defina DOWNLOAD_RUNNER_URL (ex: http://127.0.0.1:9092)."""
    import uvicorn
    uvicorn.run(
        "app.web.app:app",
        host=host,
        port=port,
        reload=False,
    )


@download_app.command("add")
def download_add_cmd(
    magnet: str = typer.Argument(..., help="Link magnet ou caminho para arquivo .torrent."),
    download_dir: str | None = typer.Option(
        None,
        "--download-dir",
        "-d",
        help="Pasta de destino. Padrão: DOWNLOAD_DIR do .env ou ./downloads.",
    ),
    name: str | None = typer.Option(None, "--name", "-n", help="Nome amigável para exibir na lista."),
    start_now: bool = typer.Option(True, "--start/--no-start", help="Iniciar o download em background agora."),
) -> None:
    """Adicionar um download à fila (e opcionalmente iniciar em background)."""
    from .config import get_settings
    from .download_manager import add, start
    from .runner_client import runner_add

    s = get_settings()
    path = (download_dir or "").strip() or s.save_path_for_content_type(None)
    did = runner_add(magnet.strip(), path, name=name, start_now=start_now)
    if did is not None:
        typer.echo(f"Adicionado à fila com id {did} (Runner). Pasta: {path}")
        if start_now:
            typer.echo("Download iniciado em background. Use 'dl-torrent download list' para acompanhar.")
        return
    did = add(magnet.strip(), path, name)
    if did <= 0:
        typer.echo("Erro ao adicionar à fila.")
        raise typer.Exit(1)
    typer.echo(f"Adicionado à fila com id {did}. Pasta: {path}")
    if start_now and start(did):
        typer.echo("Download iniciado em background. Use 'dl-torrent download list' para acompanhar.")


@download_app.command("list")
def download_list_cmd(
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filtrar por status: queued, downloading, paused, completed, failed.",
    ),
) -> None:
    """Listar downloads com status, progresso e quantidade de seeders/leechers (Se/Le)."""
    from .download_manager import list_downloads, reconcile_downloads_with_filesystem
    from .presentation import render_downloads_table
    from .runner_client import runner_list_downloads

    rows = runner_list_downloads(status)
    if rows is not None:
        if not rows:
            typer.echo("Nenhum download na fila (Runner).")
            return
        render_downloads_table(rows)
        return
    n_removed = reconcile_downloads_with_filesystem()
    if n_removed:
        typer.echo(f"  ({n_removed} download(s) removido(s): arquivos não encontrados no disco.)")
    rows = list_downloads(status_filter=status)
    if not rows:
        typer.echo("Nenhum download na fila.")
        return
    render_downloads_table(rows)


def _run_download_watch_loop(interval: float, status_filter: str | None) -> None:
    """Loop de acompanhamento de downloads (usa threads no mesmo processo ou Runner)."""
    import time

    from .download_manager import get_worker_alive, list_downloads, reconcile_downloads_with_filesystem, restart_dead_workers
    from .presentation import render_downloads_table_watch
    from .runner_client import runner_list_downloads

    def do_watch() -> None:
        rows = runner_list_downloads(status_filter)
        if rows is not None:
            if not rows:
                typer.echo("Nenhum download na fila (Runner).")
                return
            for r in rows:
                r["process_alive"] = None
            render_downloads_table_watch(rows)
            return
        n_removed = reconcile_downloads_with_filesystem()
        if n_removed:
            typer.echo(f"  ({n_removed} download(s) removido(s): arquivos não encontrados no disco.)")
        n_restarted = restart_dead_workers()
        if n_restarted:
            typer.echo(f"  ({n_restarted} download(s) reiniciado(s): thread estava morta.)")
        rows = list_downloads(status_filter=status_filter)
        if not rows:
            typer.echo("Nenhum download na fila.")
            return
        for r in rows:
            r["process_alive"] = get_worker_alive(r)
        render_downloads_table_watch(rows)

    try:
        from rich.console import Console
        console = Console()
        while True:
            console.clear()
            do_watch()
            console.print(f"[dim]Atualizando a cada {interval:.0f}s — Ctrl+C para sair[/dim]")
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


@download_app.command("watch")
def download_watch_cmd(
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filtrar por status: queued, downloading, paused, completed, failed.",
    ),
    interval: float = typer.Option(2.0, "--interval", "-i", help="Intervalo em segundos entre atualizações."),
) -> None:
    """Listar downloads em tempo real com velocidade, tamanho total, baixado e ETA (atualiza a cada N segundos)."""
    _run_download_watch_loop(interval, status)


@download_app.command("start")
def download_start_cmd(
    download_id: int = typer.Argument(..., help="ID do download (veja em 'download list')."),
) -> None:
    """Iniciar (ou retomar) um download em background."""
    from .download_manager import start
    from .runner_client import runner_start

    if runner_start(download_id):
        typer.echo(f"Download {download_id} iniciado em background (Runner).")
        return
    if start(download_id):
        typer.echo(f"Download {download_id} iniciado em background.")
    else:
        typer.echo("ID não encontrado ou download já em andamento/concluído. Use 'download list'.")
        raise typer.Exit(1)


@download_app.command("stop")
def download_stop_cmd(
    download_id: int = typer.Argument(..., help="ID do download a parar."),
) -> None:
    """Parar um download em andamento."""
    from .download_manager import stop
    from .runner_client import runner_stop

    if runner_stop(download_id):
        typer.echo(f"Download {download_id} parado (Runner).")
        return
    if stop(download_id):
        typer.echo(f"Download {download_id} parado.")
    else:
        typer.echo("ID não encontrado.")
        raise typer.Exit(1)


@download_app.command("delete")
def download_delete_cmd(
    download_id: int = typer.Argument(..., help="ID do download a remover."),
    remove_files: bool = typer.Option(False, "--remove-files", help="Apagar também os arquivos baixados (pasta do torrent)."),
) -> None:
    """Remover um download da lista (e opcionalmente apagar arquivos)."""
    from .download_manager import delete
    from .runner_client import runner_delete

    if runner_delete(download_id, remove_files=remove_files):
        typer.echo(f"Download {download_id} removido (Runner).")
        return
    if delete(download_id, remove_files=remove_files):
        typer.echo(f"Download {download_id} removido.")
    else:
        typer.echo("ID não encontrado.")
        raise typer.Exit(1)


resolve_app = typer.Typer(help="Resolver artista/álbum via Last.fm (sugestões de query para busca).")
app.add_typer(resolve_app, name="resolve")


@resolve_app.command("album")
def resolve_album_cmd(
    album: str = typer.Argument(..., help="Nome do álbum para buscar no Last.fm."),
    limit: int = typer.Option(5, "--limit", "-n", help="Máximo de sugestões."),
) -> None:
    """Listar sugestões 'Artist - Album' para um álbum (requer LASTFM_API_KEY no .env)."""
    from .config import get_settings
    from .lastfm import resolve_album

    api_key = (get_settings().lastfm_api_key or "").strip()
    if not api_key:
        typer.echo("Defina LASTFM_API_KEY no .env (obtenha em https://www.last.fm/api/account).")
        raise typer.Exit(1)
    results = resolve_album(album, api_key, limit=limit)
    if not results:
        typer.echo("Nenhum resultado no Last.fm.")
        return
    typer.echo("Sugestões (use com dl-torrent search):")
    for r in results:
        typer.echo(f"  {r['artist']} - {r['name']}")


lastfm_app = typer.Typer(help="Last.fm: charts (top tracks) para gerar lista Artist - Track.")
app.add_typer(lastfm_app, name="lastfm")


@lastfm_app.command("charts")
def lastfm_charts_cmd(
    limit: int = typer.Option(50, "--limit", "-n", help="Máximo de faixas (até 50)."),
    batch: bool = typer.Option(False, "--batch", help="Rodar batch com as faixas (buscar e baixar o melhor resultado por linha)."),
    format_filter: str | None = typer.Option(None, "--format", "-f", help="Subfiltro de formato (ex.: flac,alac,320)."),
    download_direct: bool = typer.Option(False, "--download-direct", help="Baixar diretamente com libtorrent (com --batch)."),
    download_dir: str | None = typer.Option(None, "--download-dir", help="Pasta de destino (com --batch e --download-direct)."),
    background: bool = typer.Option(False, "--background", help="Enfileirar em background (com --batch e --download-direct)."),
    indexer: str = typer.Option("1337x,tpb", "--indexer", help="Indexadores (1337x, tpb, yts, eztv, nyaa, limetorrents, etc.) para --batch."),
    batch_limit: int = typer.Option(5, "--batch-limit", help="Máximo de resultados por busca quando --batch (usa o melhor)."),
    organize: bool = typer.Option(False, "--organize", help="Subpastas Artist/Album (com --batch e --download-direct)."),
) -> None:
    """Listar top tracks do Last.fm no formato 'Artist - Track' (use com batch ou --batch)."""
    from .config import get_settings
    from .lastfm import get_chart_tracks

    api_key = (get_settings().lastfm_api_key or "").strip()
    if not api_key:
        typer.echo("Defina LASTFM_API_KEY no .env (obtenha em https://www.last.fm/api/account).")
        raise typer.Exit(1)
    results = get_chart_tracks(api_key, limit=limit)
    if not results:
        typer.echo("Nenhum resultado no Last.fm charts.")
        return
    lines = [f"{r['artist']} - {r['name']}" for r in results]
    if batch:
        from .batch import run_batch_lines
        run_batch_lines(
            lines,
            format_filter=format_filter,
            download_direct=download_direct,
            download_dir=download_dir,
            background=background,
            indexer=indexer,
            limit=batch_limit,
            organize=organize,
            content_type="music",
        )
    else:
        for ln in lines:
            typer.echo(ln)


spotify_app = typer.Typer(help="Spotify: playlists (OAuth) para gerar lista Artist - Track.")
app.add_typer(spotify_app, name="spotify")


def _spotify_playlist_id_from_arg(arg: str) -> str | None:
    """Extrai playlist_id de URL (open.spotify.com/playlist/ID) ou retorna o próprio arg se for ID."""
    s = (arg or "").strip()
    if not s:
        return None
    # URL: .../playlist/ID ou .../playlist/ID?...
    m = re.search(r"playlist/([a-zA-Z0-9]+)", s)
    if m:
        return m.group(1)
    # ID só (22 caracteres alfanuméricos típicos do Spotify)
    if re.match(r"^[a-zA-Z0-9]{22}$", s):
        return s
    if len(s) <= 50 and re.match(r"^[a-zA-Z0-9_-]+$", s):
        return s
    return None


@spotify_app.command("login")
def spotify_login_cmd() -> None:
    """Abrir navegador para autorizar Spotify e salvar tokens (~/.dl-torrent/spotify_tokens.json)."""
    from .config import get_settings
    from .spotify import (
        exchange_code_for_tokens,
        get_authorize_url,
        save_tokens,
    )

    settings = get_settings()
    cid = (settings.spotify_client_id or "").strip()
    secret = (settings.spotify_client_secret or "").strip()
    if not cid or not secret:
        typer.echo("Defina SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET no .env (Dashboard: https://developer.spotify.com/dashboard).")
        raise typer.Exit(1)
    port = settings.spotify_redirect_port or 8765
    redirect_uri = f"http://localhost:{port}/callback"
    state = __import__("secrets").token_urlsafe(16)

    auth_url = get_authorize_url(cid, redirect_uri, state)
    typer.echo("Abrindo navegador para autorizar. Após autorizar, volte aqui.")
    webbrowser.open(auth_url)

    result: dict = {}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            qs = parse_qs(parsed.query)
            got_state = (qs.get("state") or [""])[0]
            if got_state != state:
                self.send_response(400)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<p>State mismatch. Close this window.</p>")
                return
            code = (qs.get("code") or [""])[0]
            error = (qs.get("error") or [""])[0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            if error:
                self.wfile.write(f"<p>Erro: {error}. Feche esta janela.</p>".encode("utf-8"))
                return
            if not code:
                self.wfile.write(b"<p>Code missing. Close this window.</p>")
                return
            try:
                tok = exchange_code_for_tokens(code, cid, secret, redirect_uri)
                save_tokens(tok["access_token"], tok["refresh_token"], tok["expires_in"])
                result["ok"] = True
                self.wfile.write(b"<p>Autorizado. Pode fechar esta janela e voltar ao terminal.</p>")
            except Exception as e:
                result["error"] = str(e)
                self.wfile.write(f"<p>Erro ao trocar code: {e}. Feche esta janela.</p>".encode("utf-8"))

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), CallbackHandler)
    server.handle_request()
    if result.get("ok"):
        typer.echo("Spotify autorizado. Tokens salvos em ~/.dl-torrent/spotify_tokens.json")
    elif result.get("error"):
        typer.echo(f"Erro: {result['error']}")
        raise typer.Exit(1)


@spotify_app.command("playlists")
def spotify_playlists_cmd(
    limit: int = typer.Option(50, "--limit", "-n", help="Máximo de playlists listadas."),
) -> None:
    """Listar playlists do usuário (id e nome) para usar em spotify playlist <id>."""
    from .config import get_settings
    from .spotify import ensure_valid_token, get_current_user_playlists

    settings = get_settings()
    cid = (settings.spotify_client_id or "").strip()
    secret = (settings.spotify_client_secret or "").strip()
    if not cid or not secret:
        typer.echo("Defina SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET no .env.")
        raise typer.Exit(1)
    try:
        token = ensure_valid_token(cid, secret)
    except RuntimeError as e:
        typer.echo(str(e))
        raise typer.Exit(1)
    playlists = get_current_user_playlists(token, limit=limit)
    if not playlists:
        typer.echo("Nenhuma playlist encontrada.")
        return
    typer.echo("ID / Nome (use: dl-torrent spotify playlist <id>)")
    typer.echo("----")
    for p in playlists:
        pid = p.get("id") or ""
        name = (p.get("name") or "")[:50]
        url = (p.get("external_urls") or {}).get("spotify") or ""
        if url:
            typer.echo(f"  {pid}  {name}  {url}")
        else:
            typer.echo(f"  {pid}  {name}")


@spotify_app.command("playlist")
def spotify_playlist_cmd(
    playlist_id_or_url: str = typer.Argument(..., help="ID da playlist ou URL (open.spotify.com/playlist/ID)."),
    batch: bool = typer.Option(False, "--batch", help="Rodar batch com as faixas (buscar e baixar o melhor resultado por linha)."),
    format_filter: str | None = typer.Option(None, "--format", "-f", help="Subfiltro de formato (com --batch)."),
    download_direct: bool = typer.Option(False, "--download-direct", help="Baixar diretamente (com --batch)."),
    download_dir: str | None = typer.Option(None, "--download-dir", help="Pasta de destino (com --batch)."),
    background: bool = typer.Option(False, "--background", help="Enfileirar em background (com --batch)."),
    indexer: str = typer.Option("1337x,tpb", "--indexer", help="Indexadores (1337x, tpb, yts, eztv, nyaa, limetorrents, etc.) para --batch."),
    batch_limit: int = typer.Option(5, "--batch-limit", help="Máximo de resultados por busca quando --batch."),
    organize: bool = typer.Option(False, "--organize", help="Subpastas Artist/Album (com --batch)."),
) -> None:
    """Listar faixas da playlist no formato 'Artist - Track' (ou --batch para buscar e baixar)."""
    from .config import get_settings
    from .spotify import ensure_valid_token, get_playlist_tracks

    pid = _spotify_playlist_id_from_arg(playlist_id_or_url)
    if not pid:
        typer.echo("Informe o ID da playlist ou uma URL open.spotify.com/playlist/ID")
        raise typer.Exit(1)
    settings = get_settings()
    cid = (settings.spotify_client_id or "").strip()
    secret = (settings.spotify_client_secret or "").strip()
    if not cid or not secret:
        typer.echo("Defina SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET no .env.")
        raise typer.Exit(1)
    try:
        token = ensure_valid_token(cid, secret)
    except RuntimeError as e:
        typer.echo(str(e))
        raise typer.Exit(1)
    tracks = get_playlist_tracks(pid, token)
    if not tracks:
        typer.echo("Nenhuma faixa na playlist (ou playlist inacessível).")
        return
    lines = [f"{t['artist']} - {t['name']}" for t in tracks]
    if batch:
        from .batch import run_batch_lines
        run_batch_lines(
            lines,
            format_filter=format_filter,
            download_direct=download_direct,
            download_dir=download_dir,
            background=background,
            indexer=indexer,
            limit=batch_limit,
            organize=organize,
            content_type="music",
        )
    else:
        for ln in lines:
            typer.echo(ln)


wishlist_app = typer.Typer(help="Lista de desejos: termos para buscar em lote (add, list, remove, search).")
app.add_typer(wishlist_app, name="wishlist")


@wishlist_app.command("add")
def wishlist_add_cmd(
    term: str = typer.Argument(..., help="Termo ou 'Artist - Album' para buscar depois."),
) -> None:
    """Adicionar termo à wishlist."""
    from .db import wishlist_add_term

    wid = wishlist_add_term(term)
    if wid <= 0:
        typer.echo("Erro ao adicionar.")
        raise typer.Exit(1)
    typer.echo(f"Adicionado com id {wid}: {term}")


@wishlist_app.command("list")
def wishlist_list_cmd() -> None:
    """Listar termos da wishlist."""
    from .db import wishlist_list_all

    rows = wishlist_list_all()
    if not rows:
        typer.echo("Wishlist vazia.")
        return
    typer.echo("ID  | Termo")
    typer.echo("----+----------------------------------------")
    for r in rows:
        term = (r.get("term") or "")[:60]
        if len(r.get("term") or "") > 60:
            term += "…"
        typer.echo(f"{r['id']:<3} | {term}")


@wishlist_app.command("remove")
def wishlist_remove_cmd(
    wishlist_id: int = typer.Argument(..., help="ID do termo (veja em 'wishlist list')."),
) -> None:
    """Remover termo da wishlist."""
    from .db import wishlist_delete_by_id

    if wishlist_delete_by_id(wishlist_id):
        typer.echo(f"Removido id {wishlist_id}.")
    else:
        typer.echo("ID não encontrado.")
        raise typer.Exit(1)


@wishlist_app.command("search")
def wishlist_search_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="Só listar as buscas que seriam feitas, sem executar."),
    limit: int = typer.Option(15, "--limit", "-n", help="Máximo de resultados por busca."),
    content_type: str = typer.Option(
        "music",
        "--type",
        "-t",
        help="Tipo de conteúdo: music, movies ou tv (categoria e organização por termo).",
    ),
) -> None:
    """Executar busca para cada termo da wishlist (ou --dry-run para só listar)."""
    from .db import wishlist_list_all
    from .organize import ContentType
    from .search import run_search

    if content_type not in ("music", "movies", "tv"):
        typer.echo("--type deve ser music, movies ou tv.")
        raise typer.Exit(1)
    ct: ContentType = content_type
    terms = wishlist_list_all()
    if not terms:
        typer.echo("Wishlist vazia.")
        return
    if dry_run:
        typer.echo("Buscas que seriam executadas:")
        for t in terms:
            typer.echo(f"  {t['id']}: {t.get('term', '')}")
        return
    for t in terms:
        typer.echo(f"\n--- Wishlist {t['id']}: {t.get('term', '')} ---")
        run_search(
            query=(t.get("term") or "").strip(),
            album=None,
            limit=limit,
            indexers=["1337x", "tpb", "yts", "eztv", "nyaa", "limetorrents"],
            content_type=ct,
        )


@app.command()
def batch(
    file_path: str | None = typer.Argument(
        None,
        help="Arquivo com uma linha por busca (Artist - Album ou Artist - Track). Use --stdin para ler do stdin.",
    ),
    stdin: bool = typer.Option(False, "--stdin", help="Ler linhas do stdin em vez de arquivo."),
    format_filter: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Subfiltro: só formatos listados (ex: flac,alac,320).",
    ),
    download_direct: bool = typer.Option(
        False,
        "--download-direct",
        help="Baixar diretamente com libtorrent (sem cliente externo).",
    ),
    download_dir: str | None = typer.Option(
        None,
        "--download-dir",
        help="Pasta de destino (com --download-direct). Padrão: DOWNLOAD_DIR do .env.",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        help="Com --download-direct: enfileirar e baixar em background.",
    ),
    indexer: str = typer.Option(
        None,
        "--indexer",
        help="Indexadores separados por vírgula (padrão: todos).",
    ),
    limit: int = typer.Option(5, "--limit", "-n", help="Máximo de resultados por busca (usa o melhor)."),
    organize: bool = typer.Option(
        False,
        "--organize",
        help="Criar subpastas conforme o tipo (Artist/Album, Filme, Show/Season) no download direto.",
    ),
    content_type: str = typer.Option(
        "music",
        "--type",
        "-t",
        help="Tipo de conteúdo: music, movies ou tv (categoria e organização por linha).",
    ),
) -> None:
    """Para cada linha do arquivo (ou stdin), buscar e baixar o melhor resultado na melhor qualidade."""
    from .batch import run_batch_cmd
    from .search import DEFAULT_INDEXERS

    run_batch_cmd(
        file_path=file_path,
        stdin=stdin,
        format_filter=format_filter,
        download_direct=download_direct,
        download_dir=download_dir,
        background=background,
        indexer=indexer or ",".join(DEFAULT_INDEXERS),
        limit=limit,
        organize=organize,
        content_type=content_type,
    )


feed_app = typer.Typer(help="Gerenciar feeds RSS (música, filmes, séries): add, list, poll.")
app.add_typer(feed_app, name="feed")

sync_app = typer.Typer(help="Sincronizar biblioteca com o disco: reconcile e importar pastas existentes.")
app.add_typer(sync_app, name="sync")

indexers_app = typer.Typer(help="Status dos indexadores: daemon para health-check e notificações.")
app.add_typer(indexers_app, name="indexers")


@feed_app.command("add")
def feed_add(
    url: str = typer.Argument(..., help="URL do feed RSS."),
    content_type: str = typer.Option(
        "music",
        "--type",
        "-t",
        help="Tipo de conteúdo: music, movies, tv (afeta filtro de qualidade no poll).",
    ),
) -> None:
    """Adicionar um feed RSS."""
    from .feeds import add_feed

    if content_type not in ("music", "movies", "tv"):
        typer.echo("--type deve ser music, movies ou tv.")
        raise typer.Exit(1)
    add_feed(url, content_type=content_type)


@feed_app.command("list")
def feed_list_cmd() -> None:
    """Listar feeds inscritos."""
    from .feeds import list_feed

    list_feed()


@feed_app.command("pending")
def feed_pending_cmd(
    interval: float = typer.Option(5.0, "--interval", "-i", help="Intervalo do watch em segundos (após escolher itens)."),
    organize: bool = typer.Option(False, "--organize", help="Criar subpastas por tipo (Artist/Album, Movie, Show/Season) conforme o feed."),
) -> None:
    """Listar itens salvos pelo poll e escolher quais baixar (vão para a fila de download)."""
    from .feeds import run_pending_selection

    started = run_pending_selection(organize=organize)
    if started > 0:
        typer.echo("Acompanhando downloads (mantenha este terminal aberto). Ctrl+C para sair.")
        _run_download_watch_loop(interval, None)


@feed_app.command("poll")
def feed_poll_cmd(
    auto_download: bool = typer.Option(False, "--auto-download", help="Baixar automaticamente itens aceitáveis."),
    format_filter: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Subfiltro opcional: música (flac,alac,320) ou vídeo (1080p,720p,4k) conforme o tipo do feed.",
    ),
    include: str | None = typer.Option(
        None,
        "--include",
        help="Só itens cujo título contém alguma destas palavras (separadas por vírgula).",
    ),
    exclude: str | None = typer.Option(
        None,
        "--exclude",
        help="Descartar itens cujo título contém alguma destas palavras (separadas por vírgula).",
    ),
    organize: bool = typer.Option(False, "--organize", help="Criar subpastas por tipo (Artist/Album, Movie, Show/Season) ao baixar."),
) -> None:
    """Verificar feeds e listar/baixar novidades."""
    from .feeds import poll_feeds

    poll_feeds(
        auto_download=auto_download,
        format_filter=format_filter,
        include=include,
        exclude=exclude,
        organize=organize,
    )


@feed_app.command("daemon")
def feed_daemon_cmd(
    interval: int = typer.Option(30, "--interval", "-i", help="Intervalo em minutos entre cada poll."),
    auto_download: bool = typer.Option(False, "--auto-download", help="Baixar automaticamente itens aceitáveis."),
    format_filter: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Subfiltro: só itens com estes formatos (ex: flac,alac,320).",
    ),
    include: str | None = typer.Option(None, "--include", help="Só itens cujo título contém alguma destas palavras (vírgula)."),
    exclude: str | None = typer.Option(None, "--exclude", help="Descartar itens cujo título contém alguma destas palavras (vírgula)."),
    organize: bool = typer.Option(False, "--organize", help="Criar subpastas por tipo ao baixar."),
) -> None:
    """Ficar em loop fazendo poll a cada N minutos (Ctrl+C para sair)."""
    import time

    typer.echo(f"Feed daemon: poll a cada {interval} minuto(s). Ctrl+C para sair.")
    try:
        while True:
            try:
                from .feeds import poll_feeds
                poll_feeds(
                    auto_download=auto_download,
                    format_filter=format_filter,
                    include=include,
                    exclude=exclude,
                    organize=organize,
                )
            except KeyboardInterrupt:
                raise
            except Exception as e:
                typer.echo(f"Erro no poll: {e}")
            try:
                time.sleep(interval * 60)
            except KeyboardInterrupt:
                raise
    except KeyboardInterrupt:
        typer.echo("\nEncerrando.")
        raise typer.Exit(0)


@sync_app.command("daemon")
def sync_daemon_cmd(
    interval: int = typer.Option(300, "--interval", "-i", help="Intervalo em segundos entre cada ciclo de sync."),
    verbose: bool = typer.Option(True, "--verbose/--no-verbose", "-v", help="Logs verbosos (reconcile e import)."),
) -> None:
    """Ficar em loop executando reconcile (remove do DB itens cujo content_path não existe). Ctrl+C para sair."""
    import logging
    import time
    import traceback

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    typer.echo(f"Sync daemon: reconcile e importação a cada {interval}s. Ctrl+C para sair.")
    try:
        while True:
            try:
                typer.echo("[sync] Ciclo iniciado.")
                from concurrent.futures import ThreadPoolExecutor

                from .download_manager import reconcile_downloads_with_filesystem
                from .sync_library_imports import run_library_import_scan

                with ThreadPoolExecutor(max_workers=2) as pool:
                    f_reconcile = pool.submit(reconcile_downloads_with_filesystem)
                    f_import = pool.submit(run_library_import_scan)
                    n_removed = f_reconcile.result()
                    added, imp_removed = f_import.result()
                typer.echo(f"  Reconcile downloads: {n_removed} removido(s) (content_path não encontrado).")
                typer.echo(f"  Import biblioteca: {added} adicionado(s), {imp_removed} removido(s).")
                typer.echo("[sync] Ciclo concluído.")
            except KeyboardInterrupt:
                raise
            except Exception as e:
                typer.echo(f"Erro no sync: {e}")
                if verbose:
                    typer.echo(traceback.format_exc())
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                raise
    except KeyboardInterrupt:
        typer.echo("\nEncerrando.")
        raise typer.Exit(0)


@indexers_app.command("daemon")
def indexers_daemon_cmd(
    interval: int = typer.Option(300, "--interval", "-i", help="Intervalo em segundos entre cada ciclo de health-check."),
    timeout: int = typer.Option(10, "--timeout", "-t", help="Timeout em segundos por probe de busca (por indexador)."),
    verbose: bool = typer.Option(False, "--verbose/--no-verbose", "-v", help="Logs por indexador."),
) -> None:
    """Fica em loop testando cada indexador com probe de busca (mesmo código da API). Marca falha no Redis e notifica na UI quando um cai; reativa quando voltar."""
    import time

    from .config import get_settings
    from .db import notification_create
    from .indexer_status import get_indexer_base_urls, get_indexer_status, run_health_cycle

    typer.echo(f"Indexers daemon: health-check (probe de busca) a cada {interval}s. Ctrl+C para sair.")
    try:
        while True:
            try:
                settings = get_settings()
                redis_url = (settings.redis_url or "").strip()
                if not get_indexer_base_urls(settings):
                    typer.echo("[indexers] Nenhum indexador com BASE_URL configurado.")
                else:
                    previous = get_indexer_status(redis_url) if redis_url else {}
                    current = run_health_cycle(settings, redis_url, probe_timeout_sec=timeout)
                    for name, ok in current.items():
                        was_ok = previous.get(name, True)
                        if was_ok and not ok:
                            try:
                                notification_create(
                                    "indexer_down",
                                    f"Indexador {name.upper()} indisponível",
                                    f"O indexador {name} não está respondendo à busca. Foi desativado até voltar.",
                                    {"indexer": name},
                                )
                            except Exception as exc:
                                logger.debug("Falha ao criar notificação indexer_down para %s: %s", name, exc)
                            typer.echo(f"  [indexers] {name}: falha (desativado)")
                        elif not was_ok and ok:
                            try:
                                notification_create(
                                    "indexer_up",
                                    f"Indexador {name.upper()} voltou",
                                    f"O indexador {name} está respondendo à busca novamente e foi reativado.",
                                    {"indexer": name},
                                )
                            except Exception as exc:
                                logger.debug("Falha ao criar notificação indexer_up para %s: %s", name, exc)
                            typer.echo(f"  [indexers] {name}: ok (reativado)")
                        elif verbose:
                            typer.echo(f"  [indexers] {name}: {'ok' if ok else 'fail'}")
            except KeyboardInterrupt:
                raise
            except Exception as e:
                typer.echo(f"Erro no indexers daemon: {e}")
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                raise
    except KeyboardInterrupt:
        typer.echo("\nEncerrando.")
        raise typer.Exit(0)


enrichment_app = typer.Typer(help="Daemon de enriquecimento de metadados (MusicBrainz, Last.fm, Spotify, TMDB, LLM).")
app.add_typer(enrichment_app, name="enrichment")

# ─── HLS Daemon ───────────────────────────────────────────────────────────────

hls_app = typer.Typer(help="Daemon de transcodificação HLS com upload para MinIO.")
app.add_typer(hls_app, name="hls")


@hls_app.command("daemon")
def hls_daemon_cmd(
    interval: int = typer.Option(10, "--interval", "-i", help="Intervalo em segundos entre ciclos."),
    batch: int = typer.Option(4, "--batch", "-b", help="Jobs por ciclo."),
) -> None:
    """Loop de transcodificação HLS: processa hls_jobs e faz upload para MinIO."""
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from .daemons.hls_daemon import run_daemon
    run_daemon(interval=interval, batch=batch)


# ─── Cloud Sync Daemon ────────────────────────────────────────────────────────

cloud_sync_app = typer.Typer(help="Daemon de sincronização cloud: cold tiering, prefetch, play positions.")
app.add_typer(cloud_sync_app, name="cloud-sync")


@cloud_sync_app.command("daemon")
def cloud_sync_daemon_cmd(
    interval: int = typer.Option(300, "--interval", "-i", help="Intervalo em segundos entre ciclos."),
) -> None:
    """Loop de sync cloud: cold tiering, storage pressure release, prefetch offline."""
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from .daemons.cloud_sync_daemon import run_daemon
    run_daemon(interval=interval)


@enrichment_app.command("daemon")
def enrichment_daemon_cmd(
    interval: int = typer.Option(300, "--interval", "-i", help="Intervalo em segundos entre cada ciclo."),
    batch_size: int = typer.Option(10, "--batch-size", "-b", help="Itens por ciclo."),
    verbose: bool = typer.Option(True, "--verbose/--no-verbose", "-v", help="Logs verbosos."),
) -> None:
    """Loop de enriquecimento: processa itens de library_imports sem enriched_at. Ctrl+C para sair."""
    import logging
    import signal
    import time
    import traceback

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    _shutdown = False

    def _handle_sigterm(signum, frame):
        nonlocal _shutdown
        _shutdown = True
        typer.echo("\nSIGTERM recebido, encerrando após o ciclo atual...")

    signal.signal(signal.SIGTERM, _handle_sigterm)

    typer.echo(f"Enrichment daemon: ciclo a cada {interval}s, batch={batch_size}. Ctrl+C para sair.")
    try:
        while not _shutdown:
            try:
                from .ai.enrichment_daemon import run_enrichment_cycle, _get_settings_value

                eff_batch = int(_get_settings_value("enrichment_batch_size", batch_size) or batch_size)
                eff_interval = int(_get_settings_value("enrichment_interval", interval) or interval)
                n = run_enrichment_cycle(batch_size=eff_batch)
                if n > 0:
                    typer.echo(f"  [enrichment] {n} itens enriquecidos.")
                elif verbose:
                    typer.echo("  [enrichment] Nenhum item pendente.")
            except KeyboardInterrupt:
                raise
            except Exception as e:
                typer.echo(f"Erro no enrichment: {e}")
                if verbose:
                    typer.echo(traceback.format_exc())
                eff_interval = interval
            if _shutdown:
                break
            try:
                time.sleep(eff_interval)
            except KeyboardInterrupt:
                raise
    except KeyboardInterrupt:
        pass
    typer.echo("\nEncerrando.")
    raise typer.Exit(0)


@enrichment_app.command("run")
def enrichment_run_cmd(
    batch_size: int = typer.Option(50, "--batch-size", "-b", help="Itens para processar."),
) -> None:
    """Executa um único ciclo de enriquecimento (sem loop)."""
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    from .ai.enrichment_daemon import run_enrichment_cycle

    n = run_enrichment_cycle(batch_size=batch_size)
    typer.echo(f"Enriquecidos: {n} itens.")


@enrichment_app.command("reset")
def enrichment_reset_cmd() -> None:
    """Reseta enriched_at de todos os itens para forçar re-enriquecimento."""
    from .deps import get_library_import_repo

    repo = get_library_import_repo()
    if not repo:
        typer.echo("Repositório não disponível (DATABASE_URL?).")
        raise typer.Exit(1)

    from .db_postgres import connection_postgres
    from .config import get_settings
    db_url = get_settings().database_url
    if not db_url:
        typer.echo("DATABASE_URL não configurado.")
        raise typer.Exit(1)

    with connection_postgres(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE library_imports SET enriched_at = NULL, enrichment_error = NULL")
            count = cur.rowcount
            conn.commit()
    typer.echo(f"Reset: {count} itens marcados para re-enriquecimento.")


@app.command()
def library_reorganize(
    dry_run: bool = typer.Option(False, "--dry-run", help="Mostrar o que seria feito sem mover nada."),
    content_type: str | None = typer.Option(None, "--content-type", "-t", help="Filtrar por tipo: music, movies, tv."),
) -> None:
    """REORGANIZE: renomeia/move arquivos para estrutura Plex. Diferente do sync (rescan) que só descobre pastas."""
    from .deps import get_library_import_repo, get_repo, get_settings
    from .post_process import post_process_download

    settings = get_settings()
    repo = get_repo()
    import_repo = get_library_import_repo()

    # Downloads concluídos
    from .domain import DownloadStatus
    downloads = repo.list(status_filter=DownloadStatus.COMPLETED.value)
    typer.echo(f"Downloads concluídos: {len(downloads)}")

    dl_count = 0
    for row in downloads:
        ct = (row.get("content_type") or "").strip().lower()
        if content_type and ct != content_type.strip().lower():
            continue
        cp = (row.get("content_path") or "").strip()
        if not cp:
            continue
        name = (row.get("name") or "").strip()
        if not name:
            continue
        already = row.get("post_processed")
        if already:
            continue

        if dry_run:
            typer.echo(f"  [dry-run] Reorganizaria: {name} ({ct}) @ {cp}")
            dl_count += 1
            continue

        typer.echo(f"  Processando: {name} ({ct})")
        try:
            result = post_process_download(row["id"], cp, name, ct or None, force=True)
            if result.get("success"):
                dl_count += 1
                typer.echo(f"    OK: {result.get('message', '')}")
            else:
                typer.echo(f"    Pulado: {result.get('message', '')}")
        except Exception as e:
            typer.echo(f"    Erro: {e}")

    typer.echo(f"\nDownloads {'que seriam reorganizados' if dry_run else 'reorganizados'}: {dl_count}")

    # Library imports
    if import_repo:
        imports = import_repo.list(
            content_type=content_type.strip().lower() if content_type else None,
        )
        typer.echo(f"Itens importados: {len(imports)}")
        imp_count = 0
        for row in imports:
            cp = (row.get("content_path") or "").strip()
            if not cp:
                continue
            name = (row.get("name") or "").strip()
            ct = (row.get("content_type") or "music").strip().lower()
            if dry_run:
                typer.echo(f"  [dry-run] Reorganizaria import: {name} ({ct}) @ {cp}")
                imp_count += 1
                continue

            typer.echo(f"  Processando import: {name} ({ct})")
            try:
                result = post_process_download(0, cp, name, ct, force=True)
                if result.get("success"):
                    imp_count += 1
                    if result.get("library_path"):
                        import_repo.update_metadata(
                            row["id"],
                            previous_content_path=cp,
                            content_path=result["library_path"],
                            tmdb_id=result.get("tmdb_id"),
                            imdb_id=result.get("imdb_id"),
                        )
                    typer.echo(f"    OK: {result.get('message', '')}")
                else:
                    typer.echo(f"    Pulado: {result.get('message', '')}")
            except Exception as e:
                typer.echo(f"    Erro: {e}")
        typer.echo(f"Imports {'que seriam reorganizados' if dry_run else 'reorganizados'}: {imp_count}")

    typer.echo("Concluído.")


if __name__ == "__main__":
    app()
