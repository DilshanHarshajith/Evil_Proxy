#!/bin/bash

# Default values
MITM_MODE=${MITM_MODE:-regular}
SHOWHOST=${SHOWHOST:-true}
BLOCK_GLOBAL=${BLOCK_GLOBAL:-false}
BLOCK_PRIVATE=${BLOCK_PRIVATE:-false}
WEBPASSWORD=${WEBPASSWORD:-1234}
WEB_HOST=${WEB_HOST:-0.0.0.0}
WEB_PORT=${WEB_PORT:-8081}
VIEW_FILTER=${VIEW_FILTER:-'!(~c 407)'}
CONFDIR=${CONFDIR:-/home/mitmproxy/Data/Certs}

# Ensure confdir exists
mkdir -p "$CONFDIR"

# Build the command using an array to handle quoting correctly
CMD=(
    mitmweb
    --mode "$MITM_MODE"
    --set confdir="$CONFDIR"
    --set block_global="$BLOCK_GLOBAL"
    --set block_private="$BLOCK_PRIVATE"
    --set web_password="$WEBPASSWORD"
    --web-host "$WEB_HOST"
    --web-port "$WEB_PORT"
    --showhost
    --no-web-open-browser
    --scripts /home/mitmproxy/scripts/script.py
    --set view_filter="$VIEW_FILTER"
)

# Add proxy auth if provided
if [ -n "$PROXYAUTH" ]; then
    CMD+=("--proxyauth=$PROXYAUTH")
fi

# Execute the command
exec "${CMD[@]}"
