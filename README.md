<div align="center">

# 3xui-autosetup

**A Claude Code slash command that fully automates VLESS+Reality node setup.**  
One command. No web UI. QR code in your terminal.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![3x-ui](https://img.shields.io/badge/panel-3x--ui%20v2.8.11-orange.svg)
![Protocol](https://img.shields.io/badge/protocol-VLESS%20%2B%20Reality-brightgreen.svg)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)

</div>

---

## Overview

`/vps` is a [Claude Code](https://claude.ai/code) slash command that provisions a complete VLESS+Reality proxy node from scratch — SSH into a fresh VPS, install [3x-ui](https://github.com/MHSanaei/3x-ui), run SNI latency tests, configure via API, and print a scannable QR code — all without touching a web browser.

```
/vps <ip> <ssh-port> <root-password>
```

## Why 3x-ui + xray-core?

Reality protocol has two major implementations: **xray-core** and **sing-box**. They are not cross-compatible — if the server uses one and the client uses the other, the handshake always fails.

Most popular clients (Shadowrocket, v2rayN, NekoBox) use **xray-core**. So the server must too. 3x-ui embeds xray-core and exposes a clean REST API, making fully automated setup possible.

> sing-box servers will always fail with xray-core clients on Reality. This is not a key or config issue — it's a protocol-level incompatibility.

## Features

- **Single command setup** — pass IP, SSH port, and password; the rest is automatic
- **Auto SSL** — Let's Encrypt IP certificate (no domain needed), valid 6 days, auto-renews
- **Smart SNI selection** — latency-tests 20 domains across Microsoft, Apple, NVIDIA, AWS, Cloudflare, Akamai and picks the fastest
- **API-only config** — zero web UI interaction required
- **QR code output** — scan directly with Shadowrocket or any compatible client
- **Cross-distro** — Rocky Linux, Ubuntu, Debian, CentOS, Arch and more

## Client Compatibility

| Client | Platform | Status |
|--------|----------|--------|
| Shadowrocket | iOS / macOS | ✅ Verified |
| v2rayN | Windows | ✅ Compatible |
| NekoBox | Android | ✅ Compatible |
| Hiddify | macOS / Android | ✅ Compatible |
| v2rayN | macOS | ⚠️ Cannot parse Reality URI parameters |

## Prerequisites

- macOS with [Claude Code](https://claude.ai/code) installed
- `sshpass` — `brew install sshpass`
- `qrencode` — `brew install qrencode`
- A fresh VPS with root SSH access (Rocky Linux 9 / Ubuntu / Debian recommended)
- Ports **80** and **443** open on the VPS

## Installation

Copy the skill file to your Claude Code commands directory:

```bash
curl -o ~/.claude/commands/vps.md \
  https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/main/vps.md
```

Or manually:

```bash
cp vps.md ~/.claude/commands/vps.md
```

## Security Disclaimer

> **Your root password is passed as a command-line argument and used only within the current Claude Code session. It is never written to disk, logged, or sent anywhere other than the SSH connection to your own VPS. That said, be aware that:**
> - Anyone with access to your Claude Code session can see the password in the conversation history
> - Avoid using this skill on shared or untrusted machines
> - Consider changing your root password or switching to key-based SSH auth after setup

## Usage

```
/vps <ip>
/vps <ip> <ssh-port> <root-password>
```

> **Note on SSH port:** Many VPS providers use port `22` by default, but some (e.g. BandwagonHost) assign a non-standard port. Check your provider's control panel if you're unsure. If you omit the port, the skill will ask you.

**Example:**

```
/vps 1.2.3.4 22 mypassword
```

The skill walks through five stages automatically:

```
Stage 1 — Collect info (or read from arguments)
Stage 2 — Install 3x-ui + issue Let's Encrypt IP cert
Stage 3 — Latency test 20 SNI domains, pick the fastest
Stage 4 — API config: generate X25519 keypair, create VLESS+Reality inbound
Stage 5 — Print subscription link + QR code
```

## What Gets Configured

- **Protocol**: VLESS + Reality + `xtls-rprx-vision`
- **Port**: 443
- **SNI**: auto-selected (lowest latency from test pool)
- **Fingerprint**: Chrome
- **Keypair**: X25519, generated fresh each run via Python `cryptography`

## How It Works

The skill uses `sshpass` to run commands remotely without an interactive session. The 3x-ui panel is configured entirely through its REST API — no browser, no clicking. The Python setup script runs on the VPS itself to avoid firewall issues with the panel port.

```
Local machine                        VPS
     │                                │
     ├─ sshpass install 3x-ui ───────▶│
     ├─ sshpass latency test ────────▶│
     ├─ scp setup_vps.py ────────────▶│
     └─ sshpass python3 setup_vps.py ▶│
                                       ├─ POST /login
                                       ├─ generate X25519 keypair
                                       ├─ POST /panel/api/inbounds/add
                                       └─ print LINK=vless://...
```

## Attribution

This project installs and configures **[3x-ui](https://github.com/MHSanaei/3x-ui)** by [@MHSanaei](https://github.com/MHSanaei), licensed under GPL-3.0. This skill does not redistribute any 3x-ui source code.

---

<div align="center">

## 中文说明

</div>

`/vps` 是一个 [Claude Code](https://claude.ai/code) slash command，一条命令完成 VLESS+Reality 节点全流程搭建——SSH 登录、安装 3x-ui、SNI 延迟测试、API 配置、终端输出二维码，全程无需打开浏览器。

### 为什么选 3x-ui + xray-core？

Reality 协议有两套实现：**xray-core** 和 **sing-box**，两者不兼容。主流客户端（Shadowrocket、v2rayN、NekoBox）均使用 xray-core，因此服务端也必须使用 xray-core。3x-ui 内嵌 xray-core 并提供完整 REST API，是目前自动化配置的最佳选择。

### 安装

```bash
cp vps.md ~/.claude/commands/vps.md
```

### 安全提示

> root 密码仅在当前 Claude Code session 中使用，不会写入磁盘或上传至任何第三方。但请注意：不要在共享或不受信任的设备上使用此 skill，建议配置完成后改用 SSH 密钥登录。

### 使用

```
/vps <IP地址> <SSH端口> <root密码>
```

> **关于 SSH 端口**：大多数 VPS 默认为 22 端口，但部分服务商（如 BandwagonHost）会分配非标准端口，请在控制面板确认。如果不填端口，skill 会主动询问。

### 前置条件

- macOS + Claude Code
- `brew install sshpass qrencode`
- 开放端口 80、443 的全新 VPS（Rocky Linux 9 / Ubuntu / Debian）

---

<div align="center">
<sub>MIT License · Built with Claude Code</sub>
</div>
