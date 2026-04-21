import urllib.request, json, subprocess, ssl, http.cookiejar, base64, uuid as _uuid, sys

if len(sys.argv) != 8:
    print("Usage: setup_vps.py <PANEL_PORT> <WEBBASEPATH> <PANEL_USERNAME> <PANEL_PASSWORD> <VPS_IP> <SNI> <NODE_NAME>")
    sys.exit(1)

PANEL_PORT  = int(sys.argv[1])
WEBBASEPATH = sys.argv[2]
USER        = sys.argv[3]
PASS        = sys.argv[4]
VPS_IP      = sys.argv[5]
SNI         = sys.argv[6]
NODE_NAME   = sys.argv[7]
PORT        = 443

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
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"} if body else {})
    with opener.open(req) as r:
        return json.loads(r.read())

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

k    = X25519PrivateKey.generate()
PRIV = base64.urlsafe_b64encode(k.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).rstrip(b"=").decode()
PUB  = base64.urlsafe_b64encode(k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).rstrip(b"=").decode()
SID  = subprocess.check_output("openssl rand -hex 8", shell=True).decode().strip()
UUID = str(_uuid.uuid4())

# 如果 443 已有 inbound，先删除（保证幂等）
existing = api("/panel/api/inbounds/list")
for ib in existing.get("obj") or []:
    if ib.get("port") == PORT:
        api(f"/panel/api/inbounds/del/{ib['id']}")
        print(f"Removed existing inbound on port {PORT} (id={ib['id']})")

# 创建空 inbound
r = api("/panel/api/inbounds/add", {
    "up": 0, "down": 0, "total": 0,
    "remark": NODE_NAME,
    "enable": True,
    "expiryTime": 0,
    "listen": "",
    "port": PORT,
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

# 通过 addClient 添加客户端（保证 client_traffics.enable=1）
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
        f"#{NODE_NAME}")
print("LINK=" + link)
