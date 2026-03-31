import subprocess
import os
import re
from rich import print
from ...core.udp_intel import snmp_intelligence
from ...core.udp_summary import render_udp_summary


def run_cmd(cmd):

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    return result.stdout


def print_nmap_output(output):
    """Print nmap output directly, filtering out empty lines at top."""
    lines = output.splitlines()
    for line in lines:
        print(line)


def host_seems_down(output):
    return "Host seems down" in output or "0 hosts up" in output


# ---------- TCP ----------

def parse_tcp_ports(nmap_output):

    ports = []

    for line in nmap_output.splitlines():
        m = re.search(r"(\d+)/tcp\s+open", line)
        if m:
            ports.append(m.group(1))

    return ports


def run_recon_tcp(target):

    folder = f"recon_{target}"
    os.makedirs(folder, exist_ok=True)

    tcp_file     = f"{folder}/nmap_tcp_allport.txt"
    service_file = f"{folder}/nmap_tcp_service.txt"

    # ── Step 1: Full port scan (no -Pn first) ────────────────────────────
    print(f"[cyan][*] TCP Full Scan → {target}[/]")

    base_cmd = ["nmap", "-p-", "--min-rate", "1000", "-T4"]
    used_pn  = False

    output = run_cmd(base_cmd + [target])

    # ── Step 2: Retry with -Pn if host seems down ────────────────────────
    if host_seems_down(output):
        print(f"[yellow][!] Host seems down — retrying with -Pn...[/]")
        output  = run_cmd(base_cmd + ["-Pn", target])
        used_pn = True

        if host_seems_down(output):
            print(f"[yellow][!] Still no response after -Pn — host may be offline[/]")
            return

    with open(tcp_file, "w") as f:
        f.write(output)

    ports = parse_tcp_ports(output)

    if not ports:
        print(f"[yellow][!] No open TCP ports found on {target}[/]")
        print("[yellow][!] Host may be filtered / firewall present[/]")
        return

    ports.sort(key=int)
    port_str = ",".join(ports)

    # ── Step 3: Service scan on found ports ──────────────────────────────
    print("[cyan][*] TCP Service Scan[/]")

    svc_cmd = ["nmap", "-sC", "-sV", "-p", port_str]
    if used_pn:
        svc_cmd.append("-Pn")
    svc_cmd.append(target)

    service_output = run_cmd(svc_cmd)

    with open(service_file, "w") as f:
        f.write(service_output)

    print(service_output)


# ---------- UDP ----------

def parse_udp_ports(nmap_output):

    ports = []

    for line in nmap_output.splitlines():

        m = re.search(r"(\d+)/udp\s+(\S+)\s+(\S+)", line)

        if m:

            port    = m.group(1)
            state   = m.group(2)
            service = m.group(3)

            if "open" in state:
                ports.append((port, state, service))

    return ports


def run_recon_udp(target):

    folder = f"recon_{target}"
    os.makedirs(folder, exist_ok=True)

    udp_file = f"{folder}/nmap_udp.txt"

    adaptive_ports = [10, 5]
    found_ports    = []
    raw_output     = ""

    for tp in adaptive_ports:

        print(f"[cyan][*] UDP Scan Top {tp} → {target}[/]")

        output = run_cmd([
            "nmap", "-sU", "-Pn", "--top-ports", str(tp), target
        ])

        ports = parse_udp_ports(output)

        if ports:
            found_ports = ports
            raw_output  = output
            print(f"[green][+] UDP ports detected (top {tp})[/]")
            break

    if not found_ports:
        print(f"[yellow][!] No UDP ports found on {target}[/]")
        print("[yellow][!] Ports may be open|filtered or silently dropped[/]")
        return

    with open(udp_file, "w") as f:
        f.write(raw_output)

    render_udp_summary(target, udp_file)

    for port, state, service in found_ports:
        if port == "161" or "snmp" in service.lower():
            snmp_intelligence(target, folder, auto_mode=True)

    try:
        os.remove(udp_file)
    except:
        pass


def run_recon_all(target):

    run_recon_tcp(target)
    run_recon_udp(target)