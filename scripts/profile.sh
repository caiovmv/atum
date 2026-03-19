#!/bin/bash
# Gera flame graph de um serviço via py-spy.
# Uso: ./scripts/profile.sh <service> [duration_seconds]
# Ex.: ./scripts/profile.sh api 60
#      ./scripts/profile.sh feed-daemon 120
# Serviços: api, runner, feed-daemon, sync-daemon, indexers-daemon, enrichment-daemon

set -e

SERVICE=${1:?Usage: $0 <service> [duration_seconds]}
DURATION=${2:-60}

CONTAINER=$(docker compose ps -q "$SERVICE" 2>/dev/null)
if [ -z "$CONTAINER" ]; then
  echo "Erro: serviço '$SERVICE' não está rodando. Use: docker compose up -d $SERVICE"
  exit 1
fi

PID=$(docker exec "$CONTAINER" sh -c 'pgrep -f "uvicorn|dl-torrent" 2>/dev/null | head -1' 2>/dev/null || true)
if [ -z "$PID" ] || ! [[ "$PID" =~ ^[0-9]+$ ]]; then
  PID=1
fi

mkdir -p profiles
OUTPUT_FILE="${SERVICE}_$(date +%Y%m%d_%H%M%S).svg"
OUTPUT_CONTAINER="/profiles/${OUTPUT_FILE}"

echo "Profiling $SERVICE (PID $PID) por ${DURATION}s..."
docker exec --user root "$CONTAINER" sh -c "mkdir -p /profiles && py-spy record -o /profiles/${OUTPUT_FILE} --pid ${PID} --duration ${DURATION}"

if [ ! -f "profiles/${OUTPUT_FILE}" ]; then
  OUTPUT_TMP="/tmp/${OUTPUT_FILE}"
  docker exec --user root "$CONTAINER" py-spy record -o "$OUTPUT_TMP" --pid "$PID" --duration "$DURATION"
  docker cp "${CONTAINER}:${OUTPUT_TMP}" "profiles/${OUTPUT_FILE}"
fi

echo "Flame graph salvo em ./profiles/${OUTPUT_FILE}"
