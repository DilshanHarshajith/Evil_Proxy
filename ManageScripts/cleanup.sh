#!/bin/bash
echo "Cleaning up old capture files (>30 days)..."
find ./captures -name "*.har" -mtime +30 -delete
find ./captures -type d -empty -delete
du -sh ./captures
