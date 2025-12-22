# Evil_Proxy

Evil_Proxy is a robust interception proxy based on **mitmproxy**, designed for traffic analysis, HAR capture, and token extraction. It includes a comprehensive management suite for handling IP blocking, traffic monitoring, and automated deployment via Docker.

## Features

- **Traffic Interception**: Intercepts HTTP/HTTPS traffic.
- **HAR Capture**: Automatically captures and saves HTTP Archive (HAR) files for sessions.
- **Token Extraction**: Identifies and extracts authentication tokens from traffic.
- **IP Management**: Built-in IP blocker with manual management tools.
- **Dockerized**: Fully containerized for easy deployment.
- **Management Scripts**: Set of bash scripts for easy operation (start, stop, logs, etc.).

## Prerequisites

- **Docker** and **Docker Compose**
- **Python 3.x** (for local execution without Docker)
- **Bash** (for management scripts)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Evil_Proxy
   ```

2. **Prepare the environment:**
   Run the setup script to initialize directories (`Data/`, `Certs/`) and set permissions.
   ```bash
   chmod +x prepare.sh
   ./prepare.sh
   ```

## Usage

### Using Docker (Recommended)

Start the proxy stack:
```bash
docker compose up -d
```
Stop the proxy:
```bash
docker compose down
```

### Using Management Scripts

Located in the `ManageScripts/` directory, these scripts simplify common tasks:

- **Start Proxy**: `./ManageScripts/start.sh`
- **Stop Proxy**: `./ManageScripts/stop.sh`
- **Check Status**: `./ManageScripts/status.sh`
- **View Logs**: `./ManageScripts/logs.sh`
- **Manage IPs**: `./ManageScripts/manage_ips.sh` (Interactive CLI for blocking/unblocking IPs)
- **View Traffic**: `./ManageScripts/view_traffic.sh`
- **Cleanup Data**: `./ManageScripts/cleanup.sh` (Removes captured HARs and tokens)

### Local Execution (Without Docker)

If you prefer running directly on the host:
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the proxy:
   ```bash
   ./Evil_Proxy.sh
   ```

## Configuration

- **Proxy Settings**: Configured in `Evil_Proxy.sh` (Port 8081, Proxy Auth `proxy:112233`).
- **Script Configuration**: Modify `Scripts/config.py` to tune capture rules and file paths.

## Output

All captured data is stored in the `Data/` directory:
- `Data/HAR_Out/`: Captured HAR files.
- `Data/Tokens/`: Extracted tokens.
- `Data/Other/`: Logs and blocklists.

## Project Structure

```
Evil_Proxy/
├── Scripts/            # Core logic (Python: HAR capture, IP blocking, etc.)
├── ManageScripts/      # Management utilities (Bash: start, stop, monitor)
├── Data/               # Output storage (HARs, Tokens, Logs)
├── Certs/              # SSL Certificates
├── Evil_Proxy.sh       # Standalone startup script
├── prepare.sh          # Environment setup script
├── docker-compose.yml  # Docker deployment configuration
└── requirements.txt    # Python dependencies
```
