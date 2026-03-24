# 🐟 smbr — Pentest Recon & Exploitation Assistant

A fast, modular CLI tool for penetration testers and CTF players. `smbr` automates the tedious parts of initial enumeration, payload generation, and command lookup so you can focus on actually hacking.

---

## ✨ Features

| Module | Description |
|--------|-------------|
| **Arsenal TUI** | Full-screen command browser with variable substitution |
| **TCP Recon** | Full port scan → service detection → summary report |
| **UDP Recon** | Adaptive scan with automatic SNMP intelligence |
| **SNMP Intel** | Community string bruteforce + output analysis |
| **Web Enum** | Auto-detect CMS, run ffuf, wpscan, joomscan |
| **Reverse Shell** | Interactive generator (bash, python, php, powershell) |
| **msfvenom** | Guided payload builder for Windows & Linux |

---

## ⚙️ Requirements

- Python 3.8+
- `nmap` installed and in PATH
- Optional tools (used automatically if found): `onesixtyone`, `snmp-check`, `ffuf`, `wpscan`, `joomscan`, `searchsploit`, `msfvenom`, `rlwrap`

---

## 📦 Installation

### One-line install

```bash
curl -fsSL https://raw.githubusercontent.com/salmonbara/smbr/main/install.sh | bash
```

That's it. The script will automatically:

- Check Python 3.8+ and git
- Clone the repo to `~/.smbr/src`
- Install dependencies (`typer`, `rich`, `textual`, `pyperclip`)
- Add `smbr` and `s` commands to your PATH

### Updating

Run the same command again — it will `git pull` and reinstall cleanly.

```bash
curl -fsSL https://raw.githubusercontent.com/salmonbara/smbr/refs/heads/master/install.sh | bash
```

### Manual install (alternative)

```bash
git clone https://github.com/salmonbara/smbr
cd smbr
bash install.sh
```

### Verify installation

```bash
smbr --help
```

---

## 🚀 Usage

### Arsenal TUI

```bash
smbr arsenal
# or use the shortcut:
s
```

A full-screen interactive command browser powered by [Textual](https://textual.textualize.io/).

**Keybindings:**

| Key | Action |
|-----|--------|
| `/` | Search commands |
| `Enter` | Run / copy selected command |
| `s` | Set global variables (e.g. `<ip>`, `<lhost>`) |
| `v` | View all saved variables |
| `a` | Add a new command |
| `d` | Delete selected command |
| `?` | Help screen |
| `q` | Quit |

**Variable substitution:**  
Commands use `<placeholder>` syntax. Press `s` to set global variables (saved to `~/.smbr/arsenal/vars.json`), or fill them in per-run when prompted.

```
nmap -sV -sC -p- <ip> -oN scan_<ip>.txt
                  ^^^        ^^^
             auto-filled from saved vars
```

Custom commands are saved to `~/.smbr/arsenal/cheats.json` and persist across sessions.

---

### Recon

```bash
# Full recon (TCP + UDP)
smbr recon <target>

# TCP only — full port scan + service detection
smbr recon <target> tcp

# UDP only — adaptive scan + SNMP intelligence
smbr recon <target> udp
```

**Example:**

```bash
smbr recon 10.10.10.10
smbr recon 10.10.10.10 tcp
smbr recon 10.10.10.10 udp
```

**What happens during TCP recon:**

1. Full port scan (`nmap -p- --min-rate 1000`)
2. Service & version detection on open ports (`nmap -sC -sV`)
3. Summary report with next-step hints

**What happens during UDP recon:**

1. Adaptive scan (top 10 → top 5 ports)
2. Auto-runs SNMP community bruteforce if port 161 is open
3. SNMP output is color-coded: 🔴 critical keywords, 🟡 interesting, 🔵 info

Output files are saved under `recon_<target>/`.

---

### Reverse Shell Generator

```bash
smbr revshell                        # Interactive (auto-detects tun0 IP)
smbr revshell <lhost>                # Specify LHOST
smbr revshell <lhost> <lport>        # Specify LHOST + LPORT
```

**Supported payloads:**

| OS | Type |
|----|------|
| Linux | bash, python3, php |
| Windows | powershell |

- Generated payload is **automatically copied to clipboard**
- Option to start a `rlwrap nc` listener immediately after

---

### msfvenom Payload Generator

```bash
smbr venom                           # Fully interactive
smbr venom <lhost>
smbr venom <lhost> <lport>
```

Guides you through:

- OS selection (Windows / Linux)
- Payload type (Reverse Shell / Meterpreter)
- Output format (exe, ps1, bat, aspx, elf, sh, php)
- Filename

---

## 📁 Project Structure

```
smbr/
├── smbr                        # Entry point (CLI script)
├── install.sh                  # Installer
├── requirements.txt
└── smbrlib/
    ├── cli.py                  # Typer CLI definitions
    ├── core/
    │   ├── recon_summary.py    # TCP scan parser + summary renderer
    │   ├── recon_intel.py      # Service banner analysis + searchsploit
    │   ├── udp_summary.py      # UDP scan results renderer
    │   ├── udp_intel.py        # SNMP bruteforce + output highlighter
    │   ├── web_intel.py        # Web fingerprinting + tool runner
    │   └── utils_output.py     # Output directory helper
    ├── modules/
    │   ├── recon/recon.py      # TCP + UDP recon orchestration
    │   ├── payloads/
    │   │   ├── revshell.py     # Reverse shell generator
    │   │   └── venom.py        # msfvenom wrapper
    │   └── web/web_enum.py     # Web enumeration engine
    └── arsenal/
        ├── arsenal.py          # Textual TUI app
        ├── cheats.json         # Built-in command library
        └── __main__.py
```

---

## 🗂️ Built-in Arsenal Commands

The Arsenal ships with 20 ready-to-use commands across these categories:

| Category | Commands |
|----------|----------|
| Recon | Nmap Full, Quick, UDP |
| Web | Gobuster, Ffuf, Nikto, SQLMap |
| SMB | Enum4linux, SMBMap |
| LDAP | Anonymous enum, User enum |
| Kerberos | AS-REP Roast, Kerberoast |
| Exploit | MSFvenom EXE, Python reverse shell |
| Post-Exploit | LinPEAS, WinPEAS, Netcat listener |
| Crack | Hashcat, John the Ripper |

---

## ⚠️ Disclaimer

This tool is intended for **authorized penetration testing, CTF competitions, and security research only**.  
Do not use against systems you do not have explicit permission to test.  
The author is not responsible for any misuse.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
