from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core import router as game_router

app = FastAPI(
    title="Tabletop RPG API",
    description="Backend API for the multiplayer tabletop RPG game.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the heavy lifting from the core module
app.include_router(game_router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Tabletop RPG API is running"}
