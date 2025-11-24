from dataclasses import dataclass


@dataclass
class RestServerOptions:
    host: str = "localhost"
    port: int = 8080
    log_level: str = "info"
