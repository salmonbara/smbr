#!/usr/bin/env python3
"""
smbr-arsenal - Command Launcher for smbr
A personal command inventory and launcher for pentesters.
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

USER_DIR    = Path.home() / ".smbr" / "arsenal"
CHEATS_FILE = USER_DIR / "cheats.json"
VARS_FILE   = USER_DIR / "vars.json"

# ─── Category colours ────────────────────────────────────────────────────────

_PALETTE = [
    "cyan", "magenta", "yellow", "green", "blue", "red",
    "bright_cyan", "bright_magenta", "bright_green",
]
_cat_colour_cache: dict = {}

def cat_colour(category: str) -> str:
    if category not in _cat_colour_cache:
        idx = len(_cat_colour_cache) % len(_PALETTE)
        _cat_colour_cache[category] = _PALETTE[idx]
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


def apply_vars(command: str, variables: dict) -> str:
    result = command
    for key, value in variables.items():
        result = result.replace(f"<{key}>", value)
    return result


def highlight_placeholders(command: str) -> str:
    """Color command text: placeholders = bold yellow, rest = cyan."""
    parts = re.split(r"(<[^>]+>)", command)
    result = ""
    for part in parts:
        if re.match(r"<[^>]+>", part):
            result += f"[bold yellow]{part}[/]"
        elif part:
            result += f"[cyan]{part}[/]"
    return result


def extract_placeholders(command: str) -> list:
    """Return list of unique placeholder names still in a command string."""
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

# ─── Modals ──────────────────────────────────────────────────────────────────

class HelpScreen(ModalScreen):
    BINDINGS = [("escape,q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        yield Container(
            Static(
                "[bold cyan]⚙  Keybindings[/]\n\n"
                "[yellow]/[/]          Search commands\n"
                "[yellow]Enter[/]      Run command (fill vars if needed)\n"
                "[yellow]s[/]          Set global variables\n"
                "[yellow]a[/]          Add new command\n"
                "[yellow]d[/]          Delete selected command\n"
                "[yellow]v[/]          View all variables\n"
                "[yellow]?[/]          This help screen\n"
                "[yellow]q / Ctrl+C[/]  Quit\n\n"
                "[bold cyan]⚙  Variables[/]\n\n"
                "Use  [bold yellow]<varname>[/]  in commands as placeholders.\n"
                "Global vars are saved to [dim]~/.smbr/arsenal/vars.json[/]\n\n"
                "[dim]Press Escape or q to close[/]",
                id="help-content",
            ),
            id="help-box",
        )

    def action_dismiss(self):
        self.dismiss()


class SetVarScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, cheats: list, variables: dict):
        super().__init__()
        self._cheats    = cheats
        self._variables = dict(variables)
        # รวม placeholder ทุกตัวจาก cheats ทั้งหมด (unique, sorted)
        seen, self._keys = set(), []
        for cheat in cheats:
            for p in re.findall(r"<([^>]+)>", cheat["command"]):
                if p not in seen:
                    seen.add(p)
                    self._keys.append(p)

    def compose(self) -> ComposeResult:
        widgets = [
            Static("[bold cyan]Set Variables[/]", id="setvar-title"),
            Static("[dim]Fill any fields you want · leave blank to skip[/]\n",
                   id="setvar-hint"),
        ]
        for key in self._keys:
            current = self._variables.get(key, "")
            widgets.append(Static(f"[bold yellow]<{key}>[/]", classes="setvar-label"))
            widgets.append(Input(
                value=current,
                placeholder=f"current: {current}" if current else f"e.g. {key}…",
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
            if val:  # ข้าม field ที่เว้นว่าง
                result[key] = val
        self.dismiss(result if result else None)

    def action_dismiss(self):
        self.dismiss(None)


class FillVarsScreen(ModalScreen):
    """Popup: prompt for every unfilled <placeholder> before running."""
    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, command: str, missing: list, variables: dict):
        super().__init__()
        self._command   = command
        self._missing   = missing
        self._variables = dict(variables)

    def compose(self) -> ComposeResult:
        plain    = apply_vars(self._command, self._variables)
        preview  = highlight_placeholders(plain)
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
            Input(placeholder="Category  (e.g. Web)",                  id="add-category"),
            Input(placeholder="Name  (e.g. Curl Headers)",             id="add-name"),
            Input(placeholder="Command  (use <var> for variables)",    id="add-command"),
            Input(placeholder="Description  (optional)",               id="add-desc"),
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
            Static(f"[bold cyan]Global Variables[/]\n\n{lines}\n\n[dim]Escape to close[/]",
                   id="vars-content"),
            id="vars-box",
        )

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

    HelpScreen, SetVarScreen, AddCommandScreen, VarsScreen, FillVarsScreen {
        align: center middle;
        background: $background 60%;
    }
    #help-box, #add-box, #vars-box {
        background: $surface;
        border: double $primary;
        padding: 1 2;
        width: 62;
        height: auto;
        align: center middle;
    }
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
        Binding("/", "focus_search",   "Search",    show=True),
        Binding("s", "set_var",        "Set Var",   show=True),
        Binding("a", "add_command",    "Add Cmd",   show=True),
        Binding("d", "delete_command", "Delete",    show=True),
        Binding("v", "view_vars",      "Variables", show=True),
        Binding("?", "help",           "Help",      show=True),
        Binding("q", "quit",           "Quit",      show=True),
    ]

    selected_category = reactive("All")
    search_query      = reactive("")

    def __init__(self):
        super().__init__()
        self.cheats    = load_cheats()
        self.variables = load_vars()

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
        if len(plain) > 80:
            plain = plain[:78] + "…"
        return highlight_placeholders(plain)

    def _build_table(self):
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_column("Category",          width=14)
        table.add_column("Name",              width=22)
        table.add_column("Command (preview)", width=68)
        table.add_column("Tags",              width=26)

        for cheat in self._filtered_cheats():
            colour = cat_colour(cheat["category"])
            tags   = "[dim]" + ", ".join(cheat.get("tags", [])) + "[/]" if cheat.get("tags") else ""
            table.add_row(
                f"[{colour}]{cheat['category']}[/]",
                f"[bold]{cheat['name']}[/]",
                self._render_cmd_preview(cheat["command"]),
                tags,
            )
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
        if 0 <= row < len(filtered):
            cheat = filtered[row]
            self.cheats.remove(cheat)
            save_cheats(self.cheats)
            self._build_category_list()
            self._build_table()
            self.notify(f"Deleted: [bold]{cheat['name']}[/]",
                        title="Deleted", severity="warning")

    def action_view_vars(self):
        self.push_screen(VarsScreen(self.variables))

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