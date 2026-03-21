import requests

API_URL = "http://localhost:8001"

print("1. Creating game...")
res = requests.post(f"{API_URL}/game", json={"player_count": 2})
game_id = res.json()["game_id"]
print(f"Game ID: {game_id}")

print("2. Getting state...")
res = requests.get(f"{API_URL}/game/{game_id}/state")
state = res.json()["entities"]

# Find player
player_id = None
for eid, comps in state.items():
    if "PlayerComponent" in comps:
        player_id = eid
        break

print(f"Player ID: {player_id}")

print("3. Testing preview_move...")
# Pick a random tile to move to
target_tile = None
for eid, comps in state.items():
    if "TileComponent" in comps:
        target_tile = eid
        break

print(f"Target tile: {target_tile}")

res = requests.post(f"{API_URL}/game/{game_id}/player/{player_id}/preview_move", json={
    "target_tile_id": int(target_tile),
    "chosen_index": 0
})

if res.status_code == 200:
    path = res.json().get("path", [])
    print(f"Success! Path preview: {path}")
    
    if path:
        print("4. Testing move_choice...")
        res = requests.post(f"{API_URL}/game/{game_id}/player/{player_id}/move_choice", json={
            "path": path
        })
        print(f"Move response: {res.status_code}")
else:
    print(f"Error {res.status_code}: {res.text}")
