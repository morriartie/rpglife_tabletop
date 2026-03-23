import pytest
from fastapi.testclient import TestClient
from api.src.main import app

client = TestClient(app)

def test_movement_flow():
    # 1. Start game
    resp = client.post("/game", json={"player_count": 4})
    assert resp.status_code == 200
    game_id = resp.json()["game_id"]
    
    # Verify player exists
    state = client.get(f"/game/{game_id}/state")
    entities = state.json()["entities"]
    game_state = entities.get("GameState", {})
    player_id = game_state.get("active_player_id")
    if not player_id:
        pytest.fail("No active player found")
        
    player_id_str = str(player_id)
    start_pos = entities[player_id_str]["PositionComponent"]["currentTileId"]
    
    # 2. Roll movement 2d6
    roll_resp = client.post(f"/game/{game_id}/player/{player_id}/roll_movement")
    assert roll_resp.status_code == 200
    rolls = roll_resp.json()["rolls"]
    assert len(rolls) == 2
    
    # 3. Choose die
    move_resp = client.post(f"/game/{game_id}/player/{player_id}/move_choice", json={"path": [start_pos]})
    assert move_resp.status_code == 200
    moved_state = move_resp.json()["entity_state"]
    assert "PendingMovementComponent" not in moved_state

def test_invalid_move_choice_without_roll():
    resp = client.post("/game", json={"player_count": 4})
    game_id = resp.json()["game_id"]
    
    state = client.get(f"/game/{game_id}/state")
    entities = state.json()["entities"]
    game_state = entities.get("GameState", {})
    player_id = game_state.get("active_player_id")
    if not player_id:
        pytest.fail("No active player found")
    
    # Submitting choice without rolling first
    move_resp = client.post(f"/game/{game_id}/player/{player_id}/move_choice", json={"path": [1]})
    assert move_resp.status_code == 400
    assert "Invalid movement path" in move_resp.json()["detail"]
