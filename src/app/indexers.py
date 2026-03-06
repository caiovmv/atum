"""Registro central de indexadores. Fonte única para API, daemon e status."""

from __future__ import annotations

# Indexadores disponíveis: 1337x, tpb, yts, eztv, nyaa, limetorrents, iptorrents
ALL_INDEXERS = frozenset({
    "1337x", "tpb", "yts", "eztv", "nyaa", "limetorrents", "iptorrents",
})
# Por padrão busca em todos os indexadores públicos (iptorrents é privado e não implementado)
DEFAULT_INDEXERS = ["1337x", "tpb", "yts", "eztv", "nyaa", "limetorrents"]

# Mapeamento indexer -> atributo de Settings (base_url)
INDEXER_BASE_URL_ATTR: dict[str, str] = {
    "1337x": "x1337_base_url",
    "tpb": "tpb_base_url",
    "yts": "yts_base_url",
    "eztv": "eztv_base_url",
    "nyaa": "nyaa_base_url",
    "limetorrents": "limetorrents_base_url",
    "iptorrents": "iptorrents_base_url",
}
