"""Lógica de batch: executar busca para cada linha (arquivo ou stdin). SRP: único módulo responsável pelo fluxo batch."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from .organize import ContentType


def run_batch_lines(
    lines: list[str],
    *,
    format_filter: str | None = None,
    download_direct: bool = False,
    download_dir: str | None = None,
    background: bool = False,
    indexer: str = "1337x,tpb",
    limit: int = 5,
    organize: bool = False,
    content_type: str = "music",
) -> None:
    """Para cada linha, executa run_search (melhor resultado, auto-download).
    Usado por batch, lastfm charts --batch, spotify playlist --batch."""
    from .search import ALL_INDEXERS, DEFAULT_INDEXERS, run_search

    indexers_list = [x.strip().lower() for x in indexer.split(",") if x.strip()]
    indexers_list = [x for x in indexers_list if x in ALL_INDEXERS]
    if not indexers_list:
        indexers_list = list(DEFAULT_INDEXERS)
    ct: ContentType = content_type if content_type in ("music", "movies", "tv") else "music"
    for i, query in enumerate(lines, 1):
        typer.echo(f"\n[{i}/{len(lines)}] {query[:60]}{'…' if len(query) > 60 else ''}")
        try:
            run_search(
                query=query,
                album=None,
                best=True,
                auto_download_best_result=True,
                limit=limit,
                format_filter=format_filter,
                download_direct=download_direct,
                download_direct_path=download_dir,
                download_background=background,
                organize_by_artist_album=organize,
                content_type=ct,
                indexers=indexers_list,
            )
        except typer.Exit as e:
            if e.exit_code != 0:
                typer.echo("  (sem resultado aceitável ou erro)")
        except Exception as e:
            typer.echo(f"  Erro: {e}")


def run_batch_cmd(
    file_path: str | None,
    stdin: bool,
    format_filter: str | None,
    download_direct: bool,
    download_dir: str | None,
    background: bool,
    indexer: str,
    limit: int,
    organize: bool,
    content_type: str,
) -> None:
    """Lê linhas de arquivo ou stdin e chama run_batch_lines. Separado da CLI para SRP."""
    if stdin:
        lines = [ln.strip() for ln in sys.stdin.readlines() if ln.strip()]
    elif file_path:
        path = Path(file_path)
        if not path.exists():
            typer.echo(f"Arquivo não encontrado: {file_path}")
            raise typer.Exit(1)
        lines = [
            ln.strip()
            for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip()
        ]
    else:
        typer.echo("Informe o caminho do arquivo ou use --stdin. Ex.: dl-torrent batch lista.txt --download-direct")
        raise typer.Exit(1)

    if not lines:
        typer.echo("Nenhuma linha para processar.")
        return

    run_batch_lines(
        lines,
        format_filter=format_filter,
        download_direct=download_direct,
        download_dir=download_dir,
        background=background,
        indexer=indexer,
        limit=limit,
        organize=organize,
        content_type=content_type,
    )
