#!/bin/bash
echo "=== Service Status ==="
docker compose ps
echo ""
echo "=== Recent Logs ==="
docker compose logs --tail=20 mitmproxy
