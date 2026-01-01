# Evil_Proxy

A powerful interception proxy built on **mitmproxy** for advanced traffic analysis, HTTP Archive (HAR) capture, and authentication token extraction. Evil_Proxy provides intelligent IP blocking, comprehensive traffic monitoring, and seamless Docker deployment for security researchers and developers.

## ✨ Features

### Core Capabilities
- **🔍 Traffic Interception**: Intercepts and analyzes HTTP/HTTPS traffic in real-time
- **📦 HAR Capture**: Automatically captures and saves HTTP Archive (HAR) files for detailed session analysis
- **🔑 Token Extraction**: Intelligently identifies and extracts JWT and authentication tokens from traffic
- **🛡️ Smart IP Blocking**: Automatic IP blocking with configurable thresholds and auto-unblock timers
- **📊 Traffic Monitoring**: Real-time traffic analysis with customizable filters
- **🌐 Web Interface**: Built-in mitmweb interface for visual traffic inspection (Port 8081)

### Management & Deployment
- **🎯 Management Console**: Interactive, all-in-one management interface (`manage.sh`)
- **🐳 Docker Ready**: Fully containerized with Docker Compose for one-command deployment
- **⚙️ Individual Scripts**: Standalone bash scripts for automation and scripting
- **🔧 Configurable**: Extensive configuration options via environment variables and config files
- **📝 Detailed Logging**: Debug logs and status tracking for troubleshooting

## 📋 Prerequisites

- **Docker** and **Docker Compose** (recommended)
- **Python 3.x** (for local execution)
- **Bash** (for management scripts)
- **jq** (for IP management CLI)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Evil_Proxy
```

### 2. Prepare the Environment
Run the setup script to initialize directories and set proper permissions:
```bash
chmod +x prepare.sh
./prepare.sh
```

This will create:
- `Data/HAR_Out/` - HAR file storage
- `Data/Tokens/` - Extracted token storage
- `Data/Other/` - Logs and blocklists
- `Certs/` - SSL certificate storage

## ⚡ Quick Start

Get Evil_Proxy running in seconds with the interactive management console:

```bash
# 1. Make the management console executable
chmod +x manage.sh

# 2. Launch the console
./manage.sh

# 3. Select option 1 to start services
# 4. Access the web interface at http://localhost:8081 (password: 1234)
# 5. Configure your browser/device to use proxy: localhost:8080
```

**That's it!** The management console provides an intuitive menu for all operations including:
- Starting/stopping services
- Viewing logs and status
- Managing blocked IPs
- Viewing captured traffic
- Cleaning up old data


## 📖 Usage

### Docker Deployment (Recommended)

**Start the proxy:**
```bash
docker compose up -d
```

**Stop the proxy:**
```bash
docker compose down
```

**Access the web interface:**
- URL: `http://localhost:8081`
- Password: `1234`

**Proxy configuration:**
- Proxy Port: `8080`
- Web Interface: `8081`

### Management Console (Recommended)

The **consolidated management console** (`manage.sh`) provides an interactive interface for all proxy operations:

```bash
chmod +x manage.sh
./manage.sh
```

**Features:**
- 🚀 **Service Management**: Start, stop, check status, and view logs
- 📊 **Traffic Management**: View captured traffic and cleanup old data
- 🛡️ **IP Management**: Block, unblock, and manage IP blocklist
- 🎨 **Interactive Menu**: User-friendly console interface with color-coded output

**Main Menu Options:**
1. Start Services
2. Stop Services
3. Service Status
4. View Live Logs
5. View Captured Traffic
6. Cleanup Old Captures
7. IP Management (Block/Unblock)
0. Exit

### Individual Management Scripts (Alternative)

For scripting or automation, individual scripts are available in `ManageScripts/`:

| Script | Purpose |
|--------|---------|
| `start.sh` | Start the proxy container |
| `stop.sh` | Stop the proxy container |
| `status.sh` | Check proxy status |
| `logs.sh` | View proxy logs |
| `manage_ips.sh` | Interactive IP blocking management |
| `view_traffic.sh` | View captured traffic summary |
| `cleanup.sh` | Clean captured data (HARs and tokens) |

**Examples:**

```bash
# Start the proxy
./ManageScripts/start.sh

# Check status
./ManageScripts/status.sh

# View logs
./ManageScripts/logs.sh

# Manage blocked IPs
./ManageScripts/manage_ips.sh list
./ManageScripts/manage_ips.sh block 192.168.1.100
./ManageScripts/manage_ips.sh unblock 192.168.1.100
./ManageScripts/manage_ips.sh status
./ManageScripts/manage_ips.sh clear

# Clean up captured data
./ManageScripts/cleanup.sh
```

### Local Execution (Without Docker)

For development or testing without Docker:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the proxy:**
   ```bash
   chmod +x Evil_Proxy.sh
   ./Evil_Proxy.sh
   ```

**Note:** Local execution uses proxy authentication (`proxy:112233`) by default.

## ⚙️ Configuration

### Proxy Settings

**Docker (docker-compose.yml):**
- Mode: `regular`
- Proxy Port: `8080`
- Web Interface: `8081` (password: `1234`)
- Certificates: `./Certs`
- View Filter: Hides 407 Proxy Auth Required responses

**Local (Evil_Proxy.sh):**
- Mode: `regular`
- Proxy Port: `8080`
- Web Interface: `8081` (password: `1234`)
- Proxy Auth: `proxy:112233`
- Certificates: `./Certs`

### Environment Variables (Docker)

Customize behavior via environment variables in `docker-compose.yml`:

```yaml
environment:
  - MITM_MODE=regular          # Proxy mode (regular/transparent/upstream)
  - WEBPASSWORD=1234           # Web interface password
  - WEB_PORT=8081              # Web interface port
  - PROXYAUTH=proxy:112233     # Proxy authentication (optional)
  - BLOCK_GLOBAL=false         # Block global addresses
  - BLOCK_PRIVATE=false        # Block private addresses
```

### Script Configuration (Scripts/config.py)

Fine-tune capture and blocking behavior:

```python
# Blocking Configuration
BLOCK_RESET_INTERVAL = timedelta(hours=1)  # Auto-unblock after 1 hour
BLOCK_THRESHOLD = 10                        # Block after 10 failed attempts
CLEANUP_INTERVAL = 60                       # Check every 60 seconds

# Timing Configuration
SAVE_INTERVAL = 60                          # Save flows every 60 seconds
STATUS_LOG_INTERVAL = 300                   # Log status every 5 minutes
```

### IP Blocking

The IP blocker automatically blocks IPs that exceed the threshold for failed authentication attempts. Blocked IPs are stored in `Data/Other/blocked_ips.json` and automatically unblocked after 1 hour.

**Manual IP Management:**
```bash
./ManageScripts/manage_ips.sh list      # List all blocked IPs
./ManageScripts/manage_ips.sh block IP  # Manually block an IP
./ManageScripts/manage_ips.sh unblock IP # Manually unblock an IP
./ManageScripts/manage_ips.sh clear     # Clear all blocked IPs
```

## 📂 Output

All captured data is organized in the `Data/` directory:

```
Data/
├── HAR_Out/           # HTTP Archive (HAR) files
│   └── session_*.har  # Timestamped HAR captures
├── Tokens/            # Extracted authentication tokens
│   └── tokens_*.txt   # Timestamped token extracts
└── Other/             # Logs and configuration
    ├── blocked_ips.json  # IP blocklist
    └── debug.log         # Debug logging
```

## 🏗️ Project Structure

```
Evil_Proxy/
├── Scripts/                    # Core Python modules
│   ├── script.py              # Main mitmproxy addon
│   ├── config.py              # Configuration constants
│   ├── har_capture.py         # HAR capture logic
│   ├── token_extractor.py     # Token extraction logic
│   ├── ip_blocker.py          # IP blocking logic
│   └── utils.py               # Utility functions
├── ManageScripts/              # Individual bash management utilities
│   ├── start.sh               # Start proxy
│   ├── stop.sh                # Stop proxy
│   ├── status.sh              # Check status
│   ├── logs.sh                # View logs
│   ├── manage_ips.sh          # IP management CLI
│   ├── view_traffic.sh        # Traffic viewer
│   └── cleanup.sh             # Data cleanup
├── Data/                       # Output directory (created by prepare.sh)
│   ├── HAR_Out/               # HAR captures
│   ├── Tokens/                # Extracted tokens
│   └── Other/                 # Logs and blocklists
├── Certs/                      # SSL certificates (created by prepare.sh)
├── Transparent/                # Transparent proxy mode files
├── manage.sh                   # 🎯 Consolidated management console (RECOMMENDED)
├── Evil_Proxy.sh               # Standalone startup script
├── prepare.sh                  # Environment setup script
├── entrypoint.sh               # Docker entrypoint script
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker Compose configuration
├── docker-compose.image.yml    # Alternative Docker Compose (custom image)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🔧 Advanced Usage

### Custom Docker Image

Build and use a custom Docker image:

```bash
# Build the image
docker build -t evil-proxy:latest .

# Use the custom image
docker compose -f docker-compose.image.yml up -d
```

### Transparent Proxy Mode

For transparent proxy mode, additional iptables rules are required. See the `Transparent/` directory for configuration examples.

### Debugging

Enable debug logging by checking `Data/Other/debug.log`:

```bash
tail -f Data/Other/debug.log
```

## 🛠️ Troubleshooting

**Issue: Permission denied errors**
- Run `./prepare.sh` to set proper permissions
- Ensure Docker has access to the project directory

**Issue: Web interface not accessible**
- Check if port 8081 is available: `netstat -tuln | grep 8081`
- Verify the container is running: `docker ps`

**Issue: Certificates not trusted**
- Install mitmproxy CA certificate from `Certs/mitmproxy-ca-cert.pem`
- Import into your browser or system certificate store

**Issue: IP blocking not working**
- Verify `Data/Other/blocked_ips.json` exists
- Check `Data/Other/debug.log` for errors
- Ensure `jq` is installed for IP management CLI

## 📝 License

[Add your license information here]

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## ⚠️ Disclaimer

This tool is intended for authorized security testing and research purposes only. Users are responsible for complying with applicable laws and regulations.
