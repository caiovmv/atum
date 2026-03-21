#!/bin/sh
set -e

# Basic auth entre frontend e API: nginx adiciona header ao proxy
# Evita % no printf usando variável separada (%% em alguns shells)
if [ -n "$BASIC_AUTH_USER" ] && [ -n "$BASIC_AUTH_PASS" ]; then
    AUTH_B64=$(printf '%s' "$BASIC_AUTH_USER:$BASIC_AUTH_PASS" | base64 -w0 2>/dev/null || printf '%s' "$BASIC_AUTH_USER:$BASIC_AUTH_PASS" | base64)
    printf 'proxy_set_header Authorization "Basic %s";\n' "$AUTH_B64" > /etc/nginx/conf.d/api-auth-headers.conf
else
    : > /etc/nginx/conf.d/api-auth-headers.conf
fi

exec nginx -g "daemon off;"
