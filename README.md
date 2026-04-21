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
- **Credential safety** — temporary scripts are wiped at the start of every run; no old passwords left in `/tmp`

## Client Compatibility

| Client | Platform | Status |
|--------|----------|--------|
| Shadowrocket | iOS / macOS | ✅ Verified |
| v2rayN | Windows | ✅ Compatible |
| NekoBox | Android | ✅ Compatible |
| Hiddify | macOS / Android | ✅ Compatible |

## Tested VPS Distros

Verified end-to-end across two different distros:

| Distro | Version | Notes |
|--------|---------|-------|
| CentOS Stream | 9 | `ID_LIKE="rhel fedora"` — uses `.rhel` service file |
| Debian | 12 (Bookworm) | Auto-issues Let's Encrypt IP certificate (6-day, auto-renews) |

Other distros supported by 3x-ui (Ubuntu, Rocky Linux, Arch) should work via the same auto-detection logic, but have not been tested with this skill directly.

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
Stage 0 — Wipe any stale /tmp scripts; check local Python deps (paramiko, qrcode)
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
| panel port | **Localhost only** | 3x-ui panel (unreachable from internet) |

The panel is bound to `127.0.0.1` via `x-ui setting -listenIP 127.0.0.1`. The panel port disappears from public interfaces entirely — no firewall rule needed.

**To access the panel later:**

```bash
ssh -L <panel-port>:127.0.0.1:<panel-port> root@<IP>
# then open https://localhost:<panel-port>/<webbasepath> in your browser
```

Credentials are saved to `~/.vps/<IP>.txt` on your local machine (chmod 600).

## What Gets Configured

- **Protocol**: VLESS + Reality + `xtls-rprx-vision`
- **Port**: 443
- **SNI**: auto-selected (lowest latency from 20-domain test pool)
- **Fingerprint**: Chrome
- **Keypair**: X25519, generated fresh each run via Python `cryptography` library (on VPS)
- **Client**: added via `addClient` API (ensures `client_traffics.enable=1` in the database)

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

> s-ui 使用 sing-box 内核，与基于 xray-core 的客户端存在 Reality 协议不兼容问题，不要混用。

### 功能特点

- **一条命令搞定** — 传入 IP、SSH 端口和密码，其余全自动
- **纯 Python 实现** — paramiko 负责 SSH，qrcode 打印二维码，无需任何系统工具
- **跨平台本地运行** — macOS、Windows、Linux 均可，有 Python 3 即可
- **跨发行版 VPS** — 自动检测 Debian/Ubuntu、RHEL/Rocky/CentOS/CentOS Stream、Arch，注册对应的 systemd service 文件
- **智能 SNI 选择** — 对 20 个域名做延迟测试，自动选最快的
- **安全默认配置** — 每次运行随机生成面板凭据；面板端口在配置完成后绑定到 `127.0.0.1`，从公网彻底消失
- **凭据安全** — 每次运行开始时自动清除 `/tmp` 下的临时脚本，旧密码不会残留
- **本地存档** — 节点链接和面板凭据写入 `~/.vps/<IP>.txt`（权限 600）

### 已验证系统

| 系统 | 版本 | 备注 |
|------|------|------|
| CentOS Stream | 9 | `ID_LIKE="rhel fedora"`，使用 `.rhel` service 文件 |
| Debian | 12 (Bookworm) | 自动申请 Let's Encrypt IP 证书（6 天有效期，自动续期） |

其他 3x-ui 支持的发行版（Ubuntu、Rocky Linux、Arch）理论上同样可用，但尚未经过实测。

### 客户端兼容性

| 客户端 | 平台 | 状态 |
|--------|------|------|
| Shadowrocket | iOS / macOS | ✅ 已验证 |
| v2rayN | Windows | ✅ 兼容 |
| NekoBox | Android | ✅ 兼容 |
| Hiddify | macOS / Android | ✅ 兼容 |

### 安装

**方式一 — 一条命令：**

```bash
pip install paramiko qrcode
curl -fsSL https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/main/install.sh | bash
```

**方式二 — 让 Claude 帮你安装：**

把下面这句话复制给 Claude Code：

```
请帮我运行以下命令安装 /vps skill：
curl -fsSL https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/main/install.sh | bash
```

### 使用

```
/vps <IP地址> <SSH端口> <root密码>
```

> **关于 SSH 端口**：大多数 VPS 默认为 22 端口，部分服务商（如 BandwagonHost）会分配非标准端口，请在控制面板确认。不填端口时 skill 会主动询问。

**示例：**

```
/vps 1.2.3.4 22 mypassword
```

自动走完以下五个阶段：

```
阶段零 — 清除 /tmp 下的旧脚本；检查本地 Python 依赖（paramiko、qrcode）
阶段一 — 收集 VPS 信息（或从参数直接读取）
阶段二 — SSH 安装 3x-ui；自动识别发行版注册 systemd service；重置面板凭据
阶段三 — 对 20 个域名做延迟测试，选最快的作为 SNI
阶段四 — API 自动配置：生成 X25519 密钥对和 UUID；通过 addClient 接口创建
          VLESS+Reality inbound；将面板限制为仅本地访问
阶段五 — 打印 VLESS 链接 + 二维码；凭据保存到 ~/.vps/<IP>.txt
```

### 安全设计

配置完成后的暴露面：

| 端口 | 可见范围 | 用途 |
|------|----------|------|
| 22 | 公网 | SSH 管理 |
| 443 | 公网 | VLESS 代理流量 |
| 面板端口 | **仅 localhost** | 3x-ui 面板，公网不可达 |

面板通过 `x-ui setting -listenIP 127.0.0.1` 绑定到回环地址，无需防火墙规则，面板端口从公网彻底消失。

**后续访问面板：**

```bash
ssh -L <面板端口>:127.0.0.1:<面板端口> root@<IP>
# 建立隧道后浏览器打开 https://localhost:<面板端口>/<路径>
```

凭据和节点链接自动保存到本地 `~/.vps/<IP>.txt`，权限 600。

### 技术细节：为什么用 addClient 而不是 inbounds/add？

3x-ui 存在一个已知问题：通过 `inbounds/add` 接口内联创建客户端时，SQLite 数据库中 `client_traffics.enable` 会被设为 `0`，导致 x-ui 重启后 xray 配置中 clients 变为 `null`，所有客户端连接都会静默失败。

本 skill 的解决方案：先用 `inbounds/add` 创建空 inbound，再单独调用 `addClient` 接口添加客户端，后者会正确设置 `enable=1`，重启后客户端永久有效。

### 前置条件

**本地机器：**
- Python 3（macOS / Linux 自带；Windows 从 [python.org](https://python.org) 安装）
- `pip install paramiko qrcode`

**VPS：**
- 全新安装，开放 root SSH 访问
- 支持的发行版：Rocky Linux、CentOS Stream、Ubuntu、Debian、Arch
- 开放端口 443（VLESS 代理）和 22（SSH 管理）

### 故障恢复

**阶段二中断（安装不完整）：**

重新运行 postinstall 脚本即可——它会自动检测 service 文件、发行版、凭据状态并完成修复：

```bash
python3 /tmp/vps_postinstall.py
```

如果 x-ui 二进制完全不存在，才需要重新运行完整安装。

**阶段四失败（API 报错）：** 重新运行 `python3 /tmp/vps_run_setup.py`，脚本是幂等的。

**忘记面板密码：** 查 `~/.vps/<IP>.txt`，或 SSH 进 VPS 执行：

```bash
/usr/local/x-ui/x-ui setting -username admin -password <新密码>
systemctl restart x-ui
```

---

<div align="center">
<sub>MIT License · Built with Claude Code</sub>
</div>
