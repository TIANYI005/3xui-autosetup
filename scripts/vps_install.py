import paramiko, time

IP       = "<IP>"
SSH_PORT = <SSH_PORT>
PASSWORD = <PASSWORD_REPR>

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
