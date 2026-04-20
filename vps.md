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

安装完成后，从输出中提取并保存：
- `Username`
- `Password`
- `Port`
- `WebBasePath`

记录面板地址：`https://<IP>:<Port>/<WebBasePath>`

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

BASE   = "https://127.0.0.1:<PANEL_PORT>/<WEBBASEPATH>"
USER   = "<PANEL_USERNAME>"
PASS   = "<PANEL_PASSWORD>"
VPS_IP = "<IP>"
SNI    = "<SNI_DOMAIN>"
PORT   = 443

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=ctx),
    urllib.request.HTTPCookieProcessor(jar)
)

def api(path, data=None):
    url = BASE + path
    if data:
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    with opener.open(req) as r:
        return json.loads(r.read())

r = api("/login", {"username": USER, "password": PASS})
assert r["success"], f"Login failed: {r}"
print("Login OK")

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

k    = X25519PrivateKey.generate()
PRIV = base64.urlsafe_b64encode(k.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).rstrip(b"=").decode()
PUB  = base64.urlsafe_b64encode(k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).rstrip(b"=").decode()
SID  = subprocess.check_output("openssl rand -hex 8", shell=True).decode().strip()
UUID = subprocess.check_output("/usr/local/x-ui/bin/xray-linux-amd64 uuid", shell=True).decode().strip()

inbound = {
    "up": 0, "down": 0, "total": 0,
    "remark": "vless-reality",
    "enable": True,
    "expiryTime": 0,
    "listen": "",
    "port": PORT,
    "protocol": "vless",
    "settings": json.dumps({
        "clients": [{"id": UUID, "flow": "xtls-rprx-vision"}],
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
assert r["success"], f"Add inbound failed: {r}"
print("Inbound created OK")

link = (f"vless://{UUID}@{VPS_IP}:{PORT}"
        f"?security=reality&encryption=none"
        f"&pbk={PUB}&fp=chrome&sni={SNI}"
        f"&sid={SID}&spx=%2F&type=tcp"
        f"&flow=xtls-rprx-vision"
        f"#vless-reality")
print("LINK=" + link)
```

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
stdin, stdout, stderr = client.exec_command("python3 /tmp/setup_vps.py")
output = stdout.read().decode()
print(output)
client.close()
```

运行：

```bash
python3 /tmp/vps_run_setup.py
```

从输出中提取 `LINK=...` 的值。

---

## 阶段五：输出订阅链接

用 `Write` 工具写入 `/tmp/vps_qr.py`（替换 `<LINK>`）：

```python
import qrcode

link = "<LINK>"
qr = qrcode.QRCode()
qr.add_data(link)
qr.make(fit=True)
qr.print_ascii(invert=True)
print("\n" + link)
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
