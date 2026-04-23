import qrcode, os, datetime, sys, io, re, json
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

USAGE = ("Usage: vps_qr.py <LINK|LINKS_JSON> <IP> <PANEL_PORT> <WEBBASEPATH> <PANEL_USERNAME> <PANEL_PASSWORD>\n"
         "  LINK:       单条链接字符串\n"
         "  LINKS_JSON: JSON 数组，如 '[{\"email\":\"owner\",\"link\":\"vless://...\"}]'")

if len(sys.argv) != 7:
    print(USAGE)
    sys.exit(1)

def normalize_webbasepath(path):
    if re.match(r'^[A-Za-z]:[/\\]', path):
        segment = re.split(r'[/\\]', path.rstrip('/\\'))[-1]
        return '/' + segment + '/'
    return path

def detect_protocol(link):
    if 'security=reality' in link:
        return 'vless-reality', 'VLESS-Reality'
    elif link.startswith('vless://'):
        return 'vless-tls', 'VLESS-TLS'
    elif link.startswith('tuic://'):
        return 'tuic', 'TUIC-TLS'
    elif link.startswith('trojan://'):
        return 'trojan', 'Trojan-TLS'
    elif link.startswith('hysteria2://') or link.startswith('hy2://'):
        return 'hy2', 'Hysteria2'
    elif link.startswith('vmess://'):
        return 'vmess', 'VMess'
    return 'proxy', 'Proxy'

raw_links_arg = sys.argv[1]
VPS_IP, PANEL_PORT = sys.argv[2], sys.argv[3]
WEBBASEPATH = normalize_webbasepath(sys.argv[4])
PANEL_USER, PANEL_PASS = sys.argv[5], sys.argv[6]

# 解析链接：支持单条字符串或 JSON 数组
if raw_links_arg.strip().startswith('['):
    entries = json.loads(raw_links_arg)
    # 每个元素可以是 {"email": "owner", "link": "vless://..."} 或纯字符串
    link_list = [(e["email"] if isinstance(e, dict) else "", e["link"] if isinstance(e, dict) else e)
                 for e in entries]
else:
    link_list = [("", raw_links_arg)]

panel_path  = WEBBASEPATH.strip("/")
local_panel = f"http://localhost:{PANEL_PORT}" + (f"/{panel_path}" if panel_path else "")
ssh_tunnel  = f"ssh -L {PANEL_PORT}:127.0.0.1:{PANEL_PORT} root@{VPS_IP}"

save_dir = os.path.expanduser("~/.vps")
os.makedirs(save_dir, exist_ok=True)

txt_lines = [
    f"# VPS 节点配置 — {VPS_IP}",
    f"# 保存时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "",
]

for email, link in link_list:
    slug, label = detect_protocol(link)
    node_name = link.split('#', 1)[-1] if '#' in link else VPS_IP
    safe_name = re.sub(r'[^\w\-.]', '_', node_name)

    # 终端打印二维码
    qr = qrcode.QRCode()
    qr.add_data(link)
    qr.make(fit=True)
    try:
        qr.print_ascii(invert=True)
    except (UnicodeEncodeError, Exception):
        print("[提示] 终端不支持 Unicode，跳过 ASCII 二维码打印")

    print(f"\n========== 节点信息{' (' + email + ')' if email else ''} ==========")
    print(f"[{label}] {link}")

    # 保存 PNG
    try:
        from PIL import Image
        img = qr.make_image(fill_color="black", back_color="white")
        png_name = f"{safe_name}_{slug}_qr.png"
        png_path = os.path.join(save_dir, f"{VPS_IP}_{slug}_qr.png")
        img.save(png_path)
        print(f"二维码已保存到 {png_path}")
        downloads = os.path.expanduser("~/Downloads")
        if os.path.isdir(downloads):
            dl_path = os.path.join(downloads, png_name)
            img.save(dl_path)
            print(f"二维码已复制到 {dl_path}")
    except ImportError:
        pass

    txt_lines.append(f"[{label}]{' (' + email + ')' if email else ''}")
    txt_lines.append(f"LINK={link}")
    txt_lines.append("")

txt_lines += [
    f"SSH_TUNNEL={ssh_tunnel}",
    f"PANEL_LOCAL={local_panel}",
    f"PANEL_USER={PANEL_USER}",
    f"PANEL_PASS={PANEL_PASS}",
]

save_path = os.path.join(save_dir, f"{VPS_IP}.txt")
with open(save_path, "w") as f:
    f.write("\n".join(txt_lines) + "\n")
os.chmod(save_path, 0o600)
os.chmod(save_dir, 0o700)
print(f"\n配置已保存到 {save_path}")

print(f"\n========== 面板管理（仅本地访问）==========")
print(f"SSH 隧道：  {ssh_tunnel}")
print(f"隧道建立后：{local_panel}")
print(f"用户名：    {PANEL_USER}")
print(f"密码：      {PANEL_PASS}")
print("===========================================")
print(f"\n⚠ 面板已绑定 127.0.0.1，公网无法直接访问。")
print(f"  如需恢复公网访问（不推荐）：")
print(f"    ssh root@{VPS_IP} '/usr/local/x-ui/x-ui setting -listenIP \"\" && systemctl restart x-ui'")
