from main import app
from .models_v1 import *
from database import client as db_client
from fastapi import Response, status
from libs.util import get_timestamp, walk_dict
import bson
from bson.objectid import ObjectId
import inspect
from pymongo import UpdateOne
from libs.util import *


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
                {"$" + command.strip("$"): update[command]},
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
            {"$" + command.strip("$"): fields_update[command]},
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
            (
                await db_client[data.db]["global"].find_one(
                    {"_id": "settings"}, data.fields
                )
            )
            or {}
        ),
    }


@app.post("/v1/aggregate/")
async def aggregate_v1(data: Aggregate, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    for pt in data.to_int64_fields or []:
        for cmd in data.aggregate:
            last_name = pt.rsplit(".", 1)[1]
            container = walk_dict(cmd, pt.rsplit(".", 1)[0], None)

            if not container:
                continue

            obj = container.get(last_name)
            container[last_name] = bson.int64.Int64(obj)

    db_response = db_client[data.db][data.collection].aggregate(data.aggregate)
    db_response = await db_response.to_list(length=data.length)

    for obj in db_response:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, ObjectId):
                    obj[k] = str(v)

    return {"message": "ok", "response": db_response}


@app.post("/v1/count_documents/")
async def count_documents_v1(data: CountDocuments, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    return {
        "message": "ok",
        "response": await db_client[data.db][data.collection].count_documents(
            data.pattern
        ),
    }


# -- f5 exclusive queries


@app.post("/v1/f5/tsearch/")
async def f5_tsearch_v1(data: F5TSearch, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    db = db_client[data.db]

    user_skipped = (
        walk_dict(
            await db[data.user_skipped_coll].find_one(
                {"_id": data.user_id}, {data.user_skipped_game: 1}
            ),
            data.user_skipped_game,
            {},
        )
        or {}
    )

    total_documents = []

    async for doc in db[data.collection].aggregate(data.pipeline, allowDiskUse=True):
        prof_data = walk_dict(doc, data.walk_to_game, {})
        global_data = walk_dict(doc, data.walk_to_global, {})

        if global_data.get("ban", None):
            until = global_data.get("ban", {}).get("until", None)
            if not until is None and (until == -1 or until > get_utc_timestamp()):
                continue

        created_at = prof_data.get("created_at", 0)

        user_skipped_data = user_skipped.get(str(doc["_id"]), {})

        if user_skipped_data:
            unskip_at = user_skipped_data.get("unskip_at", 0)

            if user_skipped_data.get("skip_at", None) == created_at or (
                get_utc_timestamp() <= unskip_at
            ):
                continue

        total_documents.append(doc)
        break

    try:
        user = total_documents[0]
    except:
        user = None

    if data.exclude_global_fields:
        for f in data.exclude_global_fields:
            try:
                del global_data[f]
            except:
                pass

    if user != None:
        global_data["_id"] = doc["_id"]
        response = {"user": {"profile": prof_data, "global": global_data}}
    else:
        response = {}

    return {"message": "ok", "response": response}


@app.post("/v1/f5/dating_search/")
async def f5_dating_search_v1(data: F5DatingSearch, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    db = db_client[data.db]

    user_skipped = (
        walk_dict(
            await db[data.user_skipped_coll].find_one(
                {"_id": data.user_id}, {"dating": 1}
            ),
            "dating",
            {},
        )
        or {}
    )

    total_documents = []

    async for doc in db[data.collection].aggregate(data.pipeline, allowDiskUse=True):
        user_data = walk_dict(doc, data.walk_to_data, {})
        global_data = walk_dict(doc, data.walk_to_global, {})

        if global_data.get("ban", None):
            until = global_data.get("ban", {}).get("until", None)
            if not until is None and (until == -1 or until > get_utc_timestamp()):
                continue

        edited_at = user_data.get("edited_at", 0)

        user_skipped_data = user_skipped.get(str(doc["_id"]), {})

        if user_skipped_data:
            unskip_at = user_skipped_data.get("unskip_at", 0)

            if user_skipped_data.get("skip_at", None) == edited_at or (
                get_utc_timestamp() <= unskip_at
            ):
                continue

        total_documents.append(doc)
        break

    try:
        user = total_documents[0]
    except:
        user = None

    # if data.exclude_global_fields:
    #     for f in data.exclude_global_fields:
    #         try:
    #             del global_data[f]
    #         except:
    #             pass

    if user != None:
        # global_data["_id"] = doc["_id"]
        response = {"user": {"_id": user["_id"], **user_data}}
    else:
        response = {}

    return {"message": "ok", "response": response}


# --


# -- lite exclusive queries
@app.post("/v1/lite/dump_transactions/")
async def lite_dump_transactions_v1(data: LiteDumpTransactions, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    await db_client[data.db][data.collection].bulk_write(
        [
            UpdateOne(
                {"_id": int(obj[0])},
                {"$push": {"history": {"$each": [obj[1]], "$slice": -500_000}}},
                upsert=True,
            )
            for obj in data.data
        ],
        ordered=False,
    )

    return {"message": "ok"}


@app.post("/v1/lite/delete_marries/")
async def lite_delete_marries_v1(data: LiteDeleteMarries, res: Response):
    if data.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    await db_client[data.db][data.collection].bulk_write(
        [
            UpdateOne(
                {"_id": int(user_id)},
                {"$unset": {f"{data.guild_id}.marry": ""}},
            )
            for user_id in data.data
        ],
        ordered=False,
    )

    return {"message": "ok"}


# --


# unsafe
@app.post("/v1/query/")
async def query_v1(query: DirectQuery, res: Response):
    if query.db in FORBIDDEN_DB_NAMES:
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": "Wrong db name."}

    if query.method.count(".") or query.method.count("__"):
        return {"message": "Wrong method."}

    for pt in query.to_int64_fields or []:
        for cmd in query.data:
            if pt.count(".") > 0:
                last_name = pt.rsplit(".", 1)[1]
                container = walk_dict(cmd, pt.rsplit(".", 1)[0], None)

                if not container or not isinstance(container, dict):
                    continue

                obj = container.get(last_name)

                container[last_name] = bson.int64.Int64(obj)
            else:
                cmd[pt] = bson.int64.Int64(cmd[pt])

    method = getattr(db_client[query.db][query.collection], query.method)

    response = method(*query.data)

    if inspect.isawaitable(response):
        response = await response
    else:
        response = await response.to_list(length=None)

    if isinstance(response, dict):
        for obj in response:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, ObjectId):
                        obj[k] = str(v)

    if not isinstance(response, (list, int, str)):
        try:
            response = dict(response)
        except:
            response = {}

    return {"message": "ok", "response": response}
