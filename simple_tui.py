"""Simple TUI for Kherimoya server management."""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable, Label, Button
from textual.containers import Vertical, Horizontal, Container, Grid
from textual.binding import Binding
from textual.css.query import NoMatches
from typing import cast
import sys

# TODO: Fix input handling for Textual (use modals/dialogs instead of input())

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


class ServerDetails(Static):
    def __init__(self):
        super().__init__("no server selected", id="server_details")

    def update_details(self, server: KherimoyaServer | None):
        if server is None:
            self.update("no server selected")
            return
        
        status = "running" if server.running else "stopped"
        # status_style is not used in raw markdown/textual output
        
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
        /* This line forces buttons onto a single horizontal line if space allows */
        align-horizontal: left; 
    }
    #actions > Button {
        margin-right: 1;
    }
    #status_message {
        color: yellow;
        padding: 0 1; /* Add some padding around the status message */
    }
    Container {
        height: 100%;
    }
    #main_grid {
        grid-size: 1;
        grid-rows: 1fr auto;
        height: 100%;
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
                    yield Button("fix ids (c)", variant="error")
                    yield Button("new (n)", variant="success")   # <-- ADDED
                    yield Button("delete (d)", variant="error")  # <-- ADDED
                    yield Button("rename (e)", variant="primary") 


    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        
        
        
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
            
            row_key = table.highlighted_row_key.value # type: ignore
            
            for server in self.servers:
                if server.server_id == row_key:
                    return server
            return None

        except NoMatches:
            return None
        except AttributeError:
            return None
        except Exception:
            return None


    async def action_quit(self):
        self.exit()

    def _resolve_conflicts_silent(self):
        try:
            self.server_manager.resolve_id_conflicts()
        except Exception as e:
            pass


    def action_refresh_data(self):
        self._resolve_conflicts_silent()

        self.load_server_data()
        cast(Label, self.query_one("#status_message")).update("server list refreshed.")

    def action_resolve_conflicts(self):
        try:
            self.server_manager.resolve_id_conflicts()
            self.action_refresh_data()
            cast(Label, self.query_one("#status_message")).update("id conflicts resolved. please refresh again if needed.")
        except Exception as e:
            cast(Label, self.query_one("#status_message")).update(f"error resolving conflicts: {type(e).__name__}")


    def action_start_server(self):
        server = self.get_selected_server()
        if not server:
            cast(Label, self.query_one("#status_message")).update("select a server to start.")
            return

        cast(Label, self.query_one("#status_message")).update(f"attempting to start server: {server.name}...")
        
        try:
            # NOTE: Logic for starting server is missing in KherimoyaServer.Actions._stop_through_tmux, but we call the placeholder action anyway
            server.actions.start_server(method="tmux") 
            cast(Label, self.query_one("#status_message")).update(f"server {server.name} start command sent (check tmux manually).")

        except Exception as e:
            cast(Label, self.query_one("#status_message")).update(f"error starting server: {type(e).__name__}")

    def action_stop_server(self):
        server = self.get_selected_server()
        if not server:
            cast(Label, self.query_one("#status_message")).update("select a server to stop.")
            return

        cast(Label, self.query_one("#status_message")).update(f"attempting to stop server: {server.name}...")
        
        try:
            # NOTE: Logic for stopping server is missing in server.actions.stop_server(method="tmux"), add later
            cast(Label, self.query_one("#status_message")).update(f"server {server.name} stop command sent.")
        except Exception as e:
            cast(Label, self.query_one("#status_message")).update(f"error stopping server: {type(e).__name__}")

    def action_create_new_server(self):
        # NOTE: Using standard input() pauses the TUI until input is provided. A better Textual app would use a Modal or dialog, implement later.
        new_name = input("enter new server name: ")
        new_name = new_name.strip()

        if not new_name:
            cast(Label, self.query_one("#status_message")).update("creation cancelled: name cannot be empty.")
            return

        cast(Label, self.query_one("#status_message")).update(f"attempting to create server: {new_name} (this may take a moment)...")

        try:
            self.server_manager.create_server(new_name)
            self.action_refresh_data()
            cast(Label, self.query_one("#status_message")).update(f"server '{new_name}' created successfully.")
        except Exception as e:
            cast(Label, self.query_one("#status_message")).update(f"error creating server: {type(e).__name__}")


    def action_delete_selected_server(self):
        server = self.get_selected_server()
        if not server:
            cast(Label, self.query_one("#status_message")).update("select a server to delete.")
            return
        
        # NOTE: Using standard input() pauses the TUI until input is provided. A better Textual app would use a Modal or dialog, implement later.
        confirm = input(f"type 'yes' to confirm permanent deletion of '{server.name}': ")

        if confirm.lower() != 'yes':
            cast(Label, self.query_one("#status_message")).update("deletion cancelled.")
            return

        cast(Label, self.query_one("#status_message")).update(f"attempting to delete server: {server.name}...")

        try:
            self.server_manager.delete_server(server)
            self.action_refresh_data()
            cast(Label, self.query_one("#status_message")).update(f"server '{server.name}' deleted.")
        except Exception as e:
            cast(Label, self.query_one("#status_message")).update(f"error deleting server: {type(e).__name__}")


    def action_rename_selected_server(self):
        server = self.get_selected_server()
        if not server:
            cast(Label, self.query_one("#status_message")).update("select a server to rename.")
            return

        # NOTE: Using standard input() pauses the TUI until input is provided. A better Textual app would use a Modal or dialog, implement later.
        new_name = input(f"enter new name for '{server.name}': ")
        new_name = new_name.strip()

        if not new_name:
            cast(Label, self.query_one("#status_message")).update("rename cancelled: name cannot be empty.")
            return

        cast(Label, self.query_one("#status_message")).update(f"attempting to rename server '{server.name}' to '{new_name}'...")

        try:
            self.server_manager.rename_server(server, new_name)
            self.action_refresh_data()
            cast(Label, self.query_one("#status_message")).update(f"server renamed to '{new_name}'.")
        except Exception as e:
            cast(Label, self.query_one("#status_message")).update(f"error renaming server: {type(e).__name__}")


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