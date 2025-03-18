from dataclasses import dataclass, field


@dataclass
class RestServerOptions:
    host: str = "localhost"
    port: int = 8080
    log_level: str = "info"


@dataclass
class RestOptions:
    """Options for the Rest transport."""

    rest: RestServerOptions = field(default_factory=RestServerOptions)
