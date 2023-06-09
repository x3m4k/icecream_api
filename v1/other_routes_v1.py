from main import app
from .other_models_v1 import *
from database import client as db_client
from fastapi import Response, status
from libs.util import get_timestamp, walk_dict
import bson
from bson.objectid import ObjectId
import inspect
from pymongo import UpdateOne
from libs.util import *
import secrets
from math import ceil
import os
import json

FORBIDDEN_DB_NAMES = ["admin", "local", "config"]

YASNO_GUILD_ID = 1112422551025631404
YASNO_DB = "icecream_lite"
YASNO_COLL = "users"
YASNO_BLOCK_DB = "yasno_mc"
YASNO_BLOCK_COLL = "ore_awards"

YASNO_DIAMOND_ORE_AWARD = {
    "balance_bonus": {"min": 5, "max": 10},
    "items": [
        {
            "chance": 1,
            "type": "case",
            "data": {"case_locale": "Lite", "case_id": 1},
            "amount": 1,
        },
        {
            "chance": 2,
            "type": "case",
            "data": {"case_locale": "MC - Еда", "case_id": 4},
            "amount": 1,
        },
        {
            "chance": 1,
            "type": "case",
            "data": {"case_locale": "MC - Тотем или ничего", "case_id": 6},
            "amount": 1,
        },
        {"chance": 96, "type": "nothing"},
    ],
}

YASNO_EMERALD_ORE_AWARD = {
    "balance_bonus": {"min": 7, "max": 15},
    "items": [
        {
            "chance": 3,
            "type": "case",
            "data": {"case_locale": "Lite", "case_id": 1},
            "amount": 1,
        },
        {
            "chance": 3,
            "type": "case",
            "data": {"case_locale": "MC - Пластинки", "case_id": 5},
            "amount": 1,
        },
        {"chance": 94, "type": "nothing"},
    ],
}

YASNO_IRON_ORE_AWARD = {
    "balance_bonus": {"min": 1, "max": 2},
    "items": [
        {
            "chance": 1,
            "type": "case",
            "data": {"case_locale": "MC - Еда", "case_id": 4},
            "amount": 1,
        },
        {"chance": 99, "type": "nothing"},
    ],
}

YASNO_GOLD_ORE_AWARD = {
    "balance_bonus": {"min": 1, "max": 3},
    "items": [
        {
            "chance": 1,
            "type": "case",
            "data": {"case_locale": "MC - Тотем или ничего", "case_id": 6},
            "amount": 1,
        },
        {"chance": 399, "type": "nothing"},
    ],
}

YASNO_REDSTONE_ORE_AWARD = {
    "balance_bonus": {"min": 1, "max": 2},
    "items": [
        {
            "chance": 3,
            "type": "case",
            "data": {"case_locale": "MC - Редстоун", "case_id": 7},
            "amount": 1,
        },
        {"chance": 97, "type": "nothing"},
    ],
}

YASNO_BLOCK_ORE_AWARDS = {
    "minecraft:diamond_ore": YASNO_DIAMOND_ORE_AWARD,
    "minecraft:deepslate_diamond_ore": YASNO_DIAMOND_ORE_AWARD,
    "minecraft:emerald_ore": YASNO_EMERALD_ORE_AWARD,
    "minecraft:deepslate_emerald_ore": YASNO_EMERALD_ORE_AWARD,
    "minecraft:iron_ore": YASNO_IRON_ORE_AWARD,
    "minecraft:deepslate_iron_ore": YASNO_IRON_ORE_AWARD,
    "minecraft:gold_ore": YASNO_GOLD_ORE_AWARD,
    "minecraft:deepslate_gold_ore": YASNO_GOLD_ORE_AWARD,
    "minecraft:redstone_ore": YASNO_REDSTONE_ORE_AWARD,
    "minecraft:deepslate_redstone_ore": YASNO_REDSTONE_ORE_AWARD,
    "minecraft:ancient_debris": {
        "balance_bonus": {"min": 10, "max": 20},
        "items": [
            {
                "chance": 75,
                "type": "case",
                "data": {"case_locale": "MC - Случайный кейс", "case_id": 50},
                "amount": 1,
            },
            {"chance": 25, "type": "nothing"},
        ],
    },
    "minecraft:nether_quartz_ore": {
        "balance_bonus": {"min": 1, "max": 2},
        "items": [
            {
                "chance": 1,
                "type": "case",
                "data": {"case_locale": "MC - Случайный кейс", "case_id": 50},
                "amount": 1,
            },
            {"chance": 99, "type": "nothing"},
        ],
    },
    "minecraft:nether_gold_ore": {
        "balance_bonus": {"min": 1, "max": 2},
        "items": [
            {
                "chance": 15,
                "type": "case",
                "data": {"case_locale": "MC - Случайный кейс", "case_id": 50},
                "amount": 1,
            },
            {"chance": 985, "type": "nothing"},
        ],
    },
}

MC_ITEMS_TRANSLATIONS = {}
if os.path.isfile(os.getcwd() + "/data/mc_items.json"):
    with open(os.getcwd() + "/data/mc_items.json", encoding="utf-8") as f:
        MC_ITEMS_TRANSLATIONS = json.load(f)


def translate_mc_item(item_name, language="ru"):
    return MC_ITEMS_TRANSLATIONS.get(item_name, {}).get(language) or item_name


def get_rnd(minimum, maximum):
    random_byte = secrets.randbits(32)
    return minimum + (random_byte % (maximum - minimum + 1))


def yasno_get_block_award(block_id: str):
    items = YASNO_BLOCK_ORE_AWARDS.get(block_id, {}).get("items", [])
    if not items:
        return None

    items = [(i, item, item.get("chance", 0)) for i, item in enumerate(items, start=0)]

    total_chance = sum(chance for i, item, chance in items)

    random_byte = secrets.randbits(32)
    random_number = random_byte % total_chance
    for i, item, chance in items:
        if random_number < chance:
            item_data = items[i]

            return item
        else:
            random_number -= chance


@app.post("/v1/mc_yasno/inc_bal")
async def mc_yasno_inc_bal(data: MCYasnoIncBal, res: Response):
    await db_client[YASNO_DB][YASNO_COLL].update_one(
        {"_id": data.user_id}, {"$inc": {f"{YASNO_GUILD_ID}.balance": data.amount}}
    )

    return {"message": "ok"}


@app.post("/v1/mc_yasno/process_ore_award")
async def mc_yasno_process_ore_award(data: MCYasnoProcessOreAward):
    bid = data.block
    response = {}

    award_data = YASNO_BLOCK_ORE_AWARDS.get(bid, {})
    drop = yasno_get_block_award(bid) or {}
    amount = drop.get("amount", 0)
    if type(amount) == dict:
        amount = get_rnd(drop["amount"].get("min", 0), drop["amount"].get("max", 0))

    balance_bonus = award_data.get("balance_bonus", 0)
    if type(balance_bonus) == dict:
        balance_bonus = get_rnd(
            award_data["balance_bonus"].get("min", 0),
            award_data["balance_bonus"].get("max", 0),
        )

    response["balance"] = balance_bonus
    response["amount"] = amount

    inc_fields = {"balance": response["balance"]}

    response["text"] = f"§lВы получили §e§l§n{response['balance']}§r §lзвёзд(ы)"

    if drop.get("type") == "case":
        response["case"] = drop.get("data", {}).get("case_locale", "?")

        inc_fields[
            f"inventory.cases.{drop.get('data', {}).get('case_id', 0)}"
        ] = response["amount"]

        response[
            "text_chat"
        ] = f"Вы получили §c§l§n{amount}x кейс \"{drop.get('data', {}).get('case_locale', '?')}\"!"

    # elif drop.get("type") == "nothing":
    #     ...

    response["type"] = drop.get("type", "?")

    upd_fields = {"$inc": {f"{YASNO_GUILD_ID}.{k}": v for k, v in inc_fields.items()}}

    if response.get("balance"):
        await db_client[YASNO_DB]["transactions"].update_one(
            {"_id": data.user_id},
            {
                "$push": {
                    "history": {
                        "$each": [
                            {
                                "type": 23,
                                "data": {"block_id": bid},
                                "diff": response["balance"],
                                "ts": int(get_utc_timestamp()),
                            }
                        ],
                        "$slice": -500_000,
                    }
                }
            },
        )
        """
        UpdateOne(
                {"_id": int(obj[0])},
                {"$push": {"history": {"$each": [obj[1]], "$slice": -500_000}}},
                upsert=True,
            )
        """

    await db_client[YASNO_DB][YASNO_COLL].update_one(
        {"_id": data.user_id}, upd_fields, True
    )

    return response


@app.post("/v1/mc_yasno/update_sync")
async def mc_yasno_update_sync(data: MCYasnoUpdateSync):
    user_id = int(data.user_id)
    state = data.state

    await db_client[YASNO_DB][YASNO_COLL].update_one(
        {"_id": user_id},
        {
            "$set": {
                f"{YASNO_GUILD_ID}.other.mc_yasno": {
                    "nick": data.mc_nick,
                    "state": state,
                }
            }
        },
    )


@app.post("/v1/mc_yasno/get_inv")
async def mc_yasno_get_inv(data: MCYasnoGetInv):
    user_id = data.user_id

    inventory_db = (
        walk_dict(
            await db_client[YASNO_DB][YASNO_COLL].find_one(
                {"_id": user_id}, {f"{YASNO_GUILD_ID}.other.mc_yasno.inv": 1}
            ),
            f"{YASNO_GUILD_ID}.other.mc_yasno.inv",
        )
        or {}
    )

    inv_len = len(inventory_db)

    page = data.page

    inventory = [
        (translate_mc_item(i, "ru"), n)
        for i, n in list(inventory_db.items())[page * 10 : page * 10 + 10]
        if n > 0
    ]

    return {
        "inventory": inventory,
        "total_pages": ceil(inv_len / 10),
        "total_items": inv_len,
    }


@app.post("/v1/mc_yasno/get_inv_item")
async def mc_yasno_get_inv_item(data: MCYasnoGetInvItem):
    user_id = data.user_id
    item_id = data.item_id
    amount = data.item_amount

    # The inventory is not that big, so we get it all.
    inventory_db = (
        walk_dict(
            await db_client[YASNO_DB][YASNO_COLL].find_one(
                {"_id": user_id}, {f"{YASNO_GUILD_ID}.other.mc_yasno.inv": 1}
            ),
            f"{YASNO_GUILD_ID}.other.mc_yasno.inv",
        )
        or {}
    )

    inventory = [(i, n) for i, n in list(inventory_db.items()) if n > 0]
    try:
        item = inventory[item_id]
    except:
        return {"success": False, "text": "Неверный номер предмета."}

    amount_available = item[1]
    if amount_available - amount < 0:
        return {
            "success": False,
            "text": f"У Вас есть только {amount_available} этого предмета.",
        }

    await db_client[YASNO_DB][YASNO_COLL].update_one(
        {"_id": user_id},
        {"$inc": {f"{YASNO_GUILD_ID}.other.mc_yasno.inv.{item[0]}": -amount}},
    )
    return {
        "success": True,
        "text": f"Вы успешно получили {translate_mc_item(item[0])} §e[x{amount}]§r!",
        "item_id": item[0],
    }


@app.post("/v1/mc_yasno/check_ore_award")
async def mc_yasno_check_ore_award(data: MCYasnoCheckOreAward, res: Response):
    """
    The block is already broken.
    Checks if user has placed award blocks themselves.
    """

    successful = False

    if not await db_client[YASNO_BLOCK_DB][YASNO_BLOCK_COLL].find_one(
        {"_id": data.block_id}, {"_id": 1}
    ):
        successful = True
    else:
        # delete old block data, bcs the block is already broken.
        # try:
        await db_client[YASNO_BLOCK_DB][YASNO_BLOCK_COLL].delete_one(
            {"_id": data.block_id}
        )
        # except:
        # pass

    return {"successful": successful}


@app.post("/v1/mc_yasno/block_ore_award")
async def mc_yasno_block_ore_award(data: MCYasnoBlockOreAward):
    try:
        await db_client[YASNO_BLOCK_DB][YASNO_BLOCK_COLL].insert_one(
            {"_id": data.block_id}
        )
    except:
        pass
