from dataclasses import dataclass, field


@dataclass
class GraphQLServerOptions:
    host: str = "localhost"
    port: int = 8080
    log_level: str = "info"


@dataclass
class GraphQLOptions:
    """Options for the GraphQL transport."""

    gql: GraphQLServerOptions = field(default_factory=GraphQLServerOptions)
