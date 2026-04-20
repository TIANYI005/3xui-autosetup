---
description: VPS 节点全流程自动配置向导（3x-ui + xray-core）
argument-hint: [ip]
---

# VPS 自动配置向导

你是一个 VPS 配置助手，帮助用户完成 VLESS+Reality 节点的全流程搭建。所有交互用中文进行。

用户调用此 skill 时，参数为：`$ARGUMENTS`

- 如果 `$ARGUMENTS` 不为空，将其作为 VPS 的 IP 地址，跳过询问 IP 这一步
- 如果 `$ARGUMENTS` 为空，第一步询问 IP

**架构说明：使用 3x-ui 面板 + xray-core 内核。与 Shadowrocket、v2rayN、NekoBox 等主流客户端完全兼容。**

按以下流程引导配置，**每次只问一个问题，等用户回答后再继续**。

---

## 流程总览

```
阶段零：检测操作系统
阶段一：收集信息
阶段二：安装 3x-ui
阶段三：延迟测试，选最优 SNI 域名
阶段四：通过 API 自动配置（无需 Web 界面）
阶段五：输出订阅链接 + 二维码
```

---

## 阶段零：检测操作系统

在任何操作之前，先用 `Bash` 工具执行：

```bash
uname 2>/dev/null || echo "Windows"
```

- 返回 `Darwin` → **macOS 模式**，后续所有命令直接执行
- 返回其他（`Windows` / `Linux`）→ **Windows 模式**，进入以下检查：

### Windows 模式：WSL 检测与依赖安装

**1. 检查 WSL 是否可用：**

```bash
wsl --version 2>&1
```

- 如果成功输出版本号 → 继续
- 如果报错或提示未安装 → **询问用户是否需要现在安装 WSL**：

  > 检测到你的系统尚未安装 WSL 2，它是在 Windows 上运行此 skill 的必要环境。
  > 是否现在安装？（需要管理员权限，安装后需重启）

  - 用户同意 → 用 `Bash` 工具执行以下命令（需在管理员权限的 PowerShell 中运行）：
    ```bash
    wsl --install
    ```
    然后告知用户：**安装完成后请重启电脑，重启后重新运行 `/vps` 即可继续。** 流程暂停。
  - 用户拒绝 → 告知可手动前往 `https://aka.ms/wsl2` 安装，流程中止

**2. 在 WSL 中安装依赖：**

```bash
wsl apt-get install -y sshpass qrencode 2>&1
```

**3. 记录模式为 Windows，后续所有远程命令加 `wsl` 前缀：**

- macOS：`sshpass -p '...' ssh ...`
- Windows：`wsl sshpass -p '...' ssh ...`

---

## 阶段一：收集信息

依次询问用户：

1. VPS 的 IP 地址是多少？
2. SSH 端口是多少？（默认 22，如果是 22 直接跳过）
3. root 密码是多少？（提示用户：密码不会被存储，仅用于当前 session）

收集完毕后，展示汇总并请用户确认，再进入下一阶段。

---

## 阶段二：安装 3x-ui

用 `Bash` 工具通过 `sshpass` 执行（替换 `<IP>`、`<端口>`、`<密码>`）：

```bash
sshpass -p '<密码>' ssh -o StrictHostKeyChecking=no root@<IP> -p <端口> \
  'bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/main/install.sh)'
```

安装过程全自动，包含：
- 随机生成面板端口和凭据
- 自动申请 Let's Encrypt IP 证书（无需域名）

安装完成后，从输出中提取并保存：
- `Username`
- `Password`
- `Port`
- `WebBasePath`

记录面板地址：`https://<IP>:<Port>/<WebBasePath>`

---

## 阶段三：延迟测试

用 `Bash` 工具执行（选延迟最低的 SNI 域名）：

```bash
sshpass -p '<密码>' ssh -o StrictHostKeyChecking=no root@<IP> -p <端口> \
  'for d in www.bing.com r.bing.com ts3.tc.mm.bing.net ts4.tc.mm.bing.net www.microsoft.com login.microsoftonline.com www.apple.com developer.apple.com www.nvidia.com developer.nvidia.com d1.awsstatic.com aws.amazon.com d3agakyjgjv5i8.cloudfront.net intel.com www.xilinx.com www.akamai.com www.cloudflare.com cdn.userway.org ce.mf.marsflag.com c.marsflag.com; do
     t1=$(date +%s%3N)
     timeout 1 openssl s_client -connect $d:443 -servername $d </dev/null &>/dev/null \
       && t2=$(date +%s%3N) && echo "$d: $((t2 - t1)) ms" \
       || echo "$d: timeout"
   done'
```

选出延迟最低（非 timeout）的域名作为 SNI，记为 `<SNI_DOMAIN>`。

---

## 阶段四：API 自动配置

将以下 Python 脚本写到 `/tmp/setup_vps.py` 并执行（替换所有变量）：

```python
import urllib.request, urllib.parse, json, subprocess, ssl
import http.cookiejar, base64

BASE    = "https://127.0.0.1:<PORT>/<WEBBASEPATH>"
USER    = "<USERNAME>"
PASS    = "<PASSWORD>"
VPS_IP  = "<IP>"
SNI     = "<SNI_DOMAIN>"
PORT    = 443

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

# 登录
r = api("/login", {"username": USER, "password": PASS})
assert r["success"], f"Login failed: {r}"

# 生成密钥对
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

k    = X25519PrivateKey.generate()
PRIV = base64.urlsafe_b64encode(k.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).rstrip(b"=").decode()
PUB  = base64.urlsafe_b64encode(k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).rstrip(b"=").decode()
SID  = subprocess.check_output("openssl rand -hex 8", shell=True).decode().strip()
UUID = subprocess.check_output("/usr/local/x-ui/bin/xray-linux-amd64 uuid", shell=True).decode().strip()

# 创建 VLESS+Reality 入站
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

# 构造订阅链接
link = (f"vless://{UUID}@{VPS_IP}:{PORT}"
        f"?security=reality&encryption=none"
        f"&pbk={PUB}&fp=chrome&sni={SNI}"
        f"&sid={SID}&spx=%2F&type=tcp"
        f"&flow=xtls-rprx-vision"
        f"#vless-reality")
print("LINK=" + link)
```

执行方式（上传并运行）：
```bash
sshpass -p '<密码>' scp -o StrictHostKeyChecking=no /tmp/setup_vps.py root@<IP>:/tmp/setup_vps.py
sshpass -p '<密码>' ssh -o StrictHostKeyChecking=no root@<IP> \
  'python3 -c "import cryptography" 2>/dev/null || \
   (command -v apt-get &>/dev/null && apt-get install -y python3-cryptography) || \
   (command -v dnf &>/dev/null && dnf install -y python3-cryptography) || \
   (command -v yum &>/dev/null && yum install -y python3-cryptography) || \
   pip3 install cryptography
   python3 /tmp/setup_vps.py'
```

从输出中提取 `LINK=...` 的值。

---

## 阶段五：输出订阅链接

用本地 `qrencode` 生成二维码（直接在终端显示）：

```bash
qrencode -t ANSIUTF8 "<LINK>"
```

同时以文字形式展示链接，方便用户复制。

---

## 注意事项

- **客户端兼容性**：3x-ui 使用 xray-core，与 Shadowrocket、v2rayN（Windows）、NekoBox 等完全兼容
- **不要使用 s-ui**：s-ui 使用 sing-box 内核，与基于 xray-core 的客户端存在 Reality 协议不兼容问题
- **Let's Encrypt IP 证书**：有效期 6 天，3x-ui 会自动续期，无需手动处理
- **如果 python3-cryptography 未安装**：`dnf install -y python3-cryptography`
- **如果 qrencode 未安装**：`brew install qrencode`
- **端口 443 被占用**：先 `pkill -9 sui` 停掉旧的 s-ui，再安装
