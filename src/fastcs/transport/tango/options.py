from dataclasses import dataclass, field


@dataclass
class TangoDSROptions:
    dev_name: str = "MY/DEVICE/NAME"
    dev_class: str = "FAST_CS_DEVICE"
    dsr_instance: str = "MY_SERVER_INSTANCE"
    debug: bool = False


@dataclass
class TangoOptions:
    dsr: TangoDSROptions = field(default_factory=TangoDSROptions)
