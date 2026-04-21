#!/bin/bash
set -e

BASE="https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/dev"
CMDS="$HOME/.claude/commands"

echo "Installing /3xui-autosetup skill..."

mkdir -p "$CMDS/3xui-autosetup"

curl -fsSL "$BASE/3xui-autosetup.md"               -o "$CMDS/3xui-autosetup.md"
curl -fsSL "$BASE/scripts/vps_install.py"          -o "$CMDS/3xui-autosetup/vps_install.py"
curl -fsSL "$BASE/scripts/vps_postinstall.py"      -o "$CMDS/3xui-autosetup/vps_postinstall.py"
curl -fsSL "$BASE/scripts/vps_latency.py"          -o "$CMDS/3xui-autosetup/vps_latency.py"
curl -fsSL "$BASE/scripts/setup_vps.py"            -o "$CMDS/3xui-autosetup/setup_vps.py"
curl -fsSL "$BASE/scripts/vps_run_setup.py"        -o "$CMDS/3xui-autosetup/vps_run_setup.py"
curl -fsSL "$BASE/scripts/vps_qr.py"               -o "$CMDS/3xui-autosetup/vps_qr.py"

echo ""
echo "Done. Open Claude Code and run: /3xui-autosetup <ip> <port> <password>"
