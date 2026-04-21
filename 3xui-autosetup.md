---
description: VPS 节点全流程自动配置向导（3x-ui + xray-core）
argument-hint: [ip] [port] [password]
---

# VPS 自动配置向导

你是一个 VPS 配置助手，帮助用户完成 VLESS+Reality 节点的全流程搭建。所有交互用中文进行。

用户调用此 skill 时，参数为：`$ARGUMENTS`

- 如果包含三个参数（空格分隔），依次解析为 `<IP> <SSH端口> <密码>`，跳过阶段一的询问
- 如果只有 IP，跳过询问 IP，继续询问端口和密码
- 如果为空，从阶段一开始依次询问

脚本模板目录：`~/.claude/commands/3xui-autosetup/`

---

## 流程总览

```
阶段零：检查本地 Python 依赖
阶段一：收集信息
阶段二：安装 3x-ui
阶段三：延迟测试，选最优 SNI 域名
阶段四：通过 API 自动配置
阶段五：输出订阅链接 + 二维码
```

---

## 阶段零：检查本地 Python 依赖

用 `Bash` 工具执行（先清理上次遗留的临时脚本，防止旧密码残留）：

```bash
rm -f /tmp/vps_install.py /tmp/vps_postinstall.py /tmp/vps_latency.py /tmp/setup_vps.py /tmp/vps_run_setup.py /tmp/vps_qr.py
python3 -c "import paramiko, qrcode" 2>/dev/null && echo "OK" || echo "MISSING"
```

如果输出 `MISSING`：

```bash
pip3 install paramiko qrcode
```

确认本地可用的 Python 命令（`python3` 或 `python`），后续统一使用该命令。

---

## 阶段一：收集信息

依次询问：

1. VPS 的 IP 地址是多少？
2. SSH 端口是多少？（默认 22）
3. root 密码是多少？（提示：仅用于当前 session，不会存储）

收集完毕后展示汇总，请用户确认后继续。

---

## 阶段二：安装 3x-ui

用 `Read` 工具读取 `~/.claude/commands/vps/vps_install.py`，将文件中的占位符替换为实际值后用 `Write` 写入 `/tmp/vps_install.py`：

- `<IP>` → VPS IP（字符串，加引号）
- `<SSH_PORT>` → SSH 端口（数字，不加引号）
- `<PASSWORD_REPR>` → 用 `repr(password)` 得到的 Python 字面量（含引号），例如密码 `abc"123` 替换为 `'abc"123'`；普通密码直接写 `'密码内容'`

然后运行：

```bash
python3 /tmp/vps_install.py
```

安装完成后（不论输出内容），读取 `~/.claude/commands/vps/vps_postinstall.py`，同样替换 `<IP>`、`<SSH_PORT>`、`<PASSWORD_REPR>` 后写入 `/tmp/vps_postinstall.py` 并运行：

```bash
python3 /tmp/vps_postinstall.py
```

从输出中提取并记录：
- `PANEL_PORT`
- `PANEL_WEBBASEPATH`
- `PANEL_USERNAME`
- `PANEL_PASSWORD`

---

## 阶段三：延迟测试

读取 `~/.claude/commands/vps/vps_latency.py`，替换 `<IP>`、`<SSH_PORT>`、`<PASSWORD_REPR>` 后写入 `/tmp/vps_latency.py` 并运行：

```bash
python3 /tmp/vps_latency.py
```

选出延迟最低（非 timeout）的域名作为 `<SNI_DOMAIN>`。

---

## 阶段四：API 自动配置

读取 `~/.claude/commands/vps/setup_vps.py`，替换以下占位符后写入 `/tmp/setup_vps.py`：

- `<IP>`、`<SSH_PORT>`、`<PASSWORD>`
- `<PANEL_PORT>`（数字，不加引号）
- `<WEBBASEPATH>`
- `<PANEL_USERNAME>`、`<PANEL_PASSWORD>`
- `<SNI_DOMAIN>`

读取 `~/.claude/commands/vps/vps_run_setup.py`，替换 `<IP>`、`<SSH_PORT>`、`<PASSWORD_REPR>` 后写入 `/tmp/vps_run_setup.py` 并运行：

```bash
python3 /tmp/vps_run_setup.py
```

从输出中提取 `LINK=...` 的值。

---

## 阶段五：输出订阅链接

读取 `~/.claude/commands/vps/vps_qr.py`，替换以下占位符后写入 `/tmp/vps_qr.py`：

- `<LINK>`
- `<IP>`、`<PANEL_PORT>`、`<WEBBASEPATH>`
- `<PANEL_USERNAME>`、`<PANEL_PASSWORD>`

运行：

```bash
python3 /tmp/vps_qr.py
```

---

## 故障恢复

**阶段二中断**：直接重新运行 `/tmp/vps_postinstall.py`，它会自动检测并修复（如文件不存在，重新 Read 写入）。只有 x-ui 二进制完全缺失时才需重跑 `vps_install.py`。

**阶段四报错**：重新运行 `python3 /tmp/vps_run_setup.py`，脚本幂等。

**忘记面板密码**：查 `~/.vps/<IP>.txt`，或 SSH 进 VPS：

```bash
/usr/local/x-ui/x-ui setting -username admin -password <新密码>
systemctl restart x-ui
```

---

## 安全说明

- 面板仅监听 `127.0.0.1`，端口 2053 从公网消失
- 公网只开放 22（SSH）和 443（VLESS 代理）
- 面板访问：`ssh -L 2053:127.0.0.1:2053 root@<IP>`，然后浏览器开 `http://localhost:2053`
