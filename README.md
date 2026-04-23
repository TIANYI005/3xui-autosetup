<div align="center">

# 3xui-autosetup

**A Claude Code slash command that fully automates VLESS+Reality node setup.**  
One command. Multi-user. QR code in your terminal.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![3x-ui](https://img.shields.io/badge/panel-3x--ui%20v2.9.2-orange.svg)
![Protocol](https://img.shields.io/badge/protocol-VLESS%20%2B%20Reality-brightgreen.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)

</div>

---

## Overview

`/3xui-autosetup` is a [Claude Code](https://claude.ai/code) slash command that provisions a complete VLESS+Reality proxy node from scratch — SSH into a fresh VPS, install [3x-ui](https://github.com/MHSanaei/3x-ui), scan for open ports, run SNI latency tests, configure multiple users via API, and print scannable QR codes — all without touching a web browser.

```
/3xui-autosetup <ip> <root-password>
/3xui-autosetup <ip> <ssh-port> <root-password>
```

**Only requirement: Python 3 with `paramiko`, `qrcode`, `pillow`, and `cryptography`.** No brew, no WSL, no system tools.

## Why 3x-ui + xray-core?

Reality protocol has two major implementations: **xray-core** and **sing-box**. They are not cross-compatible — if the server uses one and the client uses the other, the handshake always fails.

Most popular clients (Shadowrocket, v2rayN, NekoBox) use **xray-core**. So the server must too. 3x-ui embeds xray-core and exposes a clean REST API, making fully automated setup possible.

> sing-box servers will always fail with xray-core clients on Reality. This is not a key or config issue — it's a protocol-level incompatibility.

## Features

- **Single command setup** — pass IP and password (port auto-detected); the rest is automatic
- **Outbound port scanning** — probes common ports (443, 8443, 2096, …) before setup to find what the provider actually allows; selects the best available proxy port automatically
- **Multi-user support** — create multiple clients in one run; each user gets their own UUID and optional traffic quota (e.g. 200 GB); unlimited for the owner
- **Per-user QR codes** — each user gets a dedicated QR code PNG named `<node>_vless-reality_qr.png`; protocol tag (`[VLESS-Reality]`) prepended to all subscription links
- **SSH port auto-detection** — probes port 22 via Python socket before asking; skips the question if it's open (with 3-retry backoff for freshly reset VPS); works on Windows, macOS, and Linux without `nc`
- **Sub server conflict fix** — automatically moves the 3x-ui subscription service to `127.0.0.1:4096` so it never blocks xray from binding the proxy port
- **Startup verification** — checks `journalctl` after final restart; warns immediately if xray failed to start instead of silently outputting a broken link
- **Custom node display name** — name your node anything you want (e.g. `Tokyo-Q1`); appears in Shadowrocket, v2rayN, and any other client
- **Pure Python** — uses `paramiko` for SSH and `qrcode`/`pillow` for output; no `openssl`, no `nc`, no system tools required on any platform
- **Cross-platform** — macOS, Windows (Git Bash), Linux; auto-detects `python3`/`python`/`py` command; MSYS2 path conversion for panel paths handled automatically in-script (no `MSYS_NO_PATHCONV` needed)
- **Cross-distro VPS** — auto-detects Debian/Ubuntu, RHEL/Rocky/CentOS, Arch and registers the correct systemd service file
- **Smart SNI selection** — latency-tests 20 domains across Microsoft, Apple, NVIDIA, AWS, Cloudflare, Akamai and picks the fastest
- **Secure by default** — random panel credentials generated on every run; panel port and sub server bound to `127.0.0.1` only after setup (never exposed to the internet)
- **SSH tunnel for panel access** — manage 3x-ui via `ssh -L` forwarding; no public management port
- **Config saved locally** — credentials and all VLESS links written to `~/.vps/<IP>.txt` after each run
- **QR code as PNG** — saves `~/.vps/<IP>_<protocol>_qr.png` and copies to `~/Downloads/<node>_<protocol>_qr.png` (if Downloads exists); reliable on Windows where GBK terminals can't render block characters
- **No /tmp staging** — all API calls made directly from local machine; nothing sensitive is written to `/tmp`

## Client Compatibility

| Client | Platform | Status |
|--------|----------|--------|
| Shadowrocket | iOS / macOS | ✅ Verified |
| v2rayN | Windows / macOS | ✅ Compatible — keep xray-core updated to latest |
| NekoBox | Android | ✅ Compatible |
| Hiddify | macOS / Android | ✅ Compatible |

## Tested VPS Distros

Verified end-to-end across five distros:

| Distro | Version | Arch | Notes |
|--------|---------|------|-------|
| Debian | 12 (Bookworm) | x86_64 | Auto-issues Let's Encrypt IP certificate (6-day, auto-renews) |
| CentOS Stream | 9 | x86_64 | `ID_LIKE="rhel fedora"` — uses `.rhel` service file |
| Ubuntu | 22.04 LTS | x86_64 | Uses `.debian` service file |
| Rocky Linux | 9 | x86_64 | Uses `.rhel` service file |
| AlmaLinux | 10 | x86_64 | `ID_LIKE="rhel"` — uses `.rhel` service file |

Other distros supported by 3x-ui (Arch, etc.) should work via the same auto-detection logic, but have not been tested with this skill directly.

## Prerequisites

**Local machine:**
- Python 3.7+ (pre-installed on macOS and most Linux; download at [python.org](https://python.org) for Windows)
- `pip install paramiko qrcode pillow cryptography`

**VPS:**
- Fresh install with root SSH access
- Supported distros: Rocky Linux, AlmaLinux, CentOS Stream, Ubuntu, Debian, Arch (anything 3x-ui supports)
- At least one of these ports open: **443**, 8443, 2096, 2083, 2087, 8080, 8880 (the skill scans and picks automatically)
- Port **22** open (SSH management — the only port you need long-term)

## Installation

**Option 1 — One command:**

```bash
pip install paramiko qrcode pillow cryptography
curl -fsSL https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/dev/install.sh | bash
```

**Option 2 — Ask Claude to install it for you:**

Copy the message below and send it to Claude Code:

```
Please install or upgrade the /3xui-autosetup skill by running:
curl -fsSL https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/dev/install.sh | bash
```

Claude will run the install script and confirm when done.

## Usage

```
/3xui-autosetup <ip> <root-password>
/3xui-autosetup <ip> <ssh-port> <root-password>
/3xui-autosetup <ip> <ssh-port> <root-password> | <user:gb,...>
```

- **2 arguments** — IP + password; port 22 is probed automatically (3 retries, 2s apart). If detected open, no question asked. If closed, the skill asks for the port.
- **3 arguments** — IP + SSH port + password; all three are set directly, no prompts for connection info.
- **Node display name** — always asked during Stage 1, regardless of arguments. Defaults to `vless-reality`.
- **User management** — optionally pass after `|` as `name:gb` pairs (e.g. `friend:200,family:0`); if omitted, asked interactively during Stage 1. The owner account (unlimited) is always created automatically.

**Examples:**

```
/3xui-autosetup 1.2.3.4 mypassword
/3xui-autosetup 1.2.3.4 22 mypassword
/3xui-autosetup 1.2.3.4 22 mypassword | friend:200
/3xui-autosetup 1.2.3.4 22 mypassword | friend:200,family:0,colleague:100
```

The skill walks through five stages automatically:

```
Stage 0 — Detect Python command (python3/python/py); check and install deps
Stage 1 — Probe SSH port 22; scan outbound ports to select proxy port;
           ask for node name and user list (owner + optional extra users with GB limits)
Stage 2 — Install 3x-ui; auto-register systemd service; reset panel credentials;
           move sub server to 127.0.0.1:4096 to free the proxy port for xray
Stage 3 — Latency-test 20 SNI domains; pick the fastest
Stage 4 — Generate X25519 keypair + UUID per user locally; connect to VPS panel;
           create VLESS+Reality inbound with all users; verify xray started;
           restrict panel to localhost
Stage 5 — Print all VLESS links with [VLESS-Reality] prefix + QR codes
           (one PNG per user: <node>_vless-reality_qr.png);
           save all links to ~/.vps/<IP>.txt
```

## Security Model

After setup completes, the attack surface is minimal:

| Port | Exposure | Purpose |
|------|----------|---------|
| 22 | Public | SSH (management) |
| `<proxy port>` | Public | VLESS+Reality proxy traffic |
| panel port | **Localhost only** | 3x-ui panel (unreachable from internet) |
| 4096 | **Localhost only** | 3x-ui subscription service |

The panel and sub server are both bound to `127.0.0.1`. No firewall rules needed — the ports disappear from public interfaces entirely.

**To access the panel later:**

```bash
ssh -L <panel-port>:127.0.0.1:<panel-port> root@<IP>
# then open http://localhost:<panel-port>/<webbasepath> in your browser
```

Credentials are saved to `~/.vps/<IP>.txt` on your local machine (chmod 600).

## What Gets Configured

- **Protocol**: VLESS + Reality + `xtls-rprx-vision`
- **Port**: auto-selected based on what the provider allows (443 preferred)
- **SNI**: auto-selected (lowest latency from 20-domain test pool)
- **Fingerprint**: Chrome
- **Keypair**: X25519, generated fresh each run via Python `cryptography` library (locally, no `openssl` subprocess)
- **Users**: one or more clients, each with a unique UUID and optional traffic quota; added via `addClient` API

## How It Works

All SSH interaction uses **paramiko** — a pure-Python SSH client. No `sshpass`, no shell piping, no system dependencies beyond Python itself.

```
Local machine                          VPS
     │                                  │
     ├─ paramiko: install 3x-ui ───────▶│
     ├─ SFTP: fix sub server port ─────▶│  (writes subPort=4096 to x-ui.db)
     ├─ paramiko: latency test ────────▶│
     │                                  │
     ├─ generate X25519 keypair (local) │
     ├─ generate UUID per user (local)  │
     ├─ HTTPS POST /login ─────────────▶│  (panel still on *:PORT before restriction)
     ├─ HTTPS POST /inbounds/add ──────▶│  (all users included)
     ├─ paramiko: listenIP 127.0.0.1 ──▶│
     ├─ paramiko: check journalctl ────▶│  (verify xray started OK)
     │                                  │
     └─ print [VLESS-Reality] links     │
        + per-user QR PNGs              │
```

Stage 4 runs all panel API calls directly from the local machine over HTTPS — no script is uploaded or executed on the VPS.

The `addClient` API is called separately from `inbounds/add` — this is intentional. Creating clients inline via `inbounds/add` leaves `client_traffics.enable = 0` in the 3x-ui database, causing xray to silently drop all clients on restart. Using `addClient` sets `enable = 1` correctly.

## Recovering from Failures

**Stage 2 interrupted (install incomplete):** Re-run `vps_postinstall.py` — it detects distro, registers the correct service file, starts x-ui, resets credentials, and fixes the sub server port in one pass.

**Stage 4 failed (API error):** Re-run `vps_run_setup.py` — it is idempotent (removes any existing inbound on the same port before recreating).

**xray not starting / can't browse:** The most common cause is the sub server occupying the proxy port. Check with:
```bash
# Should show xray-linux-amd64, not x-ui
ss -tlnp | grep <proxy-port>

# Look for "Sub server running HTTP on [::]:2096" followed by xray bind errors
journalctl -u x-ui -n 30
```
Re-running `vps_postinstall.py` fixes this automatically.

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

`/3xui-autosetup` 是一个 [Claude Code](https://claude.ai/code) slash command，一条命令完成 VLESS+Reality 节点全流程搭建——SSH 登录、安装 3x-ui、扫描可用端口、SNI 延迟测试、多用户 API 配置、终端输出二维码，全程无需打开浏览器。

**唯一依赖：Python 3 + `pip install paramiko qrcode pillow cryptography`。无需 brew、WSL 或任何系统工具。**

### 为什么选 3x-ui + xray-core？

Reality 协议有两套实现：**xray-core** 和 **sing-box**，两者不兼容。主流客户端（Shadowrocket、v2rayN、NekoBox）均使用 xray-core，因此服务端也必须使用 xray-core。3x-ui 内嵌 xray-core 并提供完整 REST API，是目前自动化配置的最佳选择。

> s-ui 使用 sing-box 内核，与基于 xray-core 的客户端存在 Reality 协议不兼容问题，不要混用。

### 功能特点

- **一条命令搞定** — 传入 IP 和密码，其余全自动（端口自动探测）
- **外网端口扫描** — 阶段一自动扫描服务商实际放行的端口（443、8443、2096 等），自动选最优代理端口，无需手动查防火墙设置
- **多用户支持** — 一次配置可创建多个用户；每个用户独立 UUID，可设置独立流量配额（如 200 GB），自用账户无限流量
- **分用户二维码** — 每个用户生成独立 PNG，文件名格式 `<节点名>_vless-reality_qr.png`；订阅链接统一加 `[VLESS-Reality]` 前缀标注
- **SSH 端口自动探测** — 用 Python socket 探测 22 端口是否开放（3 次重试，每次间隔 2 秒，兼容刚重置的 VPS）；无需 `nc`，Windows / macOS / Linux 全平台可用
- **Sub server 端口修复** — 自动将 3x-ui 订阅服务移至 `127.0.0.1:4096`，彻底避免其抢占 xray 代理端口
- **启动验证** — 最终重启后检查 `journalctl` 日志确认 xray 正常启动，不正常立即提示，不会静默输出失效链接
- **自定义节点名称** — 可以给节点起任意名称（如 `Tokyo-01`），直接显示在 Shadowrocket、v2rayN 等客户端的节点列表里
- **纯 Python 实现** — paramiko 负责 SSH，qrcode + pillow 输出二维码；无需 `openssl`、`nc` 或任何系统工具
- **跨平台本地运行** — macOS、Windows（Git Bash）、Linux 均可；自动探测 `python3` / `python` / `py` 命令；Git Bash 下 MSYS2 路径转换由脚本内部自动处理
- **跨发行版 VPS** — 自动检测 Debian/Ubuntu、RHEL/Rocky/CentOS/CentOS Stream、Arch，注册对应的 systemd service 文件
- **智能 SNI 选择** — 对 20 个域名做延迟测试，自动选最快的
- **安全默认配置** — 每次运行随机生成面板凭据；面板和订阅服务在配置完成后均绑定到 `127.0.0.1`，从公网彻底消失
- **二维码 PNG 输出** — 每用户独立保存 `~/.vps/<IP>_<协议>_qr.png`，同时复制到 `~/Downloads/`
- **无 /tmp 暂存** — 所有 API 调用直接从本地发出，不向 VPS 上传或执行任何脚本
- **本地存档** — 所有节点链接和面板凭据写入 `~/.vps/<IP>.txt`（权限 600）

### 已验证系统

| 系统 | 版本 | 架构 | 备注 |
|------|------|------|------|
| Debian | 12 (Bookworm) | x86_64 | 自动申请 Let's Encrypt IP 证书（6 天有效期，自动续期） |
| CentOS Stream | 9 | x86_64 | `ID_LIKE="rhel fedora"`，使用 `.rhel` service 文件 |
| Ubuntu | 22.04 LTS | x86_64 | 使用 `.debian` service 文件 |
| Rocky Linux | 9 | x86_64 | 使用 `.rhel` service 文件 |
| AlmaLinux | 10 | x86_64 | `ID_LIKE="rhel"`，使用 `.rhel` service 文件 |

其他 3x-ui 支持的发行版（Arch 等）理论上同样可用，但尚未经过实测。

### 客户端兼容性

| 客户端 | 平台 | 状态 |
|--------|------|------|
| Shadowrocket | iOS / macOS | ✅ 已验证 |
| v2rayN | Windows / macOS | ✅ 兼容 — 需保持 xray-core 为最新版本 |
| NekoBox | Android | ✅ 兼容 |
| Hiddify | macOS / Android | ✅ 兼容 |

### 安装

**方式一 — 一条命令：**

```bash
pip install paramiko qrcode pillow cryptography
curl -fsSL https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/dev/install.sh | bash
```

**方式二 — 让 Claude 帮你安装：**

把下面这句话复制给 Claude Code：

```
请帮我运行以下命令安装或升级 /3xui-autosetup skill：
curl -fsSL https://raw.githubusercontent.com/TIANYI005/3xui-autosetup/dev/install.sh | bash
```

### 使用

```
/3xui-autosetup <IP地址> <root密码>
/3xui-autosetup <IP地址> <SSH端口> <root密码>
/3xui-autosetup <IP地址> <SSH端口> <root密码> | <昵称:GB,...>
```

- **传 2 个参数**（IP + 密码）：自动探测 22 端口是否开放，开放则直接跳过端口询问；探测失败时会询问端口号
- **传 3 个参数**（IP + 端口 + 密码）：连接信息全部来自参数，不询问
- **`|` 后接用户管理**：格式为 `昵称:GB`，逗号分隔多个用户；`GB=0` 表示无限；自用 owner 账户始终自动创建。省略 `|` 则阶段一交互询问
- **节点名称**：阶段一询问（默认 `vless-reality`）

**示例：**

```
/3xui-autosetup 1.2.3.4 mypassword
/3xui-autosetup 1.2.3.4 22 mypassword
/3xui-autosetup 1.2.3.4 22 mypassword | friend:200
/3xui-autosetup 1.2.3.4 22 mypassword | friend:200,family:0,colleague:100
```

自动走完以下五个阶段：

```
阶段零 — 探测可用的 Python 命令；检查并安装依赖（paramiko、qrcode、pillow、cryptography）
阶段一 — 探测 SSH 端口；扫描外网可达代理端口并自动选择；
          询问节点名称和用户列表（owner 无限 + 可选多用户含 GB 配额）
阶段二 — 安装 3x-ui；注册 systemd service；重置面板凭据；
          将订阅服务移至 127.0.0.1:4096，释放代理端口给 xray
阶段三 — 对 20 个域名做延迟测试，选最快的作为 SNI
阶段四 — 本地生成 X25519 密钥对、每用户独立 UUID；
          通过 API 创建含所有用户的 VLESS+Reality inbound；
          验证 xray 正常启动；将面板限制为仅本地访问
阶段五 — 输出所有用户的 [VLESS-Reality] 链接 + 分用户二维码 PNG；
          凭据和链接保存到 ~/.vps/<IP>.txt
```

### 安全设计

配置完成后的暴露面：

| 端口 | 可见范围 | 用途 |
|------|----------|------|
| 22 | 公网 | SSH 管理 |
| `<代理端口>` | 公网 | VLESS 代理流量 |
| 面板端口 | **仅 localhost** | 3x-ui 面板，公网不可达 |
| 4096 | **仅 localhost** | 3x-ui 订阅服务 |

**后续访问面板：**

```bash
ssh -L <面板端口>:127.0.0.1:<面板端口> root@<IP>
# 建立隧道后浏览器打开 http://localhost:<面板端口>/<路径>
```

### 故障恢复

**阶段二中断：** 重新运行 `vps_postinstall.py`，它会自动修复 service、凭据和 sub server 端口。

**xray 无法上网（Sub server 占端口）：** 这是 3x-ui v2.x 的已知问题。重新运行 `vps_postinstall.py` 即可自动修复。手动排查：

```bash
# 检查是否是 sub server 占用了代理端口（显示 x-ui 而非 xray-linux-amd64 则说明有问题）
ss -tlnp | grep <代理端口>

# 查看日志确认
journalctl -u x-ui -n 30
```

**阶段四失败：** 重新运行 `vps_run_setup.py`，脚本幂等（会先删除同端口的旧 inbound 再重建）。

**忘记面板密码：** 查 `~/.vps/<IP>.txt`，或 SSH 进 VPS 执行：

```bash
/usr/local/x-ui/x-ui setting -username admin -password <新密码>
systemctl restart x-ui
```

### 技术细节：为什么用 addClient 而不是 inbounds/add 内联创建？

3x-ui 存在一个已知问题：通过 `inbounds/add` 接口内联创建客户端时，SQLite 数据库中 `client_traffics.enable` 会被设为 `0`，导致 x-ui 重启后 xray 配置中 clients 变为 `null`，所有客户端连接都会静默失败。

本 skill 的解决方案：先用 `inbounds/add` 创建含所有 client 的 inbound（一次性写入，避免多次 API 调用），再单独调用 `addClient` 接口——后者会正确设置 `enable=1`，重启后客户端永久有效。

---

<div align="center">
<sub>MIT License · Built with Claude Code</sub>
</div>
