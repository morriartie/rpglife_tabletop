import pytest
from fastapi.testclient import TestClient
from api.src.main import app

client = TestClient(app)

def test_session_isolation():
    """Verify that multiple games can run simultaneously without state crossover."""
    response1 = client.post("/game", json={"player_count": 4})
    assert response1.status_code == 200
    game1_id = response1.json()["game_id"]
    
    response2 = client.post("/game", json={"player_count": 5})
    assert response2.status_code == 200
    game2_id = response2.json()["game_id"]
    
    state1 = client.get(f"/game/{game1_id}/state")
    assert state1.status_code == 200
    
    state2 = client.get(f"/game/{game2_id}/state")
    assert state2.status_code == 200
    
    assert state1.json() != state2.json(), "Sessions should have isolated generated maps."
    
def test_session_not_found():
    response = client.get("/game/invalid-id/state")
    assert response.status_code == 404
