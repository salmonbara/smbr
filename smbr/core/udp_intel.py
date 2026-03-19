import subprocess
import shutil
from rich import print
from rich.console import Console

console = Console()


def tool_exists(name):
    return shutil.which(name) is not None


# ---------- OS DETECTION ----------

def detect_os(text):

    t = text.lower()

    if "windows" in t:
        return "windows"

    if "linux" in t or "unix" in t:
        return "linux"

    return "unknown"


def print_os_hint(os_type):

    print()

    if os_type == "windows":
        print("[bold yellow][HINT] Windows Foothold Focus[/]")
        print("- Running processes")
        print("- Installed software")
        print("- Local users / service accounts")
        print("- Listening ports / exposed services")
        print("- Writable shares")

    elif os_type == "linux":
        print("[bold yellow][HINT] Linux Foothold Focus[/]")
        print("- Running services")
        print("- Cron jobs")
        print("- Mounted shares / NFS")
        print("- Listening ports")
        print("- Writable directories")

    else:
        print("[yellow][HINT] OS not clearly identified — review SNMP output[/]")


# ---------- OUTPUT HIGHLIGHT ----------

def highlight_snmp_output(text):

    for line in text.splitlines():

        l = line.lower()

        # ⭐ CRITICAL
        if any(k in l for k in [
            "password",
            "community",
            "admin",
            "administrator",
            "root",
            "backup",
            "service",
            "sql",
            "writable"
        ]):
            console.print(line, style="bold red")

        # ⭐ INTERESTING
        elif any(k in l for k in [
            "user",
            "process",
            "listening",
            "share",
            "mount",
            "path",
            "cron"
        ]):
            console.print(line, style="yellow")

        # ⭐ INFO
        elif any(k in l for k in [
            "hostname",
            "system",
            "contact",
            "location",
            "hardware",
            "software"
        ]):
            console.print(line, style="cyan")

        else:
            console.print(line)


# ---------- MAIN SNMP ENGINE ----------

def snmp_intelligence(target, folder, auto_mode=False):

    print("\n[bold magenta][*] SNMP Enumeration[/]")

    if not tool_exists("onesixtyone"):
        print(f"[yellow][HINT] Try snmp-check {target} -c public[/]")
        return

    wordlists = [
        "/usr/share/seclists/Discovery/SNMP/snmp.txt",
        "/usr/share/doc/onesixtyone/dict.txt"
    ]

    community = None
    used = None

    for wl in wordlists:

        try:
            out = subprocess.run(
                ["onesixtyone", "-c", wl, target],
                capture_output=True,
                text=True,
                timeout=20
            ).stdout
        except:
            continue

        for line in out.splitlines():
            if "[" in line and "]" in line:
                community = line.split("[")[1].split("]")[0]
                used = wl
                break

        if community:
            break

    if not community:
        print("[yellow][!] SNMP community string not found[/]")
        print(f"[yellow][HINT] Try snmp-check {target} -c public[/]")
        return

    print(f"[green][+] Community string found → {community}[/]")
    print(f"[cyan][*] Found using onesixtyone -c {used}[/]")

    # ⭐ NEW BEHAVIOUR
    if auto_mode:
        print("\n[bold yellow][HINT] Manual enumeration suggested:[/]")
        print(f"snmp-check {target} -c {community}")
        return

    # ⭐ interactive mode (udp mode)
    if not tool_exists("snmp-check"):
        print(f"[yellow][HINT] snmp-check not installed[/]")
        return

    run = input(f"Run snmp-check {target} -c {community}? (y/N): ")

    if run.lower() != "y":
        return

    proc = subprocess.run(
        ["snmp-check", target, "-c", community],
        capture_output=True,
        text=True
    )

    output = proc.stdout

    highlight_snmp_output(output)

    os_type = detect_os(output)
    print_os_hint(os_type)