"""Simple TUI for Kherimoya server management."""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable, Label, Button, Input
from textual.containers import Vertical, Horizontal, Grid
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.message import Message
from typing import cast
import sys

try:
    import endstone
except ImportError:
    raise ImportError("Endstone module not found. Please install it with 'pip install endstone'!")

PROJECT_PATH = Path(__file__).parent.resolve()
if not Path(PROJECT_PATH / "core").is_dir():
    try:
        sys.path.append(str(PROJECT_PATH.parent))
        from core.servers import ServerManager, KherimoyaServer
        from core.constants import DELIMITER
    except ImportError:
        raise ImportError("core/ module not found. Ensure this script is run from the project root or the file structure is correct.")
else:
    from core.servers import ServerManager, KherimoyaServer
    from core.constants import DELIMITER


class InputModal(Static):

    class Submitted(Message):
        def __init__(self, value: str, action: str):
            super().__init__()
            self.value = value
            self.action = action

    def __init__(self, prompt: str, action: str):
        super().__init__(id="input_modal")
        self.prompt = prompt
        self.action = action

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self.prompt),
            Input(id="modal_input"),
            Horizontal(
                Button("ok", id="ok"),
                Button("cancel", id="cancel"),
            ),
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "ok":
            value = self.query_one("#modal_input", Input).value
            self.post_message(self.Submitted(value, self.action))
        self.remove()

class ServerDetails(Static):
    def __init__(self):
        super().__init__("no server selected", id="server_details")

    def update_details(self, server: KherimoyaServer | None):
        if server is None:
            self.update("no server selected")
            return
        
        status = "running" if server.running else "stopped"
        
        content = f"""
        [b]name:[/b] {server.name}
        [b]id:[/b] {server.server_id or '[i]no id[/i]'}
        [b]path:[/b] {server.path}
        [b]status:[/b] [ {status} ]
        """
        self.update(content)


class ServerList(Static):
    
    def compose(self) -> ComposeResult:
        yield DataTable(id="server_data_table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        
        table.add_columns("status", "name", "id", "exists")
        
        cast(KherimoyaManagerApp, self.app).load_server_data()

    def update_list(self, servers: list[KherimoyaServer]):
        table = self.query_one(DataTable)
        table.clear()
        
        for server in servers:
            status = "[bold white]☐[/]"
            if server.running:
                status = "[bold green]■[/]"
            elif not server.exists:
                status = "[bold yellow]? / missing[/]"
                
            exists_status = "[green]yes[/]" if server.exists else "[red]no[/]"
            
            row_key_value = server.server_id if server.server_id else str(server.path)
            
            table.add_row(
                status, 
                server.name, 
                server.server_id or "[i]no id[/i]", 
                exists_status,
                key=server.server_id
            )
            
        if table.row_count > 0:
            table.focus()

class KherimoyaManagerApp(App):
    
    BINDINGS = [
        Binding("q", "quit", "quit", show=True),
        Binding("r", "refresh_data", "refresh", show=True),
        Binding("s", "start_server", "start", show=True),
        Binding("t", "stop_server", "stop", show=True),
        Binding("c", "resolve_conflicts", "fix ids", show=True),
        Binding("n", "create_new_server", "new", show=True),
        Binding("d", "delete_selected_server", "delete", show=True),
        Binding("e", "rename_selected_server", "rename", show=True),
    ]

    CSS = """
    #server_details {
        height: auto;
        padding: 1;
        border: solid dodgerblue;
        width: 100%;
    }
    #actions {
        height: auto;
        padding: 1;
        border: solid magenta;
        width: 100%;
        align-horizontal: left;
    }
    #actions > Button {
        margin-right: 1;
    }
    #status_message {
        color: yellow;
        padding: 0 1;
    }
    Container {
        height: 100%;
    }
    #main_grid {
        grid-size: 1;
        grid-rows: 1fr auto;
        height: 100%;
    }
    #input_modal {
        border: solid cyan;
        padding: 1;
        width: 50%;
        height: auto;
        layer: modal;
    }
    """

    def __init__(self):
        super().__init__()
        self.server_manager = ServerManager(PROJECT_PATH)
        self.servers: list[KherimoyaServer] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        
        with Grid(id="main_grid"):
            yield ServerList(id="server_list_container")
            yield Label("", id="status_message")
            
            with Vertical(id="side_panel"):
                yield ServerDetails()
                with Horizontal(id="actions"):
                    yield Button("start (s)", variant="success")
                    yield Button("stop (t)", variant="warning")
                    yield Button("refresh (r)", variant="primary")
                    #yield Button("fix ids (c)", variant="error")
                    yield Button("new (n)", variant="success")
                    yield Button("delete (d)", variant="error")
                    yield Button("rename (e)", variant="primary")

    def on_mount(self) -> None:
        cast(Label, self.query_one("#status_message")).update("ready.")

    def load_server_data(self):
        self.servers = self.server_manager.list_server_objects()
        try:
            self.query_one(ServerList).update_list(self.servers)
        except NoMatches:
            pass

    def get_selected_server(self) -> KherimoyaServer | None:
        try:
            table = cast(DataTable, self.query_one(DataTable))
            row_key_obj = table.highlighted_row_key
            
            # Check if there is a highlighted key object and if its value is a string
            if row_key_obj is None or row_key_obj.value is None:
                return None
            
            row_key = str(row_key_obj.value)
            
            for server in self.servers:
                # only compare if the server itself has an ID
                if server.server_id is not None and str(server.server_id) == row_key:
                    return server
                
            return None
        except Exception:
            return None

    async def action_quit(self):
        self.exit()

    def _resolve_conflicts_silent(self):
        try:
            self.server_manager.resolve_id_conflicts()
        except Exception:
            pass

    def action_refresh_data(self):
        self._resolve_conflicts_silent()
        self.load_server_data()
        cast(Label, self.query_one("#status_message")).update("server list refreshed.")

    def action_resolve_conflicts(self):
        try:
            self.server_manager.resolve_id_conflicts()
            self.action_refresh_data()
            cast(Label, self.query_one("#status_message")).update("id conflicts resolved. refresh again if needed.")
        except Exception as e:
            cast(Label, self.query_one("#status_message")).update(f"error resolving conflicts: {type(e).__name__}")

    def action_start_server(self):
        server = self.get_selected_server()
        if not server:
            cast(Label, self.query_one("#status_message")).update("select a server to start.")
            return

        cast(Label, self.query_one("#status_message")).update(f"attempting to start server: {server.name}...")
        
        try:
            server.actions.start_server(method="tmux")
            cast(Label, self.query_one("#status_message")).update(f"server {server.name} start command sent.")
        except Exception as e:
            cast(Label, self.query_one("#status_message")).update(f"error starting server: {type(e).__name__}")

    def action_stop_server(self):
        server = self.get_selected_server()
        if not server:
            cast(Label, self.query_one("#status_message")).update("select a server to stop.")
            return

        cast(Label, self.query_one("#status_message")).update(f"attempting to stop server: {server.name}...")
        
        try:
            cast(Label, self.query_one("#status_message")).update(f"server {server.name} stop command sent.")
        except Exception as e:
            cast(Label, self.query_one("#status_message")).update(f"error stopping server: {type(e).__name__}")

    async def action_create_new_server(self):
        await self.mount(InputModal("enter new server name:", "create"))

    async def action_delete_selected_server(self):
        server = self.get_selected_server()
        if not server:
            cast(Label, self.query_one("#status_message")).update("select a server to delete.")
            return
        
        await self.mount(InputModal(f"type 'yes' to delete '{server.name}':", "delete"))

    async def action_rename_selected_server(self):
        server = self.get_selected_server()
        if not server:
            cast(Label, self.query_one("#status_message")).update("select a server to rename.")
            return
        
        await self.mount(InputModal(f"enter new name for '{server.name}':", "rename"))

    async def on_input_modal_submitted(self, message: InputModal.Submitted):
        value = message.value.strip()
        action = message.action

        if action == "create":
            if not value:
                self.query_one("#status_message").update("creation cancelled: name cannot be empty.")
                return
            try:
                self.server_manager.create_server(value)
                self.action_refresh_data()
                self.query_one("#status_message").update(f"server '{value}' created.")
            except Exception as e:
                self.query_one("#status_message").update(f"error creating server: {type(e).__name__}")

        elif action == "delete":
            server = self.get_selected_server()
            if not server:
                self.query_one("#status_message").update("select a server first.")
                return
            if value.lower() != "yes":
                self.query_one("#status_message").update("deletion cancelled.")
                return
            try:
                self.server_manager.delete_server(server)
                self.action_refresh_data()
                self.query_one("#status_message").update(f"server '{server.name}' deleted.")
            except Exception as e:
                self.query_one("#status_message").update(f"error deleting server: {type(e).__name__}")

        elif action == "rename":
            server = self.get_selected_server()
            if not server:
                self.query_one("#status_message").update("select a server first.")
                return
            if not value:
                self.query_one("#status_message").update("rename cancelled: empty name.")
                return
            try:
                self.server_manager.rename_server(server, value)
                self.action_refresh_data()
                self.query_one("#status_message").update(f"server renamed to '{value}'.")
            except Exception as e:
                self.query_one("#status_message").update(f"error renaming server: {type(e).__name__}")

    def on_data_table_row_highlighted(self, event):
        server = self.get_selected_server()
        self.query_one(ServerDetails).update_details(server)
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.label == "refresh (r)":
            self.action_refresh_data()
        elif event.button.label == "start (s)":
            self.action_start_server()
        elif event.button.label == "stop (t)":
            self.action_stop_server()
        elif event.button.label == "fix ids (c)":
            self.action_resolve_conflicts()
        elif event.button.label == "new (n)":
            self.action_create_new_server()
        elif event.button.label == "delete (d)":
            self.action_delete_selected_server()
        elif event.button.label == "rename (e)":
            self.action_rename_selected_server()


if __name__ == "__main__":
    app = KherimoyaManagerApp()
    app.run()
