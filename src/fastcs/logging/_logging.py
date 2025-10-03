import getpass
import os
from enum import StrEnum
from logging import LogRecord
from typing import TYPE_CHECKING

from prompt_toolkit.patch_stdout import StdoutProxy
from pygelf import GelfUdpHandler
from pygelf.gelf import SKIP_LIST

from fastcs.logging._graylog import (
    GraylogEndpoint,
    GraylogEnvFields,
    GraylogStaticFields,
)

if TYPE_CHECKING:
    from loguru import Logger
else:
    from typing import Any

    Logger = Any


def _configure_logger(
    logger: Logger,
    level: "LogLevel | None" = None,
    graylog_endpoint: GraylogEndpoint | None = None,
    graylog_static_fields: GraylogStaticFields | None = None,
    graylog_env_fields: GraylogEnvFields | None = None,
):
    logger.remove()
    logger.add(
        sink=StdoutProxy(raw=True),  # type: ignore
        colorize=True,
        format=format_record,
        level=level or "INFO",
    )

    if graylog_endpoint is not None:
        static_fields = {
            "app_name": "fastcs",
            "username": getpass.getuser(),
            "process_id": os.getpid(),
        }
        if graylog_static_fields is not None:
            static_fields.update(graylog_static_fields)

        logger.add(
            LoguruGelfUdpHandler(
                graylog_endpoint.host,
                graylog_endpoint.port,
                # Include built-in file, line, module, function and logger_name fields
                debug=True,
                # Include these static fields
                static_fields=static_fields,
                # Include configured fields from environment
                additional_env_fields=graylog_env_fields,
                # Include fields added dynamically to log record (log statement kwargs)
                include_extra_fields=True,
            ),
            format="{message}",
            level="INFO",
        )

    if level is None:
        logger.disable("fastcs")
    else:
        logger.enable("fastcs")


def format_record(record) -> str:
    _time = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    _timezone = record["time"].strftime("%z")
    time = f"{_time}{_timezone}"

    name = record["extra"].pop("logger_name", None) or record["name"]

    sep = "<white>,</white> "
    if "extra" in record:
        extras = [
            format_key_value(k, v)
            for k, v in record["extra"].items()
            if not k.startswith("_")
        ]
        extras = f"{sep.join(extras)}"
    else:
        extras = ""

    return f"""\
<level>[{time} {record["level"].name[0]}]</level> \
{record["message"]:<80} \
<green>[{name}]</green> \
{extras}
{{exception}}\
"""


def format_key_value(k, v):
    return f"<cyan>{k}</cyan><white>=</white><magenta>{v}</magenta>"


class LogLevel(StrEnum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoguruGelfUdpHandler(GelfUdpHandler):
    def convert_record_to_gelf(self, record: LogRecord):
        # Use full file path instead of file name
        record.__dict__["filename"] = record.__dict__["pathname"]

        # Pull loguru extra fields into root of record for pygelf to include
        extras = record.__dict__.pop("extra", {})
        for k, v in extras.items():
            if k not in SKIP_LIST and not k.startswith("_"):
                record.__dict__[k] = v

        return super().convert_record_to_gelf(record)
