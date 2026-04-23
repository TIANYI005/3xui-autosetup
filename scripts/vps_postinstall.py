import paramiko, secrets, time, re, sys, io, sqlite3, tempfile, os
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

if len(sys.argv) != 4:
    print("Usage: vps_postinstall.py <IP> <SSH_PORT> <PASSWORD>")
    sys.exit(1)

IP, SSH_PORT, PASSWORD = sys.argv[1], int(sys.argv[2]), sys.argv[3]

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
for _ in range(10):
    time.sleep(0.5)
    active, _ = run("systemctl is-active x-ui")
    if active == "active":
        break
if active != "active":
    raise SystemExit(f"[错误] x-ui 无法启动（状态：{active}）\n  → 运行 systemctl status x-ui 查看详情")
print("x-ui active")

# 4. 设置随机凭据
new_user = "admin"
new_pass = secrets.token_urlsafe(16)
run(f"/usr/local/x-ui/x-ui setting -username {new_user} -password {new_pass}")
run("systemctl restart x-ui")
for _ in range(10):
    time.sleep(0.5)
    active, _ = run("systemctl is-active x-ui")
    if active == "active":
        break
print("Credentials updated")

# 5. 修复 sub server 端口冲突（防止 sub server 占用 xray 入站端口）
try:
    db_path_out, _ = run("ls /etc/x-ui/x-ui.db 2>/dev/null || ls /usr/local/x-ui/db/x-ui.db 2>/dev/null || echo NOTFOUND")
    db_path = db_path_out.strip()
    if "NOTFOUND" in db_path or not db_path:
        raise FileNotFoundError("x-ui.db not found at /etc/x-ui/ or /usr/local/x-ui/db/")
    # 先停服务再操作 db，避免 WAL 锁
    run("systemctl stop x-ui")
    time.sleep(1)
    sftp = client.open_sftp()
    tmp = tempfile.mktemp(suffix='.db')
    sftp.get(db_path, tmp)
    conn = sqlite3.connect(tmp)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('subPort', '4096')")
    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('subListen', '127.0.0.1')")
    # 清除面板 listen 限制，确保 vps_run_setup.py 能从外部访问面板
    cur.execute("DELETE FROM settings WHERE key='webListen'")
    conn.commit()
    conn.close()
    sftp.put(tmp, db_path)
    sftp.close()
    os.unlink(tmp)
    run("systemctl start x-ui")
    for _ in range(10):
        time.sleep(0.5)
        active, _ = run("systemctl is-active x-ui")
        if active == "active":
            break
    print("Sub server fixed (127.0.0.1:4096)")
except Exception as e:
    print(f"[警告] Sub server 端口修复失败：{e}")
    print("  → 手动修复：在 VPS 上运行 x-ui 设置或修改 x-ui.db")
    # 确保 x-ui 仍在运行
    run("systemctl start x-ui 2>/dev/null || true")
    for _ in range(6):
        time.sleep(0.5)
        active, _ = run("systemctl is-active x-ui")
        if active == "active":
            break

# 6. 读取面板设置
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
