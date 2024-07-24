def get_common_record_fields():
    return [
        "SCAN",
        "PINI",
        "PHAS",
        "EVNT",
        "PRIO",
        "DISV",
        "DISA",
        "SDIS",
        "PROC",
        "DISS",
        "LSET",
        "LCNT",
        "PACT",
        "FLNK",
    ]


def get_mbb_record_fields():
    return [
        "ZRST",
        "ONST",
        "TWST",
        "THST",
        "FRST",
        "FVST",
        "SXST",
        "SVST",
        "EIST",
        "NIST",
        "TEST",
        "ELST",
        "TVST",
        "TTST",
        "FTST",
        "FFST",
    ]


def get_epics_record_fields():
    return get_common_record_fields() + get_mbb_record_fields()
