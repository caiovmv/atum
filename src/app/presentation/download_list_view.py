"""Renderização da lista de downloads (tabela rich ou fallback texto)."""

from __future__ import annotations

import typer


def _format_bytes(num_bytes: int | float | None) -> str:
    """Formata tamanho em bytes para KB/MB/GB com duas casas decimais."""
    if num_bytes is None or num_bytes < 0:
        return "-"
    n = float(num_bytes)
    if n < 1024:
        return f"{n:.2f} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.2f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.2f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


def _format_eta(seconds: float | None) -> str:
    """Formata tempo restante em segundos para s/min/h/d legível."""
    if seconds is None or seconds < 0:
        return "-"
    s = float(seconds)
    if s < 60:
        return f"{s:.0f} s"
    if s < 3600:
        return f"{s / 60:.1f} min"
    if s < 86400:
        return f"{s / 3600:.1f} h"
    return f"{s / 86400:.1f} d"


def _format_speed(bps: int | None) -> str:
    """Formata velocidade em bytes/s para KB/s, MB/s, etc."""
    if bps is None or bps <= 0:
        return "-"
    return f"{_format_bytes(bps)}/s"


def render_downloads_table(rows: list[dict]) -> None:
    """Exibe a lista de downloads em tabela (rich) ou linhas de texto. Inclui se/le quando disponível."""
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        for r in rows:
            se = r.get("num_seeds")
            # Le = peers - seeds (num_peers é total conectados)
            le = r.get("num_leechers")
            if le is None and se is not None and r.get("num_peers") is not None:
                le = max(0, (r.get("num_peers") or 0) - (r.get("num_seeds") or 0))
            se_le = f" {se}/{le}" if se is not None and le is not None else ""
            err = f" | {r.get('error_message') or ''}" if (r.get("status") or "").lower() == "failed" else ""
            typer.echo(
                f"  {r.get('id')} | {r.get('status')} | {r.get('progress', 0):.0f}% |{se_le} | "
                f"{r.get('name') or (r.get('magnet') or '')[:50]}{err}"
            )
        return
    table = Table(title="Downloads", show_header=True, header_style="bold")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Status", width=12)
    table.add_column("Tipo", width=6, style="dim")
    table.add_column("Progresso", width=8)
    table.add_column("Se/Le", width=7, justify="right", style="dim")
    table.add_column("Nome / Magnet", max_width=50, overflow="ellipsis")
    table.add_column("Pasta", max_width=32, overflow="ellipsis", style="dim")
    table.add_column("Erro (se failed)", max_width=48, overflow="ellipsis", style="red dim")
    status_style = {
        "queued": "dim",
        "downloading": "bold blue",
        "paused": "yellow",
        "completed": "green",
        "failed": "red",
    }
    for r in rows:
        sid = str(r.get("id", ""))
        status = (r.get("status") or "?").lower()
        style = status_style.get(status, "")
        prog = r.get("progress") or 0
        prog_str = f"{prog:.0f}%" if status in ("downloading", "completed") else "-"
        se = r.get("num_seeds")
        le = r.get("num_leechers")
        if le is None and se is not None and r.get("num_peers") is not None:
            le = max(0, (r.get("num_peers") or 0) - (r.get("num_seeds") or 0))
        if se is not None and le is not None:
            se_le = f"{se}/{le}"
        else:
            se_le = "-"
        name = (r.get("name") or "").strip() or (r.get("magnet") or "")[:48]
        path = (r.get("save_path") or "")[:30]
        err = (r.get("error_message") or "").strip() if status == "failed" else ""
        ct = r.get("content_type") or "-"
        if ct not in ("music", "movies", "tv"):
            ct = "-"
        table.add_row(
            sid,
            f"[{style}]{status}[/]" if style else status,
            ct,
            prog_str,
            se_le,
            name,
            path,
            err[:48] + ("..." if len(err) > 48 else ""),
        )
    Console().print(table)


def _worker_status_str(row: dict) -> str:
    """Texto ativo/morto para a coluna Worker a partir de status e pid."""
    pid = row.get("pid")
    status = (row.get("status") or "").lower()
    if status in ("queued", "completed", "failed"):
        return "-"
    if not pid:
        return "[yellow]morto[/]" if status == "downloading" else "-"
    alive = row.get("process_alive")
    if alive is True:
        return "[green]ativo[/]"
    if alive is False:
        return "[red]morto[/]"
    return "?"


def render_downloads_table_watch(rows: list[dict]) -> None:
    """Como render_downloads_table, mas com velocidade, tamanho total, baixado, ETA e estado do processo (para 'download watch')."""
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        for r in rows:
            typer.echo(
                f"  {r.get('id')} | {r.get('status')} | {r.get('progress', 0):.0f}% | "
                f"{_format_speed(r.get('download_speed_bps'))} | {_format_bytes(r.get('total_bytes'))} | "
                f"{_format_bytes(r.get('downloaded_bytes'))} | {_format_eta(r.get('eta_seconds'))} | "
                f"{r.get('name') or (r.get('magnet') or '')[:40]}"
            )
        return
    table = Table(title="Downloads (watch)", show_header=True, header_style="bold")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Status", width=12)
    table.add_column("Tipo", width=6, style="dim")
    table.add_column("Worker", width=8)
    table.add_column("Progresso", width=8)
    table.add_column("Se/Le", width=7, justify="right", style="dim")
    table.add_column("Velocidade", width=12, justify="right")
    table.add_column("Total", width=12, justify="right")
    table.add_column("Baixado", width=12, justify="right")
    table.add_column("ETA", width=10, justify="right")
    table.add_column("Nome / Magnet", max_width=38, overflow="ellipsis")
    table.add_column("Pasta", max_width=26, overflow="ellipsis", style="dim")
    status_style = {
        "queued": "dim",
        "downloading": "bold blue",
        "paused": "yellow",
        "completed": "green",
        "failed": "red",
    }
    for r in rows:
        sid = str(r.get("id", ""))
        status = (r.get("status") or "?").lower()
        style = status_style.get(status, "")
        worker_str = _worker_status_str(r)
        prog = r.get("progress") or 0
        if status == "completed":
            prog_str = "100%"
            eta_str = "0 s"
            done_str = _format_bytes(r.get("total_bytes"))
        else:
            prog_str = f"{prog:.0f}%" if status == "downloading" else "-"
            eta_str = _format_eta(r.get("eta_seconds"))
            done_str = _format_bytes(r.get("downloaded_bytes"))
        se = r.get("num_seeds")
        le = r.get("num_leechers")
        if le is None and se is not None and r.get("num_peers") is not None:
            le = max(0, (r.get("num_peers") or 0) - (r.get("num_seeds") or 0))
        se_le = f"{se}/{le}" if se is not None and le is not None else "-"
        speed_str = _format_speed(r.get("download_speed_bps"))
        total_str = _format_bytes(r.get("total_bytes"))
        name = (r.get("name") or "").strip() or (r.get("magnet") or "")[:36]
        path = (r.get("save_path") or "")[:24]
        ct = r.get("content_type") or "-"
        if ct not in ("music", "movies", "tv"):
            ct = "-"
        table.add_row(
            sid,
            f"[{style}]{status}[/]" if style else status,
            ct,
            worker_str,
            prog_str,
            se_le,
            speed_str,
            total_str,
            done_str,
            eta_str,
            name,
            path,
        )
    Console().print(table)
