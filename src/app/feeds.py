"""Lógica de feeds RSS: add, list, poll."""

from __future__ import annotations

import re
from pathlib import Path

import feedparser
import typer

from .client import create_client_from_settings
from .config import get_settings
from .db import (
    add_feed_record,
    connection,
    get_feed_by_id,
    is_processed,
    list_feed_records,
    mark_processed,
    pending_add,
    pending_delete,
    pending_list,
)
from .quality import matches_format, parse_format_filter, parse_quality
from .quality_video import (
    matches_format_video,
    parse_format_filter_video,
    parse_quality_video,
)


def _entry_link(entry: object) -> str | None:
    """Extrai link magnet ou URL do item do feed."""
    e = entry
    # Magnet em link ou em links[]
    link = getattr(e, "link", None)
    if link and str(link).startswith("magnet:"):
        return link
    links = getattr(e, "links", []) or []
    for L in links:
        href = getattr(L, "href", None)
        if href and str(href).startswith("magnet:"):
            return href
        if href and ("magnet:" in str(href) or href.endswith(".torrent")):
            return href
    return link


def _entry_id(entry: object) -> str:
    """Identificador estável do item (para não reprocessar)."""
    e = entry
    uid = getattr(e, "id", None) or getattr(e, "link", None) or getattr(e, "title", None)
    return (uid or "").strip() or str(id(e))


def add_feed(url: str, content_type: str = "music") -> None:
    """Adicionar feed RSS à lista. content_type: music, movies, tv."""
    url = url.strip()
    if not url:
        typer.echo("URL vazia.")
        raise typer.Exit(1)
    add_feed_record(url, title=None, content_type=content_type)
    typer.echo(f"Feed adicionado: {url} (tipo: {content_type})")


def list_feed() -> None:
    """Listar feeds inscritos."""
    rows = list_feed_records()
    if not rows:
        typer.echo("Nenhum feed inscrito. Use: feed add <url>")
        return
    for r in rows:
        ct = r.get("content_type") or "music"
        typer.echo(
            f"  {r['id']}. {r['url']}"
            + (f" — {r['title']}" if r.get("title") else "")
            + f" [{ct}]"
        )


def _matches_include_exclude(title: str, include: list[str] | None, exclude: list[str] | None) -> bool:
    """True se o título passa nos filtros --include e --exclude (case-insensitive)."""
    title_lower = title.lower()
    if include:
        if not any(term.strip().lower() in title_lower for term in include if term.strip()):
            return False
    if exclude:
        if any(term.strip().lower() in title_lower for term in exclude if term.strip()):
            return False
    return True


def _collect_new_items(conn, format_filter: str | None, include_list, exclude_list) -> list[dict]:
    """Coleta todos os itens novos dos feeds que passam nos filtros. Não marca como processado.
    Para feeds com content_type movies/tv usa qualidade de vídeo; senão qualidade de áudio."""
    items: list[dict] = []
    rows = list_feed_records(conn=conn)
    for rec in rows:
        feed_id = rec["id"]
        url = rec["url"]
        content_type = rec.get("content_type") or "music"
        use_video = content_type in ("movies", "tv")
        allowed = (
            None
            if format_filter is None
            else (
                parse_format_filter_video(format_filter)
                if use_video
                else parse_format_filter(format_filter)
            )
        )
        parsed = feedparser.parse(url)
        if getattr(parsed, "bozo_exception", None):
            typer.echo(f"Erro ao ler feed {url}: {parsed.bozo_exception}")
            continue
        entries = getattr(parsed, "entries", []) or []
        for entry in entries:
            entry_id = _entry_id(entry)
            if is_processed(feed_id, entry_id, conn=conn):
                continue
            title = (getattr(entry, "title", None) or "").strip()
            if not _matches_include_exclude(title, include_list, exclude_list):
                mark_processed(feed_id, entry_id, entry_link=None, title=title, conn=conn)
                continue
            link = _entry_link(entry)
            if use_video:
                quality = parse_quality_video(title)
                accept = allowed is None or matches_format_video(quality, allowed)
            else:
                quality = parse_quality(title)
                accept = allowed is None or matches_format(quality, allowed)
            if not accept:
                mark_processed(feed_id, entry_id, entry_link=link, title=title, conn=conn)
                continue
            items.append({
                "feed_id": feed_id,
                "entry_id": entry_id,
                "title": title,
                "link": link,
                "quality_label": quality.label,
                "content_type": content_type,
            })
    return items


def poll_feeds(
    auto_download: bool = False,
    format_filter: str | None = None,
    include: str | None = None,
    exclude: str | None = None,
    use_download_queue: bool = True,
    organize: bool | None = None,
    settings=None,
    client=None,
) -> None:
    """Verificar feeds, listar novidades e opcionalmente baixar.
    Se auto_download=False, mostra a lista e pergunta quais baixar; os escolhidos vão para a fila de download.
    use_download_queue=True envia para 'download add' (fila em background); False usa o cliente (Transmission etc).
    Se organize=True (ou organize=None e settings.organize_by_artist_album), cria subpastas por tipo ao baixar.
    settings e client injetáveis para testes (DIP); None usa get_settings() e create_client_from_settings.
    """
    include_list = [x.strip() for x in (include or "").split(",") if x.strip()] or None
    exclude_list = [x.strip() for x in (exclude or "").split(",") if x.strip()] or None
    s = settings or get_settings()
    if client is None:
        client = create_client_from_settings(s)
    use_organize = organize if organize is not None else getattr(s, "organize_by_artist_album", False)

    with connection() as conn:
        rows = list_feed_records(conn=conn)
        if not rows:
            typer.echo("Nenhum feed inscrito. Use: feed add <url>")
            return

        items = _collect_new_items(conn, format_filter, include_list, exclude_list)
        if not items:
            typer.echo("Nenhuma novidade.")
            return

        if auto_download:
            from .organize import extract_subpath_by_content_type

            save_path_base = (getattr(s, "download_dir", "") or s.watch_folder or "./downloads").strip()
            save_path_base = str(Path(save_path_base).expanduser().resolve())
            for it in items:
                title = it["title"]
                link = it["link"]
                quality_label = it["quality_label"]
                content_type = it.get("content_type") or "music"
                if content_type not in ("music", "movies", "tv"):
                    content_type = "music"
                typer.echo(f"  Novo: [{quality_label}] {title[:70]}{'...' if len(title) > 70 else ''}")
                if link:
                    if use_download_queue:
                        from .download_manager import add as download_add, start as download_start
                        if use_organize and title:
                            subpath = extract_subpath_by_content_type(title, content_type)
                            save_path = str(Path(save_path_base) / subpath)
                        else:
                            save_path = save_path_base
                        did = download_add(link, save_path, title, content_type=content_type)
                        if did > 0:
                            download_start(did)
                            typer.echo("    -> Enfileirado para download em background.")
                        else:
                            typer.echo("    -> Falha ao enfileirar.")
                    else:
                        if client.add(link):
                            typer.echo("    -> Adicionado ao cliente.")
                        else:
                            typer.echo("    -> Falha ao adicionar.")
                else:
                    typer.echo("    -> Sem link magnet/torrent.")
                try:
                    from .notify import send_notification
                    send_notification("dl-torrent: novo no feed", title[:200])
                except Exception:
                    pass
                mark_processed(it["feed_id"], it["entry_id"], entry_link=link, title=title, conn=conn)
            return

        # Sem auto_download: salva no DB para o usuário escolher depois com 'feed pending'
        saved = 0
        for it in items:
            pid = pending_add(
                it["feed_id"],
                it["entry_id"],
                it["title"],
                it["link"],
                it["quality_label"],
                conn=conn,
            )
            if pid:
                saved += 1
            mark_processed(it["feed_id"], it["entry_id"], entry_link=it["link"], title=it["title"], conn=conn)
        typer.echo(f"{saved} item(ns) salvo(s) no banco. Use 'dl-torrent feed pending' para listar e escolher o que baixar.")


def run_pending_selection(settings=None, organize: bool = False) -> int:
    """Lista itens pendentes (salvos pelo poll), pergunta quais baixar e enfileira na fila de download.
    Se organize=True, cria subpastas por tipo (Artist/Album, Movie (Year), Show/Season) conforme content_type do feed.
    Retorna quantos downloads foram iniciados (para o CLI manter o processo vivo e entrar no watch)."""
    from .organize import extract_subpath_by_content_type

    s = settings or get_settings()
    items = pending_list()
    if not items:
        typer.echo("Nenhum item pendente. Rode 'dl-torrent feed poll' para buscar novidades e salvar no banco.")
        return 0

    typer.echo("Itens pendentes (escolha quais baixar):")
    for it in items:
        pid = it["id"]
        label = it.get("quality_label") or "?"
        raw_title = it.get("title") or ""
        title = raw_title[:62] + ("..." if len(raw_title) > 62 else "")
        # Evitar UnicodeEncodeError no Windows (cp1252): só ASCII na saída
        title_safe = title.encode("ascii", "replace").decode("ascii")
        has_link = "  " if it.get("link") else "  [sem magnet] "
        typer.echo(f"  {pid}. {has_link}[{label}] {title_safe}")
    typer.echo("")
    prompt_msg = "Quais baixar? (IDs separados por vírgula, 'todos', ou Enter para nenhum): "
    try:
        raw = input(prompt_msg).strip()
    except EOFError:
        raw = ""
    if not raw:
        to_download = []
    elif raw.lower() in ("todos", "all", "t", "a"):
        to_download = [it["id"] for it in items]
    else:
        to_download = []
        for part in raw.replace(" ", "").split(","):
            try:
                n = int(part)
                if any(it["id"] == n for it in items):
                    to_download.append(n)
            except ValueError:
                pass
        to_download = sorted(set(to_download))

    save_path_base = (getattr(s, "download_dir", "") or s.watch_folder or "./downloads").strip()
    save_path_base = str(Path(save_path_base).expanduser().resolve())
    from .download_manager import add as download_add, start as download_start
    started = 0
    for pid in to_download:
        it = next((x for x in items if x["id"] == pid), None)
        if not it:
            continue
        if not it.get("link"):
            typer.echo(f"  [{pid}] Sem link, ignorado.")
            continue
        title = it.get("title") or ""
        content_type = it.get("content_type") or "music"
        if content_type not in ("music", "movies", "tv"):
            content_type = "music"
        if organize and title:
            subpath = extract_subpath_by_content_type(title, content_type)
            save_path = str(Path(save_path_base) / subpath)
        else:
            save_path = save_path_base
        did = download_add(it["link"], save_path, title, content_type=content_type)
        if did > 0:
            if download_start(did):
                started += 1
            pending_delete(pid)
            typer.echo(f"  [{pid}] Enfileirado (id {did}) e removido da lista pendente.")
        else:
            typer.echo(f"  [{pid}] Falha ao enfileirar.")
    if to_download:
        typer.echo("Use 'dl-torrent download list' ou 'download watch' para acompanhar.")
    else:
        typer.echo("Nenhum item selecionado.")
    return started
