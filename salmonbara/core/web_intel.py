import subprocess
import shutil
from rich import print


def tool_exists(name):
    return shutil.which(name) is not None


def run_cmd(cmd):

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True
    ).stdout


def analyze_web(url):

    print("[cyan][*] Grabbing headers[/]")

    headers = run_cmd(["curl", "-I", url])

    if "Apache" in headers:
        print("[yellow][INFO] Apache detected")

    print("[cyan][*] Fetching page[/]")

    page = run_cmd(["curl", "-s", url])

    if "wordpress" in page.lower():
        print("[red][ALERT] WordPress detected")

        if tool_exists("wpscan"):
            subprocess.run(["wpscan", "--url", url, "--enumerate", "vp"])

    if "joomla" in page.lower():
        print("[red][ALERT] Joomla detected")

        if tool_exists("joomscan"):
            subprocess.run(["joomscan", "-u", url])

    if "jenkins" in page.lower():
        print("[red][ALERT] Jenkins detected")

        subprocess.run(["searchsploit", "jenkins"])

    print("[cyan][*] Running ffuf directory scan[/]")

    subprocess.run([
        "ffuf",
        "-u", f"{url}/FUZZ",
        "-w", "/usr/share/seclists/Discovery/Web-Content/common.txt",
        "-mc", "200,204,301,302,307,401,403"
    ])