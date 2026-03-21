"""Testes unitários para app.web.hls_service.

Cobrem:
- Seleção de variantes por resolução (_select_variants)
- Geração de master.m3u8 (_build_master_m3u8)
- Geração do comando FFmpeg (_build_ffmpeg_cmd)
- Regex de progresso (_FFMPEG_TIME_RE)
- Operações de cache no filesystem: cleanup, invalidate, evict, is_playable
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# O hls_service importa get_settings na chamada (não no módulo), por isso podemos
# patch localmente sem problemas de import order.
import app.web.hls_service as hls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(tmp_path: Path) -> MagicMock:
    """Cria um mock de Settings com hls_cache_path apontando para tmp_path."""
    s = MagicMock()
    s.hls_cache_path = tmp_path
    s.download_runner_url = "http://localhost:9092"
    return s


def _make_complete_cache(base: Path, key: str, n_variants: int = 2) -> Path:
    """Cria um cache HLS completo no filesystem (com #EXT-X-ENDLIST)."""
    job_dir = base / key
    for i in range(n_variants):
        pl = job_dir / f"stream_{i}" / "playlist.m3u8"
        pl.parent.mkdir(parents=True, exist_ok=True)
        pl.write_text(
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXTINF:6.0,\nseg00001.ts\n#EXT-X-ENDLIST\n"
        )
    (job_dir / "master.m3u8").write_text("#EXTM3U\nstream_0/playlist.m3u8\n")
    return job_dir


def _make_partial_cache(base: Path, key: str, n_variants: int = 1) -> Path:
    """Cria um cache HLS parcial (sem #EXT-X-ENDLIST — transcodificação interrompida)."""
    job_dir = base / key
    for i in range(n_variants):
        pl = job_dir / f"stream_{i}" / "playlist.m3u8"
        pl.parent.mkdir(parents=True, exist_ok=True)
        pl.write_text("#EXTM3U\n#EXT-X-VERSION:3\n#EXTINF:6.0,\nseg00001.ts\n")
    return job_dir


# ---------------------------------------------------------------------------
# Seleção de variantes
# ---------------------------------------------------------------------------


class TestSelectVariants:
    def test_1080p_source_returns_all_three(self) -> None:
        variants = hls._select_variants(1080)
        assert len(variants) == 3
        assert [v.name for v in variants] == ["360p", "720p", "1080p"]

    def test_720p_source_returns_two(self) -> None:
        variants = hls._select_variants(720)
        assert len(variants) == 2
        assert [v.name for v in variants] == ["360p", "720p"]

    def test_480p_source_returns_only_360p(self) -> None:
        variants = hls._select_variants(480)
        assert len(variants) == 1
        assert variants[0].name == "360p"

    def test_below_360p_still_returns_one_variant(self) -> None:
        """Garante sempre ao menos uma variante para não travar o job."""
        variants = hls._select_variants(240)
        assert len(variants) == 1
        assert variants[0].name == "360p"

    def test_exact_boundary_720_includes_720(self) -> None:
        variants = hls._select_variants(720)
        names = [v.name for v in variants]
        assert "720p" in names
        assert "1080p" not in names

    def test_zero_height_defaults_to_at_least_one(self) -> None:
        """Source height=0 (ffprobe falhou) → ao menos 360p."""
        variants = hls._select_variants(0)
        assert len(variants) >= 1


# ---------------------------------------------------------------------------
# Geração do master.m3u8
# ---------------------------------------------------------------------------


class TestBuildMasterM3u8:
    def test_contains_extm3u_header(self) -> None:
        content = hls._build_master_m3u8(hls._select_variants(1080))
        assert "#EXTM3U" in content
        assert "#EXT-X-VERSION:3" in content

    def test_one_variant_one_stream_entry(self) -> None:
        variants = hls._select_variants(480)  # só 360p
        content = hls._build_master_m3u8(variants)
        assert "stream_0/playlist.m3u8" in content
        assert "stream_1/playlist.m3u8" not in content

    def test_three_variants_three_stream_entries(self) -> None:
        content = hls._build_master_m3u8(hls._select_variants(1080))
        assert "stream_0/playlist.m3u8" in content
        assert "stream_1/playlist.m3u8" in content
        assert "stream_2/playlist.m3u8" in content

    def test_bandwidth_values_present(self) -> None:
        content = hls._build_master_m3u8(hls._select_variants(1080))
        assert "BANDWIDTH=500000" in content
        assert "BANDWIDTH=1500000" in content
        assert "BANDWIDTH=3000000" in content


# ---------------------------------------------------------------------------
# Geração do comando FFmpeg
# ---------------------------------------------------------------------------


class TestBuildFfmpegCmd:
    def test_ffmpeg_is_first_element(self) -> None:
        variants = hls._select_variants(720)
        cmd = hls._build_ffmpeg_cmd("/video.mkv", Path("/cache"), variants)
        assert cmd[0] == "ffmpeg"

    def test_input_path_after_dash_i(self) -> None:
        variants = hls._select_variants(720)
        cmd = hls._build_ffmpeg_cmd("/video.mkv", Path("/cache"), variants)
        i_idx = cmd.index("-i")
        assert cmd[i_idx + 1] == "/video.mkv"

    def test_var_stream_map_matches_variant_count(self) -> None:
        for n_variants, source_height in [(1, 360), (2, 720), (3, 1080)]:
            variants = hls._select_variants(source_height)
            assert len(variants) == n_variants
            cmd = hls._build_ffmpeg_cmd("/v.mkv", Path("/c"), variants)
            vsm_idx = cmd.index("-var_stream_map") + 1
            # "v:0,a:0 v:1,a:1 ..." → número de pares = número de variantes
            pairs = cmd[vsm_idx].split()
            assert len(pairs) == n_variants

    def test_hls_flags_present(self) -> None:
        cmd = hls._build_ffmpeg_cmd("/v.mkv", Path("/c"), hls._select_variants(1080))
        assert "-hls_time" in cmd
        assert "-hls_list_size" in cmd
        assert "-hls_playlist_type" in cmd
        assert "event" in cmd


# ---------------------------------------------------------------------------
# Regex de progresso do FFmpeg
# ---------------------------------------------------------------------------


class TestFfmpegTimeRegex:
    def test_parses_simple_timestamp(self) -> None:
        line = "frame=  100 fps= 30 q=28.0 Lsize=   4096kB time=00:01:23.45 bitrate= 400.0kbits/s"
        m = hls._FFMPEG_TIME_RE.search(line)
        assert m is not None
        h, mn, s = m.groups()
        assert h == "00"
        assert mn == "01"
        assert s == "23.45"

    def test_parses_zero_time(self) -> None:
        line = "time=00:00:00.00 bitrate=N/A"
        m = hls._FFMPEG_TIME_RE.search(line)
        assert m is not None
        assert m.group(3) == "00.00"

    def test_no_match_on_unrelated_line(self) -> None:
        line = "Input #0, matroska, from '/video.mkv':"
        assert hls._FFMPEG_TIME_RE.search(line) is None

    def test_progress_calculation(self) -> None:
        """Simula o cálculo de progresso como feito em _run_ffmpeg."""
        line = "time=00:01:00.00 bitrate= 500kbits/s"
        m = hls._FFMPEG_TIME_RE.search(line)
        assert m is not None
        h, mn, s = m.groups()
        current = int(h) * 3600 + int(mn) * 60 + float(s)
        duration = 120.0  # 2 minutos
        progress = min(99, int(current / duration * 100))
        assert progress == 50


# ---------------------------------------------------------------------------
# Filesystem: _safe_read
# ---------------------------------------------------------------------------


class TestSafeRead:
    def test_reads_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert hls._safe_read(f) == "hello"

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        assert hls._safe_read(tmp_path / "missing.txt") == ""


# ---------------------------------------------------------------------------
# Filesystem: cleanup_partial_caches
# ---------------------------------------------------------------------------


class TestCleanupPartialCaches:
    def test_removes_partial_cache(self, tmp_path: Path) -> None:
        partial = _make_partial_cache(tmp_path, "1_0")
        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            removed = hls.cleanup_partial_caches()
        assert removed == 1
        assert not partial.exists()

    def test_keeps_complete_cache(self, tmp_path: Path) -> None:
        complete = _make_complete_cache(tmp_path, "2_0")
        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            removed = hls.cleanup_partial_caches()
        assert removed == 0
        assert complete.exists()

    def test_removes_partial_keeps_complete(self, tmp_path: Path) -> None:
        _make_partial_cache(tmp_path, "3_0")
        complete = _make_complete_cache(tmp_path, "4_0")
        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            removed = hls.cleanup_partial_caches()
        assert removed == 1
        assert complete.exists()

    def test_returns_zero_if_cache_dir_missing(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path / "nonexistent")
        with patch("app.web.hls_service.get_settings", return_value=settings):
            assert hls.cleanup_partial_caches() == 0


# ---------------------------------------------------------------------------
# Filesystem: invalidate_cache / invalidate_all_for_item
# ---------------------------------------------------------------------------


class TestInvalidateCache:
    def test_removes_existing_cache_dir(self, tmp_path: Path) -> None:
        _make_complete_cache(tmp_path, "10_0")
        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            result = hls.invalidate_cache(10, 0)
        assert result is True
        assert not (tmp_path / "10_0").exists()

    def test_returns_false_when_nothing_to_remove(self, tmp_path: Path) -> None:
        hls._jobs.pop("99_0", None)
        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            result = hls.invalidate_cache(99, 0)
        assert result is False

    def test_removes_in_memory_job(self, tmp_path: Path) -> None:
        hls._jobs["20_0"] = hls.HLSJob()
        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            hls.invalidate_cache(20, 0)
        assert "20_0" not in hls._jobs


class TestInvalidateAllForItem:
    def test_removes_all_file_indexes_for_library_id(self, tmp_path: Path) -> None:
        _make_complete_cache(tmp_path, "30_0")
        _make_complete_cache(tmp_path, "30_1")
        _make_complete_cache(tmp_path, "30_2")
        _make_complete_cache(tmp_path, "31_0")  # outro item — não deve ser removido

        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            count = hls.invalidate_all_for_item(30)

        assert count == 3
        assert not (tmp_path / "30_0").exists()
        assert not (tmp_path / "30_1").exists()
        assert not (tmp_path / "30_2").exists()
        assert (tmp_path / "31_0").exists()


# ---------------------------------------------------------------------------
# Filesystem: is_playable
# ---------------------------------------------------------------------------


class TestIsPlayable:
    def test_false_when_no_cache(self, tmp_path: Path) -> None:
        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            assert hls.is_playable(50, 0) is False

    def test_true_when_playlist_has_content(self, tmp_path: Path) -> None:
        job_dir = tmp_path / "50_0"
        pl = job_dir / "stream_0" / "playlist.m3u8"
        pl.parent.mkdir(parents=True)
        pl.write_text("#EXTM3U\n#EXTINF:6.0,\nseg00001.ts\n" * 5)  # >100 bytes

        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            assert hls.is_playable(50, 0) is True

    def test_false_when_playlist_too_small(self, tmp_path: Path) -> None:
        job_dir = tmp_path / "51_0"
        pl = job_dir / "stream_0" / "playlist.m3u8"
        pl.parent.mkdir(parents=True)
        pl.write_text("#EXTM3U\n")  # <100 bytes

        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            assert hls.is_playable(51, 0) is False


# ---------------------------------------------------------------------------
# Filesystem: evict_caches
# ---------------------------------------------------------------------------


class TestEvictCaches:
    def test_evicts_old_cache(self, tmp_path: Path) -> None:
        old_dir = _make_complete_cache(tmp_path, "60_0")
        # Simula arquivo com mtime de 40 dias atrás
        old_ts = time.time() - 40 * 86400
        for f in old_dir.rglob("*"):
            if f.is_file():
                import os
                os.utime(f, (old_ts, old_ts))

        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            result = hls.evict_caches(max_age_days=30, max_size_gb=1000.0)

        assert result["evicted"] == 1
        assert not old_dir.exists()

    def test_keeps_recent_cache(self, tmp_path: Path) -> None:
        recent = _make_complete_cache(tmp_path, "61_0")

        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            result = hls.evict_caches(max_age_days=30, max_size_gb=1000.0)

        assert result["evicted"] == 0
        assert recent.exists()

    def test_evicts_oldest_when_over_size_limit(self, tmp_path: Path) -> None:
        # Cria 2 caches; o mais antigo deve ser removido para ficar abaixo do limite
        old_dir = _make_complete_cache(tmp_path, "70_0")
        new_dir = _make_complete_cache(tmp_path, "71_0")

        # Marca o primeiro como mais antigo
        import os
        old_ts = time.time() - 2
        for f in old_dir.rglob("*"):
            if f.is_file():
                os.utime(f, (old_ts, old_ts))

        # max_size_gb=0 garante que vai remover até ficar "abaixo do limite"
        # (o limite é 0 bytes, então remove tudo que for possível)
        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            result = hls.evict_caches(max_age_days=365, max_size_gb=0.0)

        assert result["evicted"] >= 1

    def test_does_not_evict_active_processing_job(self, tmp_path: Path) -> None:
        active_dir = _make_complete_cache(tmp_path, "80_0")
        job = hls.HLSJob()
        job.status = "processing"
        hls._jobs["80_0"] = job

        # Mesmo com max_age_days=0 (tudo é antigo), job ativo não é removido
        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            result = hls.evict_caches(max_age_days=0, max_size_gb=0.0)

        assert active_dir.exists()
        hls._jobs.pop("80_0", None)  # cleanup

    def test_returns_zero_if_cache_dir_missing(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path / "nonexistent")
        with patch("app.web.hls_service.get_settings", return_value=settings):
            result = hls.evict_caches()
        assert result["evicted"] == 0
        assert result["freed_bytes"] == 0

    def test_cleans_orphan_error_jobs_from_memory(self, tmp_path: Path) -> None:
        """Jobs com status=error que nunca criaram cache devem ser removidos do dict."""
        # Job que falhou (sem cache em disco)
        hls._jobs["90_0"] = hls.HLSJob()
        hls._jobs["90_0"].status = "error"
        hls._jobs["90_0"].error = "FFmpeg não encontrado"

        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            result = hls.evict_caches(max_age_days=365, max_size_gb=1000.0)

        assert "90_0" not in hls._jobs
        assert result.get("orphans_cleaned", 0) >= 1

    def test_does_not_clean_orphan_processing_jobs(self, tmp_path: Path) -> None:
        """Jobs em processing não devem ser removidos mesmo sem cache em disco."""
        hls._jobs["91_0"] = hls.HLSJob()
        hls._jobs["91_0"].status = "processing"

        with patch("app.web.hls_service.get_settings", return_value=_make_settings(tmp_path)):
            hls.evict_caches(max_age_days=365, max_size_gb=1000.0)

        assert "91_0" in hls._jobs
        hls._jobs.pop("91_0", None)  # cleanup


# ---------------------------------------------------------------------------
# Semáforo de concorrência FFmpeg
# ---------------------------------------------------------------------------


class TestFfmpegSemaphore:
    def test_get_active_job_count_zero_initially(self) -> None:
        """Sem jobs em andamento, contagem deve ser 0."""
        # Limpa qualquer estado de testes anteriores
        processing_keys = [k for k, j in hls._jobs.items() if j.status == "processing"]
        for k in processing_keys:
            hls._jobs.pop(k, None)

        assert hls.get_active_job_count() == 0

    def test_get_active_job_count_counts_only_processing(self) -> None:
        """Apenas jobs com status='processing' são contados como ativos."""
        hls._jobs["100_0"] = hls.HLSJob()  # status=processing por padrão
        hls._jobs["100_1"] = hls.HLSJob()
        hls._jobs["100_1"].status = "ready"
        hls._jobs["100_2"] = hls.HLSJob()
        hls._jobs["100_2"].status = "error"

        count = hls.get_active_job_count()
        assert count >= 1  # pelo menos 100_0

        # Cleanup
        for k in ["100_0", "100_1", "100_2"]:
            hls._jobs.pop(k, None)
