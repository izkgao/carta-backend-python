import asyncio
import os
import webbrowser
from random import randint

import uvicorn
from dask.distributed import Client
from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket

from carta_backend.log import logger
from carta_backend.session import Session
from carta_backend.utils import get_event_info

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")


class Server:
    """Server class for the Carta backend.

    This class encapsulates the server functionality, including HTTP and
    WebSocket endpoints, route creation, and server startup.

    Attributes
    ----------
    session : Session
        The session object for handling WebSocket messages
    frontend_folder : str
        Path to the folder containing the frontend files
    host : str
        Host address to bind the server to
    port : int
        Port to bind the server to
    token : str, optional
        Authentication token for securing WebSocket connections
    """

    def __init__(self, frontend_folder='.', host="0.0.0.0", port=3002,
                 token=None, top_level_folder=None, starting_folder=None,
                 dask_scheduler=None):
        """Initialize the Server instance.

        Parameters
        ----------
        frontend_folder : str, optional
            Path to the folder containing the frontend files, by default '.'
        host : str, optional
            Host address to bind the server to, by default "0.0.0.0"
        port : int, optional
            Port to bind the server to, by default 3002
        token : str, optional
            Authentication token for securing WebSocket connections,
            by default None
        top_level_folder : str, optional
            Top level folder for file operations, by default None
        starting_folder : str, optional
            Starting folder for file operations, by default None
        dask_scheduler : str, optional
            Dask scheduler address, by default None
        """
        self.frontend_folder = frontend_folder
        self.host = host
        self.port = port
        self.token = token
        self.top_level_folder = top_level_folder
        self.starting_folder = starting_folder
        self.dask_scheduler = dask_scheduler

        self.client = None
        self.session = None

    async def http_endpoint(self, request):
        """Serve the main HTML file.

        Parameters
        ----------
        request : Request
            The HTTP request object

        Returns
        -------
        FileResponse
            The HTTP response containing the HTML file
        """
        html_path = os.path.join(self.frontend_folder, "index.html")
        return FileResponse(html_path)

    async def websocket_endpoint(self, websocket: WebSocket):
        """Handle WebSocket connections with optional token authentication.

        Parameters
        ----------
        websocket : WebSocket
            The WebSocket connection object

        Returns
        -------
        None
        """
        # Check authentication if token is provided
        if self.token:
            # First check query parameters
            client_token = websocket.query_params.get("token", None)
            if not client_token:
                # Check for token in headers
                auth_header = websocket.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    client_token = auth_header.replace("Bearer ", "")

            if client_token != self.token:
                await websocket.close(
                    code=1008, reason="Authentication failed")
                return

        await websocket.accept()

        while True:
            if self.session is None:
                await asyncio.sleep(0.01)
            else:
                break

        client_ip = websocket.client.host
        msg = f"Session {self.session.session_id:09d} [{client_ip}] Connected."
        clog.info(msg)

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._websocket_receiver(websocket))
                tg.create_task(self._websocket_sender(websocket))
        except asyncio.CancelledError:
            clog.debug("WebSocket receiver task was cancelled")
        except Exception as e:
            clog.error(f"WebSocket error: {e}")
        finally:
            if not websocket.client_state.DISCONNECTED:
                await websocket.close()
            clog.debug("WebSocket connection closed")

    async def _websocket_receiver(self, websocket: WebSocket):
        while True:
            message = await websocket.receive()
            if "text" in message:
                if message["text"] == "PING":
                    await websocket.send_text("PONG")
            elif "bytes" in message:
                await self.session.take_action(message["bytes"])
            elif message.get("type") == "websocket.disconnect":
                # Close session
                await self.session.queue.put(None)
                break

    async def _websocket_sender(self, websocket: WebSocket):
        while True:
            message = await self.session.queue.get()
            if message is None:
                break
            await websocket.send_bytes(message)
            _, event_name = get_event_info(message)
            ptlog.debug(f"<yellow>==> {event_name}</>")

    async def serve_root_file(self, request):
        """Serve files from the root directory.

        Parameters
        ----------
        request : Request
            The HTTP request object

        Returns
        -------
        FileResponse
            The HTTP response containing the requested file or index.html
        """
        filename = request.path_params["filename"]
        file_path = os.path.join(self.frontend_folder, filename)
        if os.path.exists(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(self.frontend_folder, "index.html"))

    def create_app(self):
        """Create the Starlette application with routes.

        Returns
        -------
        Starlette
            The configured Starlette application
        """
        routes = []

        # HTTP Route
        routes.append(Route("/", endpoint=self.http_endpoint,
                            methods=["GET", "POST"]))
        # WebSocket Route
        routes.append(WebSocketRoute("/", endpoint=self.websocket_endpoint))

        # Serve static files from the frontend directory
        directory = os.path.join(self.frontend_folder, "static")
        static = StaticFiles(directory=directory)
        routes.append(Mount("/static", static, name="static"))
        routes.append(Route("/{filename:path}", endpoint=self.serve_root_file))

        app = Starlette(
            routes=routes,
            on_startup=[],
        )
        return app

    async def open_browser_when_ready(self, url):
        """Wait for the server to start before opening the browser.

        Parameters
        ----------
        url : str
            The URL to open in the browser

        Returns
        -------
        None
        """
        while True:
            try:
                # Check if the server is responding
                reader, writer = await asyncio.open_connection(
                    self.host, self.port
                )
                writer.close()
                await writer.wait_closed()
                clog.debug("WebBrowser: using default browser.")
                msg = ("WebBrowser: Trying to launch CARTA with the "
                       f"default browser using: open {url}")
                clog.debug(msg)
                break
            except (OSError, ConnectionRefusedError):
                await asyncio.sleep(0.01)

        # Open the browser once the server is ready
        webbrowser.open(url)

    async def create_session(self):
        session_id = randint(100000000, 999999999)
        while True:
            if self.client is None:
                await asyncio.sleep(0.01)
            else:
                break
        self.session = Session(
            lock=asyncio.Lock(),
            top_level_folder=self.top_level_folder,
            starting_folder=self.starting_folder,
            session_id=session_id,
            client=self.client)

    async def start_dask_client(self):
        if self.dask_scheduler is None:
            self.client = await Client(
                asynchronous=True,
                threads_per_worker=4,
                n_workers=os.cpu_count() // 4
            )
        else:
            self.client = await Client(
                address=self.dask_scheduler
            )
        clog.info("Dask client started.")
        clog.info(f"Dask scheduler served at {self.client.scheduler.address}")
        clog.info(f"Dask dashboard link: {self.client.dashboard_link}")

    async def start(self, open_browser=True, enable_uvicorn_logs=False):
        """Start the Starlette server to serve the frontend application.

        Parameters
        ----------
        open_browser : bool, optional
            Whether to open a browser window on startup, by default True
        enable_uvicorn_logs : bool, optional
            Whether to enable Uvicorn logs, by default False

        Returns
        -------
        None
        """
        app = self.create_app()

        url = f"http://{self.host}:{self.port}/"
        if self.token:
            url += f"?token={self.token}"

        if enable_uvicorn_logs:
            config = uvicorn.Config(app, host=self.host, port=self.port)
        else:
            config = uvicorn.Config(
                app, host=self.host, port=self.port, log_config=None
            )

        server = uvicorn.Server(config=config)

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(server.serve())
                if open_browser:
                    tg.create_task(self.open_browser_when_ready(url))
                tg.create_task(self.create_session())
                tg.create_task(self.start_dask_client())
        except KeyboardInterrupt:
            pass
        finally:
            raise KeyboardInterrupt
