from dataclasses import dataclass, field


@dataclass
class P4PIOCOptions:
    pv_prefix: str = "MY-DEVICE-PREFIX"


@dataclass
class P4POptions:
    ioc: P4PIOCOptions = field(default_factory=P4PIOCOptions)
