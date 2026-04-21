import paramiko, sys, os, shlex

if len(sys.argv) != 10:
    print("Usage: vps_run_setup.py <IP> <SSH_PORT> <PASSWORD> <PANEL_PORT> <WEBBASEPATH> <PANEL_USERNAME> <PANEL_PASSWORD> <SNI> <NODE_NAME>")
    sys.exit(1)

IP, SSH_PORT, PASSWORD = sys.argv[1], int(sys.argv[2]), sys.argv[3]
PANEL_PORT, WEBBASEPATH, PANEL_USERNAME, PANEL_PASSWORD = sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7]
SNI, NODE_NAME = sys.argv[8], sys.argv[9]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, port=SSH_PORT, username="root", password=PASSWORD, timeout=10)

# 上传 setup_vps.py 直接从源文件
sftp = client.open_sftp()
sftp.put(os.path.join(SCRIPT_DIR, "setup_vps.py"), "/tmp/setup_vps.py")
sftp.close()

# 安装 cryptography（自动识别包管理器）
install_cmd = (
    'python3 -c "import cryptography" 2>/dev/null || '
    '(command -v apt-get &>/dev/null && apt-get install -y python3-cryptography) || '
    '(command -v dnf &>/dev/null && dnf install -y python3-cryptography) || '
    '(command -v yum &>/dev/null && yum install -y python3-cryptography) || '
    'pip3 install cryptography --break-system-packages 2>/dev/null || pip3 install cryptography'
)
stdin, stdout, stderr = client.exec_command(install_cmd)
stdout.read()

# 运行配置脚本（带参数）
args = " ".join(shlex.quote(a) for a in [PANEL_PORT, WEBBASEPATH, PANEL_USERNAME, PANEL_PASSWORD, IP, SNI, NODE_NAME])
stdin, stdout, stderr = client.exec_command(f"python3 /tmp/setup_vps.py {args} 2>&1")
output = stdout.read().decode()
print(output)

# 配置成功后将面板收回 localhost
if "Client added OK" in output:
    stdin, stdout, stderr = client.exec_command(
        "/usr/local/x-ui/x-ui setting -listenIP 127.0.0.1 && systemctl restart x-ui"
    )
    stdout.read()
    print("Panel restricted to localhost")

client.close()
