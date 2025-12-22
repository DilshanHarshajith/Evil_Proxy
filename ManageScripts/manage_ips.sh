#!/bin/bash

# IP Management CLI Tool (Bash Version)
# This script provides a command-line interface to manage blocked IPs
# in the mitmproxy Evil_Proxy system.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
# Try to find the blocked_ips.json file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POSSIBLE_PATHS=(
    "$SCRIPT_DIR/../Data/Other/blocked_ips.json"
    "/home/mitmproxy/Data/Other/blocked_ips.json"
    "./Data/Other/blocked_ips.json"
)

BLOCKLIST_FILE=""
for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -f "$path" ]; then
        BLOCKLIST_FILE="$path"
        break
    fi
done

# Default to the one in Setup/Data if not found
if [ -z "$BLOCKLIST_FILE" ]; then
    BLOCKLIST_FILE="$SCRIPT_DIR/../Data/Other/blocked_ips.json"
fi

BLOCK_RESET_INTERVAL_SECONDS=3600 # 1 hour

usage() {
    echo -e "${BLUE}IP Management CLI Tool${NC}"
    echo
    echo "Usage:"
    echo "    $0 list                    # List all blocked IPs"
    echo "    $0 unblock <ip>            # Unblock a specific IP"
    echo "    $0 block <ip>              # Block a specific IP"
    echo "    $0 status                  # Show detailed status"
    echo "    $0 clear                   # Clear all blocked IPs"
    echo
}

load_blocked_ips() {
    if [ ! -f "$BLOCKLIST_FILE" ] || [ ! -s "$BLOCKLIST_FILE" ]; then
        echo "{}"
        return
    fi
    local raw_data=$(cat "$BLOCKLIST_FILE")
    # If it's an array, convert to dict with current time
    if echo "$raw_data" | jq -e 'type == "array"' > /dev/null 2>&1; then
        local current_iso=$(date --iso-8601=seconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
        echo "$raw_data" | jq --arg time "$current_iso" 'reduce .[] as $ip ({}; .[$ip] = $time)'
    elif echo "$raw_data" | jq -e 'type == "object"' > /dev/null 2>&1; then
        echo "$raw_data"
    else
        # Invalid JSON, return empty object
        echo "{}"
    fi
}

save_blocked_ips() {
    local data="$1"
    if [ -z "$data" ]; then data="{}"; fi
    local dir=$(dirname "$BLOCKLIST_FILE")
    mkdir -p "$dir"
    echo "$data" | jq '.' > "$BLOCKLIST_FILE.tmp" 2>/dev/null
    if [ $? -eq 0 ] && [ -s "$BLOCKLIST_FILE.tmp" ]; then
        mv "$BLOCKLIST_FILE.tmp" "$BLOCKLIST_FILE"
        return 0
    else
        rm -f "$BLOCKLIST_FILE.tmp"
        return 1
    fi
}

list_blocked_ips() {
    local data=$(load_blocked_ips)
    local count=$(echo "$data" | jq 'length')
    
    if [ "$count" -eq 0 ]; then
        echo "No IPs are currently blocked."
        return
    fi
    
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}BLOCKED IPS ($count)${NC}"
    echo -e "${BLUE}======================================================================${NC}"
    
    local current_time=$(date +%s)
    
    echo "$data" | jq -r 'to_entries[] | "\(.key) \(.value)"' | while read -r ip block_time_str; do
        # Try to parse the ISO date
        local block_time
        if [[ "$OSTYPE" == "darwin"* ]]; then
            block_time=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${block_time_str%.*}" +%s 2>/dev/null || date -j -f "%Y-%m-%d %H:%M:%S" "$block_time_str" +%s 2>/dev/null)
        else
            block_time=$(date -d "$block_time_str" +%s 2>/dev/null)
        fi
        
        if [ -z "$block_time" ]; then
            printf "  %-20s | Blocked: %s (invalid timestamp)\n" "$ip" "$block_time_str"
            echo "  ----------------------------------------------------------------------"
            continue
        fi
        
        local time_elapsed=$((current_time - block_time))
        local time_remaining=$((BLOCK_RESET_INTERVAL_SECONDS - time_elapsed))
        
        printf "  %-20s | Blocked: %s\n" "$ip" "$(date -d "@$block_time" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r "$block_time" '+%Y-%m-%d %H:%M:%S')"
        
        if [ "$time_remaining" -gt 0 ]; then
            local hours=$((time_remaining / 3600))
            local minutes=$(( (time_remaining % 3600) / 60 ))
            local seconds=$((time_remaining % 60))
            printf "  %-20s | Auto-unblock in: %02dh %02dm %02ds\n" "" "$hours" "$minutes" "$seconds"
        else
            printf "  %-20s | ${YELLOW}⚠ Should auto-unblock soon (expired)${NC}\n" ""
        fi
        echo "  ----------------------------------------------------------------------"
    done
    echo
}

block_ip() {
    local ip="$1"
    if [ -z "$ip" ]; then
        echo -e "${RED}✗ Error: Please specify an IP address to block.${NC}"
        return 1
    fi
    
    local data=$(load_blocked_ips)
    if echo "$data" | jq -e --arg ip "$ip" 'has($ip)' > /dev/null; then
        echo -e "${YELLOW}⚠ IP $ip is already blocked.${NC}"
        return 0
    fi
    
    local current_iso=$(date --iso-8601=seconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
    local new_data=$(echo "$data" | jq --arg ip "$ip" --arg time "$current_iso" '.[$ip] = $time')
    
    if save_blocked_ips "$new_data"; then
        echo -e "${GREEN}✓ Successfully blocked IP: $ip${NC}"
        echo "  The IP will be auto-unblocked in 1 hour."
    else
        echo -e "${RED}✗ Error saving blocked IPs.${NC}"
        return 1
    fi
}

unblock_ip() {
    local ip="$1"
    if [ -z "$ip" ]; then
        echo -e "${RED}✗ Error: Please specify an IP address to unblock.${NC}"
        return 1
    fi
    
    local data=$(load_blocked_ips)
    if ! echo "$data" | jq -e --arg ip "$ip" 'has($ip)' > /dev/null; then
        echo -e "${RED}✗ IP $ip is not currently blocked.${NC}"
        return 1
    fi
    
    local new_data=$(echo "$data" | jq --arg ip "$ip" 'del(.[$ip])')
    
    if save_blocked_ips "$new_data"; then
        echo -e "${GREEN}✓ Successfully unblocked IP: $ip${NC}"
        echo "  The IP can now connect to the proxy."
    else
        echo -e "${RED}✗ Error saving blocked IPs.${NC}"
        return 1
    fi
}

show_status() {
    local data=$(load_blocked_ips)
    local count=$(echo "$data" | jq 'length')
    
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}IP BLOCKER STATUS${NC}"
    echo -e "${BLUE}======================================================================${NC}"
    echo -e "  Blocklist File:      $BLOCKLIST_FILE"
    echo -e "  File Exists:         $( [ -f "$BLOCKLIST_FILE" ] && echo "Yes" || echo "No" )"
    echo -e "  Blocked IPs:         $count"
    echo -e "  Auto-unblock After:  1 hour"
    echo -e "${BLUE}======================================================================${NC}\n"
    
    if [ "$count" -gt 0 ]; then
        list_blocked_ips
    fi
}

clear_all() {
    local data=$(load_blocked_ips)
    local count=$(echo "$data" | jq 'length')
    
    if [ "$count" -eq 0 ]; then
        echo "No IPs are currently blocked."
        return
    fi
    
    echo -e "${YELLOW}⚠ This will unblock $count IP(s).${NC}"
    read -p "Are you sure? (yes/no): " choice
    case "$choice" in 
        yes|y|YES|Y)
            if save_blocked_ips "{}"; then
                echo -e "${GREEN}✓ Successfully cleared all $count blocked IP(s).${NC}"
            else
                echo -e "${RED}✗ Error clearing blocked IPs.${NC}"
            fi
            ;;
        *)
            echo "Operation cancelled."
            ;;
    esac
}

# Main entry point
case "$1" in
    list)
        list_blocked_ips
        ;;
    block)
        block_ip "$2"
        ;;
    unblock)
        unblock_ip "$2"
        ;;
    status)
        show_status
        ;;
    clear)
        clear_all
        ;;
    *)
        usage
        exit 1
        ;;
esac
