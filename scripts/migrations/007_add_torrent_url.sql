-- 007: Adiciona coluna torrent_url na tabela downloads
-- Permite persistir a URL do .torrent separadamente do magnet link,
-- habilitando fallback (torrent_url HTTP -> magnet DHT) no download worker.

ALTER TABLE downloads ADD COLUMN IF NOT EXISTS torrent_url TEXT;
