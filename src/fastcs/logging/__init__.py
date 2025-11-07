import logging

from loguru import logger as _logger

from ._graylog import GraylogEndpoint as GraylogEndpoint
from ._graylog import GraylogEnvFields as GraylogEnvFields
from ._graylog import GraylogStaticFields as GraylogStaticFields
from ._graylog import parse_graylog_env_fields as parse_graylog_env_fields
from ._graylog import parse_graylog_static_fields as parse_graylog_static_fields
from ._logging import Logger, LogLevel, _configure_logger

logger = _logger.bind(logger_name="fastcs")
"""FastCS logger

This is a singleton logger instance to be used throughout the library and in specific
drivers. This logger uses ``loguru`` as underlying logging library, which enables much
simpler configuration as well as structured logging.

Keyword arguments to log statments will be attached as extra fields on the log record.
These fields are displayed separately in the console output and can used for filtering
and metrics in graylog.

It is best to keep the message short and use extra fields for additional information for
messages to be formatted nicely in the console. To add kwargs to format the message
without them appearing as extra fields, prepend the key with ``_``.

.. code-block:: python

    from fastcs.logging import logger

    logger.info("PV put: {pv} = {value}", pv=pv, value=value)

By default messages will be logged with the name ``fastcs``. Within different modules
and classes it can be useful to override this name. This can be done with the ``bind``
method. To create a module logger with its name

.. code-block:: python

    from fastcs.logging import logger as _logger

    logger = _logger.bind(logger_name=__name__)

or to create a class logger with its name

.. code-block:: python

    self.logger = _logger.bind(logger_name=__class__.__name__)

As standard ``loguru`` supports ``trace`` level monitoring, but it should not be used in
fastcs. Instead there is a ``Tracer`` class for verbose logging with fine-grained
controls that can be enabled by the user at runtime.

Use ``configure_logging`` to re-configure the logger at runtime. For more advanced
controls, configure the ``logger`` singleton directly.

See the ``loguru`` docs for more information: https://loguru.readthedocs.io
"""


def bind_logger(logger_name: str) -> Logger:
    """Create a wrapper of the singleton fastcs logger with the given name bound

    The name will be displayed in all log messages from the returned wrapper.

    See the docstring for ``fastcs.logging.logger`` for more information.

    """

    return logger.bind(logger_name=logger_name)


def configure_logging(
    level: LogLevel | None = None,
    graylog_endpoint: GraylogEndpoint | None = None,
    graylog_static_fields: GraylogStaticFields | None = None,
    graylog_env_fields: GraylogEnvFields | None = None,
):
    """Configure FastCS logger

    This function can be called at any time to
      - Change the console log level
      - Enable/disable graylog logging

    :param level: Log level to set
    :param graylog_endpoint: Endpoint for graylog logging - '<host>:<port>'
    :param graylog_static_fields: Fields to add to graylog messages with static values
    :param graylog_env_fields: Fields to add to graylog messages from env variables

    """
    global logger

    _configure_logger(
        logger, level, graylog_endpoint, graylog_static_fields, graylog_env_fields
    )


# Configure logger with defaults - INFO level and disabled
configure_logging()


class _StdLoggingInterceptHandler(logging.Handler):
    """A std logging handler to forward messages to loguru with nice formatting."""

    def emit(self, record: logging.LogRecord):
        logger.bind(logger_name=self.name).log(record.levelname, record.getMessage())


def intercept_std_logger(logger_name: str):
    """Intercept std logging messages from the given logger

    To find the correct ``logger_name`` for a message. Add a breakpoint in
    ``logging.Logger.callHandlers``, debug and run until the log message appears as
    ``record.msg``. The logger name will be in ``self.name``.

    :param logger_name: Name of the logger to intercept

    """
    handler = _StdLoggingInterceptHandler()
    handler.set_name(logger_name)

    std_logger = logging.getLogger(logger_name)
    std_logger.handlers = [handler]
    std_logger.propagate = False
