import typer
import subprocess
import sys

from .modules.recon.recon import run_recon_tcp, run_recon_udp, run_recon_all
from .modules.payloads.revshell import run_revshell
from .modules.payloads.venom import run_venom

app = typer.Typer(
    help="""
🐟 smbr tools - Recon & Exploitation Assistant

Main Features:
• Fast TCP/UDP Recon
• SNMP Intelligence Enumeration
• Reverse Shell Generator
• msfvenom Payload Generator
• Interactive Arsenal Launcher (TUI)

Examples:

smbr recon 10.10.10.10
smbr recon 10.10.10.10 tcp
smbr recon 10.10.10.10 udp

smbr revshell 10.10.14.5 4444
smbr venom 10.10.14.5 4444

smbr arsenal
"""
)


# ---------- RECON ----------

@app.command(help="""
Recon Modes:

default  → Run TCP full scan + UDP adaptive scan
tcp      → Run TCP full scan + service detection
udp      → Run UDP adaptive scan + SNMP intelligence

Examples:

smbr recon 10.10.10.10
smbr recon 10.10.10.10 tcp
smbr recon 10.10.10.10 udp
""")
def recon(
    target: str,
    mode: str = typer.Argument("default")
):

    if mode == "tcp":
        run_recon_tcp(target)

    elif mode == "udp":
        run_recon_udp(target)

    else:
        run_recon_all(target)


# ---------- REVSHELL ----------

@app.command(help="""
Generate Reverse Shell Payloads

Examples:

smbr revshell
smbr revshell 10.10.14.5
smbr revshell 10.10.14.5 4444

If no IP/PORT provided:
• Tool will auto-detect tun0 IP
• Default port = 4444
""")
def revshell(
    lhost: str = typer.Argument(None),
    lport: int = typer.Argument(None)
):
    run_revshell(lhost, lport)


# ---------- VENOM ----------

@app.command(help="""
Generate msfvenom Payload File

Examples:

smbr venom
smbr venom 10.10.14.5
smbr venom 10.10.14.5 4444
""")
def venom(
    lhost: str = typer.Argument(None),
    lport: int = typer.Argument(None)
):
    run_venom(lhost, lport)


# ---------- ARSENAL (NEW) ----------

@app.command(help="""
Launch Interactive Pentest Arsenal (TUI)

Examples:

smbr arsenal
""")
def arsenal():
    subprocess.run(
        [sys.executable, "-m", "smbrlib.arsenal"]
    )


if __name__ == "__main__":
    app()