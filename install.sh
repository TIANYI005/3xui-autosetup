#!/bin/bash
set -e

BASE="https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/main"
CMDS="$HOME/.claude/commands"

echo "Installing /vps skill..."

mkdir -p "$CMDS/vps"

curl -fsSL "$BASE/vps.md"                          -o "$CMDS/vps.md"
curl -fsSL "$BASE/scripts/vps_install.py"          -o "$CMDS/vps/vps_install.py"
curl -fsSL "$BASE/scripts/vps_postinstall.py"      -o "$CMDS/vps/vps_postinstall.py"
curl -fsSL "$BASE/scripts/vps_latency.py"          -o "$CMDS/vps/vps_latency.py"
curl -fsSL "$BASE/scripts/setup_vps.py"            -o "$CMDS/vps/setup_vps.py"
curl -fsSL "$BASE/scripts/vps_run_setup.py"        -o "$CMDS/vps/vps_run_setup.py"
curl -fsSL "$BASE/scripts/vps_qr.py"               -o "$CMDS/vps/vps_qr.py"

echo ""
echo "Done. Open Claude Code and run: /vps <ip> <port> <password>"
