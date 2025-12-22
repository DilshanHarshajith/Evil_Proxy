#!/usr/bin/env python3
"""
Utility functions for the mitmproxy script.
"""

from datetime import datetime
from typing import Optional
from mitmproxy import http, ctx
from config import DEBUG_LOG


def normalize_ip(ip: str) -> str:
    """
    Normalize IP address by removing special characters.
    
    Args:
        ip: Raw IP address string
        
    Returns:
        Normalized IP address string
    """
    if not ip:
        return "unknown"
    return ip.replace(":", "_").replace("[", "").replace("]", "")


def get_client_ip(flow: http.HTTPFlow) -> str:
    """
    Extract client IP from flow with fallback chain.
    
    Priority:
    1. X-Real-IP header
    2. X-Forwarded-For header (first IP)
    3. Client connection peername
    
    Args:
        flow: HTTP flow object
        
    Returns:
        Normalized client IP address
    """
    if not flow or not flow.client_conn:
        return "unknown"
    
    # Try to get IP from headers first (if request exists)
    if flow.request:
        # Check X-Real-IP header
        real_ip = flow.request.headers.get("X-Real-IP")
        if real_ip:
            return normalize_ip(real_ip)
        
        # Check X-Forwarded-For header
        forwarded_for = flow.request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
            if ip:
                return normalize_ip(ip)
    
    # Fall back to client connection IP
    if flow.client_conn.peername:
        return normalize_ip(flow.client_conn.peername[0])
    
    return "unknown"


def debug_log(message: str) -> None:
    """
    Write debug message to log file and mitmproxy log.
    
    Args:
        message: Message to log
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(log_message + "\n")
    except Exception as e:
        # Silently fail if we can't write to log file
        pass
    
    # Only log to ctx if it's available (when running in mitmproxy)
    try:
        if hasattr(ctx, 'log') and ctx.log:
            ctx.log.info(f"[DEBUG] {message}")
    except (AttributeError, NameError):
        # ctx not available during import
        pass


def safe_decode(content: Optional[bytes], encoding: str = "utf-8") -> str:
    """
    Safely decode bytes to string with base64 fallback.
    
    Args:
        content: Bytes to decode
        encoding: Character encoding to use
        
    Returns:
        Decoded string or base64-encoded string if decode fails
    """
    import base64
    
    if not content:
        return ""
    
    try:
        return content.decode(encoding)
    except (UnicodeDecodeError, AttributeError):
        return base64.b64encode(content).decode("ascii")
