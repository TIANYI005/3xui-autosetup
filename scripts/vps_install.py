import paramiko, time, sys, io
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

if len(sys.argv) != 4:
    print("Usage: vps_install.py <IP> <SSH_PORT> <PASSWORD>")
    sys.exit(1)

IP, SSH_PORT, PASSWORD = sys.argv[1], int(sys.argv[2]), sys.argv[3]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, port=SSH_PORT, username="root", password=PASSWORD, timeout=15)

channel = client.get_transport().open_session()
channel.set_combine_stderr(True)
channel.exec_command("yes n | bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/main/install.sh)")

output_parts = []
while True:
    if channel.recv_ready():
        chunk = channel.recv(4096).decode("utf-8", errors="replace")
        print(chunk, end="", flush=True)
        output_parts.append(chunk)
    if channel.exit_status_ready() and not channel.recv_ready():
        break
    time.sleep(0.1)

client.close()
print("\n---INSTALL_DONE---")
