import paramiko, sys, json, urllib.request, ssl, http.cookiejar, base64, uuid as _uuid, secrets, re, io
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

if len(sys.argv) != 10:
    print("Usage: vps_run_setup.py <IP> <SSH_PORT> <PASSWORD> <PANEL_PORT> <WEBBASEPATH> <PANEL_USERNAME> <PANEL_PASSWORD> <SNI> <NODE_NAME>")
    sys.exit(1)

def normalize_webbasepath(path):
    # MSYS2 在 Windows Git Bash 下会把 /abc/ 转换为 C:/Program Files/Git/abc/
    # 检测到 Windows 绝对路径时，提取最后一段还原为 /segment/
    if re.match(r'^[A-Za-z]:[/\\]', path):
        segment = re.split(r'[/\\]', path.rstrip('/\\'))[-1]
        return '/' + segment + '/'
    return path

IP, SSH_PORT, PASSWORD = sys.argv[1], int(sys.argv[2]), sys.argv[3]
PANEL_PORT, WEBBASEPATH = int(sys.argv[4]), normalize_webbasepath(sys.argv[5])
PANEL_USERNAME, PANEL_PASSWORD = sys.argv[6], sys.argv[7]
SNI, NODE_NAME = sys.argv[8], sys.argv[9]
PROXY_PORT = 443

# 本地生成加密材料（避免依赖远端 openssl，跨平台兼容）
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

k    = X25519PrivateKey.generate()
PRIV = base64.urlsafe_b64encode(k.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).rstrip(b"=").decode()
PUB  = base64.urlsafe_b64encode(k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).rstrip(b"=").decode()
SID  = secrets.token_hex(8)
UUID = str(_uuid.uuid4())

# 直接连接面板（此时 postinstall 尚未限制 localhost，面板监听在 *:PANEL_PORT）
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
BASE = opener = None
for scheme in ["https", "http"]:
    _opener, _jar = make_opener(scheme)
    _base = f"{scheme}://{IP}:{PANEL_PORT}" + (f"/{path_prefix}" if path_prefix else "")
    try:
        body = json.dumps({"username": PANEL_USERNAME, "password": PANEL_PASSWORD}).encode()
        req = urllib.request.Request(_base + "/login", body, {"Content-Type": "application/json"})
        with _opener.open(req, timeout=5) as r:
            result = json.loads(r.read())
        if result.get("success"):
            BASE, opener = _base, _opener
            print(f"Panel connected via {scheme.upper()}")
            break
    except Exception:
        continue

if not BASE:
    raise SystemExit(
        f"[错误] 无法连接面板 {IP}:{PANEL_PORT}（HTTPS 和 HTTP 均失败）\n"
        f"  → 检查 x-ui 是否在运行：systemctl status x-ui\n"
        f"  → 检查端口是否正确：ss -tlnp | grep {PANEL_PORT}"
    )
print("Login OK")

def api(path, data=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"} if body else {})
    with opener.open(req) as r:
        return json.loads(r.read())

# 如果 443 已有 inbound，先删除（保证幂等）
existing = api("/panel/api/inbounds/list")
for ib in existing.get("obj") or []:
    if ib.get("port") == PROXY_PORT:
        api(f"/panel/api/inbounds/del/{ib['id']}")
        print(f"Removed existing inbound on port {PROXY_PORT} (id={ib['id']})")

r = api("/panel/api/inbounds/add", {
    "up": 0, "down": 0, "total": 0,
    "remark": NODE_NAME,
    "enable": True,
    "expiryTime": 0,
    "listen": "",
    "port": PROXY_PORT,
    "protocol": "vless",
    "settings": json.dumps({"clients": [], "decryption": "none"}),
    "streamSettings": json.dumps({
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
            "show": False,
            "dest": f"{SNI}:443",
            "xver": 0,
            "serverNames": [SNI],
            "privateKey": PRIV,
            "shortIds": [SID, ""]
        },
        "tcpSettings": {"header": {"type": "none"}}
    }),
    "sniffing": json.dumps({"enabled": True, "destOverride": ["http", "tls", "quic", "fakedns"]})
})
if not r.get("success"):
    raise SystemExit(f"[错误] 创建 inbound 失败：{r}")
inbound_id = r["obj"]["id"]
print(f"Inbound created OK (id={inbound_id})")

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

link = (f"vless://{UUID}@{IP}:{PROXY_PORT}"
        f"?security=reality&encryption=none"
        f"&pbk={PUB}&fp=chrome&sni={SNI}"
        f"&sid={SID}&spx=%2F&type=tcp"
        f"&flow=xtls-rprx-vision"
        f"#{NODE_NAME}")
print("LINK=" + link)

# 配置完成后将面板收回 localhost
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, port=SSH_PORT, username="root", password=PASSWORD, timeout=10)
stdin, stdout, stderr = client.exec_command(
    "/usr/local/x-ui/x-ui setting -listenIP 127.0.0.1 && systemctl restart x-ui"
)
stdout.read()
client.close()
print("Panel restricted to localhost")
