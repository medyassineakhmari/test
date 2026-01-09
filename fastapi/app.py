import os
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

MONGO_URI = os.getenv("MONGO_URL", "")
DB_NAME = "cybersecurity_db"
COLLECTION_NAME = "predictions"

@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(MONGO_URI)
    app.mongodb = app.mongodb_client[DB_NAME]
    print("Connected to MongoDB")

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()
    print("Disconnected from MongoDB")

@app.get("/fetch")
async def fetch_data():
    try:
        cursor = app.mongodb[COLLECTION_NAME].find()
        documents = await cursor.to_list(length=100)

        for doc in documents:
            doc["_id"] = str(doc["_id"])

        return {"results": documents}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))