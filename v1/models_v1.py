from pydantic import BaseModel
from typing import Union, List, Optional


class UpdateBody(BaseModel):
    fields: Union[dict, None] = None
    fields_guild: Union[dict, None] = None
    upsert: bool = True


class GetGuildUser(BaseModel):
    db: str
    user_id: int
    guild_id: Union[None, int] = None
    fields: Union[None, List[str]] = None
    # suppress_id: bool = True
    get_preferences: bool = True


class GetGuildServer(BaseModel):
    db: str
    guild_id: Union[None, int] = None
    fields: Union[None, List[str]] = None
    # suppress_id: bool = True


class UpdateGuildUser(BaseModel):
    db: str
    user_id: int
    guild_id: int
    update: UpdateBody


class UpdateGuildServer(BaseModel):
    db: str
    guild_id: int
    update: UpdateBody  # fields_guild is not used.


class GetTranslations(BaseModel):
    db: str
    schemes: List[str]
    only_timestamps: bool = False
    as_one_document: bool = False


class AddTranslation(BaseModel):
    db: str
    scheme_name: str
    language: str
    code: str
    translation: str


class GetGlobalSettings(BaseModel):
    db: str
    fields: Union[None, List[str]] = None


class Aggregate(BaseModel):
    db: str
    aggregate: Union[list, tuple]
    collection: str
    length: Optional[int]
    to_int64_fields: Optional[List[str]] = []
