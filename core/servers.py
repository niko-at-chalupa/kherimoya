"""Kherimoya server management classes and methods."""

from pathlib import Path
import shutil
from . import exceptions
import uuid
import json
import libtmux
from typing import Literal, cast
import re
import secrets
import time
import sys
import logging
import platform
import yaml

try:
    import endstone # unused, only here to ensure endstone is installed #type: ignore
except ImportError as e:
    if platform.machine() in ["arm64", "aarch64"]:
        pass
    raise e

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

    class _Actions:
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
            session_name = f'{server.name}{DELIMITER}{server.server_id}'
            tmux_server = None
            session = None

            base_path = server.path.resolve()

            try:  # start session
                tmux_server = libtmux.Server()
                
                # kill any existing session with the same name
                try:
                    existing = tmux_server.find_where({"session_name": session_name})
                    if existing:
                        existing.kill_session()
                except Exception:
                    pass

                # create new session
                session = tmux_server.new_session(
                    session_name=session_name,
                    start_directory=str(base_path / "server"),
                    kill_session=True
                )


                window = session.windows[0]
                pane = window.panes[0]

                venv_path = Path(sys.executable).parent.parent
                pane.send_keys(f'bash -c \'source {venv_path}/bin/activate && export HISTCONTROL=ignoreboth && {sys.executable} -m endstone -y -s "{base_path / "server"}"; echo __FINISHED__\'; exit', enter=True)


            except Exception as e:
                raise exceptions.ServerStartError(f"Failed to start tmux session for server {session_name}") from e
        
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
            session_name = f'{server.name}{DELIMITER}{server.server_id}'
            
            try:
                tmux_server = libtmux.Server()
                session = tmux_server.find_where({"session_name": session_name})
                
                if session:
                    window = session.windows[0]
                    pane = window.panes[0]
                    
                    pane.send_keys("stop", enter=True)
                else:
                    pass
            except Exception as e:
                raise exceptions.ServerStopError(f"Failed to send stop command to tmux session for server {session_name}") from e
            pass

        def _stop_through_plugin(self, server):
            # TODO: When the plugin is finished, make it use the port for the server to stop the server.
            # Example URI: {ip}:{port}/{name}{DELIMITER}{id}/stop_server
            pass

    def __repr__(self) -> str:
        return (
            f"<KherimoyaServer {self.name!r}{DELIMITER}{self.server_id!r}"
            f"exists={self.exists!r} running={self.running!r} path={self.path!r}>"
        )

    def __init__(self, project_path: Path, name: str, server_id: str | None = None):
        self._project_path = project_path
        self._name = name
        self._type = None

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
        self._actions = KherimoyaServer._Actions(self)
    
    # --- properties --- #

    _name: str = ''
    _server_id: str | None = None
    _path: Path
    _exists: bool = False
    _running: bool = False 
    _type: Literal['python', 'docker'] | None = None

    # We do this so that it's a a bit harder for external things to change attributes, and making the real attributes private emphasizes that we don't want others to change them
    # Attributes like KherimoyaServer._name and KherimoyaServer._server_id are based off of the server's actual folder, and since KherimoyaServer represents that folder, we only really change them in KherimoyaServer.refresh()

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
    def actions(self) -> "KherimoyaServer._Actions":
        return self._actions
    
    @property
    def type(self) -> Literal['python', 'docker'] | None:
        return self._type

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
        
        if DELIMITER not in path.name:
            raise exceptions.ImproperServerError(
                f"Path passed into load_and_save_metadata_plus_self does not have a valid server folder name (missing '{DELIMITER}' to separate name & ID): {path.name}"
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

    def __init__(self, project_path: Path, strict_names: bool = True, log_level: int = logging.INFO):
        self._project_path = project_path
        self._strict_names = strict_names
        self.logger = logging.getLogger(__name__)
    
        self.set_log_level(log_level)

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

    def set_log_level(self, level: int) -> None:
        self.logger.setLevel(level)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(level)

            formatter = logging.Formatter(
                "[%(levelname)s] %(name)s: %(message)s"
            )
            handler.setFormatter(formatter)

            self.logger.addHandler(handler)

    def _list_servers(self, sole_names: bool = False, sole_ids: bool = False) -> list[tuple[str, str]] | list[str | None]:
        """
        Private because list_server_* methods should be used instead.
        Don't use this unless you want issues with type checking!!

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

        servers_dir = self.project_path / "servers"
        if not servers_dir.is_dir():
            return []  # no servers yet
        servers = []
        for p in servers_dir.iterdir():
            self.logger.debug(f"Checking path in servers/: {p}")
            if not p.is_dir():
                continue
            if DELIMITER in p.name:
                self.logger.debug(f"Found non-server folder in servers/: {p.name}. Avoid making servers without a {DELIMITER} in its name, and avoid putting non-server folders in servers/.")
                name, server_id = p.name.split(DELIMITER, 1)
            else:
                continue  # Folders without DELIMITER are NOT considered servers
            if sole_names:
                servers.append(name)
            elif sole_ids:
                servers.append(server_id)
            else:
                servers.append((name, server_id))
                self.logger.debug(f"Found server: {name}{DELIMITER}{server_id}")
        return servers
    
    def list_server_ids(self) -> list[str | None]:
        """
        Lists all of the server IDs in the servers/ directory.

        Returns:
            list[str | None]: A list of server IDs for each server found.
        """
        return cast(list[str | None], self._list_servers(sole_ids=True))
    
    def list_server_names(self) -> list[str]:
        """
        Lists all of the server names in the servers/ directory.

        Returns:
            list[str]: A list of server names for each server found.
        """
        return cast(list[str], self._list_servers(sole_names=True))

    def list_server_objects(self) -> list[KherimoyaServer]:
        """
        Lists all of the servers in the servers/ directory as KherimoyaServer objects.

        Returns:
            list[KherimoyaServer]: A list of KherimoyaServer objects for each server found.
        """
        server_objects = []
        all_servers = cast(list[tuple[str, str | None]], self._list_servers())
        
        for server in all_servers:
            try:
                kherimoya_server = KherimoyaServer(project_path=self.project_path, name=server[0])
                kherimoya_server.refresh(self.project_path / "servers" / f"{server[0]}{DELIMITER}{server[1]}")
                server_objects.append(kherimoya_server)
            except Exception:
                continue
        return server_objects

    def get_server_by_id(self, server_id: str) -> KherimoyaServer | None:
        """
        Gets a KherimoyaServer by its ID.

        Args:
            server_id (str): The server ID to look for.

        Returns:
            KherimoyaServer | None: The KherimoyaServer with the given ID, or None if not found.
        """
        all_servers = self.list_server_objects()
        for server in all_servers:
            if server.server_id and server.server_id.lower() == server_id.lower():
                self.logger.info(f"Found server: {server.name}{DELIMITER}{server.server_id}")
                return server
        self.logger.info(f"Failed to find a server with ID: {server_id}")
        return None

    def _generate_unique_id(self, max_random_tries: int = 1000) -> str:
        """
        Generate a short human-readable, hyphen-separated unique ID

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
        MAX_RANDOM_TRIES = max_random_tries

        # collect existing IDs, lowercased and filter None entries
        existing = [str(x).lower() for x in self.list_server_ids() if isinstance(x, str) and x is not None]
        existing_set = set(existing)

        def _random_id(groups: int) -> str:
            return "-".join("".join(secrets.choice(ALPHABET) for _ in range(GROUP_SIZE)) for _ in range(groups))

        # try group counts starting at 1 and increasing if the space is exhausted
        for groups in range(1, 10):  # sane upper bound; will fall back to uuid4 if needed
            self.logger.debug(f"Trying to generate unique ID with {groups} groups")
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
                    self.logger.info(f"Generated unique ID: {candidate}")
                    return candidate

            # if we couldn't find a unique ID after MAX_RANDOM_TRIES (very unlikely),
            # continue to next groups count and try again.

        # as a last fallback (VERY unlikely), generate a uuid4 to be safe.
        # this keeps compatibility with old long IDs and guarantees uniqueness.
        while True:
            candidate = str(uuid.uuid4())
            if candidate.lower() not in existing_set:
                self.logger.info(f"Generated fallback UUID: {candidate}")
                return candidate

    def resolve_id_conflicts(self) -> bool:
        """
        Resolves possible ID conflicts among existing servers by checking each one for conflicts, then generating a new unique ID for certain servers if needed.

        Returns:
            bool: True if any conflicts were found and resolved, False otherwise.
        """

        conflicts_found = False
        seen_ids = set()

        for server in self.list_server_objects():            
            # check if the ID is already seen
            if (server.server_id or "").lower() in seen_ids:
                # generate a new unique ID for this server, renaming the folder accordingly
                server._server_id = self._generate_unique_id()
                new_path = (server.path.parent / f"{server.name}{DELIMITER}{server.server_id}").resolve()
                server.path.rename(new_path)
                server.refresh(new_path) # refresh sets the name and id
                conflicts_found = True
            else:
                if server.server_id is not None:
                    seen_ids.add(server.server_id.lower())

        return conflicts_found

    # - server actions - #

    def _create_server_with_python(self, server: KherimoyaServer, install_timeout: float | None = 300) -> KherimoyaServer:
        """
        Creates a new server using the Python method (endstone).

        Args:
            server (KherimoyaServer): The KherimoyaServer to create.
        """
        new_server = server
        # - set up the server - #
        new_server._server_id = str(self._generate_unique_id())
        self.logger.info(f"Generated server ID: {new_server.server_id}")

        base_path = (self.project_path / "servers" / f"{new_server.name}{DELIMITER}{new_server.server_id}").resolve()
        self.logger.debug(f"Creating server directory at: {base_path}")
        base_path.mkdir(parents=False, exist_ok=False)

        # - make the filestructure - #
        for subdir in ["config", "extra", "server", "state"]:
            self.logger.debug(f"Creating subdirectory: {subdir}")
            (base_path / subdir).resolve().mkdir()

        new_server.refresh(base_path) # sets all attributes and writes to server.json

        # - set up with Endstone - #
        session_name = f'{new_server.name}{DELIMITER}{new_server.server_id}'
        tmux_server = None
        session = None

        self.logger.info(f"Starting Endstone to set up server in tmux session: {session_name}")

        try:  # start session
            tmux_server = libtmux.Server()
            
            # kill any existing session with the same name
            try:
                existing = tmux_server.find_where({"session_name": session_name})
                if existing:
                    existing.kill_session()
            except Exception:
                pass

            # create new session
            session = tmux_server.new_session(
                session_name=session_name,
                start_directory=str(base_path / "server"),
                kill_session=True
            )

            # use the first window and pane (attached_window/attached_pane removed)
            window = session.windows[0]
            pane = window.panes[0]

            # run the server start command
            pane.send_keys(f'bash -c \'export HISTCONTROL=ignoreboth; {sys.executable} -m endstone -y -s "{base_path / "server"}"; echo __FINISHED__\'; exit', enter=True)

        except Exception as e:
            # delete base_path
            self.logger.error(f"Failed to create tmux session for server {session_name}, cleaning up created files.")
            try:
                if base_path.exists() and base_path.is_dir():
                    for sub in base_path.iterdir():
                        if sub.is_dir():
                            for subsub in sub.iterdir():
                                subsub.unlink()
                            sub.rmdir()
                    base_path.rmdir()
            except Exception:
                pass
            raise exceptions.ServerCreationError(f"Failed to create tmux session for server {session_name}") from e


        # when endstone is ran in an environment which does not have a endstone BDS installed, it will create the server and start it
        start_time = time.monotonic()
        sleep_interval = 0.5
        while not Path(base_path / "server" / "worlds").is_dir(): # wait until server is installed
            if install_timeout is not None and (time.monotonic() - start_time) > install_timeout:
                # best-effort cleanup: kill tmux session, then raise
                try:
                    if tmux_server:
                        s = tmux_server.find_where({"session_name": session_name})
                        if s:
                            s.kill_session()
                except Exception:
                    pass
                # delete base_path
                self.logger.error(f"Server installation/start timed out for server {session_name}, cleaning up created files.")
                try:
                    if base_path.exists() and base_path.is_dir():
                        for sub in base_path.iterdir():
                            if sub.is_dir():
                                for subsub in sub.iterdir():
                                    subsub.unlink()
                                sub.rmdir()
                        base_path.rmdir()
                except Exception:
                    pass
                raise TimeoutError(f"Server installation/start did not complete within {install_timeout} seconds.")
            
            output = "\n".join(pane.capture_pane()[-20:])  # last 20 lines only
            if "__ENDSTONE_DONE__" in output or session not in tmux_server.sessions:
                raise exceptions.ServerCreationError(f"Endstone process exited unexpectedly during server creation for server {session_name}; output:\n{output}")
                
            time.sleep(sleep_interval)
            sleep_interval = min(2.0, sleep_interval * 1.5)

        time.sleep(1)

        # send stop command, which should gracefully stop the server
        pane.send_keys("stop", enter=True)
        stop_start = time.monotonic()
        self.logger.info(f"Sent stop command to server {session_name}, waiting for tmux session to close.")

        while True:
            if not tmux_server.has_session(session_name):  # session gone
                break
            if time.monotonic() - stop_start > 60: # good enough timeout
                break
            time.sleep(0.5)

        # - finishing up - #
        with open(base_path / "state" / "state.json", "w", encoding="utf-8") as f:
            json.dump({"running": False}, f, indent=4) 

        with open(base_path / "kherimoya.yaml", "w") as f:
            yaml.dump({
                "type": "python"
            }, f)

        self.logger.info(f"Successfully created server: {new_server.name}{DELIMITER}{new_server.server_id}")

        return new_server

    def create_server(self, server: str | KherimoyaServer, install_timeout: float | None = 300, method: Literal["python", "docker"] = "python") -> KherimoyaServer:
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
        elif new_server.name in self.list_server_names() and self.strict_names:
            raise exceptions.ServerCreationError(f"Server with name '{new_server.name}' already exists, and strict_names is enabled.")
        elif new_server.name.strip() == "":
            raise exceptions.ServerCreationError("Server name cannot be empty or whitespace.")
        elif "-" in new_server.name or ":" in new_server.name or "/" in new_server.name or "\\" in new_server.name or DELIMITER in new_server.name:
            raise exceptions.ServerCreationError(f"Server name cannot contain '-', ':', '/', '{DELIMITER}', or '\\' characters.")

        if method == "python":
            return self._create_server_with_python(new_server, install_timeout=install_timeout)        
        elif method == "docker":
            raise NotImplementedError("Docker method is not yet implemented.")

    def delete_server(self, server: KherimoyaServer) -> None:
        """
        Deletes an existing server.

        Args:
            server (KherimoyaServer): An existing KherimoyaServer to delete.

        Example:
            ```python
            server = ServerManager.create_server("deleteserver")
            ServerManager.delete_server(server)
            ```
        """
        if not server.exists or not server.path.is_dir():
            raise FileNotFoundError("Server does not exist")
        
        shutil.rmtree(server.path)

    def rename_server(self, server: KherimoyaServer, new_name: str) -> None:
        """
        Renames an existing server.

        Args:
            server (KherimoyaServer): An existing KherimoyaServer to rename.
            new_name (str): The new name for the server.

        Example:
            ```python
            server = ServerManager.create_server("oldname")
            ServerManager.rename_server(server, "newname")
            ```
        """
        if not server.exists or not server.path.is_dir():
            raise FileNotFoundError("Server does not exist")
        elif new_name in self.list_server_names() and self.strict_names:
            raise exceptions.ServerRenameError(f"Server with name '{new_name}' already exists, and strict_names is enabled.")
        elif new_name.strip() == "":
            raise exceptions.ServerRenameError("Server name cannot be empty or whitespace.")
        elif "-" in new_name or ":" in new_name or "/" in new_name or "\\" in new_name or DELIMITER in new_name:
            raise exceptions.ServerRenameError(f"Server name cannot contain '-', ':', '/', '{DELIMITER}', or '\\' characters.")

        new_path = (server.path.parent / f"{new_name}{DELIMITER}{server.server_id}").resolve()
        server.path.rename(new_path)
        server.refresh(new_path) # refresh sets the name and id
