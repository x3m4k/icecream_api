from pydantic import BaseModel
from typing import Union, List, Optional


class MCYasnoIncBal(BaseModel):
    user_id: int
    amount: int


class MCYasnoCheckOreAward(BaseModel):
    block_id: str  # block coordinates


class MCYasnoBlockOreAward(BaseModel):
    block_id: str


class MCYasnoProcessOreAward(BaseModel):
    user_id: int  # -    discord id
    block: str  #   -    modern block naming: minecraft:diamond


class MCYasnoUpdateSync(BaseModel):
    user_id: str
    mc_nick: str
    state: bool


class MCYasnoGetInv(BaseModel):
    user_id: int  # - discord id
    page: int


class MCYasnoGetInvItem(BaseModel):
    user_id: int  # - discord id
    item_id: int
    item_amount: int
