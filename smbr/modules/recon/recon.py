import subprocess
import os
import re
from rich import print
from smbr.core.recon_summary import render_summary
from smbr.core.udp_intel import snmp_intelligence
from smbr.core.udp_summary import render_udp_summary


def run_cmd(cmd):

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    return result.stdout


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

    tcp_file = f"{folder}/nmap_tcp_allport.txt"
    service_file = f"{folder}/nmap_tcp_service.txt"

    print(f"[cyan][*] TCP Full Scan → {target}[/]")

    output = run_cmd([
        "nmap", "-p-", "--min-rate", "1000", "-T4",
        target
    ])

    with open(tcp_file, "w") as f:
        f.write(output)

    ports = parse_tcp_ports(output)

    if not ports:
        print(f"[yellow][!] No open TCP ports found on {target}[/]")
        print("[yellow][!] Host may be filtered / firewall present[/]")
        return

    ports.sort(key=int)
    port_str = ",".join(ports)

    print("[cyan][*] TCP Service Scan[/]")

    service_output = run_cmd([
        "nmap", "-sC", "-sV",
        "-p", port_str,
        target
    ])

    with open(service_file, "w") as f:
        f.write(service_output)

    render_summary(target, tcp_file, service_file)


# ---------- UDP ----------

def parse_udp_ports(nmap_output):

    ports = []

    for line in nmap_output.splitlines():

        m = re.search(r"(\d+)/udp\s+(\S+)\s+(\S+)", line)

        if m:

            port = m.group(1)
            state = m.group(2)
            service = m.group(3)

            # ONLY accept if open in state
            if "open" in state:
                ports.append((port, state, service))

    return ports


def run_recon_udp(target):

    folder = f"recon_{target}"
    os.makedirs(folder, exist_ok=True)

    # save
    udp_file = f"{folder}/nmap_udp.txt"

    adaptive_ports = [10, 5]
    found_ports = []
    raw_output = ""

    for tp in adaptive_ports:

        print(f"[cyan][*] UDP Scan Top {tp} → {target}[/]")

        output = run_cmd([
            "nmap",
            "-sU",
            "-Pn",
            "--top-ports", str(tp),
            target
        ])

        ports = parse_udp_ports(output)

        if ports:
            found_ports = ports
            raw_output = output
            print(f"[green][+] UDP ports detected (top {tp})[/]")
            break

    if not found_ports:
        print(f"[yellow][!] No UDP ports found on {target}[/]")
        print("[yellow][!] Ports may be open|filtered or silently dropped[/]")
        return

    # save output
    with open(udp_file, "w") as f:
        f.write(raw_output)

    render_udp_summary(target, udp_file)

    # intelligence phase
    for port, state, service in found_ports:

        if port == "161" or "snmp" in service.lower():
            snmp_intelligence(target, folder, auto_mode=True)

    # delete file after end process
    try:
        os.remove(udp_file)
    except:
        pass


def run_recon_all(target):

    run_recon_tcp(target)
    run_recon_udp(target)