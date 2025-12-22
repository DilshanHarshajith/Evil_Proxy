#!/usr/bin/env python3
"""
Mitmproxy addon for traffic capture, token extraction, and IP blocking.

This script provides:
- HAR file generation for traffic analysis
- Token and authentication data extraction
- IP-based rate limiting and blocking
- Automatic unblocking after timeout
"""

from datetime import datetime
from mitmproxy import http, ctx

# Import modular components
from config import (
    ensure_directories, BLOCK_THRESHOLD, BLOCK_RESET_INTERVAL,
    CLEANUP_INTERVAL, CONNECTION_TIMEOUT, DEBUG_LOG,
    HTTP_OK, HTTP_MULTIPLE_CHOICES, HTTP_UNAUTHORIZED,
    HTTP_FORBIDDEN, HTTP_PROXY_AUTH_REQUIRED
)
from utils import get_client_ip, debug_log, normalize_ip
from ip_blocker import IPBlocker
from har_capture import TrafficCapture
from token_extractor import TokenExtractor


# Ensure all directories exist
ensure_directories()

# Initialize global instances
ip_blocker = IPBlocker()
traffic_capture = TrafficCapture()
token_extractor = TokenExtractor()


class MitmProxyAddon:
    """Main mitmproxy addon that coordinates all functionality."""
    
    def __init__(self):
        self.ip_blocker = ip_blocker
        self.traffic_capture = traffic_capture
        self.token_extractor = token_extractor
        debug_log("MitmProxyAddon initialized")

    def tcp_start(self, flow: http.HTTPFlow) -> None:
        """
        Handle TCP connection start - block connections from blocked IPs immediately.
        
        Args:
            flow: HTTP flow object
        """
        try:
            if flow.client_conn and flow.client_conn.peername:
                client_ip = normalize_ip(flow.client_conn.peername[0])
                
                # Check if IP is blocked FIRST
                if self.ip_blocker.is_ip_blocked(client_ip):
                    debug_log(f"KILLING TCP connection from blocked IP: {client_ip}")
                    flow.kill()
                    return
                
                debug_log(f"TCP connection from {client_ip}")
                
                # Track connection attempt for rate limiting
                should_block = self.ip_blocker.track_connection_attempt(client_ip)
                
                if should_block:
                    debug_log(f"KILLING TCP connection from {client_ip} (rate limited)")
                    flow.kill()
                    return
                    
        except Exception as e:
            debug_log(f"Error in tcp_start: {e}")

    def tcp_end(self, flow: http.HTTPFlow) -> None:
        """
        Handle TCP connection end.
        
        Args:
            flow: HTTP flow object
        """
        try:
            if flow.client_conn and flow.client_conn.peername:
                client_ip = normalize_ip(flow.client_conn.peername[0])
                debug_log(f"TCP disconnect from {client_ip}")
                
        except Exception as e:
            debug_log(f"Error in tcp_end: {e}")

    def http_connect(self, flow: http.HTTPFlow) -> None:
        """
        Handle HTTP CONNECT requests - block at tunnel establishment.
        
        Args:
            flow: HTTP flow object
        """
        try:
            client_ip = get_client_ip(flow)
            
            if self.ip_blocker.is_ip_blocked(client_ip):
                debug_log(f"KILLING HTTP CONNECT from blocked IP {client_ip}")
                flow.kill()
                return
                
        except Exception as e:
            debug_log(f"Error in http_connect: {e}")

    def requestheaders(self, flow: http.HTTPFlow) -> None:
        """
        Handle request headers - earliest point to block HTTP flows.
        
        Args:
            flow: HTTP flow object
        """
        try:
            client_ip = get_client_ip(flow)
            
            # Check if IP is blocked at the earliest possible moment
            if self.ip_blocker.is_ip_blocked(client_ip):
                debug_log(f"KILLING flow at headers stage from blocked IP {client_ip}")
                flow.kill()
                return
                
        except Exception as e:
            debug_log(f"Error in requestheaders: {e}")

    def request(self, flow: http.HTTPFlow) -> None:
        """
        Handle incoming requests - extract tokens and perform secondary blocking check.
        
        Args:
            flow: HTTP flow object
        """
        try:
            # Get client IP
            client_ip = get_client_ip(flow)
            
            # Double-check if IP is blocked (should be caught earlier)
            if self.ip_blocker.is_ip_blocked(client_ip):
                debug_log(f"KILLING request from blocked IP {client_ip} (fallback)")
                flow.kill()
                return
            
            # Extract tokens for allowed IPs
            self.token_extractor.extract_from_request(flow)
            
            debug_log(f"Processing request from {client_ip} to {flow.request.pretty_url}")
            
        except Exception as e:
            debug_log(f"Error in request handler: {e}")

    def response(self, flow: http.HTTPFlow) -> None:
        """
        Handle responses - process only flows from non-blocked IPs.
        
        Args:
            flow: HTTP flow object
        """
        try:
            client_ip = get_client_ip(flow)
            
            # Skip ALL processing for blocked IPs
            if self.ip_blocker.is_ip_blocked(client_ip):
                debug_log(f"Skipping response processing for blocked IP {client_ip}")
                return
            
            if not flow.response:
                debug_log(f"No response for {client_ip}")
                return
            
            status_code = flow.response.status_code
            debug_log(f"Response {status_code} for {client_ip}")
            
            # Handle authentication failures
            if status_code == HTTP_PROXY_AUTH_REQUIRED:
                debug_log(f"407 Proxy Authentication Required from {client_ip}")
                was_blocked = self.ip_blocker.increment_failure_count(client_ip)
                if was_blocked:
                    try:
                        if hasattr(ctx, 'log') and ctx.log:
                            ctx.log.warn(f"[BLOCKED] {client_ip} after repeated 407 errors")
                    except (AttributeError, NameError):
                        pass
                    return
            
            # Handle other authentication/authorization failures
            elif status_code in [HTTP_UNAUTHORIZED, HTTP_FORBIDDEN]:
                debug_log(f"{status_code} Auth failure from {client_ip}")
                was_blocked = self.ip_blocker.increment_failure_count(client_ip)
                if was_blocked:
                    try:
                        if hasattr(ctx, 'log') and ctx.log:
                            ctx.log.warn(f"[BLOCKED] {client_ip} after repeated auth failures")
                    except (AttributeError, NameError):
                        pass
                    return
            
            # Reset failure count on successful responses
            elif HTTP_OK <= status_code < HTTP_MULTIPLE_CHOICES:
                self.ip_blocker.reset_failure_count(client_ip)
            
            # Only create HAR entry for responses from non-blocked IPs
            if not self.ip_blocker.is_ip_blocked(client_ip):
                har_entry = self.traffic_capture.create_har_entry(flow)
                self.traffic_capture.add_flow(client_ip, har_entry)
                
        except Exception as e:
            debug_log(f"Error in response handler: {e}")

    def error(self, flow: http.HTTPFlow) -> None:
        """
        Handle flow errors - only process flows from non-blocked IPs.
        
        Args:
            flow: HTTP flow object
        """
        try:
            client_ip = get_client_ip(flow)
            
            # Skip processing for blocked IPs
            if self.ip_blocker.is_ip_blocked(client_ip):
                debug_log(f"Skipping error processing for blocked IP {client_ip}")
                return
            
            error_msg = str(flow.error) if flow.error else "Unknown error"
            debug_log(f"Flow error for {client_ip}: {error_msg}")
            
        except Exception as e:
            debug_log(f"Error in error handler: {e}")


# === Management Commands ===

def block_ip(ip: str) -> str:
    """
    Manually block an IP.
    
    Args:
        ip: IP address to block
        
    Returns:
        Status message
    """
    ip_blocker.block_ip(ip, "Manual block")
    return f"IP {ip} has been blocked"


def unblock_ip(ip: str) -> str:
    """
    Manually unblock an IP.
    
    Args:
        ip: IP address to unblock
        
    Returns:
        Status message
    """
    success = ip_blocker.unblock_ip(ip)
    return f"IP {ip} {'unblocked' if success else 'was not blocked'}"


def list_blocked_ips() -> str:
    """
    List all blocked IPs with timestamps.
    
    Returns:
        Formatted string with blocking status
    """
    status = ip_blocker.get_status()
    blocked = status["blocked_ips"]
    pending = status["pending_blocks"]
    connections = status["connection_attempts"]
    
    result = []
    result.append(f"=== BLOCKED IPS ({len(blocked)}) ===")
    current_time = datetime.now()
    for ip, block_time_str in blocked.items():
        try:
            block_time = datetime.fromisoformat(block_time_str)
            time_remaining = BLOCK_RESET_INTERVAL - (current_time - block_time)
            if time_remaining.total_seconds() > 0:
                result.append(
                    f"{ip} - blocked at {block_time_str} "
                    f"(unblocks in {time_remaining.total_seconds():.0f}s)"
                )
            else:
                result.append(f"{ip} - blocked at {block_time_str} (should auto-unblock soon)")
        except (ValueError, TypeError):
            result.append(f"{ip} - blocked at {block_time_str} (invalid timestamp)")
    
    result.append(f"\n=== PENDING BLOCKS ({len(pending)}) ===")
    for ip, count in pending.items():
        result.append(f"{ip} - {count}/{status['block_threshold']} failures")
    
    result.append(f"\n=== RECENT CONNECTIONS ({len(connections)}) ===")
    for ip, count in connections.items():
        result.append(f"{ip} - {count} recent attempts")
    
    return "\n".join(result)


def get_debug_info() -> dict:
    """
    Get debug information.
    
    Returns:
        Dictionary with debug information
    """
    status = ip_blocker.get_status()
    return {
        "blocked_count": len(status["blocked_ips"]),
        "pending_count": len(status["pending_blocks"]),
        "connection_count": len(status["connection_attempts"]),
        "block_threshold": status["block_threshold"],
        "auto_unblock_hours": BLOCK_RESET_INTERVAL.total_seconds() / 3600,
        "cleanup_interval_seconds": CLEANUP_INTERVAL,
        "debug_log_path": str(DEBUG_LOG)
    }


# Initialize debug log
debug_log("=== MITMPROXY SCRIPT STARTED ===")
debug_log(f"Block threshold: {BLOCK_THRESHOLD}")
debug_log(f"Auto-unblock interval: {BLOCK_RESET_INTERVAL}")
debug_log(f"Cleanup interval: {CLEANUP_INTERVAL}s")
debug_log(f"Connection timeout: {CONNECTION_TIMEOUT}s")
debug_log(f"Debug log: {DEBUG_LOG}")

# Register the addon
addons = [MitmProxyAddon()]

# Log startup information
try:
    if hasattr(ctx, 'log') and ctx.log:
        ctx.log.info("=== Enhanced IP Blocking System Ready ===")
        ctx.log.info(f"Block threshold: {BLOCK_THRESHOLD} failures")
        ctx.log.info(f"Auto-unblock after: {BLOCK_RESET_INTERVAL}")
        ctx.log.info(f"Cleanup runs every: {CLEANUP_INTERVAL} seconds")
        ctx.log.info(f"Debug log: {DEBUG_LOG}")
except (AttributeError, NameError):
    pass