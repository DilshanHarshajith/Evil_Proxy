#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: $0 <client_ip>"
    echo "Available client IPs:"
    find ./captures -type d -name "*.*.*.*" -o -name "*:*" | xargs -I {} basename {} | sort -u
    exit 1
fi

CLIENT_IP="$1"
TODAY=$(date +%Y-%m-%d)
CAPTURE_DIR="./captures/$TODAY/$CLIENT_IP"

echo "Recent traffic for $CLIENT_IP on $TODAY:"
if [ -d "$CAPTURE_DIR" ]; then
    ls -lt "$CAPTURE_DIR"
else
    echo "No traffic found for $CLIENT_IP today"
fi
