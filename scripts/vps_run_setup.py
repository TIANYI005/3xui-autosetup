import paramiko, sys, json, urllib.request, ssl, http.cookiejar, base64, uuid as _uuid, secrets, re, io, time
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

USAGE = ("Usage: vps_run_setup.py <IP> <SSH_PORT> <PASSWORD> <PANEL_PORT> <WEBBASEPATH> "
         "<PANEL_USERNAME> <PANEL_PASSWORD> <SNI> <NODE_NAME> [PROXY_PORT] [USERS_JSON]\n"
         "  USERS_JSON example: '[{\"email\":\"owner\",\"gb\":0},{\"email\":\"friend\",\"gb\":200}]'\n"
         "  gb=0 means unlimited")

if not (9 <= len(sys.argv) <= 12):
    print(USAGE)
    sys.exit(1)

def normalize_webbasepath(path):
    # MSYS2 在 Windows Git Bash 下会把 /abc/ 转换为 C:/Program Files/Git/abc/
    if re.match(r'^[A-Za-z]:[/\\]', path):
        segment = re.split(r'[/\\]', path.rstrip('/\\'))[-1]
        return '/' + segment + '/'
    return path

IP, SSH_PORT, PASSWORD = sys.argv[1], int(sys.argv[2]), sys.argv[3]
PANEL_PORT, WEBBASEPATH = int(sys.argv[4]), normalize_webbasepath(sys.argv[5])
PANEL_USERNAME, PANEL_PASSWORD = sys.argv[6], sys.argv[7]
SNI, NODE_NAME = sys.argv[8], sys.argv[9]
PROXY_PORT = int(sys.argv[10]) if len(sys.argv) > 10 else 443

DEFAULT_USERS = json.dumps([{"email": "owner", "gb": 0}])
users = json.loads(sys.argv[11] if len(sys.argv) > 11 else DEFAULT_USERS)

# 本地生成加密材料
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

k    = X25519PrivateKey.generate()
PRIV = base64.urlsafe_b64encode(k.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())).rstrip(b"=").decode()
PUB  = base64.urlsafe_b64encode(k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).rstrip(b"=").decode()
SID  = secrets.token_hex(8)

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

# 已有入站先删除（幂等）
existing = api("/panel/api/inbounds/list")
for ib in existing.get("obj") or []:
    if ib.get("port") == PROXY_PORT:
        api(f"/panel/api/inbounds/del/{ib['id']}")
        print(f"Removed existing inbound on port {PROXY_PORT} (id={ib['id']})")

# 生成每个用户的 UUID
user_uuids = {u["email"]: str(_uuid.uuid4()) for u in users}

clients = [
    {
        "id": user_uuids[u["email"]],
        "flow": "xtls-rprx-vision",
        "email": u["email"],
        "enable": True,
        "expiryTime": 0,
        "totalGB": u.get("gb", 0),
    }
    for u in users
]

r = api("/panel/api/inbounds/add", {
    "up": 0, "down": 0, "total": 0,
    "remark": NODE_NAME,
    "enable": True,
    "expiryTime": 0,
    "listen": "",
    "port": PROXY_PORT,
    "protocol": "vless",
    "settings": json.dumps({"clients": clients, "decryption": "none"}),
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
print(f"Inbound created OK (id={r['obj']['id']}, port={PROXY_PORT}, users={len(users)})")

# 输出每个用户的链接
def make_link(uid, email):
    label = NODE_NAME if email == "owner" else f"{NODE_NAME}-{email}"
    return (f"vless://{uid}@{IP}:{PROXY_PORT}"
            f"?security=reality&encryption=none"
            f"&pbk={PUB}&fp=chrome&sni={SNI}"
            f"&sid={SID}&spx=%2F&type=tcp"
            f"&flow=xtls-rprx-vision"
            f"#{label}")

links = [(u["email"], make_link(user_uuids[u["email"]], u["email"])) for u in users]

for email, link in links:
    print(f"LINK_{email}={link}")

# 兼容旧接口：LINK= 始终指向第一个用户（owner）
print(f"LINK={links[0][1]}")

# 将面板收回 localhost，并验证 xray 启动
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(IP, port=SSH_PORT, username="root", password=PASSWORD, timeout=10)

def run(cmd):
    _, o, e = ssh.exec_command(cmd)
    return o.read().decode().strip()

run("/usr/local/x-ui/x-ui setting -listenIP 127.0.0.1 && systemctl restart x-ui")
time.sleep(4)

log = run("journalctl -u x-ui --no-pager -n 10 2>/dev/null")
if "Xray" in log and ("started" in log.lower() or "start" in log.lower()) and "ERROR" not in log:
    print("Xray started OK")
elif "ERROR" in log or "Failed" in log:
    print(f"WARNING: xray 可能未正常启动，请检查：\n{log}")
else:
    print("Xray status unknown (check: journalctl -u x-ui -n 20)")

ssh.close()
print("Panel restricted to localhost")
