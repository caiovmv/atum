"""Portas (abstrações) para inversão de dependência. O domínio não depende de infra."""

from __future__ import annotations

from typing import Protocol


class DownloadRepository(Protocol):
    """Abstração do repositório de downloads (DIP). Permite testar e trocar implementação."""

    def add(
        self,
        magnet: str,
        save_path: str,
        name: str | None = None,
        content_type: str | None = None,
    ) -> int:
        """Adiciona download à fila. Retorna id."""
        ...

    def list(self, status_filter: str | None = None) -> list[dict]:
        """Lista downloads (todos ou por status)."""
        ...

    def get(self, download_id: int) -> dict | None:
        """Retorna um download por id."""
        ...

    def update_status(
        self,
        download_id: int,
        status: str,
        error_message: str | None = None,
        progress: float | None = None,
    ) -> None:
        """Atualiza status (e opcionalmente progress)."""
        ...

    def set_pid(self, download_id: int, pid: int | None) -> None:
        """Define PID do processo do worker."""
        ...

    def set_content_path(self, download_id: int, content_path: str | None) -> None:
        """Define caminho do conteúdo no disco."""
        ...

    def set_cover_paths(
        self,
        download_id: int,
        cover_path_small: str | None = None,
        cover_path_large: str | None = None,
    ) -> None:
        """Define caminhos das capas (pequena/grande) no disco."""
        ...

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
        """Atualiza campos de progresso."""
        ...

    def delete(self, download_id: int) -> bool:
        """Remove o registro. Retorna True se existia."""
        ...
