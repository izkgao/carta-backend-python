import argparse
import asyncio
import os
import sys
from importlib.metadata import version as get_version
from uuid import uuid4

os.environ["NUMBA_THREADING_LAYER"] = "omp"

import dask.config

from carta_backend.log import configure_logger, logger
from carta_backend.server import Server
from carta_backend.settings import ProgramSettings
from carta_backend.utils import is_port_available


def main():
    parser = argparse.ArgumentParser(
        description="Cube Analysis and Rendering Tool for Astronomy",
        usage="carta [OPTION...] <file or folder to open>",
    )

    parser.add_argument(
        "file_or_folder", nargs="?", help="File or folder to open"
    )
    parser.add_argument(
        "--dask-scheduler",
        type=str,
        help="Dask scheduler address (e.g., 127.0.0.1:8786)",
    )
    parser.add_argument(
        "-v", "--version", action="store_true", help="Print version"
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        default=4,
        help="Display verbose logging from this level (default: 4)",
    )
    parser.add_argument(
        "--no_log", action="store_true", help="Do not log output to a log file"
    )
    parser.add_argument(
        "--log_performance",
        action="store_true",
        help="Enable performance debug logs",
    )
    parser.add_argument(
        "--log_protocol_messages",
        action="store_true",
        help="Enable protocol message debug logs",
    )
    parser.add_argument(
        "--max_log_file_size",
        type=str,
        default="5 MB",
        help="Maximum log file size (default: 5 MB)",
    )
    parser.add_argument(
        "--no_frontend",
        action="store_true",
        help="Disable built-in HTTP frontend interface",
    )
    parser.add_argument(
        # Not implemented yet
        "--no_database",
        action="store_true",
        help="Disable built-in HTTP database interface",
    )
    parser.add_argument(
        # Not implemented yet
        "--http_url_prefix",
        type=str,
        help="Custom URL prefix for HTTP server",
    )
    parser.add_argument(
        "--no_browser",
        action="store_true",
        help="Don't open the frontend URL in a browser on startup",
    )
    parser.add_argument(
        # Not implemented yet
        "--browser",
        type=str,
        help="Custom browser command",
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Only listen on the specified interface (IP address or hostname)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=3002,
        help="Manually set the HTTP and WebSocket port (default: 3002)",
    )
    parser.add_argument(
        "--top_level_folder",
        type=str,
        default="/",
        help="Set top-level folder for data files",
    )
    parser.add_argument(
        "--frontend_folder",
        type=str,
        help="Set folder from which frontend files are served",
    )
    parser.add_argument(
        # Not implemented yet
        "--exit_timeout",
        type=int,
        help="Number of seconds to stay alive after last session exits",
    )
    parser.add_argument(
        # Not implemented yet
        "--initial_timeout",
        type=int,
        help="Number of seconds to stay alive at start if no clients connect",
    )
    parser.add_argument(
        # Not implemented yet
        "--idle_timeout",
        type=int,
        help="Number of seconds to keep idle sessions alive",
    )
    parser.add_argument(
        # Not implemented yet
        "--read_only_mode",
        action="store_true",
        help="Disable write requests",
    )
    parser.add_argument(
        # Not implemented yet
        "--enable_scripting",
        action="store_true",
        help="Enable HTTP scripting interface",
    )
    parser.add_argument(
        # Not implemented yet
        "--no_user_config",
        action="store_true",
        help="Ignore user configuration file",
    )
    parser.add_argument(
        # Not implemented yet
        "--no_system_config",
        action="store_true",
        help="Ignore system configuration file",
    )
    parser.add_argument(
        "--use_dask",
        action="store_true",
        help="Use Dask for file operations",
    )

    # Debug options
    parser.add_argument(
        "--debug_no_auth",
        action="store_true",
        help="Accept all incoming WebSocket connections (not secure)",
    )
    parser.add_argument(
        # Not implemented yet
        "--no_runtime_config",
        action="store_true",
        help="Do not send a runtime config object to frontend clients",
    )
    parser.add_argument(
        # Not implemented yet
        "--controller_deployment",
        action="store_true",
        help="Used when backend is launched by carta-controller",
    )
    parser.add_argument(
        "--dask_chunk_size",
        type=str,
        default="132.25Mib",
        help="Chunk size for Dask arrays",
    )

    args = parser.parse_args()

    # Show version
    if args.version:
        print(get_version("carta-backend"))
        return None

    # Set program settings
    ps = ProgramSettings(
        host=args.host,
        socket_port=args.port,
        frontend_folder=args.frontend_folder,
        top_level_folder=args.top_level_folder,
        file_or_folder=args.file_or_folder,
    )

    # Configure logger
    configure_logger(
        file=ps.log_file,
        rotation=args.max_log_file_size,
        verbosity=args.verbosity,
        no_log=args.no_log,
        log_performance=args.log_performance,
        log_protocol_messages=args.log_protocol_messages,
    )
    clog = logger.bind(name="CARTA")

    # Check if the port is available
    if not is_port_available(ps.socket_port):
        msg = f"Port {ps.socket_port} is already in use."
        clog.warning(msg)

        for port in range(ps.socket_port + 1, 65536):
            if is_port_available(port):
                ps.socket_port = port
                break

        msg = f"Change to the nearest available port {ps.socket_port}."
        clog.warning(msg)

    # Set token
    base_url = f"http://{ps.host}:{ps.socket_port}"
    if args.debug_no_auth:
        token = None
        url = f"{base_url}/"
    else:
        token = str(uuid4())
        url = f"{base_url}/?token={token}"

    # Open file
    if ps.file is not None:
        url += f"&file={ps.file}"

    # Show information
    clog.info(f"Writing to the log file: {ps.log_file}")
    clog.info(f"{ps.backend_path}: Version {ps.version}")
    clog.info(f"Serving CARTA frontend from {ps.frontend_folder}")
    clog.info(
        f"Listening on port {ps.socket_port} "
        f"with top level folder {ps.top_level_folder}, "
        f"starting folder {ps.starting_folder}."
    )
    clog.info(f"CARTA is accessible at {url}")

    if not args.no_database:
        database_url = f"{base_url}/api/database/..."
        clog.debug(f"The CARTA database API is accessible at {database_url}")

    if args.enable_scripting:
        scripting_url = f"{base_url}/api/scripting/action"
        clog.debug(
            f"To use the CARTA scripting interface, "
            f"send POST requests to {scripting_url}"
        )

    # Set Dask chunk size
    dask.config.set({"array.chunk-size": args.dask_chunk_size})

    # Start server
    server = Server(
        frontend_folder=ps.frontend_folder,
        host=ps.host,
        port=ps.socket_port,
        token=token,
        top_level_folder=ps.top_level_folder,
        starting_folder=ps.starting_folder,
        dask_scheduler=args.dask_scheduler,
        file=ps.file,
        use_dask=args.use_dask,
    )

    try:
        asyncio.run(
            server.start(
                open_browser=not args.no_browser,
            )
        )
    except KeyboardInterrupt:
        clog.info("Exiting backend.")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
