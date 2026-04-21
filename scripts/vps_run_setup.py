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
stdin, stdout, stderr = client.exec_command("python3 /tmp/setup_vps.py 2>&1")
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
