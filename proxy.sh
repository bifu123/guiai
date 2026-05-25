#!/bin/bash

# Configuration paths
CONFIG_CACHE="/tmp/.proxy_url_cache"
PROFILE_FILE="/etc/profile.d/proxy.sh"
DOCKER_PROXY_DIR="/etc/systemd/system/docker.service.d"
DOCKER_PROXY_FILE="$DOCKER_PROXY_DIR/http-proxy.conf"
APT_PROXY_FILE="/etc/apt/apt.conf.d/95proxies"

# Default fallback value
DEFAULT_PROXY="http://192.168.2.16:65532"

# Check for root privileges
if [ "$EUID" -ne 0 ]; then 
  echo "Error: Please run as root (use sudo): sudo $0"
  exit 1
fi

# Function to get the proxy URL from user
get_proxy_url() {
    local saved_url
    [ -f "$CONFIG_CACHE" ] && saved_url=$(cat "$CONFIG_CACHE")
    local current_default=${saved_url:-$DEFAULT_PROXY}

    read -p "Enter proxy URL (Default: $current_default): " input_url
    local final_url=${input_url:-$current_default}
    
    # Simple validation
    if [[ ! $final_url =~ ^http://.* ]]; then
        echo "Warning: URL does not start with 'http://'. Please double-check."
    fi

    # Save to cache for next time
    echo "$final_url" > "$CONFIG_CACHE"
    echo "$final_url"
}

set_proxy() {
    local PROXY_URL=$(get_proxy_url)
    echo "? Setting proxy to: $PROXY_URL ..."

    # 1. Shell environment variables
    tee $PROFILE_FILE > /dev/null <<EOF
export http_proxy="$PROXY_URL"
export https_proxy="$PROXY_URL"
export ftp_proxy="$PROXY_URL"
export no_proxy="localhost,127.0.0.1,::1,192.168.*,172.16.*,172.17.*,172.18.*,172.19.*,172.20.*,172.21.*,172.22.*,172.23.*,172.24.*,172.25.*,172.26.*,172.27.*,172.28.*,172.29.*,172.30.*,172.31.*,10.*"
EOF

    # 2. Docker proxy configuration
    mkdir -p $DOCKER_PROXY_DIR
    tee $DOCKER_PROXY_FILE > /dev/null <<EOF
[Service]
Environment="HTTP_PROXY=$PROXY_URL"
Environment="HTTPS_PROXY=$PROXY_URL"
Environment="NO_PROXY=localhost,127.0.0.1,::1,192.168.*,172.16.*,172.17.*,172.18.*,172.19.*,172.20.*,172.21.*,172.22.*,172.23.*,172.24.*,172.25.*,172.26.*,172.27.*,172.28.*,172.29.*,172.30.*,172.31.*,10.*"
EOF

    systemctl daemon-reload
    systemctl restart docker 2>/dev/null

    # 3. APT proxy configuration
    tee $APT_PROXY_FILE > /dev/null <<EOF
APT::Acquire::http::Proxy "$PROXY_URL";
APT::Acquire::https::Proxy "$PROXY_URL";
EOF

    echo "? Proxy enabled successfully."
    echo "Notice: Run 'source $PROFILE_FILE' to apply changes to current shell."
}

unset_proxy() {
    echo "? Disabling proxy..."
    rm -f $PROFILE_FILE $DOCKER_PROXY_FILE $APT_PROXY_FILE
    systemctl daemon-reload
    systemctl restart docker 2>/dev/null
    echo "? Proxy disabled."
    echo "Notice: Run 'unset http_proxy https_proxy ftp_proxy no_proxy' to clean current session."
}

show_status() {
    echo "--- Configuration Status ---"
    [ -f "$PROFILE_FILE" ] && echo "[ENABLED] Shell Environment" || echo "[DISABLED] Shell Environment"
    [ -f "$DOCKER_PROXY_FILE" ] && echo "[ENABLED] Docker Proxy" || echo "[DISABLED] Docker Proxy"
    [ -f "$APT_PROXY_FILE" ] && echo "[ENABLED] APT Proxy" || echo "[DISABLED] APT Proxy"
}

show_menu() {
    echo "=============================="
    echo "  Proxy Manager (v2.1)"
    echo "=============================="
    echo "1) Enable proxy"
    echo "2) Disable proxy"
    echo "3) Show status"
    echo "0) Exit"
    echo "=============================="
    read -p "Please choose: " choice

    case $choice in
        1) set_proxy ;;
        2) unset_proxy ;;
        3) show_status ;;
        0) exit 0 ;;
        *) echo "Invalid choice." ;;
    esac
}

# Command line argument support
case "$1" in
    on)     set_proxy ;;
    off)    unset_proxy ;;
    status) show_status ;;
    *)      show_menu ;;
esac