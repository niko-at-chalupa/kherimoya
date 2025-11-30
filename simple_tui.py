"""Simple TUI for Kherimoya server management."""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static
from textual.containers import Vertical, Horizontal
from core.servers import ServerManager, KherimoyaServer

PROJECT_PATH = Path(__file__).parent.resolve()
if not Path(PROJECT_PATH / "core").is_dir():
    raise ImportError("Core module not found. Ensure this script is from the project root.")

server_manager = ServerManager(PROJECT_PATH)

servers = server_manager.list_server_objects()

from core.constants import DELIMITER

raise NotImplementedError("This TUI is under development and not yet functional!")