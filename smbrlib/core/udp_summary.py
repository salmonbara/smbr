import re
from rich import print
from rich.table import Table


def render_udp_summary(target, udp_file):

    table = Table(title=f"UDP Recon Summary → {target}")

    table.add_column("PORT")
    table.add_column("STATE")
    table.add_column("SERVICE")
    table.add_column("NEXT ACTION")

    actions = {
        "snmp": "Bruteforce community / snmp-check",
        "domain": "Try zone transfer (dig axfr)",
        "netbios-ns": "Try enum4linux / nbtscan",
        "ntp": "Try ntpdc query",
    }

    found = False

    with open(udp_file) as f:
        for line in f:

            m = re.search(r"(\d+/udp)\s+(\S+)\s+(\S+)", line)

            if m:
                port = m.group(1)
                state = m.group(2)
                service = m.group(3)

                # ⭐ SHOW ONLY open states
                if "open" not in state:
                    continue

                found = True

                action = actions.get(service, "")

                table.add_row(port, state, service, action)

    print()

    if not found:
        print(f"[yellow][!] No UDP open ports found on {target}[/]")
        print("[yellow][!] Ports may be silently dropped / filtered[/]")
        return

    print(table)