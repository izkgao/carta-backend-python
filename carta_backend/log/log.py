import sys

from loguru import logger

VERBOSITY_LEVELS = {
    0: "OFF",
    1: "CRITICAL",
    2: "ERROR",
    3: "WARNING",
    4: "INFO",
    5: "DEBUG",
    6: "TRACE",
}

# Remove default handler
logger.remove()


def formatter(record):
    message = record["message"]
    log_format = [
            "[{time:YYYY-MM-DD HH:mm:ss.SSSZ}]",
            "[{extra[name]}]",
            "[<level>{level}</level>]",
            message,
            "\n{exception}"]
    log_format = " ".join(log_format)
    return log_format


def configure_logger(file=None, rotation="5 MB", verbosity=4, no_log=False,
                     log_performance=False, log_protocol_messages=False):
    # Get log level
    if log_performance or log_protocol_messages:
        verbosity = max(verbosity, 5)
    level = VERBOSITY_LEVELS.get(verbosity, "INFO")

    if not (level == "OFF" or no_log):
        # Set log filters
        filt_list = []
        if not log_performance:
            filt_list.append('Performance')
        if not log_protocol_messages:
            filt_list.append('Protocol')

        def log_filter(record):
            return record['extra']['name'] not in filt_list

        # Set INFO to green
        logger.level("INFO", color="<green>")

        # Add stderr handler
        logger.add(sys.stderr, level=level, format=formatter,
                   filter=log_filter, enqueue=True)

        # Add file handler
        if file is not None:
            logger.add(file, level=level, format=formatter, filter=log_filter,
                       rotation=rotation, enqueue=True)


__all__ = ["configure_logger", "logger"]
