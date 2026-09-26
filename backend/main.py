from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from fastapi import FastAPI
from routers.users import router as users_router

app = FastAPI()

app.include_router(users_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}