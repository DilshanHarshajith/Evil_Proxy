#!/usr/bin/env python3
"""
IP blocking and rate limiting functionality.
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from mitmproxy import ctx

from config import (
    BLOCKLIST_FILE, BLOCK_RESET_INTERVAL, BLOCK_THRESHOLD,
    CLEANUP_INTERVAL, CONNECTION_TIMEOUT, STATUS_LOG_INTERVAL
)
from utils import debug_log


class IPBlocker:
    """Manages IP blocking, rate limiting, and auto-unblocking."""
    
    def __init__(self):
        self.blocked_ips: Dict[str, str] = {}  # IP -> block_time mapping
        self.to_block: Dict[str, int] = defaultdict(int)  # IP -> failure count
        self.connection_attempts: Dict[str, List[float]] = defaultdict(list)  # IP -> [timestamps]
        self.block_threshold = BLOCK_THRESHOLD
        self.lock = threading.Lock()
        self._last_save_state: Optional[str] = None
        self._last_file_mtime: float = 0  # Track file modification time
        
        self._load_blocked_ips()
        self._start_background_threads()
        
        debug_log(f"IPBlocker initialized with threshold: {self.block_threshold}")

    def _start_background_threads(self) -> None:
        """Start all background threads."""
        threading.Thread(target=self._periodic_cleanup, daemon=True).start()
        threading.Thread(target=self._periodic_status, daemon=True).start()

    def _periodic_status(self) -> None:
        """Periodically log status for debugging."""
        while True:
            time.sleep(STATUS_LOG_INTERVAL)
            with self.lock:
                blocked_count = len(self.blocked_ips)
                pending_count = len(self.to_block)
                connection_count = len(self.connection_attempts)
                debug_log(
                    f"Status: {blocked_count} blocked, {pending_count} pending, "
                    f"{connection_count} tracked connections"
                )
                
                if self.blocked_ips:
                    current_time = datetime.now()
                    for ip, block_time_str in self.blocked_ips.items():
                        try:
                            block_time = datetime.fromisoformat(block_time_str)
                            time_remaining = BLOCK_RESET_INTERVAL - (current_time - block_time)
                            if time_remaining.total_seconds() > 0:
                                debug_log(
                                    f"  Blocked: {ip} - {time_remaining.total_seconds():.0f}s remaining"
                                )
                        except (ValueError, TypeError):
                            debug_log(f"  Blocked: {ip} - invalid timestamp")

    def _load_blocked_ips(self) -> None:
        """Load blocked IPs from file."""
        if BLOCKLIST_FILE.exists():
            try:
                # Track file modification time
                self._last_file_mtime = BLOCKLIST_FILE.stat().st_mtime
                
                with open(BLOCKLIST_FILE) as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.blocked_ips = data
                    else:
                        # Old format - convert to new format
                        self.blocked_ips = {}
                        for ip in data:
                            self.blocked_ips[ip] = datetime.now().isoformat()
                debug_log(f"Loaded {len(self.blocked_ips)} blocked IPs from file")
            except Exception as e:
                debug_log(f"Failed to load blocked IPs: {e}")
                self.blocked_ips = {}

    def _save_blocked_ips(self) -> None:
        """Save blocked IPs to file with deduplication."""
        # Only save if state has changed
        current_state = json.dumps(self.blocked_ips, sort_keys=True)
        if current_state == self._last_save_state:
            return
        
        try:
            # Atomic write using temporary file
            temp_file = BLOCKLIST_FILE.with_suffix('.tmp')
            with open(temp_file, "w") as f:
                json.dump(self.blocked_ips, f, indent=2)
            temp_file.replace(BLOCKLIST_FILE)
            
            # Update modification time tracking to avoid reloading our own changes
            if BLOCKLIST_FILE.exists():
                self._last_file_mtime = BLOCKLIST_FILE.stat().st_mtime
            
            self._last_save_state = current_state
            debug_log(f"Saved {len(self.blocked_ips)} blocked IPs to file")
        except Exception as e:
            debug_log(f"Failed to save blocked IPs: {e}")

    def _check_external_changes(self) -> None:
        """Check if blocklist file was modified externally and reload if needed."""
        if not BLOCKLIST_FILE.exists():
            # File was deleted externally, clear blocklist
            if self.blocked_ips:
                debug_log("Blocklist file deleted externally, clearing all blocks")
                self.blocked_ips = {}
                self._last_file_mtime = 0
            return
        
        try:
            current_mtime = BLOCKLIST_FILE.stat().st_mtime
            if current_mtime > self._last_file_mtime:
                debug_log(f"Blocklist file modified externally (mtime: {current_mtime} > {self._last_file_mtime}), reloading...")
                old_count = len(self.blocked_ips)
                self._load_blocked_ips()
                new_count = len(self.blocked_ips)
                
                if old_count != new_count:
                    debug_log(f"Reloaded blocklist: {old_count} -> {new_count} blocked IPs")
                    try:
                        if hasattr(ctx, 'log') and ctx.log:
                            ctx.log.info(f"[SYNC] Blocklist reloaded from file: {old_count} -> {new_count} IPs")
                    except (AttributeError, NameError):
                        pass
        except Exception as e:
            debug_log(f"Error checking for external changes: {e}")

    def _periodic_cleanup(self) -> None:
        """Periodically unblock IPs and clean up old connection attempts."""
        debug_log("Starting periodic cleanup thread")
        while True:
            time.sleep(CLEANUP_INTERVAL)
            try:
                self._check_external_changes()  # Check for external modifications first
                self._cleanup_expired_blocks()
                self._cleanup_old_connections()
            except Exception as e:
                debug_log(f"Error in periodic cleanup: {e}")

    def _cleanup_expired_blocks(self) -> None:
        """Remove expired IP blocks."""
        current_time = datetime.now()
        to_unblock = []
        
        with self.lock:
            for ip, block_time_str in self.blocked_ips.items():
                try:
                    block_time = datetime.fromisoformat(block_time_str)
                    if current_time - block_time > BLOCK_RESET_INTERVAL:
                        to_unblock.append(ip)
                except (ValueError, TypeError):
                    debug_log(f"Invalid timestamp for {ip}: {block_time_str}")
                    to_unblock.append(ip)
            
            if to_unblock:
                for ip in to_unblock:
                    del self.blocked_ips[ip]
                    self.to_block.pop(ip, None)
                    self.connection_attempts.pop(ip, None)
                    debug_log(f"AUTO-UNBLOCKED {ip} after {BLOCK_RESET_INTERVAL}")
                
                self._save_blocked_ips()
                try:
                    if hasattr(ctx, 'log') and ctx.log:
                        ctx.log.info(f"Auto-unblocked {len(to_unblock)} IPs after timeout")
                except (AttributeError, NameError):
                    pass

    def _cleanup_old_connections(self) -> None:
        """Clean up old connection attempt records."""
        current_time = time.time()
        cutoff_time = current_time - CONNECTION_TIMEOUT
        
        with self.lock:
            for ip in list(self.connection_attempts.keys()):
                # Remove old attempts
                self.connection_attempts[ip] = [
                    t for t in self.connection_attempts[ip] 
                    if t > cutoff_time
                ]
                # Remove IPs with no recent attempts
                if not self.connection_attempts[ip]:
                    del self.connection_attempts[ip]

    def track_connection_attempt(self, ip: str) -> bool:
        """
        Track connection attempts and block if too many.
        
        Args:
            ip: Client IP address
            
        Returns:
            True if IP should be blocked, False otherwise
        """
        current_time = time.time()
        
        with self.lock:
            if ip in self.blocked_ips:
                debug_log(f"Connection attempt from already blocked IP: {ip}")
                return True
            
            # Add current attempt
            self.connection_attempts[ip].append(current_time)
            
            # Remove old attempts
            cutoff_time = current_time - CONNECTION_TIMEOUT
            self.connection_attempts[ip] = [
                t for t in self.connection_attempts[ip] 
                if t > cutoff_time
            ]
            
            attempt_count = len(self.connection_attempts[ip])
            debug_log(f"Connection attempt from {ip}: {attempt_count} attempts in {CONNECTION_TIMEOUT}s")
            
            # Block if too many attempts
            if attempt_count >= self.block_threshold:
                self.blocked_ips[ip] = datetime.now().isoformat()
                self.to_block.pop(ip, None)
                del self.connection_attempts[ip]
                self._save_blocked_ips()
                debug_log(f"BLOCKED {ip} after {attempt_count} connection attempts")
                try:
                    if hasattr(ctx, 'log') and ctx.log:
                        ctx.log.warn(f"[BLOCKED] {ip} blocked after {attempt_count} rapid connection attempts")
                except (AttributeError, NameError):
                    pass
                return True
            
            return False

    def is_ip_blocked(self, ip: str) -> bool:
        """
        Check if an IP is currently blocked.
        
        Args:
            ip: Client IP address
            
        Returns:
            True if blocked, False otherwise
        """
        with self.lock:
            if ip in self.blocked_ips:
                # Double-check if block has expired
                try:
                    block_time = datetime.fromisoformat(self.blocked_ips[ip])
                    if datetime.now() - block_time > BLOCK_RESET_INTERVAL:
                        # Block has expired, remove it
                        del self.blocked_ips[ip]
                        self.to_block.pop(ip, None)
                        self.connection_attempts.pop(ip, None)
                        self._save_blocked_ips()
                        debug_log(f"AUTO-UNBLOCKED {ip} during check (expired)")
                        return False
                    return True
                except (ValueError, TypeError):
                    # Invalid timestamp, unblock
                    del self.blocked_ips[ip]
                    return False
            return False

    def block_ip(self, ip: str, reason: str = "Manual") -> None:
        """
        Block an IP address.
        
        Args:
            ip: Client IP address
            reason: Reason for blocking
        """
        with self.lock:
            self.blocked_ips[ip] = datetime.now().isoformat()
            self.to_block.pop(ip, None)
            self.connection_attempts.pop(ip, None)
            self._save_blocked_ips()
            debug_log(f"BLOCKED {ip} - Reason: {reason}")
            try:
                if hasattr(ctx, 'log') and ctx.log:
                    ctx.log.warn(f"[BLOCKED] {ip} - {reason}")
            except (AttributeError, NameError):
                pass

    def unblock_ip(self, ip: str) -> bool:
        """
        Unblock an IP address.
        
        Args:
            ip: Client IP address
            
        Returns:
            True if IP was blocked and is now unblocked, False otherwise
        """
        with self.lock:
            if ip in self.blocked_ips:
                del self.blocked_ips[ip]
                self.to_block.pop(ip, None)
                self.connection_attempts.pop(ip, None)
                self._save_blocked_ips()
                debug_log(f"MANUALLY UNBLOCKED {ip}")
                try:
                    if hasattr(ctx, 'log') and ctx.log:
                        ctx.log.info(f"[UNBLOCKED] {ip} manually unblocked")
                except (AttributeError, NameError):
                    pass
                return True
            else:
                debug_log(f"IP {ip} not found in blocklist")
                return False

    def increment_failure_count(self, ip: str) -> bool:
        """
        Increment failure count for an IP and block if threshold reached.
        
        Args:
            ip: Client IP address
            
        Returns:
            True if IP was blocked, False otherwise
        """
        with self.lock:
            if ip in self.blocked_ips:
                debug_log(f"IP {ip} already blocked, ignoring failure")
                return False
            
            self.to_block[ip] += 1/2
            current_count = self.to_block[ip]
            
            debug_log(f"Incremented failure count for {ip}: {current_count}/{self.block_threshold}")
            
            if current_count >= self.block_threshold:
                self.blocked_ips[ip] = datetime.now().isoformat()
                del self.to_block[ip]
                self.connection_attempts.pop(ip, None)
                self._save_blocked_ips()
                debug_log(f"BLOCKED {ip} after {self.block_threshold} failures")
                try:
                    if hasattr(ctx, 'log') and ctx.log:
                        ctx.log.warn(f"[BLOCKED] {ip} blocked after {self.block_threshold} authentication failures")
                except (AttributeError, NameError):
                    pass
                return True
            
            return False

    def reset_failure_count(self, ip: str) -> None:
        """
        Reset failure count for an IP on successful response.
        
        Args:
            ip: Client IP address
        """
        with self.lock:
            if ip in self.to_block:
                old_count = self.to_block[ip]
                del self.to_block[ip]
                debug_log(f"Reset failure count for {ip} (was {old_count})")

    def get_status(self) -> Dict:
        """
        Get current blocking status.
        
        Returns:
            Dictionary with blocking statistics
        """
        with self.lock:
            return {
                "blocked_ips": dict(self.blocked_ips),
                "pending_blocks": dict(self.to_block),
                "connection_attempts": {
                    ip: len(attempts) 
                    for ip, attempts in self.connection_attempts.items()
                },
                "block_threshold": self.block_threshold
            }
