from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class Rarity(StrEnum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class UIColorToken(StrEnum):
    CYAN = "cyan"
    VIOLET_HI = "violetHi"
    GOLD = "gold"
    PINK = "pink"


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


def rarity_sa_enum() -> SAEnum:
    return SAEnum(Rarity, values_callable=enum_values, name="rarity")


def ui_color_token_sa_enum() -> SAEnum:
    return SAEnum(
        UIColorToken,
        values_callable=enum_values,
        name="ui_color_token",
    )
