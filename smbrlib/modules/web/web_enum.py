import subprocess
import shutil
from rich import print
from ...core.web_intel import analyze_web


COMMON_WEB_PORTS = [
    80, 443, 8000, 8080, 8443, 8888, 3000
]


def tool_exists(name):
    return shutil.which(name) is not None


def build_urls(target, ports):

    urls = []

    for p in ports:

        if p == 80:
            urls.append(f"http://{target}")

        elif p == 443:
            urls.append(f"https://{target}")

        else:
            urls.append(f"http://{target}:{p}")

    return urls


def run_web_enum(target):

    print("\n[bold cyan][*] Web Enumeration Engine[/]")

    open_ports = input("Enter web ports (ex: 80,443,8080): ")

    ports = [int(x.strip()) for x in open_ports.split(",")]

    urls = build_urls(target, ports)

    for url in urls:

        print(f"\n[bold magenta][*] Enumerating → {url}[/]")

        analyze_web(url)