#!/bin/sh
set -e

SSL_DIR="/etc/nginx/ssl"
CA_KEY="$SSL_DIR/ca.key"
CA_CERT="$SSL_DIR/ca.crt"
SRV_KEY="$SSL_DIR/server.key"
SRV_CERT="$SSL_DIR/server.crt"

if [ -f "$SRV_CERT" ] && [ -f "$SRV_KEY" ] && [ -f "$CA_CERT" ]; then
  echo "[certs] Certificados já existem, pulando geração."
  exit 0
fi

echo "[certs] Gerando CA + certificado de servidor auto-assinado..."
mkdir -p "$SSL_DIR"

HOSTNAME_VAL=$(hostname 2>/dev/null || echo "atum")

openssl genrsa -out "$CA_KEY" 4096 2>/dev/null

openssl req -new -x509 -days 3650 -key "$CA_KEY" -out "$CA_CERT" \
  -subj "/C=BR/O=Atum Media Center/CN=Atum Root CA" 2>/dev/null

openssl genrsa -out "$SRV_KEY" 2048 2>/dev/null

cat > "$SSL_DIR/server.cnf" <<CNFEOF
[req]
distinguished_name = req_dn
req_extensions     = v3_req
prompt             = no

[req_dn]
C  = BR
O  = Atum Media Center
CN = $HOSTNAME_VAL

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.local
DNS.3 = $HOSTNAME_VAL
DNS.4 = frontend
IP.1  = 127.0.0.1
IP.2  = 0.0.0.0
CNFEOF

openssl req -new -key "$SRV_KEY" -out "$SSL_DIR/server.csr" \
  -config "$SSL_DIR/server.cnf" 2>/dev/null

openssl x509 -req -days 3650 \
  -in "$SSL_DIR/server.csr" \
  -CA "$CA_CERT" -CAkey "$CA_KEY" -CAcreateserial \
  -extfile "$SSL_DIR/server.cnf" -extensions v3_req \
  -out "$SRV_CERT" 2>/dev/null

rm -f "$SSL_DIR/server.csr" "$SSL_DIR/server.cnf" "$SSL_DIR/ca.srl"

echo "[certs] Certificados gerados em $SSL_DIR"
echo "[certs] Importe $CA_CERT nos dispositivos para confiar no HTTPS."
