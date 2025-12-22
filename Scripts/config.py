#!/usr/bin/env python3
"""
Configuration constants for the mitmproxy script.
"""

from pathlib import Path
from datetime import timedelta
import re

# === Directory Paths ===
DATA_DIR = Path(__file__).resolve().parent.parent/"Data"
CAPTURE_DIR = DATA_DIR / "HAR_Out"
EXTRACT_DIR = DATA_DIR / "Tokens"
BLOCKLIST_FILE = DATA_DIR / "Other" / "blocked_ips.json"
DEBUG_LOG = DATA_DIR / "Other" / "debug.log"

# === HTTP Status Codes ===
HTTP_OK = 200
HTTP_MULTIPLE_CHOICES = 300
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_PROXY_AUTH_REQUIRED = 407

# === Blocking Configuration ===
BLOCK_RESET_INTERVAL = timedelta(hours=1)  # Auto-unblock after 1 hour
BLOCK_THRESHOLD = 10  # Block after 10 attempts
CLEANUP_INTERVAL = 60  # Check every 1 minute for more responsive unblocking
CONNECTION_TIMEOUT = 30  # Seconds to track connection attempts

# === Regular Expressions ===
JWT_REGEX = re.compile(r'eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+')

# === Timing Configuration ===
SAVE_INTERVAL = 60  # Save flows every 60 seconds
STATUS_LOG_INTERVAL = 300  # Log status every 5 minutes

def ensure_directories():
    """Create all required directories. Handles permission errors gracefully."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
        BLOCKLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Will be created when mitmproxy runs with proper permissions
        pass
    except Exception:
        # Log but don't fail on other errors
        pass
