import re
import subprocess
from rich import print
from rich.table import Table


def run_searchsploit(keyword):
    print(f"[cyan][*] Running searchsploit: {keyword}[/]")
    subprocess.run(["searchsploit", keyword], check=False)


def extract_service_versions(file):

    results = []

    with open(file) as f:
        for line in f:

            # match example:
            # 80/tcp open http Apache httpd 2.4.49
            match = re.search(r"\d+/tcp\s+open\s+\S+\s+(.+)", line)

            if match:
                service_banner = match.group(1).strip()
                results.append(service_banner)

    return results


def analyze_nmap_detail(file):

    print("\n[bold magenta][*] Recon Intelligence Analysis[/]\n")

    banners = extract_service_versions(file)

    if not banners:
        print("[yellow][!] No service banners detected[/]")
        return

    for banner in banners:

        banner_lower = banner.lower()

        # Apache
        if "apache" in banner_lower:
            print(f"[red][ALERT] {banner} detected[/]")
            run_searchsploit(banner)

        # OpenSSH
        elif "openssh" in banner_lower:
            print(f"[red][ALERT] {banner} detected[/]")
            run_searchsploit(banner)

        # SMB
        elif "microsoft-ds" in banner_lower or "smb" in banner_lower:
            print(f"[red][ALERT] SMB Service Found ({banner})[/]")
            print(" → Try enum4linux / smbclient / crackmapexec")

        # FTP
        elif "ftp" in banner_lower:
            print(f"[red][ALERT] FTP Service Found ({banner})[/]")
            print(" → Try anonymous login")

        # Jenkins
        elif "jenkins" in banner_lower:
            print(f"[red][ALERT] Jenkins detected ({banner})[/]")
            run_searchsploit("jenkins")

        # Tomcat
        elif "tomcat" in banner_lower:
            print(f"[red][ALERT] Tomcat detected ({banner})[/]")
            run_searchsploit("tomcat")

        # Generic Web
        elif "http" in banner_lower:
            print(f"[yellow][INFO] Web service detected ({banner})[/]")
            print(" → Run directory brute / check login panels")