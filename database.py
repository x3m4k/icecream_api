import asyncio
from main import config
import motor.motor_asyncio


if config.get("debug", {}).get("is_debug", False):
    debug_cfg = config.get("debug", {})

    db_uri = debug_cfg.get("db_uri")
else:
    main_cfg = config.get("main", {})

    db_uri = main_cfg.get("db_uri")

client = motor.motor_asyncio.AsyncIOMotorClient(db_uri)
client.get_io_loop = asyncio.get_running_loop
