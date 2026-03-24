import re
from rich import print
from rich.panel import Panel


def parse_tcp_ports(file):
    results = []
    if not file:
        return results

    with open(file) as f:
        for line in f:
            m = re.search(r"(\d+)/tcp\s+open\s+(\S+)", line)
            if m:
                results.append((m.group(1), m.group(2)))
    return results


def parse_service_versions(file):

    results = []
    if not file:
        return results

    with open(file) as f:
        for line in f:
            m = re.search(r"\d+/\w+\s+open\s+\S+\s+(.+)", line)
            if m:
                results.append(m.group(1))
    return results


def detect_web(file):

    findings = []
    if not file:
        return findings

    with open(file) as f:
        content = f.read().lower()

        if "joomla" in content:
            findings.append("Joomla detected")

        if "wordpress" in content:
            findings.append("WordPress detected")

        if "php/" in content:
            findings.append("PHP detected")

        if "robots.txt" in content:
            findings.append("robots.txt present")

    return findings


def render_summary(target, tcp_file=None, service_file=None):

    ports = parse_tcp_ports(tcp_file)
    services = parse_service_versions(service_file)
    web = detect_web(service_file)

    port_text = "\n".join([f"{p}  {s}" for p, s in ports]) or "None"
    service_text = "\n".join(services) or "Unknown"
    web_text = "\n".join(web) or "None"

    hint = []

    if any("http" in s for _, s in ports):
        hint.append(f"Run: smbr web {target}")

    if any("ssh" in s for _, s in ports):
        hint.append("Try SSH creds reuse")

    if any("mysql" in s for _, s in ports):
        hint.append("Try MySQL bruteforce")

    hint_text = "\n".join(hint) or "Manual enumeration"

    output = f"""
TARGET: {target}

OPEN PORTS
----------
{port_text}

SERVICE INFO
----------
{service_text}

WEB FINDINGS
----------
{web_text}

NEXT ACTION
----------
{hint_text}
"""

    print(Panel(output, title="RECON SUMMARY", border_style="green"))