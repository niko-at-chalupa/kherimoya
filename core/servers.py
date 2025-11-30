"""Kherimoya server management classes and methods."""

from pathlib import Path
from . import exceptions
import uuid
import json
import libtmux
import endstone # to ensure endstone is installed
from typing import Literal, cast
import re
import secrets
import time

PROJECT_PATH = Path(__file__).parent.parent.resolve()
if not Path(PROJECT_PATH / "core").is_dir():
    raise exceptions.KherimoyaPathNotFoundError(
        f"Kherimoya root path could not be resolved. Expected to find core/ in {PROJECT_PATH}"
    )

from .constants import DELIMITER

class KherimoyaServer:
    """
    Represents a server in servers/, existing or one which does not exist (to work as a placeholder).
    """
    # --- initialization --- #

    class Actions:
        """
        Methods which require the server to exist. This only checks KherimoyaServer.exists, which means if it was nonexisting in the past you have to call KherimoyaServer.refresh
        """
        def __init__(self, server: "KherimoyaServer") -> None:
            self.server: KherimoyaServer = server

        def _checkserver(self, requires_exists: bool = True, requires_running: bool = False, reason: str=''):
            if not self.server.exists and requires_exists:
                raise exceptions.ServerDoesNotExistError(reason)
            if requires_running and not self.server.running:
                raise exceptions.ServerNotRunningError(reason)

        def start_server(self, method: Literal["tmux", "plugin"] = "tmux"):
            """
            Starts the parent KherimoyaServer.

            Args:
                Method (Literal["tmux", "plugin"]): Method in which is how you start the server. Screen will start the server through the screen session, and plugin will use the plugin (which is not yet implemented)
            """
            self._checkserver(requires_exists=True, requires_running=False, reason="Attempted to start a server which does NOT exist")

            server = self.server

            if method == "tmux":
                self._start_through_tmux(server)
            elif method == "plugin":
                raise NotImplementedError('Kherimoya\'s plugin does not exist as of now.')
                #self._start_through_plugin(server)
            else:
                raise ValueError(f"Invalid start method: {method}")
        
        def _start_through_tmux(self, server):
            # TODO: Make it so that it uses similar logic to our old scripts, where we used screen -dmS "$SERVER_NAME" endstone -y -s "$SERVER_DIR_PATH" to start servers
            session_name = f'{server.name}{DELIMITER}{server.server_id}'
            tmux_server = None
            session = None

            try: # start session
                tmux_server = libtmux.Server()
                try:
                    existing = tmux_server.find_where({"session_name": session_name})
                    if existing:
                        existing.kill_session()
                except Exception as e:
                    pass

                session = tmux_server.new_session(session_name=session_name, start_directory=str(server.path / "server"), attach=False, kill_session=True)
                window = session.attached_window or session.windows[0]
                pane = window.attached_pane or window.panes[0]
                pane.send_keys(f'endstone -y -s {str(server.path / "server")}', enter=True)
            except Exception as e:
                raise exceptions.ServerStartError(f"Failed to create tmux session for server {session_name}") from e

        def _start_through_plugin(self, server):
            # TODO: When the plugin is finished, make it use the port for the server.
            # Example URI: {ip}:{port}/{name}{DELIMITER}{id}/start_server
            pass
        
        def stop_server(self, method: Literal["tmux", "plugin"] = "tmux") -> None:
            """
            Stops the parent KherimoyaServer.

            Args:
                Method (Literal["tmux", "plugin"]): Method in which is how you stop the server. Tmux will stop the server through the tmux session, and plugin will use the plugin (which is not yet implemented)
            """
            self._checkserver(requires_exists=True, requires_running=True, reason="Attempted to stop a server which does NOT exist/is not running")

            server = self.server

            if method == "tmux":
                self._stop_through_tmux(server)
            elif method == "plugin":
                raise NotImplementedError('Kherimoya\'s plugin does not exist as of now.')
                #self._stop_through_plugin(server)
            else:
                raise ValueError(f"Invalid stop method: {method}")

        def _stop_through_tmux(self, server):
            # TODO: Make it so that it essentially just sends the command "stop" to the server. Do this last because we can do this manually
            pass

        def _stop_through_plugin(self, server):
            # TODO: When the plugin is finished, make it use the port for the server to stop the server.
            # Example URI: {ip}:{port}/{name}{DELIMITER}{id}/stop_server
            pass

    def __init__(self, project_path: Path, name: str, server_id: str | None = None):
        self._project_path = project_path
        self._name = name

        if server_id:
            self._path = Path(project_path / "servers" / f"{name}{DELIMITER}{server_id}").resolve()
            self._server_id = server_id
        else:
            self._path = Path(project_path / "servers" / f"{name}").resolve()
            self._server_id = None

        self._exists = self._path.is_dir()
        if self._exists:
            if DELIMITER in self._path.name:
                self._name, self._server_id = self._path.name.split(DELIMITER, 1)
            else:
                self._name = self._path.name
                self._server_id = None

        if self._exists:
            self._running = False  # TODO: Load from JSON later
        else:
            self._running = False

        # Attach Actions interface
        self._actions = KherimoyaServer.Actions(self)
    
    # --- properties --- #

    # We do this so that it's a a bit harder for external things to change attributes, and making the real attributes private emphasizes that we don't want others to change them
    # Attributes like KherimoyaServer._name and KherimoyaServer._server_id are based off of the server's actual folder, and since KherimoyaServer represents that folder, we only really change them in KherimoyaServer.refresh()

    # name: str = ''
    # server_id: str | None = None
    # path: Path
    # exists: bool = False
    # running: bool = False

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def server_id(self) -> str | None:
        return self._server_id
    
    @property
    def path(self) -> Path:
        return self._path
    
    @property
    def exists(self) -> bool:
        return self._exists
    
    @property
    def running(self) -> bool:
        return self._running

    @property
    def actions(self) -> "KherimoyaServer.Actions":
        return self._actions

    # --- methods --- #

    def refresh(self, path: Path) -> None:
        """
        Resets server_id, name, & path. Also writes to server.json, creating the file if it does not exist

        Should be called when creating a server, changing its name, and every once in a while
        """
        # --- check ---

        if not self._exists:
            self._server_id = None
        
        if not path.is_dir():
            if self._path.is_dir():
                return
            else:
                self._server_id = None

        if not path.is_dir():
            raise FileNotFoundError(
                f"Path passed into load_and_save_metadata_plus_self is not a directory: {path}"
            )

        if path.parent.name != "servers":
            raise exceptions.ServerNotInPathError(
                f"Path passed into load_and_save_metadata_plus_self is not in servers/"
            )

        # --- set name, id, & path ---

        self._path = path

        if DELIMITER in path.name:
            self._name, self._server_id = path.name.split(DELIMITER, 1)
        else:
            self._name = path.name
            self._server_id = None

        if not self._path.is_dir():
            self._exists = False
            self._server_id = None
            self._server_index = None
            return
        else:
            self._exists = True
            self._running = False  # TODO: Load from JSON later

        # --- write to json ---
        with open(path / "server.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "name": self._name,
                    "id": self._server_id
                },
                f,
                indent=4
            )


class ServerManager:
    """
    Holds methods to manage servers.
    """

    # --- initialization --- #

    def __init__(self, project_path: Path, strict_names: bool = True):
        self._project_path = project_path
        self._strict_names = strict_names

    @property
    def project_path(self) -> Path:
        """
        The path to the Kherimoya project.
        """
        return self._project_path

    @property
    def strict_names(self) -> bool:
        """
        Whether or not server names must be unique.
        """
        return self._strict_names

    # --- methods --- #

    def list_servers(self, sole_names: bool = False, sole_ids: bool = False) -> list[tuple[str, str]] | list[str | None]:
        """
        Lists all of the servers in the servers/ directory.

        Args:
            sole_names (bool = False): Appends the name of the server rather than a tuple with the server's id as well
            sole_ids (bool = False): Appends the id of the server rather than a tuple with the server's name as well

        Returns:
            Either a list with tuples for each server (index 0 is the name, index 1 is the id)
            OR a plain list with strings of the name and/or id of each server.

        Example:
            ```python
            # Get all servers as (name, id) tuples (default behavior)
            # Type checker sees: list[tuple[str, str | None]]
            tuples = list_servers() # [('server1', '2392839'), ('server2', '9398239')]

            # Get only server names
            # Type checker sees: list[str]
            names = list_servers(sole_names=True) # ['server1', 'server2']

            # Get only server IDs
            # Type checker sees: list[str | None]
            ids = list_servers(sole_ids=True) # ['2392839', '9398239']
            ```
        """

        servers = []
        for p in (self.project_path / "servers").iterdir():
            if not p.is_dir():
                continue

            if DELIMITER in p.name:
                name, server_id = p.name.split(DELIMITER, 1)
            else:
                name, server_id = p.name, None

            if sole_names:
                servers.append(name)
            elif sole_ids:
                servers.append(server_id)
            else:
                servers.append((name, server_id))

        return servers

    def list_server_objects(self) -> list[KherimoyaServer]:
        """
        Lists all of the servers in the servers/ directory as KherimoyaServer objects.

        Returns:
            list[KherimoyaServer]: A list of KherimoyaServer objects for each server found.
        """
        server_objects = []
        all_servers = cast(list[tuple[str, str | None]], self.list_servers())
        
        for server in all_servers:
            try:
                kherimoya_server = KherimoyaServer(project_path=self.project_path, name=server[0])
                kherimoya_server.refresh(self.project_path / "servers" / f"{server[0]}{DELIMITER}{server[1]}")
                server_objects.append(kherimoya_server)
            except Exception:
                continue
        return server_objects

    def create_server(self, server: str | KherimoyaServer, install_timeout: float | None = 300) -> KherimoyaServer:
        """
        Creates a new server from a string for the name, or a nonexisting KherimoyaServer

        Args:
            server (str | KherimoyaServer): A name for the server, or a nonexisting KherimoyaServer
            install_timeout (float | None = 300): Maximum seconds to wait for endstone to finish initial install/start.
                If None, wait indefinitely.

        Returns:
            KherimoyaServer: The new, existing server.

        Example:
            ```
            # Create a server from a name
            server1 = ServerManager.create_server(Path("path/to/your/kherimoya/installation"), "newserver1")

            # Create a server from a nonexisting KherimoyaServer
            server2 = KherimoyaServer(PROJECT_PATH, "newserver2")
            server2 = ServerManager.create_server(server2)
            ```
        """
        if isinstance(server, KherimoyaServer):
            if server.exists:
                raise FileExistsError("Server already exists")
            new_server = server
        else:
            new_server = KherimoyaServer(self.project_path, server)

        if new_server.exists:
            raise exceptions.ServerCreationError(f"Server '{new_server.name}' already exists.")
        elif new_server.name in self.list_servers(sole_names=True) and self.strict_names:
            raise exceptions.ServerCreationError(f"Server with name '{new_server.name}' already exists, and strict_names is enabled.")
        elif new_server.name.strip() == "":
            raise exceptions.ServerCreationError("Server name cannot be empty or whitespace.")
        elif "-" in new_server.name or ":" in new_server.name or "/" in new_server.name or "\\" in new_server.name or DELIMITER in new_server.name:
            raise exceptions.ServerCreationError(f"Server name cannot contain '-', ':', '/', '{DELIMITER}', or '\\' characters.")

        # - set up the server - #
        new_server._server_id = str(self._generate_unique_id())

        base_path = (self.project_path / "servers" / f"{new_server.name}{DELIMITER}{new_server.server_id}").resolve()
        base_path.mkdir(parents=False, exist_ok=False)

        # - make the filestructure - #
        for subdir in ["config", "extra", "server", "state"]:
            (base_path / subdir).mkdir()

        new_server.refresh(base_path) # sets all attributes and writes to server.json

        # - set up with Endstone - #
        session_name = f'{new_server.name}{DELIMITER}{new_server.server_id}'
        tmux_server = None
        session = None

        try: # start session
            tmux_server = libtmux.Server()
            try:
                existing = tmux_server.find_where({"session_name": session_name})
                if existing:
                    existing.kill_session()
            except Exception as e:
                pass

            session = tmux_server.new_session(session_name=session_name, start_directory=str(base_path / "servers"), attach=False, kill_session=True)
            window = session.attached_window or session.windows[0]
            pane = window.attached_pane or window.panes[0]
            pane.send_keys(f'endstone -y -s {str(Path(base_path / "server"))}', enter=True)
        except Exception as e:
            raise exceptions.ServerCreationError(f"Failed to create tmux session for server {session_name}") from e

        # when endstone is ran in an environment which does not have a endstone BDS installed, it will create the server and start it
        start_time = time.monotonic()
        sleep_interval = 0.5
        while not Path(base_path / "server" / "worlds").is_dir():
            if install_timeout is not None and (time.monotonic() - start_time) > install_timeout:
                # best-effort cleanup: kill tmux session, then raise
                try:
                    if tmux_server:
                        s = tmux_server.find_where({"session_name": session_name})
                        if s:
                            s.kill_session()
                except Exception:
                    pass
                raise TimeoutError(f"Server installation/start did not complete within {install_timeout} seconds.")
            time.sleep(sleep_interval)
            sleep_interval = min(2.0, sleep_interval * 1.5)

        time.sleep(1)

        # send stop command, which should gracefully stop the server
        stopped = False
        try:
            if tmux_server:
                sess = tmux_server.find_where({"session_name": session_name})
                if sess:
                    win = sess.attached_window or sess.windows[0]
                    pane = win.attached_pane or win.panes[0]
                    pane.send_keys("stop", enter=True)
                    time.sleep(1)
                    try:
                        sess.kill_session()
                    except Exception:
                        pass
                    stopped = True
        except Exception:
            stopped = False

        if not stopped:
            raise exceptions.ServerCreationError(f"failed to stop tmux session for server {session_name}")

        # - finishing up - #
        with open(base_path / "state" / "state.json", "w", encoding="utf-8") as f:
            json.dump({"running": False}, f, indent=4) 

        return new_server

    def _generate_unique_id(self) -> str:
        """
        Generate a short human-readable, hyphen-separated unique ID.

        The ID is groups of 4 characters separated by hyphens e.g.:
        - "abcd" (1 group)
        - "abcd-ef12" (2 groups)
        - "abcd-ef12-3456" (3 groups)
        and so on.
        
        Uses a base36 alphabet (0-9a-z) and generate the shortest group count
        possible (to keep it easy to read, opposed to UUIDs which generate excessively 
        long IDs). If the ID space for the current group count is fully occupied
        (i.e. all possibilities are taken), we extend with an additional group.

        Case is normalized to lowercase, comparisons with existing IDs are
        case-insensitive.
        """
        ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
        GROUP_SIZE = 4
        MAX_RANDOM_TRIES = 1000

        # collect existing IDs, lowercased and filter None entries
        existing = [str(x).lower() for x in self.list_servers(sole_ids=True) if isinstance(x, str) and x is not None]
        existing_set = set(existing)

        def _random_id(groups: int) -> str:
            return "-".join("".join(secrets.choice(ALPHABET) for _ in range(GROUP_SIZE)) for _ in range(groups))

        # try group counts starting at 1 and increasing if the space is exhausted
        for groups in range(1, 10):  # sane upper bound; will fall back to uuid4 if needed
            # pattern to detect existing IDs at this groups length (lowercase)
            # e.g. for groups=1 -> ^[0-9a-z]{4}$ ; groups=2 -> ^[0-9a-z]{4}(?:-[0-9a-z]{4}){1}$
            if groups == 1:
                pattern = re.compile(rf"^[0-9a-z]{{{GROUP_SIZE}}}$")
            else:
                pattern = re.compile(rf"^[0-9a-z]{{{GROUP_SIZE}}}(?:-[0-9a-z]{{{GROUP_SIZE}}}){{{groups-1}}}$")

            existing_of_length = sum(1 for e in existing_set if pattern.match(e))
            space_size = len(ALPHABET) ** (GROUP_SIZE * groups)

            # if space is frozen (all combos used), try next groups count
            if existing_of_length >= space_size:
                continue

            # try to find a new ID with random tries
            for _ in range(MAX_RANDOM_TRIES):
                candidate = _random_id(groups)
                if candidate not in existing_set:
                    return candidate

            # if we couldn't find a unique ID after MAX_RANDOM_TRIES (very unlikely),
            # continue to next groups count and try again.

        # as a last fallback (VERY unlikely), generate a uuid4 to be safe.
        # this keeps compatibility with old long IDs and guarantees uniqueness.
        while True:
            candidate = str(uuid.uuid4())
            if candidate.lower() not in existing_set:
                return candidate
