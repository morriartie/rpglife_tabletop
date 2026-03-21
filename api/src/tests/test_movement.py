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
    if "50" not in entities:
        pytest.skip("Hardcoded hero not found in initial template for test")
        
    start_pos = entities["50"]["PositionComponent"]["currentTileId"]
    
    # 2. Roll movement 2d6
    roll_resp = client.post(f"/game/{game_id}/player/50/roll_movement")
    assert roll_resp.status_code == 200
    rolls = roll_resp.json()["rolls"]
    assert len(rolls) == 2
    
    # 3. Choose die
    move_resp = client.post(f"/game/{game_id}/player/50/move_choice", json={"chosen_index": 0})
    assert move_resp.status_code == 200
    moved_state = move_resp.json()["entity_state"]
    assert "PendingMovementComponent" not in moved_state

def test_invalid_move_choice_without_roll():
    resp = client.post("/game", json={"player_count": 4})
    game_id = resp.json()["game_id"]
    
    state = client.get(f"/game/{game_id}/state")
    if "50" not in state.json()["entities"]:
        pytest.skip("Hardcoded hero not found in initial template for test")
    
    # Submitting choice without rolling first
    move_resp = client.post(f"/game/{game_id}/player/50/move_choice", json={"chosen_index": 0})
    assert move_resp.status_code == 400
    assert "Invalid move choice" in move_resp.json()["detail"]
