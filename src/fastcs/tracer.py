from collections import defaultdict
from typing import Any

from fastcs.logging import logger


class Tracer:
    """A mixin or standalone class for conditionally logging trace events.

    This can be used for verbose logging that is disabled by default and enabled on a
    per-instance basis, with filtering based on specific key-value pairs on the event.

    Any instance of this class can enable tracing independently. Some key classes
    inherit this class, such as ``Attributes``, and some modules have their own
    ``Tracer``, such as ``fastcs.launch``. When enabled, any event logged from the
    object, or from another ``Tracer`` that uses the object as the ``topic``, will be
    logged.

    Note: The global logger level must be set to ``TRACE`` for the messages to be logged

    Example usage:
    >>> controller.ramp_rate.enable_tracing()
    >>> controller.ramp_rate.disable_tracing()
    >>> controller.connection.enable_tracing()
    >>> controller.connection.add_tracing_filter("query", "V?")
    >>> controller.connection.remove_tracing_filter("query", "V?")
    >>> controller.connection.disable_tracing()

    :param name: The name of the logger. Attached to log messages as ``logger_name``.

    """

    def __init__(self, name: str | None = None):
        self.__tracing_enabled: bool = False
        self.__tracing_filters: dict[str, list[Any]] = defaultdict(list)
        self.__logger_name = name if name is not None else self.__class__.__name__

    def log_event(self, event: str, topic: "Tracer | None" = None, *args, **kwargs):
        """Log an event only if tracing is enabled and the filter matches

        :param event: A message describing the event
        :param topic: Another `Tracer` related to this event to enable it to be logged
        :param args: Positional arguments for underlying logger
        :param kwargs: Keyword arguments for underlying logger

        """
        if self.__tracing_enabled or (topic is not None and topic.__tracing_enabled):  # noqa: SLF001
            if self.__tracing_filters:
                for kwarg, values in self.__tracing_filters.items():
                    if kwarg in kwargs and any(kwargs[kwarg] == v for v in values):
                        break
                else:
                    return

            logger.trace(event, *args, logger_name=self.__logger_name, **kwargs)

    def enable_tracing(self):
        """Enable trace logging for this object"""
        self.__tracing_enabled = True

    def disable_tracing(self):
        """Disable trace logging for this object"""
        self.__tracing_enabled = False

    def add_tracing_filter(self, key: str, value: Any):
        """Add a filter for trace log messages from this object

        To reduce trace messages further, a filter can be applied such that events must
        have a key with a specific value for it to be logged.

        :param key: A new or existing key to filter on
        :param value: An allowed value for the event to be logged

        """
        self.__tracing_filters[key].append(value)

    def remove_tracing_filter(self, key: str, value: Any):
        """Remove a specific key-value pair from the filter

        :param key: An existing filter key
        :param value: The allowed value to remove

        """
        if (
            key not in self.__tracing_filters
            or value not in self.__tracing_filters[key]
        ):
            return

        self.__tracing_filters[key].remove(value)
        if not self.__tracing_filters[key]:
            self.__tracing_filters.pop(key)

    def clear_tracing_filters(self):
        """Clear all filters and allow all messages to be logged (if enabled)"""
        self.__tracing_filters.clear()
