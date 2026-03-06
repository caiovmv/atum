"""Configuração do app (cliente, indexadores, paths)."""

from pathlib import Path
from typing import Literal, Protocol

from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsProvider(Protocol):
    """Abstração para fornecer configuração (permite injeção em testes)."""

    def get_settings(self) -> "Settings":
        ...


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    client_type: Literal["transmission", "utorrent", "folder"] = "transmission"

    # Transmission
    transmission_host: str = "localhost"
    transmission_port: int = 9091
    transmission_user: str = ""
    transmission_password: str = ""

    # uTorrent
    utorrent_url: str = "http://localhost:8080"
    utorrent_user: str = "admin"
    utorrent_password: str = ""

    # Folder (FrostWire / pasta monitorada)
    watch_folder: str = "./torrents"
    download_dir: str = ""

    # Bibliotecas por tipo: música e vídeo (ex.: D:\Library\Music e D:\Library\Videos no host).
    # No Docker: LIBRARY_MUSIC_PATH=/library/music, LIBRARY_VIDEOS_PATH=/library/videos.
    library_music_path: str = ""
    library_videos_path: str = ""

    # 1337x: URL base (espelho 1377x.to costuma responder quando 1337x.to falha)
    x1337_base_url: str = "https://www.1377x.to"

    # The Pirate Bay: domínio varia por região (tpb.party, thepiratebay.org, etc.)
    tpb_base_url: str = "https://tpb.party"

    # YTS (filmes; API JSON)
    yts_base_url: str = "https://yts.lt"

    # EZTV (séries TV)
    eztv_base_url: str = "https://eztv.re"

    # NYAA (anime)
    nyaa_base_url: str = "https://nyaa.si"

    # Limetorrents
    limetorrents_base_url: str = "https://www.limetorrents.lol"

    # IPTorrents (tracker privado; requer cookie de sessão)
    iptorrents_base_url: str = "https://iptorrents.com"

    # Last.fm: API key opcional para resolver artista/álbum (obtenha em https://www.last.fm/api/account)
    lastfm_api_key: str = ""

    # Spotify: OAuth para playlists (obtenha em https://developer.spotify.com/dashboard)
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_port: int = 8765

    # Organizar download direto em subpastas Artist/Album (extraído do título)
    organize_by_artist_album: bool = False

    # Notificação ao detectar/baixar item do feed (webhook ou desktop)
    notify_enabled: bool = False
    notify_webhook_url: str = ""
    notify_desktop: bool = False

    # Download Runner: URL do processo que expõe a fila (ex: http://127.0.0.1:9092). Vazio = usar download_manager no processo.
    download_runner_url: str = ""

    # Progresso do download: intervalo em segundos entre atualizações no DB (padrão 1.0). Valores menores deixam a UI mais fluida; o worker aplica rate-limit mínimo de 1s nas escritas.
    download_progress_interval_seconds: float = 1.0

    # TMDB (The Movie Database): capas para filmes e séries na interface web (obtenha em https://www.themoviedb.org/settings/api).
    tmdb_api_key: str = ""
    tmdb_read_access_token: str = ""

    # Pasta para cache de capas (artwork baixado). Vazio = ~/.dl-torrent/covers.
    covers_dir: str = ""

    # Persistência: PostgreSQL (obrigatório). Ex.: postgresql://user:pass@host:5432/dbname
    database_url: str = ""

    # Cache: se definido, usa Redis para cache de capas/TMDB (ex.: redis://redis:6379/0).
    redis_url: str = ""

    @property
    def watch_folder_path(self) -> Path:
        return Path(self.watch_folder).expanduser().resolve()

    def save_path_for_content_type(self, content_type: str | None) -> str:
        """Retorna o diretório base para download conforme content_type (music -> library_music_path, movies/tv -> library_videos_path)."""
        ct = (content_type or "").strip().lower()
        if ct == "music" and self.library_music_path and self.library_music_path.strip():
            return str(Path(self.library_music_path.strip()).expanduser().resolve())
        if ct in ("movies", "tv") and self.library_videos_path and self.library_videos_path.strip():
            return str(Path(self.library_videos_path.strip()).expanduser().resolve())
        base = (
            (self.download_dir or "").strip()
            or getattr(self, "watch_folder", "") or "./downloads"
        )
        return str(Path(base).expanduser().resolve())

    @property
    def covers_path(self) -> Path:
        """Diretório para cache de capas. Padrão: ~/.dl-torrent/covers."""
        if self.covers_dir and self.covers_dir.strip():
            return Path(self.covers_dir).expanduser().resolve()
        return Path.home() / ".dl-torrent" / "covers"


_settings_override: Settings | None = None


def get_settings() -> Settings:
    """Retorna as configurações (ou override injetado via set_settings_override, para testes)."""
    global _settings_override
    if _settings_override is not None:
        return _settings_override
    return Settings()


def set_settings_override(settings: Settings | None) -> None:
    """Injeta Settings para testes. None restaura o padrão."""
    global _settings_override
    _settings_override = settings
