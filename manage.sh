#!/bin/bash

# ==============================================================================
# Evil Proxy Management Console
# ==============================================================================
# This script consolidates functionality from separate management scripts
# into a single, modular, and interactive interface.
#
# Functionality included:
# - Service Management (Start/Stop/Status/Logs)
# - Traffic Management (View/Cleanup)
# - IP Management (Block/Unblock/List)
# ==============================================================================

# --- Configuration & Globals ---
SCRIPT_DIR="$(pwd)"
# Assumes the script is in the project root
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
# Adjust this if your docker-compose.yml is elsewhere. 
# Usually it's in the project root.
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# IP Management Config
BLOCKLIST_FILE=""
POSSIBLE_PATHS=(
    "$PROJECT_ROOT/Data/Other/blocked_ips.json"
    "/home/mitmproxy/Data/Other/blocked_ips.json"
    "./Data/Other/blocked_ips.json"
)

# Attempt to locate blocklist
for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -f "$path" ]; then
        BLOCKLIST_FILE="$path"
        break
    fi
done

# Default path if not found
if [ -z "$BLOCKLIST_FILE" ]; then
    BLOCKLIST_FILE="$PROJECT_ROOT/Data/Other/blocked_ips.json"
fi

BLOCK_RESET_INTERVAL_SECONDS=3600 # 1 hour

# --- Helper Functions ---

# Print a standardized header
print_header() {
    clear
    echo -e "${CYAN}======================================================================${NC}"
    echo -e "${CYAN}                  EVIL PROXY MANAGEMENT CONSOLE                       ${NC}"
    echo -e "${CYAN}======================================================================${NC}"
    echo ""
}

# Pause and wait for user input
wait_for_key() {
    echo ""
    read -n 1 -s -r -p "Press any key to return..."
    echo ""
}

# Check for necessary tools
check_dependencies() {
    local missing=0
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}Warning: 'jq' is not installed. IP management features will function poorly.${NC}"
        missing=1
    fi
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: 'docker' is not installed. Service management will not work.${NC}"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        read -p "Press Enter to continue anyway..."
    fi
}

# --- Service Management ---

start_services() {
    echo -e "${GREEN}Starting mitmproxy services...${NC}"
    if [ -f "$COMPOSE_FILE" ]; then
        docker compose -f "$COMPOSE_FILE" up -d
    else
        echo -e "${YELLOW}docker-compose.yml not found at $COMPOSE_FILE. Trying current dir...${NC}"
        docker compose up -d
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Services started.${NC}"
    else
        echo -e "${RED}✗ Failed to start services.${NC}"
    fi
    wait_for_key
}

stop_services() {
    echo -e "${YELLOW}Stopping mitmproxy services...${NC}"
    if [ -f "$COMPOSE_FILE" ]; then
        docker compose -f "$COMPOSE_FILE" down
    else
        docker compose down
    fi
    echo -e "${GREEN}✓ Services stopped.${NC}"
    wait_for_key
}

service_status() {
    echo -e "${BLUE}=== Service Status ===${NC}"
    if [ -f "$COMPOSE_FILE" ]; then
        docker compose -f "$COMPOSE_FILE" ps
    else
        docker compose ps
    fi
    echo ""
    echo -e "${BLUE}=== Recent Logs (Last 20) ===${NC}"
    if [ -f "$COMPOSE_FILE" ]; then
        docker compose -f "$COMPOSE_FILE" logs --tail=20 mitmproxy
    else
        docker compose logs --tail=20 mitmproxy
    fi
    wait_for_key
}

view_logs() {
    echo -e "${BLUE}Viewing logs (Press Ctrl+C to exit)...${NC}"
    trap 'echo -e "\n${YELLOW}Log view stopped.${NC}"; return' SIGINT
    if [ -f "$COMPOSE_FILE" ]; then
        docker compose -f "$COMPOSE_FILE" logs -f mitmproxy
    else
        docker compose logs -f mitmproxy
    fi
    trap - SIGINT
}

# --- Traffic Management ---

# Consolidates view_traffic.sh logic
view_traffic() {
    # Assuming captures are in ManageScripts/captures based on existing scripts
    local captures_dir="$SCRIPT_DIR/captures"
    
    echo -e "${BLUE}=== Traffic Viewer ===${NC}"
    
    if [ ! -d "$captures_dir" ]; then
        echo -e "${YELLOW}No 'captures' directory found at $captures_dir.${NC}"
        wait_for_key
        return
    fi

    # Find unique client IPs (directories)
    echo "Available Client IPs:"
    # This complex find command looks for directories named like IPs
    local clients=$(find "$captures_dir" -type d \( -name "*.*.*.*" -o -name "*:*" \) 2>/dev/null | xargs -I {} basename {} | sort -u)
    
    if [ -z "$clients" ]; then
        echo "No captured traffic found."
        wait_for_key
        return
    fi
    
    echo "$clients"
    echo ""
    echo -e "${CYAN}Enter the Client IP to view details:${NC}"
    read -p "> " client_ip
    
    if [ -z "$client_ip" ]; then return; fi
    
    local today=$(date +%Y-%m-%d)
    local target_dir="$captures_dir/$today/$client_ip"
    
    echo ""
    echo -e "Checking traffic for ${BLUE}$client_ip${NC} on ${BLUE}$today${NC}..."
    
    if [ -d "$target_dir" ]; then
        ls -lt "$target_dir"
    else
        echo -e "${YELLOW}No traffic found for $client_ip today.${NC}"
        # Optional: check if traffic exists for this IP on other days
        local other_days=$(find "$captures_dir" -type d -name "$client_ip" | grep -v "$today")
        if [ ! -z "$other_days" ]; then
            echo "Found traffic on other dates:"
            echo "$other_days"
        fi
    fi
    wait_for_key
}

cleanup_captures() {
    local captures_dir="$SCRIPT_DIR/captures"
    echo -e "${YELLOW}=== Cleanup Old Captures ===${NC}"
    echo "This will delete .har files older than 30 days and empty directories."
    read -p "Are you sure? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        if [ -d "$captures_dir" ]; then
            find "$captures_dir" -name "*.har" -mtime +30 -delete
            find "$captures_dir" -type d -empty -delete
            echo -e "${GREEN}Cleanup complete.${NC}"
            echo "Current usage:"
            du -sh "$captures_dir"
        else
            echo "Captures directory not found."
        fi
    else
        echo "Cancelled."
    fi
    wait_for_key
}

# --- IP Management Integration ---

# JSON Helper: Load IPs
load_blocked_ips() {
    if [ ! -f "$BLOCKLIST_FILE" ] || [ ! -s "$BLOCKLIST_FILE" ]; then
        echo "{}"
        return
    fi
    local raw_data=$(cat "$BLOCKLIST_FILE")
    # Compatibility handler handling array vs object format
    if echo "$raw_data" | jq -e 'type == "array"' > /dev/null 2>&1; then
        local current_iso=$(date --iso-8601=seconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
        echo "$raw_data" | jq --arg time "$current_iso" 'reduce .[] as $ip ({}; .[$ip] = $time)'
    elif echo "$raw_data" | jq -e 'type == "object"' > /dev/null 2>&1; then
        echo "$raw_data"
    else
        echo "{}"
    fi
}

# JSON Helper: Save IPs
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

# IP Action: List
list_ips() {
    local data=$(load_blocked_ips)
    local count=$(echo "$data" | jq 'length')
    
    echo -e "\n${BLUE}=== Blocked IPs ($count) ===${NC}"
    if [ "$count" -eq 0 ]; then
        echo "No IPs are currently blocked."
    else
        echo "IP Address           | Blocked At"
        echo "--------------------------------------------------------"
        echo "$data" | jq -r 'to_entries[] | "\(.key) \(.value)"' | while read -r ip block_time_str; do
             printf "%-20s | %s\n" "$ip" "$block_time_str"
        done
    fi
    echo ""
}

# IP Action: Block
block_ip_action() {
    read -p "Enter IP to block: " ip
    if [ -z "$ip" ]; then return; fi
    
    local data=$(load_blocked_ips)
    if echo "$data" | jq -e --arg ip "$ip" 'has($ip)' > /dev/null; then
        echo -e "${YELLOW}IP $ip is already blocked.${NC}"
        wait_for_key
        return
    fi
    
    local current_iso=$(date --iso-8601=seconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
    local new_data=$(echo "$data" | jq --arg ip "$ip" --arg time "$current_iso" '.[$ip] = $time')
    
    if save_blocked_ips "$new_data"; then
        echo -e "${GREEN}Successfully blocked IP: $ip${NC}"
    else
        echo -e "${RED}Error saving blocked IPs.${NC}"
    fi
    wait_for_key
}

# IP Action: Unblock
unblock_ip_action() {
    read -p "Enter IP to unblock: " ip
    if [ -z "$ip" ]; then return; fi
    
    local data=$(load_blocked_ips)
    if ! echo "$data" | jq -e --arg ip "$ip" 'has($ip)' > /dev/null; then
        echo -e "${YELLOW}IP $ip is not blocked.${NC}"
        wait_for_key
        return
    fi
    
    local new_data=$(echo "$data" | jq --arg ip "$ip" 'del(.[$ip])')
    
    if save_blocked_ips "$new_data"; then
        echo -e "${GREEN}Successfully unblocked IP: $ip${NC}"
    else
        echo -e "${RED}Error saving changes.${NC}"
    fi
    wait_for_key
}

# IP Action: Clear All
clear_all_ips() {
    echo -e "${RED}WARNING: This will unblock ALL IPs.${NC}"
    read -p "Are you sure? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
         if save_blocked_ips "{}"; then
             echo -e "${GREEN}All blocked IPs cleared.${NC}"
         else
             echo -e "${RED}Error clearing IPs.${NC}"
         fi
    else
        echo "Cancelled."
    fi
    wait_for_key
}

# IP Management Menu
ip_menu() {
    while true; do
        clear
        echo -e "${CYAN}=== IP Management ===${NC}"
        echo "Current Blocklist: $BLOCKLIST_FILE"
        echo ""
        list_ips
        echo "1. Block an IP"
        echo "2. Unblock an IP"
        echo "3. Clear Blocklist"
        echo "0. Back to Main Menu"
        echo ""
        read -p "Select option: " choice
        case "$choice" in
            1) block_ip_action ;;
            2) unblock_ip_action ;;
            3) clear_all_ips ;;
            0) return ;;
            *) echo "Invalid option." ;;
        esac
    done
}

# --- Main Loop ---

# Ensure executable permissions on self if needed
chmod +x "$0" 2>/dev/null

check_dependencies

while true; do
    print_header
    echo "1. Start Services"
    echo "2. Stop Services"
    echo "3. Service Status"
    echo "4. View Live Logs"
    echo "------------------------"
    echo "5. View Captured Traffic"
    echo "6. Cleanup Old Captures"
    echo "------------------------"
    echo "7. IP Management (Block/Unblock)"
    echo "------------------------"
    echo "0. Exit"
    echo ""
    read -p "Select an option: " choice
    
    case "$choice" in
        1) start_services ;;
        2) stop_services ;;
        3) service_status ;;
        4) view_logs ;;
        5) view_traffic ;;
        6) cleanup_captures ;;
        7) ip_menu ;;
        0) echo "Goodbye!"; exit 0 ;;
        *) echo -e "${RED}Invalid option.${NC}"; sleep 1 ;;
    esac
done
