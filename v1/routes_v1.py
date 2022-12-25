from main import app
from .models_v1 import *
from database import client as db_client
from fastapi import Response, status
from libs.util import get_timestamp


FORBIDDEN_DB_NAMES = ["admin", "local", "config"]


@app.get("/v1/")  # must be in every version! Bots are testing connection to this!
async def root():
    return {"message": "ok"}


@app.get("/v1/get_user/")
async def get_user_v1(data: GetGuildUser, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    fields_filter = None

    if data.fields:
        if data.guild_id:
            fields_filter = {f"{data.guild_id}.{field}": 1 for field in data.fields}
        else:
            fields_filter = {f: 1 for f in data.fields}
    else:
        if data.guild_id:
            fields_filter = {f"{data.guild_id}": 1}

    if data.get_preferences and fields_filter != None:
        fields_filter["preferences"] = 1

    user_data = await db_client[data.db].users.find_one(
        {"_id": data.user_id}, fields_filter
    )

    response = {
        "message": "ok",
        "response": user_data,
    }

    return response


@app.post("/v1/update_user/")
async def update_user_v1(data: UpdateGuildUser, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    # fields_update - update without knowing target guild_id (free modify)
    # fields_guild_update - update with knowing target guild_id (guild modify)
    fields_update = data.update.fields or {}
    fields_guild_update = data.update.fields_guild or {}

    # Adds a guild id to each field at the beginning for fields_guild_update
    for value in fields_guild_update:
        c = fields_guild_update[value].copy()

        for v in c:
            fields_guild_update[value][f"{data.guild_id}." + v] = fields_guild_update[
                value
            ][v]
            del fields_guild_update[value][v]

    for update in [fields_update, fields_guild_update]:
        for command in update:
            await db_client[data.db].users.update_one(
                {"_id": data.user_id},
                {"$" + command: update[command]},
                data.update.upsert,
            )

    return {"message": "ok"}


@app.get("/v1/get_server/")
async def get_server_v1(data: GetGuildServer, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    fields_filter = None

    if data.fields:
        fields_filter = {f: 1 for f in data.fields}

    server_data = await db_client[data.db].servers.find_one(
        {"_id": data.guild_id}, fields_filter
    )

    response = {
        "message": "ok",
        "response": server_data,
    }

    return response


@app.post("/v1/update_server/")
async def update_server_v1(data: UpdateGuildServer, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    fields_update = data.update.fields or {}

    for command in fields_update:
        await db_client[data.db].servers.update_one(
            {"_id": data.guild_id},
            {"$" + command: fields_update[command]},
            data.update.upsert,
        )

    return {"message": "ok"}


@app.get("/v1/get_translations/")
async def get_translations_v1(data: GetTranslations, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    total_data = {}

    for scheme in data.schemes:
        if data.only_timestamps:
            total_data[scheme] = (
                (await db_client[data.db][scheme].find_one({"_id": "_meta"})) or {}
            ).get("last_update", 0)
        else:
            scheme_data = await db_client[data.db][scheme].find().to_list(length=None)

            for document in scheme_data:
                _id = document["_id"]
                del document["_id"]
                if data.as_one_document:
                    total_data[_id] = document
                else:
                    if total_data.get(scheme, None) == None:
                        total_data[scheme] = {}
                    total_data[scheme][_id] = document

    return {"message": "ok", "response": total_data}


@app.post("/v1/add_translation/")
async def add_translation_v1(data: AddTranslation, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    await db_client[data.db][data.scheme_name].update_one(
        {"_id": data.code}, {"$set": {data.language: data.translation}}, True
    )

    await db_client[data.db][data.scheme_name].update_one(
        {"_id": "_meta"}, {"$set": {"last_update": get_timestamp()}}, True
    )

    return {"message": "ok"}


@app.get("/v1/get_global_settings/")
async def get_global_settings_v1(data: GetGlobalSettings, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    return {
        "message": "ok",
        "response": (
            await db_client[data.db]["global"].find_one(
                {"_id": "settings"}, data.fields
            )
        ),
    }


@app.get("/v1/aggregate/")
async def aggregate_v1(data: Aggregate, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    db_response = db_client[data.db][data.collection].aggregate(data.aggregate)
    db_response = await db_response.to_list(length=data.length)

    return {"message": "ok", "response": db_response}
