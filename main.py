import os
import json
from fastapi import FastAPI

app = FastAPI()

with open(os.getcwd() + "/config.json") as f:
    config = json.load(f)


@app.get("/")
async def root():
    return {"message": "ok"}


from v1 import routes_v1
import database
import uvicorn

if __name__ == "__main__":
    is_debug = config.get("debug", {}).get("is_debug", False) == True

    server_config = uvicorn.Config(
        "main:app",
        reload=True if is_debug else False,
        host="127.0.0.1",
        port=config.get("port", 8000),
        log_level="info" if is_debug else "warning",
    )

    server = uvicorn.Server(server_config)
    server.run()
