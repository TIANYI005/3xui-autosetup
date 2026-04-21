import qrcode, os, datetime

LINK        = "<LINK>"
VPS_IP      = "<IP>"
PANEL_PORT  = "<PANEL_PORT>"
WEBBASEPATH = "<WEBBASEPATH>"
PANEL_USER  = "<PANEL_USERNAME>"
PANEL_PASS  = "<PANEL_PASSWORD>"

panel_path  = WEBBASEPATH.strip("/")
local_panel = f"http://localhost:{PANEL_PORT}" + (f"/{panel_path}" if panel_path else "")
ssh_tunnel  = f"ssh -L {PANEL_PORT}:127.0.0.1:{PANEL_PORT} root@{VPS_IP}"

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
