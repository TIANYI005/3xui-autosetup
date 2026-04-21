import paramiko

IP       = "<IP>"
SSH_PORT = <SSH_PORT>
PASSWORD = "<PASSWORD>"

DOMAINS = [
    "www.bing.com", "r.bing.com", "ts3.tc.mm.bing.net", "ts4.tc.mm.bing.net",
    "www.microsoft.com", "login.microsoftonline.com",
    "www.apple.com", "developer.apple.com",
    "www.nvidia.com", "developer.nvidia.com",
    "d1.awsstatic.com", "aws.amazon.com",
    "d3agakyjgjv5i8.cloudfront.net", "intel.com", "www.xilinx.com",
    "www.akamai.com", "www.cloudflare.com",
    "cdn.userway.org", "ce.mf.marsflag.com", "c.marsflag.com"
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, port=SSH_PORT, username="root", password=PASSWORD, timeout=10)
stdin, stdout, stderr = client.exec_command("; ".join([
    f't1=$(date +%s%3N); timeout 1 openssl s_client -connect {d}:443 -servername {d} </dev/null &>/dev/null'
    f' && t2=$(date +%s%3N) && echo "{d}: $((t2-t1)) ms" || echo "{d}: timeout"'
    for d in DOMAINS
]))
print(stdout.read().decode())
client.close()
