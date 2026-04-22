import qrcode, os, datetime, sys, io, re
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

if len(sys.argv) != 7:
    print("Usage: vps_qr.py <LINK> <IP> <PANEL_PORT> <WEBBASEPATH> <PANEL_USERNAME> <PANEL_PASSWORD>")
    sys.exit(1)

def normalize_webbasepath(path):
    if re.match(r'^[A-Za-z]:[/\\]', path):
        segment = re.split(r'[/\\]', path.rstrip('/\\'))[-1]
        return '/' + segment + '/'
    return path

LINK, VPS_IP, PANEL_PORT = sys.argv[1], sys.argv[2], sys.argv[3]
WEBBASEPATH = normalize_webbasepath(sys.argv[4])
PANEL_USER, PANEL_PASS = sys.argv[5], sys.argv[6]

panel_path  = WEBBASEPATH.strip("/")
local_panel = f"http://localhost:{PANEL_PORT}" + (f"/{panel_path}" if panel_path else "")
ssh_tunnel  = f"ssh -L {PANEL_PORT}:127.0.0.1:{PANEL_PORT} root@{VPS_IP}"

qr = qrcode.QRCode()
qr.add_data(LINK)
qr.make(fit=True)
try:
    qr.print_ascii(invert=True)
except (UnicodeEncodeError, Exception):
    print("[提示] 终端不支持 Unicode 字符，跳过 ASCII 二维码打印，将保存为 PNG")

print("\n========== 节点信息 ==========")
print(f"VLESS 链接：{LINK}")
print(f"\n========== 面板管理（仅本地访问）==========")
print(f"SSH 隧道：  {ssh_tunnel}")
print(f"隧道建立后：{local_panel}")
print(f"用户名：    {PANEL_USER}")
print(f"密码：      {PANEL_PASS}")
print("===========================================")
print(f"\n⚠ 面板已绑定 127.0.0.1，公网无法直接访问。")
print(f"  如需恢复公网访问（不推荐）：")
print(f"    ssh root@{VPS_IP} '/usr/local/x-ui/x-ui setting -listenIP \"\" && systemctl restart x-ui'")

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
os.chmod(save_path, 0o600)
os.chmod(save_dir, 0o700)
print(f"\n配置已保存到 {save_path}")

try:
    from PIL import Image
    png_name = f"{VPS_IP}_qr.png"
    img = qr.make_image(fill_color="black", back_color="white")
    png_path = os.path.join(save_dir, png_name)
    img.save(png_path)
    print(f"二维码图片已保存到 {png_path}")
    downloads = os.path.expanduser("~/Downloads")
    if os.path.isdir(downloads):
        dl_path = os.path.join(downloads, png_name)
        img.save(dl_path)
        print(f"二维码图片已复制到 {dl_path}")
except ImportError:
    pass
