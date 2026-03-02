"""Repositório de downloads (fila em background). Implementa a porta DownloadRepository (DIP)."""

from __future__ import annotations

from pathlib import Path

from ..db import get_connection
from ..domain import DownloadStatus
from ..domain.ports import DownloadRepository


def _conn(db_path: Path | None = None):
    return get_connection(db_path=db_path)


def download_add(
    magnet: str,
    save_path: str,
    name: str | None = None,
    content_type: str | None = None,
    db_path: Path | None = None,
) -> int:
    """Adiciona um download à fila. content_type opcional: music, movies, tv. Retorna o id."""
    conn = _conn(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO downloads (magnet, name, save_path, status, content_type) VALUES (?, ?, ?, ?, ?)",
            (
                magnet.strip(),
                (name or "").strip() or None,
                save_path,
                DownloadStatus.QUEUED.value,
                content_type if content_type in ("music", "movies", "tv") else None,
            ),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def _download_list_columns(conn) -> str:
    """Retorna lista de colunas para SELECT em downloads (inclui colunas de progresso e content_path se existirem)."""
    cur = conn.execute("PRAGMA table_info(downloads)")
    existing = {row[1] for row in cur.fetchall()}
    base = "id, magnet, name, save_path, status, progress, pid, error_message, added_at, updated_at"
    extra = [
        "num_seeds", "num_peers", "download_speed_bps", "total_bytes", "downloaded_bytes", "eta_seconds",
        "content_path", "content_type",
        "cover_path_small", "cover_path_large",
        "year", "video_quality_label", "audio_codec", "music_quality",
    ]
    for c in extra:
        if c in existing:
            base += f", {c}"
    return base


def download_list(
    status_filter: str | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    """Lista downloads (todos ou por status)."""
    conn = _conn(db_path)
    try:
        cols = _download_list_columns(conn)
        if status_filter:
            rows = conn.execute(
                f"SELECT {cols} FROM downloads WHERE status = ? ORDER BY id DESC",
                (status_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {cols} FROM downloads ORDER BY id DESC"
            ).fetchall()
        out = [dict(r) for r in rows]
        _apply_download_defaults(out)
        return out
    finally:
        conn.close()


def download_get(download_id: int, db_path: Path | None = None) -> dict | None:
    """Retorna um download por id."""
    conn = _conn(db_path)
    try:
        cols = _download_list_columns(conn)
        row = conn.execute(
            f"SELECT {cols} FROM downloads WHERE id = ?",
            (download_id,),
        ).fetchone()
        if not row:
            return None
        out = dict(row)
        _apply_download_defaults([out])
        return out
    finally:
        conn.close()


def _apply_download_defaults(rows: list[dict]) -> None:
    """Preenche None para colunas opcionais de downloads."""
    keys = [
        "num_seeds", "num_peers", "download_speed_bps", "total_bytes", "downloaded_bytes", "eta_seconds",
        "content_path", "content_type",
        "cover_path_small", "cover_path_large",
        "year", "video_quality_label", "audio_codec", "music_quality",
    ]
    for row in rows:
        for k in keys:
            row.setdefault(k, None)


def download_set_content_path(download_id: int, content_path: str | None, db_path: Path | None = None) -> None:
    """Define o caminho real do conteúdo no disco (pasta/arquivo do torrent)."""
    conn = _conn(db_path)
    try:
        conn.execute(
            "UPDATE downloads SET content_path = ?, updated_at = datetime('now') WHERE id = ?",
            (content_path, download_id),
        )
        conn.commit()
    finally:
        conn.close()


def download_set_cover_paths(
    download_id: int,
    cover_path_small: str | None = None,
    cover_path_large: str | None = None,
    db_path: Path | None = None,
) -> None:
    """Define os caminhos das capas (pequena e/ou grande). None limpa a coluna."""
    conn = _conn(db_path)
    try:
        conn.execute(
            "UPDATE downloads SET cover_path_small = ?, cover_path_large = ?, updated_at = datetime('now') WHERE id = ?",
            (cover_path_small, cover_path_large, download_id),
        )
        conn.commit()
    finally:
        conn.close()


def download_update_status(
    download_id: int,
    status: str,
    error_message: str | None = None,
    progress: float | None = None,
    db_path: Path | None = None,
) -> None:
    conn = _conn(db_path)
    try:
        if progress is not None:
            conn.execute(
                "UPDATE downloads SET status = ?, error_message = ?, progress = ?, updated_at = datetime('now') WHERE id = ?",
                (status, error_message, progress, download_id),
            )
        else:
            conn.execute(
                "UPDATE downloads SET status = ?, error_message = ?, updated_at = datetime('now') WHERE id = ?",
                (status, error_message, download_id),
            )
        conn.commit()
    finally:
        conn.close()


def download_set_pid(download_id: int, pid: int | None, db_path: Path | None = None) -> None:
    conn = _conn(db_path)
    try:
        conn.execute(
            "UPDATE downloads SET pid = ?, updated_at = datetime('now') WHERE id = ?",
            (pid, download_id),
        )
        conn.commit()
    finally:
        conn.close()


def download_update_progress(
    download_id: int,
    *,
    progress: float | None = None,
    num_seeds: int | None = None,
    num_peers: int | None = None,
    download_speed_bps: int | None = None,
    total_bytes: int | None = None,
    downloaded_bytes: int | None = None,
    eta_seconds: float | None = None,
    db_path: Path | None = None,
) -> None:
    """Atualiza campos de progresso do download (worker chama durante o download)."""
    conn = _conn(db_path)
    try:
        updates = ["updated_at = datetime('now')"]
        args: list = []
        if progress is not None:
            updates.append("progress = ?")
            args.append(progress)
        if num_seeds is not None:
            updates.append("num_seeds = ?")
            args.append(num_seeds)
        if num_peers is not None:
            updates.append("num_peers = ?")
            args.append(num_peers)
        if download_speed_bps is not None:
            updates.append("download_speed_bps = ?")
            args.append(download_speed_bps)
        if total_bytes is not None:
            updates.append("total_bytes = ?")
            args.append(total_bytes)
        if downloaded_bytes is not None:
            updates.append("downloaded_bytes = ?")
            args.append(downloaded_bytes)
        if eta_seconds is not None:
            updates.append("eta_seconds = ?")
            args.append(eta_seconds)
        if args:
            args.append(download_id)
            conn.execute(
                f"UPDATE downloads SET {', '.join(updates)} WHERE id = ?",
                args,
            )
            conn.commit()
    finally:
        conn.close()


def download_delete(download_id: int, db_path: Path | None = None) -> bool:
    """Remove o registro do download. Retorna True se existia."""
    conn = _conn(db_path)
    try:
        cur = conn.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


class SqliteDownloadRepository:
    """Implementação concreta de DownloadRepository (SQLite). Permite injeção em download_manager (DIP)."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path

    def add(
        self,
        magnet: str,
        save_path: str,
        name: str | None = None,
        content_type: str | None = None,
    ) -> int:
        return download_add(magnet, save_path, name, content_type, self._db_path)

    def list(self, status_filter: str | None = None) -> list[dict]:
        return download_list(status_filter=status_filter, db_path=self._db_path)

    def get(self, download_id: int) -> dict | None:
        return download_get(download_id, db_path=self._db_path)

    def update_status(
        self,
        download_id: int,
        status: str,
        error_message: str | None = None,
        progress: float | None = None,
    ) -> None:
        download_update_status(
            download_id, status, error_message=error_message, progress=progress, db_path=self._db_path
        )

    def set_pid(self, download_id: int, pid: int | None) -> None:
        download_set_pid(download_id, pid, db_path=self._db_path)

    def set_content_path(self, download_id: int, content_path: str | None) -> None:
        download_set_content_path(download_id, content_path, db_path=self._db_path)

    def set_cover_paths(
        self,
        download_id: int,
        cover_path_small: str | None = None,
        cover_path_large: str | None = None,
    ) -> None:
        download_set_cover_paths(
            download_id,
            cover_path_small=cover_path_small,
            cover_path_large=cover_path_large,
            db_path=self._db_path,
        )

    def update_progress(
        self,
        download_id: int,
        *,
        progress: float | None = None,
        num_seeds: int | None = None,
        num_peers: int | None = None,
        download_speed_bps: int | None = None,
        total_bytes: int | None = None,
        downloaded_bytes: int | None = None,
        eta_seconds: float | None = None,
    ) -> None:
        download_update_progress(
            download_id,
            progress=progress,
            num_seeds=num_seeds,
            num_peers=num_peers,
            download_speed_bps=download_speed_bps,
            total_bytes=total_bytes,
            downloaded_bytes=downloaded_bytes,
            eta_seconds=eta_seconds,
            db_path=self._db_path,
        )

    def delete(self, download_id: int) -> bool:
        return download_delete(download_id, db_path=self._db_path)


# Ponto único de acesso ao repositório (DIP): DATABASE_URL → Postgres; senão SQLite; testes podem injetar via set_repo.
_repo: DownloadRepository | None = None
_singleton: SqliteDownloadRepository | None = None
_postgres_singleton: object | None = None


def get_repo() -> DownloadRepository:
    """Retorna o repositório de downloads (injetado, Postgres se DATABASE_URL, senão SQLite)."""
    global _singleton, _postgres_singleton
    if _repo is not None:
        return _repo
    from ..config import get_settings
    database_url = (get_settings().database_url or "").strip()
    if database_url:
        if _postgres_singleton is None:
            from .download_repository_postgres import PostgresDownloadRepository
            _postgres_singleton = PostgresDownloadRepository(database_url)
        return _postgres_singleton
    if _singleton is None:
        _singleton = SqliteDownloadRepository()
    return _singleton


def set_repo(repo: DownloadRepository | None) -> None:
    """Injeta o repositório (para testes). None restaura o padrão."""
    global _repo
    _repo = repo
