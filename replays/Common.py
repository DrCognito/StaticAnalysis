import enum


class Team(enum.Enum):
    RADIANT = 2
    DIRE = 3


class WardType(enum.Enum):
    OBSERVER = "observer"
    SENTRY = "sentry"