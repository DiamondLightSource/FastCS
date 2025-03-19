from dataclasses import dataclass, field


@dataclass
class TangoDSROptions:
    dev_name: str = "MY/DEVICE/NAME"
    dsr_instance: str = "MY_SERVER_INSTANCE"
    debug: bool = False


@dataclass
class TangoOptions:
    """Options for the Tango transport."""

    dsr: TangoDSROptions = field(default_factory=TangoDSROptions)
