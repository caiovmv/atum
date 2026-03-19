#!/bin/sh
# Garante que o volume de capas seja gravável pelo usuário atum (roda como root)
if [ -d /app/covers ]; then
  chown -R atum:atum /app/covers 2>/dev/null || true
fi
exec runuser -u atum -- "$@"
