#!/usr/bin/env python3
"""
smbr-arsenal - Command Launcher for smbr
"""

import json
import re
import sys
import termios
import tty
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    ListItem,
    ListView,
    Static,
)

# ─── Paths ───────────────────────────────────────────────────────────────────

BUNDLE_DIR    = Path(__file__).parent
BUNDLE_CHEATS = BUNDLE_DIR / "cheats.json"

USER_DIR     = Path.home() / ".smbr" / "arsenal"
CHEATS_FILE  = USER_DIR / "cheats.json"
VARS_FILE     = USER_DIR / "vars.json"
SETTINGS_FILE = USER_DIR / "settings.json"

BUNDLE_PRIVESC = BUNDLE_DIR / "privesc.json"
PRIVESC_FILE   = USER_DIR / "privesc.json"

# ─── Default settings ────────────────────────────────────────────────────────

DEFAULT_SETTINGS = {
    "show_category": True,
    "show_name":     True,
    "show_command":  True,
    "show_tags":     True,
}

# ─── Category colours ────────────────────────────────────────────────────────

# Fixed colours per category — no random assignment
_CAT_COLOURS: dict = {
    "Recon":            "bright_cyan",
    "Web":              "bright_green",
    "SMB":              "yellow",
    "LDAP":             "magenta",
    "Kerberos":         "bright_magenta",
    "AD":               "cyan",
    "ADCS":             "bright_cyan",
    "Lateral Movement": "red",
    "Exploit":          "bright_magenta",
    "Post-Exploit":     "green",
    "File Transfer":    "yellow",
    "Remote":           "cyan",
    "Bruteforce":       "red",
    "Crack":            "magenta",
    "DB":               "green",
    # privesc
    "Linux":            "green",
    "Windows":          "cyan",
}
_FALLBACK_PALETTE = [
    "bright_cyan", "bright_magenta", "yellow",
    "bright_green", "magenta", "red",
]
_cat_colour_cache: dict = {}

def cat_colour(category: str) -> str:
    if category in _CAT_COLOURS:
        return _CAT_COLOURS[category]
    if category not in _cat_colour_cache:
        idx = len(_cat_colour_cache) % len(_FALLBACK_PALETTE)
        _cat_colour_cache[category] = _FALLBACK_PALETTE[idx]
    return _cat_colour_cache[category]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_cheats():
    USER_DIR.mkdir(parents=True, exist_ok=True)
    if not CHEATS_FILE.exists():
        if BUNDLE_CHEATS.exists():
            import shutil
            shutil.copy(BUNDLE_CHEATS, CHEATS_FILE)
        else:
            with open(CHEATS_FILE, "w") as f:
                json.dump([], f, indent=2)
    with open(CHEATS_FILE) as f:
        return json.load(f)


def save_cheats(cheats):
    with open(CHEATS_FILE, "w") as f:
        json.dump(cheats, f, indent=2)


def load_vars():
    USER_DIR.mkdir(parents=True, exist_ok=True)
    if not VARS_FILE.exists():
        with open(VARS_FILE, "w") as f:
            json.dump({}, f)
    with open(VARS_FILE) as f:
        return json.load(f)


def save_vars(v: dict):
    with open(VARS_FILE, "w") as f:
        json.dump(v, f, indent=2)


def load_settings() -> dict:
    USER_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    with open(SETTINGS_FILE) as f:
        saved = json.load(f)
    # merge with defaults so new keys are always present
    merged = dict(DEFAULT_SETTINGS)
    merged.update(saved)
    return merged


def save_settings(s: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)


def load_privesc() -> list:
    USER_DIR.mkdir(parents=True, exist_ok=True)
    if not PRIVESC_FILE.exists():
        if BUNDLE_PRIVESC.exists():
            import shutil
            shutil.copy(BUNDLE_PRIVESC, PRIVESC_FILE)
        else:
            with open(PRIVESC_FILE, "w") as f:
                json.dump([], f, indent=2)
    with open(PRIVESC_FILE) as f:
        return json.load(f)


def apply_vars(command: str, variables: dict) -> str:
    result = command
    for key, value in variables.items():
        result = result.replace(f"<{key}>", value)
    return result


def highlight_placeholders(command: str) -> str:
    parts = re.split(r"(<[^>]+>)", command)
    result = ""
    for part in parts:
        if re.match(r"<[^>]+>", part):
            result += f"[bold yellow]{part}[/]"
        elif part:
            result += f"[cyan]{part}[/]"
    return result


def extract_placeholders(command: str) -> list:
    found = re.findall(r"<([^>]+)>", command)
    seen, result = set(), []
    for p in found:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


def send_to_terminal(command: str):
    try:
        import fcntl
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        for char in command:
            fcntl.ioctl(fd, termios.TIOCSTI, char.encode())
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return True
    except Exception:
        return False


def copy_to_clipboard(text: str) -> bool:
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False

# ─── Modals ──────────────────────────────────────────────────────────────────

class HelpScreen(ModalScreen):
    BINDINGS = [("escape,q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        yield Container(
            Static(
                "[bold cyan]⚙  Keybindings[/]\n\n"
                "[yellow]/[/]              Search commands\n"
                "[yellow]Enter[/]          Run command (fill vars if needed)\n"
                "[yellow]Ctrl+C[/]         Copy command to clipboard\n"
                "[yellow]Ctrl+Shift+C[/]   Copy command to clipboard\n"
                "[yellow]s[/]              Set global variables\n"
                "[yellow]a[/]              Add new command\n"
                "[yellow]d[/]              Delete selected command (with confirm)\n"
                "[yellow]v[/]              View / clear all variables\n"
                "[yellow]t[/]              Column visibility settings\n"
                "[yellow]p[/]              PrivEsc reference guide\n"
                "[yellow]?[/]              This help screen\n"
                "[yellow]Ctrl+Q[/]         Quit\n\n"
                "[bold cyan]⚙  Variables[/]\n\n"
                "Use  [bold yellow]<varname>[/]  in commands as placeholders.\n"
                "Global vars saved to [dim]~/.smbr/arsenal/vars.json[/]\n\n"
                "[dim]Press Escape or q to close[/]",
                id="help-content",
            ),
            id="help-box",
        )

    def action_dismiss(self):
        self.dismiss()


class ConfirmDeleteScreen(ModalScreen):
    BINDINGS = [("escape,n", "dismiss", "Cancel")]

    def __init__(self, cheat_name: str):
        super().__init__()
        self._name = cheat_name

    def compose(self) -> ComposeResult:
        yield Container(
            Static(
                f"[bold red]Delete command?[/]\n\n"
                f"[bold]{self._name}[/]\n\n"
                "[dim]Press [bold yellow]y[/] to confirm · [bold yellow]Escape / n[/] to cancel[/]",
                id="confirm-content",
            ),
            id="confirm-box",
        )

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)

    def action_dismiss(self):
        self.dismiss(False)


class SettingsScreen(ModalScreen):
    """Toggle which columns are visible in the command table."""
    BINDINGS = [("escape,q", "dismiss", "Close")]

    COLUMN_LABELS = {
        "show_category": "Category",
        "show_name":     "Name",
        "show_command":  "Command",
        "show_tags":     "Tags",
    }

    def __init__(self, settings: dict):
        super().__init__()
        self._settings = dict(settings)

    def compose(self) -> ComposeResult:
        widgets = [
            Static("[bold cyan]⚙  Column Visibility[/]", id="settings-title"),
            Static("[dim]Space / click to toggle · Escape to close[/]\n", id="settings-hint"),
        ]
        for key, label in self.COLUMN_LABELS.items():
            widgets.append(
                Checkbox(label, value=self._settings.get(key, True), id=f"chk-{key}")
            )
        widgets.append(Static(
            "\n[dim]Changes apply immediately[/]",
            id="settings-footer",
        ))
        yield Container(*widgets, id="settings-box")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        key = event.checkbox.id.replace("chk-", "")
        self._settings[key] = event.value
        self.dismiss(self._settings)
        # re-open so user can keep toggling without reopening manually
        self.app.push_screen(SettingsScreen(self._settings), self.app._handle_settings)

    def action_dismiss(self):
        self.dismiss(None)


class SetVarScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Cancel")]

    # Only these vars are set globally — everything else is filled per-command
    GLOBAL_VARS = ["ip", "lhost", "lport", "user", "password", "domain", "dc_ip"]
    GLOBAL_HINTS = {
        "ip":       "Target IP  e.g. 10.10.10.10",
        "lhost":    "Attacker IP  e.g. 10.10.14.5",
        "lport":    "Listener port  e.g. 4444",
        "user":     "Username  e.g. Administrator",
        "password": "Password  e.g. Password123@",
        "domain":   "Domain name  e.g. corp.com",
        "dc_ip":    "Domain Controller IP  e.g. 10.10.10.1",
    }

    def __init__(self, cheats: list, variables: dict):
        super().__init__()
        self._cheats    = cheats
        self._variables = dict(variables)
        self._keys      = self.GLOBAL_VARS

    def compose(self) -> ComposeResult:
        widgets = [
            Static("[bold cyan]Set Global Variables[/]", id="setvar-title"),
            Static("[dim]These values apply to all commands · leave blank to skip[/]\n",
                   id="setvar-hint"),
        ]
        for key in self._keys:
            current = self._variables.get(key, "")
            hint    = self.GLOBAL_HINTS.get(key, f"e.g. {key}")
            widgets.append(Static(f"[bold yellow]<{key}>[/]", classes="setvar-label"))
            widgets.append(Input(
                value=current,
                placeholder=f"current: {current}" if current else hint,
                id=f"sv-{key}",
                classes="setvar-input",
            ))
        widgets.append(Static(
            "\n[dim]Enter moves to next · Enter on last field saves[/]",
            id="setvar-footer",
        ))
        yield Container(*widgets, id="setvar-box")

    def on_mount(self):
        if self._keys:
            self.query_one(f"#sv-{self._keys[0]}").focus()

    def on_input_submitted(self, event: Input.Submitted):
        idx = next(
            (i for i, k in enumerate(self._keys) if f"sv-{k}" == event.input.id),
            None,
        )
        if idx is None:
            return
        if idx < len(self._keys) - 1:
            self.query_one(f"#sv-{self._keys[idx + 1]}").focus()
        else:
            self._save()

    def _save(self):
        result = {}
        for key in self._keys:
            val = self.query_one(f"#sv-{key}", Input).value.strip()
            if val:
                result[key] = val
        self.dismiss(result if result else None)

    def action_dismiss(self):
        self.dismiss(None)


class FillVarsScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, command: str, missing: list, variables: dict):
        super().__init__()
        self._command   = command
        self._missing   = missing
        self._variables = dict(variables)

    def compose(self) -> ComposeResult:
        plain   = apply_vars(self._command, self._variables)
        preview = highlight_placeholders(plain)
        if len(plain) > 110:
            preview = highlight_placeholders(plain[:108]) + "[dim]…[/]"

        widgets = [
            Static("[bold cyan]⚡ Fill Variables[/]", id="fill-title"),
            Static(f"[dim]{preview}[/]\n", id="fill-preview"),
        ]
        for name in self._missing:
            widgets.append(Static(f"[bold yellow]<{name}>[/]", classes="fill-label"))
            widgets.append(Input(placeholder=f"Enter {name}…",
                                 id=f"fill-{name}", classes="fill-input"))
        widgets.append(Static(
            "\n[dim]Enter moves to next field · Enter on last field runs the command[/]",
            id="fill-hint",
        ))
        yield Container(*widgets, id="fill-box")

    def on_mount(self):
        self.query_one(f"#fill-{self._missing[0]}").focus()

    def on_input_submitted(self, event: Input.Submitted):
        idx = next(
            (i for i, n in enumerate(self._missing) if f"fill-{n}" == event.input.id),
            None,
        )
        if idx is None:
            return
        self._variables[self._missing[idx]] = event.value.strip()
        if idx < len(self._missing) - 1:
            self.query_one(f"#fill-{self._missing[idx + 1]}").focus()
        else:
            self._finalise()

    def _finalise(self):
        for name in self._missing:
            w = self.query_one(f"#fill-{name}", Input)
            if w.value.strip():
                self._variables[name] = w.value.strip()
        cmd = apply_vars(self._command, self._variables)
        self.dismiss((cmd, self._variables))

    def action_dismiss(self):
        self.dismiss(None)


class AddCommandScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold cyan]Add New Command[/]", id="add-title"),
            Input(placeholder="Category  (e.g. Web)",               id="add-category"),
            Input(placeholder="Name  (e.g. Curl Headers)",          id="add-name"),
            Input(placeholder="Command  (use <var> for variables)", id="add-command"),
            Input(placeholder="Description  (optional)",            id="add-desc"),
            Static("[dim]Enter on last field to save · Escape to cancel[/]"),
            id="add-box",
        )

    def on_mount(self):
        self.query_one("#add-category").focus()

    def on_input_submitted(self, event):
        if event.input.id == "add-desc":
            self._save()

    def _save(self):
        cat  = self.query_one("#add-category").value.strip()
        name = self.query_one("#add-name").value.strip()
        cmd  = self.query_one("#add-command").value.strip()
        desc = self.query_one("#add-desc").value.strip()
        if cat and name and cmd:
            self.dismiss({"category": cat, "name": name, "command": cmd,
                          "description": desc, "tags": []})
        else:
            self.dismiss(None)

    def action_dismiss(self):
        self.dismiss(None)


class VarsScreen(ModalScreen):
    BINDINGS = [("escape,q", "dismiss", "Close")]

    def __init__(self, variables: dict):
        super().__init__()
        self._vars = variables

    def compose(self) -> ComposeResult:
        if self._vars:
            lines = "\n".join(
                f"  [bold yellow]<{k}>[/] = [green]{v}[/]"
                for k, v in self._vars.items()
            )
        else:
            lines = "  [dim]No variables set yet. Press [yellow]s[/] to set one.[/]"
        yield Container(
            Static(
                f"[bold cyan]Global Variables[/]\n\n{lines}\n\n"
                "[dim]Press [yellow]c[/] to clear all · Escape to close[/]",
                id="vars-content",
            ),
            id="vars-box",
        )

    def on_key(self, event) -> None:
        if event.key == "c":
            self.dismiss("clear")

    def action_dismiss(self):
        self.dismiss(None)


# ─── PrivEsc Tab ─────────────────────────────────────────────────────────────

class PrivEscScreen(ModalScreen):
    """Full-screen PrivEsc reference — Category → Technique → Steps."""
    BINDINGS = [
        Binding("escape,q", "dismiss",  "Back"),
        Binding("ctrl+c",   "copy_cmd", "Copy", show=True),
    ]

    CAT_COLOURS = {"Linux": "green", "Windows": "cyan", "AD": "magenta"}

    def __init__(self, variables: dict):
        super().__init__()
        self._variables    = variables
        self._privesc      = load_privesc()
        self._categories   = sorted({e["category"] for e in self._privesc})
        self._sel_category = self._categories[0] if self._categories else "Linux"
        self._sel_tech_idx = 0   # index into technique list for current category

    # ── helpers ───────────────────────────────────────────────────────────

    def _techniques(self):
        return [e for e in self._privesc if e["category"] == self._sel_category]

    def _current_technique(self):
        techs = self._techniques()
        if 0 <= self._sel_tech_idx < len(techs):
            return techs[self._sel_tech_idx]
        return None

    def _colour(self):
        return self.CAT_COLOURS.get(self._sel_category, "yellow")

    # ── compose ───────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Container(id="pe-layout"):
            # Left — categories
            with Vertical(id="pe-cat-panel"):
                yield Static("🔓 PrivEsc", id="pe-cat-title")
                yield ListView(id="pe-cat-list")
            # Middle — techniques
            with Vertical(id="pe-tech-panel"):
                yield Static("Techniques", id="pe-tech-title")
                yield ListView(id="pe-tech-list")
            # Right — steps detail
            with Vertical(id="pe-step-panel"):
                yield Static("", id="pe-tech-name")
                yield Static("", id="pe-tech-desc")
                yield DataTable(id="pe-step-table", cursor_type="row")
                with Vertical(id="pe-step-detail"):
                    yield Static("", id="pe-step-cmd")
                    yield Static("", id="pe-step-note")
        yield Footer()

    def on_mount(self):
        self._build_cat_list()
        self._build_tech_list()
        self._build_step_table()
        self.query_one("#pe-cat-list").focus()

    # ── category panel ────────────────────────────────────────────────────

    def _build_cat_list(self):
        lv = self.query_one("#pe-cat-list", ListView)
        lv.clear()
        for cat in self._categories:
            colour = self.CAT_COLOURS.get(cat, "yellow")
            marker = "▶ " if cat == self._sel_category else "  "
            count  = sum(1 for e in self._privesc if e["category"] == cat)
            lv.append(ListItem(Static(
                f"{marker}[{colour}]{cat}[/] [dim]({count})[/]"
            )))

    # ── technique panel ───────────────────────────────────────────────────

    def _build_tech_list(self):
        lv     = self.query_one("#pe-tech-list", ListView)
        colour = self._colour()
        lv.clear()
        for i, tech in enumerate(self._techniques()):
            marker = "▶ " if i == self._sel_tech_idx else "  "
            lv.append(ListItem(Static(
                f"{marker}[{colour}]{tech['technique']}[/]"
            )))

    # ── step table ────────────────────────────────────────────────────────

    def _build_step_table(self):
        tech   = self._current_technique()
        colour = self._colour()

        # Header
        name = tech["technique"] if tech else ""
        desc = tech.get("description", "") if tech else ""
        self.query_one("#pe-tech-name").update(f"[bold {colour}]{name}[/]")
        self.query_one("#pe-tech-desc").update(f"[dim]{desc}[/]")

        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_column("#",    width=3)
        table.add_column("Note", width=36)
        table.add_column("Command (preview)", width=70)

        if tech:
            for s in tech.get("steps", []):
                cmd_preview = apply_vars(s["command"], self._variables)
                if len(cmd_preview) > 68:
                    cmd_preview = cmd_preview[:66] + "…"
                table.add_row(
                    f"[dim]{s['step']}[/]",
                    f"[{colour}]{s['note']}[/]",
                    f"[cyan]{cmd_preview}[/]",
                )
        self._update_step_detail()

    def _update_step_detail(self):
        tech = self._current_technique()
        if not tech:
            self.query_one("#pe-step-cmd").update("")
            self.query_one("#pe-step-note").update("")
            return

        steps = tech.get("steps", [])
        row   = self.query_one(DataTable).cursor_row
        if 0 <= row < len(steps):
            s   = steps[row]
            cmd = apply_vars(s["command"], self._variables)
            self.query_one("#pe-step-cmd").update(
                f"[bold]$ {highlight_placeholders(cmd)}[/]"
            )
            self.query_one("#pe-step-note").update(f"[dim]💡 {s['note']}[/]")
        else:
            self.query_one("#pe-step-cmd").update("")
            self.query_one("#pe-step-note").update("")

    # ── events ────────────────────────────────────────────────────────────

    def on_data_table_row_highlighted(self, _event):
        self._update_step_detail()

    def on_list_view_selected(self, event: ListView.Selected):
        lv = event.list_view

        if lv.id == "pe-cat-list":
            idx = lv.index
            if idx is not None and idx < len(self._categories):
                self._sel_category = self._categories[idx]
                self._sel_tech_idx = 0
                self._build_cat_list()
                self._build_tech_list()
                self._build_step_table()
                self.query_one("#pe-tech-list").focus()

        elif lv.id == "pe-tech-list":
            idx = lv.index
            if idx is not None and idx < len(self._techniques()):
                self._sel_tech_idx = idx
                self._build_tech_list()
                self._build_step_table()
                self.query_one(DataTable).focus()

    # ── actions ───────────────────────────────────────────────────────────

    def action_copy_cmd(self):
        tech  = self._current_technique()
        if not tech:
            return
        steps = tech.get("steps", [])
        row   = self.query_one(DataTable).cursor_row
        if 0 <= row < len(steps):
            cmd = apply_vars(steps[row]["command"], self._variables)
            if copy_to_clipboard(cmd):
                self.notify(f"Copied step {steps[row]['step']}", title="Clipboard")

    def action_dismiss(self):
        self.dismiss()


# ─── Main App ────────────────────────────────────────────────────────────────

class Arsenal(App):
    CSS = """
    Screen { background: $surface; }

    #main-layout { layout: horizontal; height: 1fr; }

    #left-panel {
        width: 26;
        border: solid $primary;
        padding: 0 1;
        overflow-y: auto;
    }
    #left-title {
        color: $primary;
        text-style: bold;
        padding: 0 0 1 0;
        border-bottom: solid $primary-darken-2;
    }
    #category-list               { background: transparent; border: none; padding: 0; }
    #category-list > ListItem    { background: transparent; padding: 0 1; }
    #category-list > ListItem.--highlight { background: $primary-darken-2; }
    #category-list > ListItem:hover       { background: $primary-darken-3; }

    #right-panel   { width: 1fr; layout: vertical; }
    #search-bar    { height: 3; border: solid $primary; margin: 0 0 0 1; }
    #command-table { height: 1fr; margin: 0 0 0 1; border: solid $primary; }

    #detail-panel {
        height: 7;
        margin: 0 0 0 1;
        border: solid $accent;
        padding: 0 1;
    }
    #detail-title   { color: $accent; text-style: bold; }
    #detail-command { text-style: bold; }
    #detail-desc    { color: $text-muted; }
    #detail-vars    { color: $warning; }

    PrivEscScreen {
        align: center middle;
        background: $surface;
    }
    #pe-layout { layout: horizontal; height: 1fr; }

    #pe-cat-panel {
        width: 18;
        border: solid $success;
        padding: 0 1;
    }
    #pe-cat-title {
        color: $success;
        text-style: bold;
        padding: 0 0 1 0;
        border-bottom: solid $success-darken-2;
    }
    #pe-cat-list             { background: transparent; border: none; padding: 0; }
    #pe-cat-list > ListItem  { background: transparent; padding: 0 1; }
    #pe-cat-list > ListItem.--highlight { background: $success-darken-2; }

    #pe-tech-panel {
        width: 28;
        border: solid $primary;
        padding: 0 1;
    }
    #pe-tech-title {
        color: $primary;
        text-style: bold;
        padding: 0 0 1 0;
        border-bottom: solid $primary-darken-2;
    }
    #pe-tech-list             { background: transparent; border: none; padding: 0; }
    #pe-tech-list > ListItem  { background: transparent; padding: 0 1; }
    #pe-tech-list > ListItem.--highlight { background: $primary-darken-2; }

    #pe-step-panel  { width: 1fr; layout: vertical; padding: 0 1; border: solid $accent; }
    #pe-tech-name   { text-style: bold; padding: 0 0 0 0; }
    #pe-tech-desc   { color: $text-muted; padding: 0 0 1 0; border-bottom: solid $accent-darken-3; }
    #pe-step-table  { height: 1fr; }
    #pe-step-detail { height: 5; border: solid $accent-darken-2; padding: 0 1; margin-top: 1; }
    #pe-step-cmd    { text-style: bold; }
    #pe-step-note   { color: $text-muted; }

    HelpScreen, SetVarScreen, AddCommandScreen, VarsScreen,
    FillVarsScreen, ConfirmDeleteScreen, SettingsScreen {
        align: center middle;
        background: $background 60%;
    }
    #help-box, #add-box, #vars-box, #confirm-box {
        background: $surface;
        border: double $primary;
        padding: 1 2;
        width: 62;
        height: auto;
        align: center middle;
    }
    #confirm-box  { border: double $error; width: 50; }
    #settings-box {
        background: $surface;
        border: double $primary;
        padding: 1 2;
        width: 44;
        height: auto;
        align: center middle;
    }
    #settings-title  { text-style: bold; margin-bottom: 0; }
    #settings-hint   { color: $text-muted; }
    #settings-footer { color: $text-muted; }
    #settings-box Checkbox { margin: 0 0 0 1; }

    #confirm-content { width: 100%; }
    #help-content, #vars-content { width: 100%; }
    #add-title { margin-bottom: 1; }
    #add-box Input { margin-bottom: 1; }

    #setvar-box {
        background: $surface;
        border: double $primary;
        padding: 1 2;
        width: 68;
        height: auto;
        max-height: 80vh;
        overflow-y: auto;
        align: center middle;
    }
    #setvar-title  { text-style: bold; margin-bottom: 0; }
    #setvar-hint   { color: $text-muted; }
    #setvar-footer { color: $text-muted; }
    .setvar-label  { color: $warning; margin-top: 1; }
    .setvar-input  { margin-bottom: 0; }

    #fill-box {
        background: $surface;
        border: double $accent;
        padding: 1 2;
        width: 74;
        height: auto;
        align: center middle;
    }
    #fill-title   { text-style: bold; }
    #fill-preview { color: $text-muted; }
    #fill-hint    { color: $text-muted; }
    .fill-label   { color: $warning; }
    .fill-input   { margin-bottom: 1; }
    """

    BINDINGS = [
        Binding("/",           "focus_search",   "Search",    show=True),
        Binding("ctrl+c",      "copy_command",   "Copy",      show=True),
        Binding("ctrl+shift+c","copy_command",   "Copy",      show=False),
        Binding("s",           "set_var",        "Set Var",   show=True),
        Binding("a",           "add_command",    "Add Cmd",   show=True),
        Binding("d",           "delete_command", "Delete",    show=True),
        Binding("v",           "view_vars",      "Variables", show=True),
        Binding("t",           "settings",       "Columns",   show=True),
        Binding("?",           "help",           "Help",      show=True),
        Binding("ctrl+q",      "quit",           "Quit",      show=True),
        Binding("q",           "quit",           "Quit",      show=False),
        Binding("p",           "privesc",        "PrivEsc",   show=True),
    ]

    selected_category = reactive("All")
    search_query      = reactive("")

    def __init__(self):
        super().__init__()
        self.cheats    = load_cheats()
        self.variables = load_vars()
        self.settings  = load_settings()

    # ── Compose ───────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-layout"):
            with Vertical(id="left-panel"):
                yield Static("⚡ Categories", id="left-title")
                yield ListView(id="category-list")
            with Vertical(id="right-panel"):
                yield Input(placeholder="🔍  Search commands...", id="search-bar")
                yield DataTable(id="command-table", cursor_type="row")
                with Vertical(id="detail-panel"):
                    yield Static("", id="detail-title")
                    yield Static("", id="detail-command")
                    yield Static("", id="detail-desc")
                    yield Static("", id="detail-vars")
        yield Footer()

    def on_mount(self):
        self._build_category_list()
        self._build_table()
        self.query_one(DataTable).focus()

    # ── Category list ─────────────────────────────────────────────────────

    def _build_category_list(self):
        lv = self.query_one("#category-list", ListView)
        lv.clear()
        categories = ["All"] + sorted({c["category"] for c in self.cheats})
        for cat in categories:
            count  = len(self.cheats) if cat == "All" else sum(
                1 for c in self.cheats if c["category"] == cat
            )
            colour = cat_colour(cat) if cat != "All" else "white"
            marker = "▶ " if cat == self.selected_category else "  "
            lv.append(ListItem(Static(
                f"{marker}[{colour}]{cat}[/] [dim]({count})[/]"
            )))

    # ── Command table ─────────────────────────────────────────────────────

    def _filtered_cheats(self):
        q      = self.search_query.lower()
        result = self.cheats
        if self.selected_category != "All":
            result = [c for c in result if c["category"] == self.selected_category]
        if q:
            result = [
                c for c in result
                if q in c["name"].lower()
                or q in c["command"].lower()
                or q in c.get("description", "").lower()
                or any(q in t.lower() for t in c.get("tags", []))
            ]
        return result

    def _render_cmd_preview(self, command: str) -> str:
        plain = apply_vars(command, self.variables)
        max_w = getattr(self, "_cmd_preview_width", 78)
        if len(plain) > max_w:
            plain = plain[:max_w - 2] + "…"
        return highlight_placeholders(plain)

    def _build_table(self):
        table = self.query_one(DataTable)
        table.clear(columns=True)

        s = self.settings

        # Fixed widths for non-command columns (min sizes)
        FIXED = {"category": 14, "name": 22, "tags": 24}
        # Total usable width (left panel=26 + borders, right panel fills rest)
        # We use console width minus left panel and padding as approximation
        try:
            total_w = self.app.console.width - 30  # subtract left panel + borders
        except Exception:
            total_w = 100

        show_cat  = s.get("show_category", True)
        show_name = s.get("show_name",     True)
        show_cmd  = s.get("show_command",  True)
        show_tags = s.get("show_tags",     True)

        # Fallback: always show command if everything hidden
        if not any([show_cat, show_name, show_cmd, show_tags]):
            show_cmd = True

        # Calculate fixed column space consumed
        fixed_used = 0
        if show_cat:  fixed_used += FIXED["category"] + 2
        if show_name: fixed_used += FIXED["name"] + 2
        if show_tags: fixed_used += FIXED["tags"] + 2

        # Command column gets whatever is left (min 30)
        cmd_width = max(30, total_w - fixed_used) if show_cmd else 0

        # Register columns in order with dynamic widths
        if show_cat:  table.add_column("Category",          width=FIXED["category"])
        if show_name: table.add_column("Name",              width=FIXED["name"])
        if show_cmd:  table.add_column("Command (preview)", width=cmd_width)
        if show_tags: table.add_column("Tags",              width=FIXED["tags"])

        # Also update preview renderer to use new cmd_width
        self._cmd_preview_width = cmd_width - 2

        for cheat in self._filtered_cheats():
            colour   = cat_colour(cheat["category"])
            tags_str = "[dim]" + ", ".join(cheat.get("tags", [])) + "[/]" if cheat.get("tags") else ""
            row = []
            if show_cat:  row.append(f"[{colour}]{cheat['category']}[/]")
            if show_name: row.append(f"[bold]{cheat['name']}[/]")
            if show_cmd:  row.append(self._render_cmd_preview(cheat["command"]))
            if show_tags: row.append(tags_str)
            table.add_row(*row)

        self._update_detail()

    # ── Detail panel ──────────────────────────────────────────────────────

    def _update_detail(self):
        table    = self.query_one(DataTable)
        filtered = self._filtered_cheats()
        row      = table.cursor_row
        if 0 <= row < len(filtered):
            cheat    = filtered[row]
            colour   = cat_colour(cheat["category"])
            cmd_full = apply_vars(cheat["command"], self.variables)
            unfilled = extract_placeholders(cmd_full)
            cmd_rich = highlight_placeholders(cmd_full)

            self.query_one("#detail-title").update(
                f"[bold {colour}]{cheat['name']}[/]  [dim][{colour}]{cheat['category']}[/][/]"
            )
            self.query_one("#detail-command").update(f"[bold]$ {cmd_rich}[/]")
            self.query_one("#detail-desc").update(f"[dim]{cheat.get('description', '')}[/]")
            if unfilled:
                varlist = "  ".join(f"[bold yellow]<{v}>[/]" for v in unfilled)
                self.query_one("#detail-vars").update(
                    f"[yellow]⚠ needs:[/]  {varlist}  [dim](Enter → fill now)[/]"
                )
            else:
                self.query_one("#detail-vars").update("[green]✓ ready to run[/]")
        else:
            for wid in ["#detail-title", "#detail-command", "#detail-desc", "#detail-vars"]:
                self.query_one(wid).update("")

    # ── Events ────────────────────────────────────────────────────────────

    def on_data_table_row_highlighted(self, _event):
        self._update_detail()

    def on_data_table_row_selected(self, event):
        filtered = self._filtered_cheats()
        row      = event.cursor_row
        if not (0 <= row < len(filtered)):
            return

        cheat   = filtered[row]
        cmd     = apply_vars(cheat["command"], self.variables)
        missing = extract_placeholders(cmd)

        if missing:
            def handle(result):
                if result:
                    final_cmd, updated_vars = result
                    self.variables.update(updated_vars)
                    save_vars(self.variables)
                    self._build_table()
                    self.exit(final_cmd)
            self.push_screen(
                FillVarsScreen(cheat["command"], missing, self.variables),
                handle,
            )
        else:
            self.exit(cmd)

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search-bar":
            self.search_query = event.value
            self._build_table()

    def on_list_view_selected(self, _event: ListView.Selected):
        lv         = self.query_one("#category-list", ListView)
        categories = ["All"] + sorted({c["category"] for c in self.cheats})
        idx        = lv.index
        if idx is not None and idx < len(categories):
            self.selected_category = categories[idx]
            self._build_table()
            self._build_category_list()
            self.query_one(DataTable).focus()

    # ── Actions ───────────────────────────────────────────────────────────

    def action_focus_search(self):
        self.query_one("#search-bar").focus()

    def action_copy_command(self):
        """Ctrl+C / Ctrl+Shift+C — copy selected command to clipboard."""
        filtered = self._filtered_cheats()
        table    = self.query_one(DataTable)
        row      = table.cursor_row
        if not (0 <= row < len(filtered)):
            return
        cheat = filtered[row]
        cmd   = apply_vars(cheat["command"], self.variables)
        if copy_to_clipboard(cmd):
            self.notify(f"Copied: [bold]{cheat['name']}[/]", title="Clipboard")
        else:
            self.notify("pyperclip not available", title="Copy failed", severity="warning")

    def action_set_var(self):
        def handle(result):
            if result:
                self.variables.update(result)
                save_vars(self.variables)
                self._build_table()
                names = ", ".join(f"[bold yellow]<{k}>[/]" for k in result)
                self.notify(f"Updated: {names}", title="Variables Set")
        self.push_screen(SetVarScreen(self.cheats, self.variables), handle)

    def action_add_command(self):
        def handle(result):
            if result:
                self.cheats.append(result)
                save_cheats(self.cheats)
                self._build_category_list()
                self._build_table()
                self.notify(f"Added: [bold]{result['name']}[/]", title="Command Added")
        self.push_screen(AddCommandScreen(), handle)

    def action_delete_command(self):
        table    = self.query_one(DataTable)
        filtered = self._filtered_cheats()
        row      = table.cursor_row
        if not (0 <= row < len(filtered)):
            return
        cheat = filtered[row]

        def handle(confirmed):
            if confirmed:
                self.cheats.remove(cheat)
                save_cheats(self.cheats)
                self._build_category_list()
                self._build_table()
                self.notify(f"Deleted: [bold]{cheat['name']}[/]",
                            title="Deleted", severity="warning")

        self.push_screen(ConfirmDeleteScreen(cheat["name"]), handle)

    def action_view_vars(self):
        def handle(result):
            if result == "clear":
                self.variables = {}
                save_vars(self.variables)
                self._build_table()
                self.notify("All variables cleared", title="Variables", severity="warning")
        self.push_screen(VarsScreen(self.variables), handle)

    def action_settings(self):
        self.push_screen(SettingsScreen(self.settings), self._handle_settings)

    def _handle_settings(self, result):
        if result:
            self.settings = result
            save_settings(self.settings)
            self._build_table()

    def action_privesc(self):
        self.push_screen(PrivEscScreen(self.variables))

    def action_help(self):
        self.push_screen(HelpScreen())


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    app    = Arsenal()
    result = app.run()
    if result:
        if not send_to_terminal(result):
            print(result)


if __name__ == "__main__":
    main()