from dataclasses import dataclass


@dataclass
class TangoDSROptions:
    dev_name: str = "MY/DEVICE/NAME"
    dsr_instance: str = "MY_SERVER_INSTANCE"
    debug: bool = False
