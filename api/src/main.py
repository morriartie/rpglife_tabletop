from fastapi import FastAPI
from .core import router as game_router

app = FastAPI(
    title="Tabletop RPG API",
    description="Backend API for the multiplayer tabletop RPG game.",
    version="1.0.0"
)

# Include the heavy lifting from the core module
app.include_router(game_router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Tabletop RPG API is running"}
