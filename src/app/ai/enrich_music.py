"""Pipeline de enriquecimento de música em 5 fases: MusicBrainz, Last.fm, Spotify, essentia, LLM."""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import time as _time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Global rate limiter for MusicBrainz API (max 1 req/s across all threads)
_mb_lock = threading.Lock()
_mb_last_call: float = 0.0


def _musicbrainz_rate_limit() -> None:
    global _mb_last_call
    with _mb_lock:
        elapsed = _time.monotonic() - _mb_last_call
        if elapsed < 1.0:
            _time.sleep(1.0 - elapsed)
        _mb_last_call = _time.monotonic()

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".aiff", ".aac", ".opus", ".wma"}


@dataclass
class MusicEnrichmentResult:
    """Resultado consolidado do pipeline de enriquecimento de música."""
    bpm: float | None = None
    musical_key: str | None = None
    energy: float | None = None
    danceability: float | None = None
    valence: float | None = None
    loudness_db: float | None = None
    replaygain_db: float | None = None
    musicbrainz_id: str | None = None
    sub_genres: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)
    descriptors: list[str] = field(default_factory=list)
    record_label: str | None = None
    release_type: str | None = None
    enrichment_sources: list[str] = field(default_factory=list)
    enriched_at: str | None = None

    def to_update_dict(self) -> dict:
        """Retorna dict com apenas campos não-None para update_metadata."""
        d: dict = {}
        if self.bpm is not None:
            d["bpm"] = self.bpm
        if self.musical_key is not None:
            d["musical_key"] = self.musical_key
        if self.energy is not None:
            d["energy"] = self.energy
        if self.danceability is not None:
            d["danceability"] = self.danceability
        if self.valence is not None:
            d["valence"] = self.valence
        if self.loudness_db is not None:
            d["loudness_db"] = self.loudness_db
        if self.replaygain_db is not None:
            d["replaygain_db"] = self.replaygain_db
        if self.musicbrainz_id is not None:
            d["musicbrainz_id"] = self.musicbrainz_id
        if self.sub_genres:
            d["sub_genres"] = self.sub_genres
        if self.moods:
            d["moods"] = self.moods
        if self.descriptors:
            d["descriptors"] = self.descriptors
        if self.record_label is not None:
            d["record_label"] = self.record_label
        if self.release_type is not None:
            d["release_type"] = self.release_type
        if self.enrichment_sources:
            d["enrichment_sources"] = self.enrichment_sources
        d["enriched_at"] = self.enriched_at or datetime.now(timezone.utc).isoformat()
        d["enrichment_error"] = None
        return d


def _first_audio_file(content_path: str) -> Path | None:
    """Retorna o primeiro arquivo de áudio encontrado no content_path."""
    p = Path(content_path)
    if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
        return p
    if p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS:
                return f
    return None


# ---------------------------------------------------------------------------
# Fase 1: MusicBrainz
# ---------------------------------------------------------------------------

def _enrich_musicbrainz(artist: str, album: str) -> dict:
    """Busca no MusicBrainz por release group. Retorna label, release_type, musicbrainz_id."""
    try:
        import musicbrainzngs
        musicbrainzngs.set_useragent("Atum", "0.2.0", "https://github.com/caiovmv/dl-torrent")
    except ImportError:
        logger.debug("musicbrainzngs não instalado, pulando fase MusicBrainz")
        return {}

    if not artist or not album:
        return {}

    try:
        _musicbrainz_rate_limit()
        result = musicbrainzngs.search_release_groups(
            artist=artist, releasegroup=album, limit=5
        )
        rg_list = result.get("release-group-list", [])
        if not rg_list:
            return {}

        best = rg_list[0]
        mb_id = best.get("id")
        rtype = best.get("type", "")
        tags = [t.get("name", "") for t in best.get("tag-list", []) if t.get("name")]

        label = None
        try:
            _musicbrainz_rate_limit()
            releases = musicbrainzngs.browse_releases(
                release_group=mb_id, includes=["labels"], limit=1
            )
            for rel in releases.get("release-list", []):
                for li in rel.get("label-info-list", []):
                    lbl = li.get("label", {}).get("name")
                    if lbl:
                        label = lbl
                        break
                if label:
                    break
        except Exception:
            pass

        out: dict = {}
        if mb_id:
            out["musicbrainz_id"] = mb_id
        if rtype:
            out["release_type"] = rtype
        if label:
            out["record_label"] = label
        if tags:
            out["mb_tags"] = tags
        return out

    except Exception as e:
        logger.debug("MusicBrainz error: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Fase 2: Last.fm Tags
# ---------------------------------------------------------------------------

def _enrich_lastfm_tags(artist: str, album: str) -> dict:
    """Busca tags da comunidade no Last.fm (artist + album em paralelo)."""
    from concurrent.futures import ThreadPoolExecutor

    from ..deps import get_settings_repo

    repo = get_settings_repo()
    api_key = None
    if repo:
        api_key = repo.get("lastfm_api_key")
    if not api_key:
        from ..deps import get_settings
        api_key = (get_settings().lastfm_api_key or "").strip()
    if not api_key or not artist:
        return {}

    def _fetch_artist_tags() -> tuple[list[str], list[str]]:
        sg: list[str] = []
        desc: list[str] = []
        try:
            r = requests.get(
                "https://ws.audioscrobbler.com/2.0/",
                params={
                    "method": "artist.getTopTags",
                    "artist": artist,
                    "api_key": api_key,
                    "format": "json",
                },
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                for tag in data.get("toptags", {}).get("tag", []):
                    name = (tag.get("name") or "").strip().lower()
                    count = int(tag.get("count", 0))
                    if not name:
                        continue
                    if count >= 50:
                        sg.append(name)
                    elif count >= 20:
                        desc.append(name)
        except Exception as e:
            logger.debug("Last.fm artist tags error: %s", e)
        return sg, desc

    def _fetch_album_tags() -> list[str]:
        tags: list[str] = []
        if not album:
            return tags
        try:
            r = requests.get(
                "https://ws.audioscrobbler.com/2.0/",
                params={
                    "method": "album.getInfo",
                    "artist": artist,
                    "album": album,
                    "api_key": api_key,
                    "format": "json",
                },
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                for tag in data.get("album", {}).get("tags", {}).get("tag", []):
                    name = (tag.get("name") or "").strip().lower()
                    if name:
                        tags.append(name)
        except Exception as e:
            logger.debug("Last.fm album info error: %s", e)
        return tags

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_artist = pool.submit(_fetch_artist_tags)
        f_album = pool.submit(_fetch_album_tags)
        sub_genres, descriptors = f_artist.result()
        album_tags = f_album.result()

    existing = set(sub_genres) | set(descriptors)
    for name in album_tags:
        if name not in existing:
            descriptors.append(name)
            existing.add(name)

    out: dict = {}
    if sub_genres:
        out["sub_genres"] = sub_genres[:10]
    if descriptors:
        out["descriptors"] = descriptors[:10]
    return out


# ---------------------------------------------------------------------------
# Fase 3: Spotify Audio Features
# ---------------------------------------------------------------------------

def _enrich_spotify_features(artist: str, track_title: str | None) -> dict:
    """Busca audio features no Spotify."""
    from ..deps import get_settings_repo, get_settings

    repo = get_settings_repo()
    client_id = ""
    client_secret = ""
    if repo:
        client_id = repo.get("spotify_client_id") or ""
        client_secret = repo.get("spotify_client_secret") or ""
    if not client_id:
        s = get_settings()
        client_id = s.spotify_client_id or ""
        client_secret = s.spotify_client_secret or ""
    if not client_id or not client_secret or not artist:
        return {}

    try:
        from ..spotify import ensure_valid_token
        token = ensure_valid_token(client_id, client_secret)
    except Exception as e:
        logger.debug("Spotify token error: %s", e)
        return {}

    query = f"artist:{artist}"
    if track_title:
        query += f" track:{track_title}"

    try:
        r = requests.get(
            "https://api.spotify.com/v1/search",
            params={"q": query, "type": "track", "limit": 1},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.status_code != 200:
            return {}
        tracks = r.json().get("tracks", {}).get("items", [])
        if not tracks:
            return {}
        track_id = tracks[0].get("id")
        if not track_id:
            return {}

        r2 = requests.get(
            f"https://api.spotify.com/v1/audio-features/{track_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r2.status_code != 200:
            return {}
        features = r2.json()

        out: dict = {}
        if features.get("tempo"):
            out["bpm"] = round(float(features["tempo"]), 1)
        if features.get("energy") is not None:
            out["energy"] = round(float(features["energy"]), 3)
        if features.get("danceability") is not None:
            out["danceability"] = round(float(features["danceability"]), 3)
        if features.get("valence") is not None:
            out["valence"] = round(float(features["valence"]), 3)
        if features.get("loudness") is not None:
            out["loudness_db"] = round(float(features["loudness"]), 1)
        if features.get("key") is not None:
            keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            mode = "major" if features.get("mode", 0) == 1 else "minor"
            key_idx = int(features["key"])
            if 0 <= key_idx < 12:
                out["musical_key"] = f"{keys[key_idx]} {mode}"
        return out

    except Exception as e:
        logger.debug("Spotify features error: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Fase 4: Análise de áudio local (essentia ou ffmpeg)
# ---------------------------------------------------------------------------

def _analyze_audio_essentia(filepath: str) -> dict:
    """Analisa áudio com essentia. Retorna bpm, key, energy, loudness, replaygain."""
    try:
        import essentia.standard as es  # type: ignore[import-untyped]
    except ImportError:
        return {}

    try:
        audio = es.MonoLoader(filename=filepath, sampleRate=44100)()
        out: dict = {}

        bpm, *_ = es.RhythmExtractor2013()(audio)
        if bpm and bpm > 0:
            out["bpm"] = round(float(bpm), 1)

        key, scale, _ = es.KeyExtractor()(audio)
        if key:
            out["musical_key"] = f"{key} {scale}"

        energy = es.Energy()(audio)
        if energy is not None:
            out["energy"] = round(float(energy), 6)

        loudness = es.Loudness()(audio)
        if loudness is not None:
            out["loudness_db"] = round(float(loudness), 1)

        try:
            rg = es.ReplayGain()(audio)
            if rg is not None:
                out["replaygain_db"] = round(float(rg), 2)
        except Exception:
            pass

        return out
    except Exception as e:
        logger.debug("essentia analysis error: %s", e)
        return {}


def _analyze_audio_ffmpeg(filepath: str) -> dict:
    """Fallback: calcula loudness via ffmpeg loudnorm."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-i", filepath,
                "-af", "loudnorm=print_format=json",
                "-f", "null", "-",
            ],
            capture_output=True, text=True, timeout=60,
        )
        output = result.stderr
        json_start = output.rfind("{")
        json_end = output.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            data = json.loads(output[json_start:json_end])
            out: dict = {}
            if data.get("input_i"):
                try:
                    out["loudness_db"] = round(float(data["input_i"]), 1)
                except (ValueError, TypeError):
                    pass
            if data.get("input_i"):
                try:
                    out["replaygain_db"] = round(-18.0 - float(data["input_i"]), 2)
                except (ValueError, TypeError):
                    pass
            return out
    except Exception as e:
        logger.debug("ffmpeg loudnorm error: %s", e)
    return {}


def _analyze_audio_local(filepath: str) -> dict:
    """Tenta essentia, fallback para ffmpeg."""
    result = _analyze_audio_essentia(filepath)
    if result:
        return result
    return _analyze_audio_ffmpeg(filepath)


# ---------------------------------------------------------------------------
# Fase 5: LLM (moods, contexto)
# ---------------------------------------------------------------------------

def _enrich_with_llm(item: dict, features: dict, llm_client: object) -> dict:
    """Usa LLM para inferir moods e contextos de uso."""
    from ..deps import get_settings_repo
    from .prompts_registry import get_prompt_config

    artist = item.get("artist") or ""
    album = item.get("album") or ""
    genre = item.get("genre") or ""
    sub_genres = features.get("sub_genres", [])
    descriptors = features.get("descriptors", [])
    bpm = features.get("bpm")
    key = features.get("musical_key")
    energy = features.get("energy")
    valence = features.get("valence")

    user_content = (
        f"Artista: {artist}\n"
        f"Álbum: {album}\n"
        f"Gênero principal: {genre or 'desconhecido'}\n"
        f"Sub-gêneros conhecidos: {', '.join(sub_genres[:5]) if sub_genres else 'nenhum'}\n"
        f"Tags externas: {', '.join(descriptors[:5]) if descriptors else 'nenhuma'}\n"
        f"BPM: {bpm or '?'} | Key: {key or '?'} | Energy: {energy or '?'} | Valence: {valence or '?'}"
    )

    repo = get_settings_repo() or {"ai_prompts": {}}
    config = get_prompt_config("enrichment", repo)
    try:
        data = llm_client.chat_json(
            [
                {"role": "system", "content": config["system"]},
                {"role": "user", "content": user_content},
            ],
            temperature=config["temperature"],
        )
        out: dict = {}
        if isinstance(data.get("moods"), list):
            out["moods"] = [str(m).strip() for m in data["moods"] if m][:5]
        if isinstance(data.get("descriptors"), list):
            out["descriptors"] = [str(d).strip() for d in data["descriptors"] if d][:5]
        if isinstance(data.get("sub_genres"), list):
            refined = [str(g).strip().lower() for g in data["sub_genres"] if g][:8]
            if refined:
                out["sub_genres"] = refined
        return out
    except Exception as e:
        logger.warning("LLM enrichment error: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def enrich_music_item(item: dict, llm_client: object | None = None) -> MusicEnrichmentResult:
    """Pipeline de enriquecimento para um item de música.

    Fases 1-4 (MusicBrainz, Last.fm, Spotify, Essentia) rodam em paralelo
    pois são independentes. Fase 5 (LLM) roda ao final com os dados agregados.
    """
    from concurrent.futures import ThreadPoolExecutor

    result = MusicEnrichmentResult()
    sources: list[str] = []
    all_features: dict = {}

    artist = (item.get("artist") or "").strip()
    album = (item.get("album") or "").strip()
    content_path = (item.get("content_path") or "").strip()

    audio_file = _first_audio_file(content_path) if content_path else None
    first_track = None
    if audio_file:
        from ..audio_metadata import read_audio_metadata
        meta = read_audio_metadata(audio_file)
        first_track = meta.title

    # Fases 1-4 em paralelo
    with ThreadPoolExecutor(max_workers=4) as pool:
        mb_future = pool.submit(_enrich_musicbrainz, artist, album)
        lfm_future = pool.submit(_enrich_lastfm_tags, artist, album)
        sp_future = pool.submit(_enrich_spotify_features, artist, first_track)
        ea_future = pool.submit(_analyze_audio_local, str(audio_file)) if audio_file else None

        mb = mb_future.result()
        lfm = lfm_future.result()
        sp = sp_future.result()
        ea = ea_future.result() if ea_future else {}

    # Merge: MusicBrainz
    if mb:
        result.musicbrainz_id = mb.get("musicbrainz_id")
        result.record_label = mb.get("record_label")
        result.release_type = mb.get("release_type")
        sources.append("musicbrainz")
        all_features.update(mb)

    # Merge: Last.fm
    if lfm:
        result.sub_genres = lfm.get("sub_genres", [])
        result.descriptors = lfm.get("descriptors", [])
        sources.append("lastfm")
        all_features.update(lfm)

    # Merge: Spotify
    if sp:
        result.bpm = sp.get("bpm")
        result.musical_key = sp.get("musical_key")
        result.energy = sp.get("energy")
        result.danceability = sp.get("danceability")
        result.valence = sp.get("valence")
        result.loudness_db = sp.get("loudness_db")
        sources.append("spotify")
        all_features.update(sp)

    # Merge: Essentia/ffmpeg (complemento ou fallback do Spotify)
    if ea:
        if result.bpm is None and ea.get("bpm"):
            result.bpm = ea["bpm"]
        if result.musical_key is None and ea.get("musical_key"):
            result.musical_key = ea["musical_key"]
        if result.energy is None and ea.get("energy"):
            result.energy = ea["energy"]
        if result.loudness_db is None and ea.get("loudness_db"):
            result.loudness_db = ea["loudness_db"]
        if ea.get("replaygain_db") is not None:
            result.replaygain_db = ea["replaygain_db"]
        sources.append("essentia" if ea.get("bpm") else "ffmpeg")
        all_features.update(ea)

    # Fase 5: LLM (precisa dos dados agregados)
    if llm_client:
        llm_data = _enrich_with_llm(item, all_features, llm_client)
        if llm_data:
            if llm_data.get("moods"):
                result.moods = llm_data["moods"]
            if llm_data.get("sub_genres"):
                result.sub_genres = llm_data["sub_genres"]
            if llm_data.get("descriptors"):
                merged = list(dict.fromkeys(result.descriptors + llm_data["descriptors"]))
                result.descriptors = merged[:10]
            sources.append("llm")

    result.enrichment_sources = sources
    result.enriched_at = datetime.now(timezone.utc).isoformat()
    return result
