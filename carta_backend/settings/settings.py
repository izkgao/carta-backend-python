import os
import platform
import sys
from pathlib import Path
from urllib.parse import quote


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
        file_or_folder: str | None = None,
        version: str = "0.0.1",
    ) -> None:
        self.host = host
        self.socket_port = socket_port
        self.frontend_folder = os.path.abspath(frontend_folder)
        self.backend_path = os.path.abspath(backend_path)
        self.user_folder_prefix = user_folder_prefix
        if platform.system() == "Windows":
            if top_level_folder == "/":
                self.top_level_folder = top_level_folder
            else:
                self.top_level_folder = os.path.abspath(top_level_folder)
        else:
            self.top_level_folder = os.path.abspath(top_level_folder)
        self.starting_folder = os.path.abspath(starting_folder)
        self.file_or_folder = file_or_folder
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

        # Set file or folder
        self.file = None
        if self.file_or_folder is not None:
            self.file_or_folder = os.path.abspath(self.file_or_folder)

            if os.path.isdir(self.file_or_folder):
                # Zarr
                if os.path.exists(os.path.join(self.file_or_folder, ".zattrs")):
                    self.file = self.file_or_folder
                # CASA
                elif os.path.exists(os.path.join(self.file_or_folder, "table.lock")):
                    self.file = self.file_or_folder
                # Directory
                else:
                    self.starting_folder = self.file_or_folder
            else:
                self.file = self.file_or_folder

        if self.file is not None:
            file = Path(self.file).relative_to(self.top_level_folder)
            self.file = quote(bytes(file), safe="")
