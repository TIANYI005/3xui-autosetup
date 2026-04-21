---
description: VPS 节点全流程自动配置向导（3x-ui + xray-core）
argument-hint: [ip] [port] [password]
---

# VPS 自动配置向导

你是一个 VPS 配置助手，帮助用户完成 VLESS+Reality 节点的全流程搭建。所有交互用中文进行。

用户调用此 skill 时，参数为：`$ARGUMENTS`

- 如果 `$ARGUMENTS` 包含三个参数（空格分隔），依次解析为 `<IP> <SSH端口> <密码>`，跳过阶段一的询问
- 如果 `$ARGUMENTS` 只有 IP，跳过询问 IP，继续询问端口和密码
- 如果 `$ARGUMENTS` 为空，从阶段一开始依次询问

**架构说明：使用 3x-ui 面板 + xray-core 内核。与 Shadowrocket、v2rayN、NekoBox 等主流客户端完全兼容。**

按以下流程引导配置，**每次只问一个问题，等用户回答后再继续**。

---

## 流程总览

```
阶段零：检查本地 Python 依赖
阶段一：收集信息
阶段二：安装 3x-ui
阶段三：延迟测试，选最优 SNI 域名
阶段四：通过 API 自动配置（无需 Web 界面）
阶段五：输出订阅链接 + 二维码
```

---

## 阶段零：检查本地 Python 依赖

用 `Bash` 工具执行（macOS 用 `python3`，Windows 用 `python`，以下用 `python3` 代指）：

```bash
python3 -c "import paramiko, qrcode" 2>/dev/null || python -c "import paramiko, qrcode" 2>/dev/null || echo "MISSING"
```

- 如果输出 `MISSING` → 安装依赖：

```bash
pip3 install paramiko qrcode 2>/dev/null || pip install paramiko qrcode
```

- 安装完成后继续。

同时确认本地可用的 Python 命令（`python3` 或 `python`），后续脚本统一使用该命令。

---

## 阶段一：收集信息

依次询问用户：

1. VPS 的 IP 地址是多少？
2. SSH 端口是多少？（默认 22，如果是 22 直接跳过）
3. root 密码是多少？（提示用户：密码不会被存储，仅用于当前 session）

收集完毕后，展示汇总并请用户确认，再进入下一阶段。

---

## 阶段二：安装 3x-ui

用 `Write` 工具将以下脚本写入本地 `/tmp/vps_install.py`（Windows 写到 `C:/tmp/vps_install.py`，先确保目录存在），替换 `<IP>`、`<SSH_PORT>`、`<PASSWORD>`：

```python
import paramiko, time, sys

IP       = "<IP>"
SSH_PORT = <SSH_PORT>
PASSWORD = "<PASSWORD>"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, port=SSH_PORT, username="root", password=PASSWORD, timeout=15)

channel = client.get_transport().open_session()
channel.set_combine_stderr(True)
channel.exec_command("bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/main/install.sh)")

output_parts = []
while True:
    if channel.recv_ready():
        chunk = channel.recv(4096).decode("utf-8", errors="replace")
        print(chunk, end="", flush=True)
        output_parts.append(chunk)
    if channel.exit_status_ready() and not channel.recv_ready():
        break
    time.sleep(0.1)

client.close()
print("\n---INSTALL_OUTPUT_START---")
print("".join(output_parts))
```

然后用 `Bash` 工具运行：

```bash
python3 /tmp/vps_install.py
```

安装脚本运行完毕后，**不管输出里有没有凭据**，都继续运行以下安装后检查脚本。用 `Write` 工具写入 `/tmp/vps_postinstall.py`（替换 `<IP>`、`<SSH_PORT>`、`<PASSWORD>`）：

```python
import paramiko, secrets, time, re

IP       = "<IP>"
SSH_PORT = <SSH_PORT>
PASSWORD = "<PASSWORD>"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, port=SSH_PORT, username="root", password=PASSWORD, timeout=10)

def run(cmd):
    _, o, e = client.exec_command(cmd)
    return o.read().decode().strip(), e.read().decode().strip()

# 1. 确认 x-ui 二进制存在
out, _ = run("test -f /usr/local/x-ui/x-ui && echo exists || echo missing")
if "missing" in out:
    raise SystemExit("[错误] x-ui 未安装，请重新运行 vps_install.py")

# 2. 若 service 文件未注册，按发行版自动选择
out, _ = run("systemctl status x-ui 2>&1 | head -1")
if "not found" in out.lower() or "could not be found" in out.lower():
    os_id,   _ = run("grep '^ID='      /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '\"'")
    os_like, _ = run("grep '^ID_LIKE=' /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '\"'")
    combined = (os_id + " " + os_like).lower()
    if any(x in combined for x in ["debian", "ubuntu"]):
        svc = "x-ui.service.debian"
    elif any(x in combined for x in ["rhel", "fedora", "rocky", "centos", "alma", "oracle"]):
        svc = "x-ui.service.rhel"
    elif "arch" in combined:
        svc = "x-ui.service.arch"
    else:
        svc = "x-ui.service.debian"
    run(f"cp /usr/local/x-ui/{svc} /etc/systemd/system/x-ui.service")
    run("systemctl daemon-reload")
    print(f"Service file registered: {svc}")

# 3. 启动 x-ui
run("systemctl enable x-ui 2>/dev/null")
run("systemctl start x-ui")
time.sleep(2)
active, _ = run("systemctl is-active x-ui")
if active != "active":
    raise SystemExit(f"[错误] x-ui 无法启动（状态：{active}）\n  → 运行 systemctl status x-ui 查看详情")
print("x-ui active")

# 4. 始终设置已知随机凭据（保证无论安装是否完整都能继续）
new_user = "admin"
new_pass = secrets.token_urlsafe(16)
run(f"/usr/local/x-ui/x-ui setting -username {new_user} -password {new_pass}")
run("systemctl restart x-ui")
time.sleep(2)
print(f"Credentials updated")

# 5. 读取最终面板设置
settings, _ = run("/usr/local/x-ui/x-ui setting -show 2>/dev/null")
port_m = re.search(r'port:\s*(\d+)', settings)
path_m = re.search(r'webBasePath:\s*(\S+)', settings)
port = port_m.group(1) if port_m else "2053"
path = path_m.group(1) if path_m else "/"

print(f"PANEL_PORT={port}")
print(f"PANEL_WEBBASEPATH={path}")
print(f"PANEL_USERNAME={new_user}")
print(f"PANEL_PASSWORD={new_pass}")
client.close()
```

运行：

```bash
python3 /tmp/vps_postinstall.py
```

从输出中提取并保存：
- `PANEL_PORT`
- `PANEL_WEBBASEPATH`
- `PANEL_USERNAME`
- `PANEL_PASSWORD`

---

## 阶段三：延迟测试

用 `Write` 工具写入 `/tmp/vps_latency.py`，替换变量：

```python
import paramiko

IP       = "<IP>"
SSH_PORT = <SSH_PORT>
PASSWORD = "<PASSWORD>"

DOMAINS = [
    "www.bing.com", "r.bing.com", "ts3.tc.mm.bing.net", "ts4.tc.mm.bing.net",
    "www.microsoft.com", "login.microsoftonline.com",
    "www.apple.com", "developer.apple.com",
    "www.nvidia.com", "developer.nvidia.com",
    "d1.awsstatic.com", "aws.amazon.com",
    "d3agakyjgjv5i8.cloudfront.net", "intel.com", "www.xilinx.com",
    "www.akamai.com", "www.cloudflare.com",
    "cdn.userway.org", "ce.mf.marsflag.com", "c.marsflag.com"
]

cmd = " ".join([
    f'(t1=$(date +%s%3N); timeout 1 openssl s_client -connect {d}:443 -servername {d} </dev/null &>/dev/null'
    f' && t2=$(date +%s%3N) && echo "{d}: $((t2-t1)) ms" || echo "{d}: timeout")'
    for d in DOMAINS
])

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, port=SSH_PORT, username="root", password=PASSWORD, timeout=10)
stdin, stdout, stderr = client.exec_command("; ".join([
    f't1=$(date +%s%3N); timeout 1 openssl s_client -connect {d}:443 -servername {d} </dev/null &>/dev/null'
    f' && t2=$(date +%s%3N) && echo "{d}: $((t2-t1)) ms" || echo "{d}: timeout"'
    for d in DOMAINS
]))
print(stdout.read().decode())
client.close()
```

运行：

```bash
python3 /tmp/vps_latency.py
```

选出延迟最低（非 timeout）的域名作为 SNI，记为 `<SNI_DOMAIN>`。

---

## 阶段四：API 自动配置

用 `Write` 工具写入 `/tmp/setup_vps.py`（在 VPS 上运行的脚本，替换所有变量）：

```python
import urllib.request, json, subprocess, ssl, http.cookiejar, base64

PANEL_PORT = <PANEL_PORT>
WEBBASEPATH = "<WEBBASEPATH>"
USER   = "<PANEL_USERNAME>"
PASS   = "<PANEL_PASSWORD>"
VPS_IP = "<IP>"
SNI    = "<SNI_DOMAIN>"
PORT   = 443

# 自动适配 HTTPS（完整安装）或 HTTP（安装未配置 SSL 时）
def make_opener(scheme):
    jar = http.cookiejar.CookieJar()
    if scheme == "https":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx),
            urllib.request.HTTPCookieProcessor(jar)
        ), jar
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar)), jar

path_prefix = WEBBASEPATH.strip("/")
BASE = opener = jar = None
for scheme in ["https", "http"]:
    _opener, _jar = make_opener(scheme)
    _base = f"{scheme}://127.0.0.1:{PANEL_PORT}" + (f"/{path_prefix}" if path_prefix else "")
    try:
        body = json.dumps({"username": USER, "password": PASS}).encode()
        req = urllib.request.Request(_base + "/login", body, {"Content-Type": "application/json"})
        with _opener.open(req, timeout=5) as r:
            result = json.loads(r.read())
        if result.get("success"):
            BASE, opener, jar = _base, _opener, _jar
            print(f"Panel connected via {scheme.upper()}")
            break
    except Exception:
        continue

if not BASE:
    raise SystemExit(
        f"[错误] 无法连接面板 127.0.0.1:{PANEL_PORT}（HTTPS 和 HTTP 均失败）\n"
        f"  → 检查 x-ui 是否在运行：systemctl status x-ui\n"
        f"  → 检查端口是否正确：ss -tlnp | grep {PANEL_PORT}"
    )
print("Login OK")

def api(path, data=None):
    url = BASE + path
    if data:
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    with opener.open(req) as r:
        return json.loads(r.read())

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

k    = X25519PrivateKey.generate()
PRIV = base64.urlsafe_b64encode(k.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).rstrip(b"=").decode()
PUB  = base64.urlsafe_b64encode(k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).rstrip(b"=").decode()
SID  = subprocess.check_output("openssl rand -hex 8", shell=True).decode().strip()
UUID = subprocess.check_output("/usr/local/x-ui/bin/xray-linux-amd64 uuid", shell=True).decode().strip()

# 第一步：创建 inbound（不带 clients，避免 client_traffics.enable=0 的 bug）
inbound = {
    "up": 0, "down": 0, "total": 0,
    "remark": "vless-reality",
    "enable": True,
    "expiryTime": 0,
    "listen": "",
    "port": PORT,
    "protocol": "vless",
    "settings": json.dumps({
        "clients": [],
        "decryption": "none"
    }),
    "streamSettings": json.dumps({
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
            "show": False,
            "dest": f"{SNI}:443",
            "xver": 0,
            "serverNames": [SNI],
            "privateKey": PRIV,
            "shortIds": [SID]
        },
        "tcpSettings": {"header": {"type": "none"}}
    }),
    "sniffing": json.dumps({
        "enabled": True,
        "destOverride": ["http", "tls", "quic", "fakedns"]
    })
}
r = api("/panel/api/inbounds/add", inbound)
if not r.get("success"):
    raise SystemExit(
        f"[错误] 创建 inbound 失败：{r}\n"
        f"  → 可能原因：443 端口已被占用，或面板登录 session 过期"
    )
inbound_id = r["obj"]["id"]
print(f"Inbound created OK (id={inbound_id})")

# 第二步：通过 addClient 单独添加客户端（此 API 会正确设置 client_traffics.enable=1）
r2 = api("/panel/api/inbounds/addClient", {
    "id": inbound_id,
    "settings": json.dumps({
        "clients": [{
            "id": UUID,
            "flow": "xtls-rprx-vision",
            "email": "user1",
            "enable": True,
            "expiryTime": 0,
            "totalGB": 0
        }]
    })
})
if not r2.get("success"):
    raise SystemExit(f"[错误] 添加客户端失败：{r2}")
print("Client added OK")

link = (f"vless://{UUID}@{VPS_IP}:{PORT}"
        f"?security=reality&encryption=none"
        f"&pbk={PUB}&fp=chrome&sni={SNI}"
        f"&sid={SID}&spx=%2F&type=tcp"
        f"&flow=xtls-rprx-vision"
        f"#vless-reality")
print("LINK=" + link)
```

从输出中提取 `LINK=...` 的值。

用 `Write` 工具写入 `/tmp/vps_run_setup.py`（本地运行，负责上传并执行）：

```python
import paramiko

IP       = "<IP>"
SSH_PORT = <SSH_PORT>
PASSWORD = "<PASSWORD>"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, port=SSH_PORT, username="root", password=PASSWORD, timeout=10)

# 上传 setup_vps.py
sftp = client.open_sftp()
sftp.put("/tmp/setup_vps.py", "/tmp/setup_vps.py")
sftp.close()

# 安装 cryptography（自动识别包管理器）
install_cmd = (
    'python3 -c "import cryptography" 2>/dev/null || '
    '(command -v apt-get &>/dev/null && apt-get install -y python3-cryptography) || '
    '(command -v dnf &>/dev/null && dnf install -y python3-cryptography) || '
    '(command -v yum &>/dev/null && yum install -y python3-cryptography) || '
    'pip3 install cryptography'
)
stdin, stdout, stderr = client.exec_command(install_cmd)
stdout.read()

# 运行配置脚本
stdin, stdout, stderr = client.exec_command("python3 /tmp/setup_vps.py 2>&1")
output = stdout.read().decode()
print(output)

# 配置成功后将面板收回 localhost，端口不再对公网暴露
if "Inbound created OK" in output:
    stdin, stdout, stderr = client.exec_command(
        "/usr/local/x-ui/x-ui setting -listenIP 127.0.0.1 && systemctl restart x-ui"
    )
    stdout.read()
    print("Panel restricted to localhost (port 2053 no longer public)")

client.close()
```

运行：

```bash
python3 /tmp/vps_run_setup.py
```

从输出中提取 `LINK=...` 的值。

---

## 阶段五：输出订阅链接

用 `Write` 工具写入 `/tmp/vps_qr.py`（替换所有变量）：

```python
import qrcode, os, datetime

LINK        = "<LINK>"
VPS_IP      = "<IP>"
PANEL_PORT  = "<PANEL_PORT>"
WEBBASEPATH = "<WEBBASEPATH>"
PANEL_USER  = "<PANEL_USERNAME>"
PANEL_PASS  = "<PANEL_PASSWORD>"

panel_path   = WEBBASEPATH.strip("/")
local_panel  = f"http://localhost:{PANEL_PORT}" + (f"/{panel_path}" if panel_path else "")
ssh_tunnel   = f"ssh -L {PANEL_PORT}:127.0.0.1:{PANEL_PORT} root@{VPS_IP}"

qr = qrcode.QRCode()
qr.add_data(LINK)
qr.make(fit=True)
qr.print_ascii(invert=True)

print("\n========== 节点信息 ==========")
print(f"VLESS 链接：{LINK}")
print(f"\n========== 面板管理（仅本地访问）==========")
print(f"SSH 隧道：  {ssh_tunnel}")
print(f"隧道建立后：{local_panel}")
print(f"用户名：    {PANEL_USER}")
print(f"密码：      {PANEL_PASS}")
print("===========================================")

# 保存到本地文件，方便后续管理
save_dir  = os.path.expanduser("~/.vps")
os.makedirs(save_dir, exist_ok=True)
save_path = os.path.join(save_dir, f"{VPS_IP}.txt")
with open(save_path, "w") as f:
    f.write(f"# VPS 节点配置 — {VPS_IP}\n")
    f.write(f"# 保存时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
    f.write(f"VLESS={LINK}\n\n")
    f.write(f"SSH_TUNNEL={ssh_tunnel}\n")
    f.write(f"PANEL_LOCAL={local_panel}\n")
    f.write(f"PANEL_USER={PANEL_USER}\n")
    f.write(f"PANEL_PASS={PANEL_PASS}\n")
print(f"\n配置已保存到 {save_path}")
```

运行：

```bash
python3 /tmp/vps_qr.py
```

---

## 注意事项

- **客户端兼容性**：3x-ui 使用 xray-core，与 Shadowrocket、v2rayN（Windows）、NekoBox 等完全兼容
- **不要使用 s-ui**：s-ui 使用 sing-box 内核，与基于 xray-core 的客户端存在 Reality 协议不兼容问题
- **Let's Encrypt IP 证书**：有效期 6 天，3x-ui 会自动续期，无需手动处理
- **Windows 用户**：只需本地有 Python 3，无需 WSL 或任何其他工具
- **端口 443 被占用**：先在 VPS 上 `pkill -9 sui` 停掉旧服务，再安装
- **配置文件位置**：每次运行后凭据保存在本地 `~/.vps/<IP>.txt`，忘记密码或面板地址时查这里

---

## 安全提示

- **面板端口不对外暴露**：`listenIP 127.0.0.1` 使 x-ui 只监听 loopback，端口 2053 从公网彻底消失，无需防火墙规则
- **面板访问需 SSH 隧道**：`ssh -L 2053:127.0.0.1:2053 root@<IP>`，建立后浏览器开 `http://localhost:2053`
- **公网只开放必要端口**：22（SSH 管理）和 443（VLESS 代理），其他全部关闭
- **SSH 安全**：配置完成后建议配置 SSH 密钥登录并禁用密码登录，彻底消除暴力破解风险

---

## 故障恢复

**阶段二失败（安装中断）**：

直接重新运行 `vps_postinstall.py`——它会自动检测 service 文件、发行版、凭据状态并修复，无需手动干预：

```bash
python3 /tmp/vps_postinstall.py
```

如果 `/tmp/vps_postinstall.py` 不存在（新 session），重新写入后运行即可。
如果 x-ui 二进制完全不存在，才需要重新运行 `vps_install.py`。

**阶段四失败（API 报错）**：直接重新运行 `python3 /tmp/vps_run_setup.py`，脚本是幂等的

**忘记面板密码**：查 `~/.vps/<IP>.txt`，或 SSH 进 VPS 执行：

```bash
/usr/local/x-ui/x-ui setting -username <新用户名> -password <新密码>
systemctl restart x-ui
```
