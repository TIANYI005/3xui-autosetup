<div align="center">

# 3xui-autosetup

**A Claude Code slash command that fully automates VLESS+Reality node setup.**  
One command. No web UI. QR code in your terminal.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![3x-ui](https://img.shields.io/badge/panel-3x--ui%20v2.9.1-orange.svg)
![Protocol](https://img.shields.io/badge/protocol-VLESS%20%2B%20Reality-brightgreen.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)

</div>

---

## Overview

`/vps` is a [Claude Code](https://claude.ai/code) slash command that provisions a complete VLESS+Reality proxy node from scratch — SSH into a fresh VPS, install [3x-ui](https://github.com/MHSanaei/3x-ui), run SNI latency tests, configure via API, and print a scannable QR code — all without touching a web browser.

```
/vps <ip> <ssh-port> <root-password>
```

**Only requirement: Python 3 with `paramiko` and `qrcode`.** No brew, no WSL, no system tools.

## Why 3x-ui + xray-core?

Reality protocol has two major implementations: **xray-core** and **sing-box**. They are not cross-compatible — if the server uses one and the client uses the other, the handshake always fails.

Most popular clients (Shadowrocket, v2rayN, NekoBox) use **xray-core**. So the server must too. 3x-ui embeds xray-core and exposes a clean REST API, making fully automated setup possible.

> sing-box servers will always fail with xray-core clients on Reality. This is not a key or config issue — it's a protocol-level incompatibility.

## Features

- **Single command setup** — pass IP, SSH port, and password; the rest is automatic
- **Pure Python** — uses `paramiko` for SSH and `qrcode` for terminal output; no system tools required
- **Cross-platform** — macOS, Windows, Linux (anything with Python 3)
- **Cross-distro VPS** — auto-detects Debian/Ubuntu, RHEL/Rocky/CentOS, Arch and registers the correct systemd service file
- **Smart SNI selection** — latency-tests 20 domains across Microsoft, Apple, NVIDIA, AWS, Cloudflare, Akamai and picks the fastest
- **Secure by default** — random panel credentials generated on every run; panel port bound to `127.0.0.1` only after setup (never exposed to the internet)
- **SSH tunnel for panel access** — manage 3x-ui via `ssh -L` forwarding; no public management port
- **Config saved locally** — credentials and VLESS link written to `~/.vps/<IP>.txt` after each run

## Client Compatibility

| Client | Platform | Status |
|--------|----------|--------|
| Shadowrocket | iOS / macOS | ✅ Verified |
| v2rayN | Windows | ✅ Compatible |
| NekoBox | Android | ✅ Compatible |
| Hiddify | macOS / Android | ✅ Compatible |

## Prerequisites

**Local machine:**
- Python 3 (pre-installed on macOS and most Linux; download at [python.org](https://python.org) for Windows)
- `pip install paramiko qrcode`

**VPS:**
- Fresh install with root SSH access
- Supported distros: Rocky Linux, CentOS Stream, Ubuntu, Debian, Arch (anything 3x-ui supports)
- Port **443** open (used by the VLESS proxy)
- Port **22** open (SSH management — the only port you need long-term)

## Installation

**Option 1 — One command:**

```bash
curl -fsSL https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/main/install.sh | bash
```

**Option 2 — Ask Claude to install it for you:**

Copy the message below and send it to Claude Code:

```
Please install the /vps skill by running:
curl -fsSL https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/main/install.sh | bash
```

Claude will run the install script and confirm when done.

## Usage

```
/vps <ip>
/vps <ip> <ssh-port> <root-password>
```

> **SSH port:** Most VPS providers default to `22`, but some (e.g. BandwagonHost) assign a non-standard port. Check your provider's control panel if unsure. If omitted, the skill will ask.

**Example:**

```
/vps 1.2.3.4 22 mypassword
```

The skill walks through five stages automatically:

```
Stage 0 — Check local Python deps (paramiko, qrcode); install if missing
Stage 1 — Collect VPS info (or read from arguments)
Stage 2 — Install 3x-ui on VPS; auto-register systemd service for the detected distro;
           reset panel credentials to a random password
Stage 3 — Latency-test 20 SNI domains; pick the fastest
Stage 4 — API config: generate X25519 keypair + UUID; create VLESS+Reality inbound via
           addClient API; restrict panel to localhost
Stage 5 — Print VLESS link + QR code; save config to ~/.vps/<IP>.txt
```

## Security Model

After setup completes, the attack surface is minimal:

| Port | Exposure | Purpose |
|------|----------|---------|
| 22 | Public | SSH (management) |
| 443 | Public | VLESS+Reality proxy traffic |
| 2053 | **Localhost only** | 3x-ui panel (unreachable from internet) |

The panel is bound to `127.0.0.1` via `x-ui setting -listenIP 127.0.0.1`. Port 2053 disappears from public interfaces entirely — no firewall rule needed.

**To access the panel later:**

```bash
ssh -L 2053:127.0.0.1:2053 root@<IP>
# then open http://localhost:2053 in your browser
```

Credentials are saved to `~/.vps/<IP>.txt` on your local machine.

## What Gets Configured

- **Protocol**: VLESS + Reality + `xtls-rprx-vision`
- **Port**: 443
- **SNI**: auto-selected (lowest latency from 20-domain test pool)
- **Fingerprint**: Chrome
- **Keypair**: X25519, generated fresh each run via Python `cryptography` library (on VPS)

## How It Works

All SSH interaction uses **paramiko** — a pure-Python SSH client. No `sshpass`, no shell piping, no system dependencies beyond Python itself.

```
Local machine                          VPS
     │                                  │
     ├─ paramiko: install 3x-ui ───────▶│
     ├─ paramiko: latency test ────────▶│
     ├─ paramiko sftp: upload script ──▶│
     └─ paramiko: python3 setup_vps.py ▶│
                                         ├─ POST /login
                                         ├─ generate X25519 keypair
                                         ├─ POST /panel/api/inbounds/add
                                         ├─ POST /panel/api/inbounds/addClient
                                         └─ print LINK=vless://...
```

The `addClient` API is called separately from `inbounds/add` — this is intentional. Creating clients inline via `inbounds/add` leaves `client_traffics.enable = 0` in the 3x-ui database, causing xray to silently drop all clients on restart. Using `addClient` sets `enable = 1` correctly.

## Recovering from Failures

**Stage 2 interrupted (install incomplete):** Re-run `vps_postinstall.py` — it detects distro, registers the correct service file, starts x-ui, and resets credentials in one pass. Only re-run `vps_install.py` if the x-ui binary itself is missing.

**Stage 4 failed (API error):** Re-run `vps_run_setup.py` directly — it is idempotent.

**Forgot panel password:** Check `~/.vps/<IP>.txt`, or SSH into the VPS and run:
```bash
/usr/local/x-ui/x-ui setting -username admin -password <new-password>
systemctl restart x-ui
```

## Attribution

This project installs and configures **[3x-ui](https://github.com/MHSanaei/3x-ui)** by [@MHSanaei](https://github.com/MHSanaei), licensed under GPL-3.0. This skill does not redistribute any 3x-ui source code.

---

<div align="center">

## 中文说明

</div>

`/vps` 是一个 [Claude Code](https://claude.ai/code) slash command，一条命令完成 VLESS+Reality 节点全流程搭建——SSH 登录、安装 3x-ui、SNI 延迟测试、API 配置、终端输出二维码，全程无需打开浏览器。

**唯一依赖：Python 3 + `pip install paramiko qrcode`。无需 brew、WSL 或任何系统工具。**

### 为什么选 3x-ui + xray-core？

Reality 协议有两套实现：**xray-core** 和 **sing-box**，两者不兼容。主流客户端（Shadowrocket、v2rayN、NekoBox）均使用 xray-core，因此服务端也必须使用 xray-core。3x-ui 内嵌 xray-core 并提供完整 REST API，是目前自动化配置的最佳选择。

### 安装

```bash
pip install paramiko qrcode
cp vps.md ~/.claude/commands/vps.md
```

### 使用

```
/vps <IP地址> <SSH端口> <root密码>
```

> **关于 SSH 端口**：大多数 VPS 默认为 22 端口，部分服务商（如 BandwagonHost）会分配非标准端口，请在控制面板确认。如果不填端口，skill 会主动询问。

### 安全设计

配置完成后：
- **端口 22**：公网开放，用于 SSH 管理
- **端口 443**：公网开放，用于 VLESS 代理流量
- **端口 2053**：**仅 localhost**，3x-ui 面板从公网彻底消失

面板通过 SSH 隧道访问：`ssh -L 2053:127.0.0.1:2053 root@<IP>`，然后浏览器开 `http://localhost:2053`。

凭据和节点链接自动保存到本地 `~/.vps/<IP>.txt`。

### 前置条件

- Python 3（macOS/Linux 自带；Windows 从 python.org 安装）
- `pip install paramiko qrcode`
- 开放端口 443 的全新 VPS（Rocky Linux / CentOS Stream / Ubuntu / Debian 均支持）

---

<div align="center">
<sub>MIT License · Built with Claude Code</sub>
</div>
