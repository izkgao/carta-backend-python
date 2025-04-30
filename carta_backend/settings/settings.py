import os
import platform
import sys
from pathlib import Path


class ProgramSettings:
    def __init__(
            self,
            host: str | None = None,
            socket_port: int = 3002,
            frontend_folder: str = "../share/carta/frontend",
            backend_path: str = sys.executable,
            user_folder_prefix: str = ".carta",
            top_level_folder: str = "/",
            starting_folder: str = ".",
            version: str = "0.0.1",
    ) -> None:
        self.host = host
        self.socket_port = socket_port
        self.frontend_folder = os.path.abspath(frontend_folder)
        self.backend_path = os.path.abspath(backend_path)
        self.user_folder_prefix = user_folder_prefix
        if platform.system() == "Windows":
            cwd = Path.cwd()
            self.top_level_folder = Path(f"{cwd.drive}\\")
        else:
            self.top_level_folder = top_level_folder
        self.starting_folder = os.path.abspath(starting_folder)
        self.version = version

        # Set host
        if self.host is None or self.host == "0.0.0.0":
            self.host = os.getenv("SERVER_IP", "localhost")

        # Set user directory
        home: Path = Path.home()
        self.user_directory: Path = home / self.user_folder_prefix

        # Set log file
        log_dir: Path = self.user_directory / "log"
        log_dir.mkdir(exist_ok=True, parents=True)
        self.log_file: Path = log_dir / "carta.log"
