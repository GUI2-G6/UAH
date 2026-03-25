#!/bin/sh
set -eu

DOMAIN="${DEV_DOMAIN:-_}"
TLS_ENABLED="${DEV_TLS_ENABLED:-false}"
TLS_CERT_PATH="${DEV_TLS_CERT_PATH:-/etc/nginx/certs/tls.crt}"
TLS_KEY_PATH="${DEV_TLS_KEY_PATH:-/etc/nginx/certs/tls.key}"

select_http() {
  sed "s|__DOMAIN__|${DOMAIN}|g" \
    /etc/nginx/templates/nginx.http.conf > /etc/nginx/conf.d/default.conf
  echo "[nginx] Using HTTP config (TLS disabled or cert files missing)."
}

select_https() {
  sed -e "s|__DOMAIN__|${DOMAIN}|g" \
      -e "s|__TLS_CERT_PATH__|${TLS_CERT_PATH}|g" \
      -e "s|__TLS_KEY_PATH__|${TLS_KEY_PATH}|g" \
    /etc/nginx/templates/nginx.https.conf > /etc/nginx/conf.d/default.conf
  echo "[nginx] Using HTTPS config for ${DOMAIN}."
}

if [ "${TLS_ENABLED}" = "true" ] && [ -f "${TLS_CERT_PATH}" ] && [ -f "${TLS_KEY_PATH}" ]; then
  select_https
else
  select_http
fi
