from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import sys

# Ensure the game module can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from game.systems import World, MovementSystem, CombatSystem, PickupSystem, TurnSystem
from game.session import SessionManager

router = APIRouter()

# Load the session manager using the entities file
entities_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'game', 'entities.json')
session_manager = SessionManager(entities_file_path)

# Pydantic models for API Requests
class PreviewMoveRequest(BaseModel):
    chosen_index: int
    target_tile_id: int

class MoveChoiceRequest(BaseModel):
    path: List[int]

class SubmitDiceRequest(BaseModel):
    dice_selection: List[Dict[str, Any]]

class PickupRequest(BaseModel):
    target_entity_id: int

def get_game(game_id: str):
    game_world = session_manager.get_session(game_id)
    if not game_world:
         raise HTTPException(status_code=404, detail="Game session not found")
    return game_world

class CreateGameRequest(BaseModel):
    player_count: int = 4

@router.post("/game")
def create_game(request: CreateGameRequest):
    """Create a new game session."""
    game_id = session_manager.create_session(request.player_count)
    return {"status": "success", "game_id": game_id}

@router.get("/games")
def list_games():
    """List all active game sessions."""
    return {"status": "success", "games": list(session_manager.sessions.keys())}


@router.get("/game/{game_id}/state")
def get_world_state(game_id: str = Path(...)):
    """Retrieve the current state of all entities in the game."""
    game_world = get_game(game_id)
    return {"entities": game_world.entities}

@router.get("/game/{game_id}/entity/{entity_id}")
def get_entity_state(game_id: str = Path(...), entity_id: int = Path(..., description="The ID of the entity")):
    """Retrieve the current state of a specific entity."""
    game_world = get_game(game_id)
    if entity_id not in game_world.entities:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    return {"entity_id": entity_id, "components": game_world.entities[entity_id]}

@router.get("/template/{type_name}")
def get_template(type_name: str = Path(...)):
    """Retrieve template details by its type string (e.g. WOLF_PELT)."""
    for template in session_manager.registry.templates.values():
        for comp_name, comp_data in template.items():
            if isinstance(comp_data, dict) and comp_data.get("type") == type_name:
                return {"status": "success", "template": template}
    raise HTTPException(status_code=404, detail=f"Template with type {type_name} not found")

@router.post("/game/{game_id}/player/{player_id}/roll_movement")
def roll_movement(game_id: str = Path(...), player_id: int = Path(...)):
    """Roll 2d6 for movement phase."""
    game_world = get_game(game_id)
    rolls = MovementSystem.roll_movement(game_world, player_id)
    if not rolls:
        raise HTTPException(status_code=400, detail="Cannot roll movement for this player.")
    return {"status": "success", "rolls": rolls}

@router.post("/game/{game_id}/player/{player_id}/preview_move")
def preview_move(request: PreviewMoveRequest, game_id: str = Path(...), player_id: int = Path(...)):
    """Calculate the A* path up to the dice roll limit towards the target."""
    game_world = get_game(game_id)
    result = MovementSystem.preview_path(game_world, player_id, request.chosen_index, request.target_tile_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return {"status": "success", "preview": result}

@router.post("/game/{game_id}/player/{player_id}/move_choice")
def move_choice(request: MoveChoiceRequest, game_id: str = Path(...), player_id: int = Path(...)):
    """Execute the confirmed movement path."""
    game_world = get_game(game_id)
    success = MovementSystem.move_player(game_world, player_id, request.path)
    if not success:
         raise HTTPException(status_code=400, detail="Invalid movement path. Did you roll first?")
         
    return {
        "status": "success", 
        "entity_state": game_world.entities.get(player_id)
    }

@router.post("/game/{game_id}/player/{player_id}/combat/submit_dice")
def submit_dice(request: SubmitDiceRequest, game_id: str = Path(...), player_id: int = Path(...)):
    """Submit a selection of dice for the combat FIFO pool."""
    game_world = get_game(game_id)
    if not CombatSystem.submit_dice(game_world, player_id, request.dice_selection):
        raise HTTPException(status_code=400, detail="Failed to submit dice pool. Entity may not exist or cannot fight.")
    return {"status": "success"}

@router.post("/game/{game_id}/player/{player_id}/combat/resolve_turn")
def resolve_combat_turn(game_id: str = Path(...), player_id: int = Path(...)):
    """Resolve the front dice in the FIFO pool for this turn of combat."""
    game_world = get_game(game_id)
    combat_state = game_world.get_component(player_id, "CombatStateComponent")
    if not combat_state:
        raise HTTPException(status_code=400, detail="Player is not in combat.")
        
    target_id = combat_state["targetEntityId"]
    result = CombatSystem.resolve_combat_turn(game_world, player_id, target_id)
    
    return {
        "status": "success",
        "combat_log": result
    }

@router.post("/game/{game_id}/player/{player_id}/pickup")
def player_pickup(request: PickupRequest, game_id: str = Path(...), player_id: int = Path(...)):
    """Attempt to pick up an item."""
    game_world = get_game(game_id)
    if player_id not in game_world.entities:
        raise HTTPException(status_code=404, detail="Player not found")
        
    success = PickupSystem.pickup_item(game_world, player_id, request.target_entity_id)
    
    if not success:
         raise HTTPException(status_code=400, detail="Failed to pick up item.")
         
    return {
        "status": "success",
        "message": f"Player {player_id} picked up item {request.target_entity_id}.",
        "entity_state": game_world.entities.get(player_id)
    }

@router.post("/game/{game_id}/end_turn")
def execute_end_turn(game_id: str = Path(...)):
    """Advances global game turn and checks phase transitions."""
    game_world = get_game(game_id)
    
    # Check if a boss was defeated during this round to trigger PVP
    TurnSystem.check_boss_defeat(game_world)
    
    msg = TurnSystem.advance_turn(game_world)
    
    return {
        "status": "success",
        "message": msg,
        "game_state": game_world.entities.get("GameState")
    }
