from dataclasses import dataclass


@dataclass
class GraphQLServerOptions:
    host: str = "localhost"
    port: int = 8080
    log_level: str = "info"
