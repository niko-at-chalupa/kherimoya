"""
Alternative to the default TUI that works directly with commands

Example: 
    Directly in the terminal
    ```shell
    $ python3 cli.py --help
    ```

    ```shell
    $ python3 cli.py
    kherimoya> help
    ```
"""

import traceback
import argparse
from pathlib import Path
import sys
import rich
from rich.console import Console; console = Console()
from rich.markdown import Markdown
import textwrap
import logging

from core import exceptions
from core.servers import ServerManager, KherimoyaServer

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

def _get_server_by_id(server_manager, server_id) -> KherimoyaServer:
    """Raises error if no server found"""
    if server_id is None:
        raise exceptions.InvalidParameterError("Server ID must be provided!")
    server = server_manager.get_server_by_id(server_id)
    if not server:
        raise exceptions.ServerDoesNotExistError("Server doesn't exist!")
    return server

class Commands:
    def __init__(self, server_manager: ServerManager):
        self.server_manager = server_manager

    def list_servers(self, args):
        """
        Lists all servers, with their names and IDs

        Example:

            ```python
            commands.list_servers() # Prints out servers
            ```

            In the terminal:

            ```shell
            $ python3 cli.py list # Prints out servers

            kherimoya> list # Prints out servers
            ```
        """
        servers = self.server_manager.list_server_objects()

        for server in servers:
            print(f"{server.name}{DELIMITER}{server.server_id}")

    def create_server(self, args):
        """
        Create a new server with the given name

        You can not specify the server ID, it will be generated automatically.

        Example:

            ```python
            commands.create_server(name="MyServer") # Creates a server named "MyServer", with a generated ID
            ```

            In the terminal:

            ```shell
            $ python3 cli.py create --name "MyServer" # Creates a server named "MyServer", with a generated ID

            kherimoya> create "MyServer" # Creates a server named "MyServer", with a generated ID
            ```
        """
        if args.name is None:
            raise exceptions.InvalidParameterError("Server name must be provided!")
        name = args.name
        server = self.server_manager.create_server(name)
        print(f"Created server: {server.name}{DELIMITER}{server.server_id}")

    def delete_server(self, args):
        """
        Delete a server by its ID

        Find these IDs through the `list` command.

        Example:

            ```python
            commands.delete_server(server_id="1234-5678") # Deletes the server with ID "1234-5678"
            ```

            In the terminal:

            ```shell
            $ python3 cli.py delete --server-id "1234-5678" # Deletes the server with ID "1234-5678"

            kherimoya> delete "1234-5678" # Deletes the server with ID "1234-5678"
            ```
        """
        server = _get_server_by_id(self.server_manager, args.server_id)
        
        self.server_manager.delete_server(server)
        print(f"Deleted server: {server.name}{DELIMITER}{server.server_id}")

    def start_server(self, args):
        """
        Start a server by its ID

        Example:

            ```python
            commands.start_server(server_id="1234-5678") # Starts the server with ID "1234-5678"
            ```

            In the terminal:

            ```shell
            $ python3 cli.py start --server-id "1234-5678" # Starts the server with ID "1234-5678"

            kherimoya> start
            ```
        """
        server = _get_server_by_id(self.server_manager, args.server_id)
        server.actions.start_server()
        print(f"Started server: {server.name}{DELIMITER}{server.server_id})")

    def stop_server(self, args):
        """
        Stop a server by its ID

        Example:

            ```python
            commands.stop_server(server_id="1234-5678") # Stops the server with ID "1234-5678"
            ```

            In the terminal:

            ```shell
            $ python3 cli.py stop --server-id "1234-5678" # Stops

            kherimoya> stop "1234-5678" # Stops the server with ID "1234-5678"
            ```
        """
        server = _get_server_by_id(self.server_manager, args.server_id)
        server.actions.stop_server()
        print(f"Stopped server: {server.name}{DELIMITER}{server.server_id}")

    def get_server_info(self, args):
        """
        Prints out the direct server object for the given server ID, which includes its status and path.

        Example:

            ```python
            commands.get_server_info(server_id="1234-5678") # Prints out the server object for the server with ID "1234-5678"
            ```

            In the terminal:

            ```shell
            $ python3 cli.py info --server-id "1234-5678" # Prints

            kherimoya> info "1234-5678" # Prints out the server object for the server with ID "1234-5678"
            ```
        """
        print(_get_server_by_id(self.server_manager, args.server_id))

    def help(self, args, command_map):
        """Prints out help information for commands"""
        if args.name in command_map:
            func = command_map[args.name]
            content = Markdown(textwrap.dedent(func.__doc__))
            console.print(content)
        else:
            console.print("Available commands:")
            for command in command_map:
                console.print(f"- {command}")

server_manager = ServerManager(PROJECT_PATH)
commands = Commands(server_manager)
command_map = {
    "list": commands.list_servers,
    "create": commands.create_server,
    "delete": commands.delete_server,
    "start": commands.start_server,
    "stop": commands.stop_server,
    "info": commands.get_server_info,
    "help": lambda args: commands.help(args, command_map),
}

if len(sys.argv) == 1: CONSOLE_MODE = True
else: CONSOLE_MODE = False

def run_command(args):
    try:
        if args.command in command_map:
            command_map[args.command](args)
        else:
            commands.help(args, command_map)
    except Exception as e:
        print("ERROR !!!!!!!!!!!!! 😭😭😭 Check following!! 🥺🥺🥺")
        console.print_exception(show_locals=False, word_wrap=True)

if __name__ == "__main__":
    if CONSOLE_MODE:
        try:
            while True:
                user_input = input("kherimoya> ")
                if user_input.strip().lower() in ["exit", "quit"]:
                    print("Exiting Kherimoya CLI. Goodbye!")
                    break
                try:
                    args = user_input.split()
                    parser = argparse.ArgumentParser(description="Kherimoya CLI", exit_on_error=False)
                    parser.add_argument("command", type=str, help="Command to execute")
                    parser.add_argument("--name", type=str, help="Name of the server")
                    parser.add_argument("--server-id", type=str, help="ID of the server")
                    parser.add_argument("--log-level", type=int, help="Log level for ServerManager", default=logging.INFO)
                    parsed_args = parser.parse_args(args)
                except Exception as e:
                    console.print_exception(show_locals=False, word_wrap=True)
                    continue
                if parsed_args.log_level:
                    commands.server_manager.logger.setLevel(parsed_args.log_level)
                run_command(parsed_args)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Kherimoya CLI. Goodbye!")
    else: 
        parser = argparse.ArgumentParser(description="Kherimoya CLI")
        parser.add_argument("command", type=str, help="Command to execute")
        parser.add_argument("--name", type=str, help="Name of the server")
        parser.add_argument("--server-id", type=str, help="ID of the server")
        args = parser.parse_args()
        run_command(args)
