import pytest
from game.systems import World
from game.map_builder import GameSetupSystem

def test_city_count_calculation():
    # CITIES = N + |N * (2/3)|
    # 4 -> 4 + 3 = 7
    assert GameSetupSystem.calculate_city_count(4) == 7
    # 5 -> 5 + 3 = 8
    assert GameSetupSystem.calculate_city_count(5) == 8
    # 6 -> 6 + 4 = 10
    assert GameSetupSystem.calculate_city_count(6) == 10

def test_map_generation(tmp_path):
    d = tmp_path / "entities.json"
    d.write_text("{}")
    
    world = World(str(d))
    city_ids, pool = GameSetupSystem.generate_map(world, 4)
    
    assert len(city_ids) == 7
    assert len(pool) == 7
    
    for cid in city_ids:
        assert "NameComponent" in world.entities[cid]
        assert world.entities[cid]["TileComponent"]["type"] == "CITY"
        assert len(world.entities[cid]["GraphNodeComponent"]["nextTileIds"]) == 1
        assert len(world.entities[cid]["GraphNodeComponent"]["previousTileIds"]) == 1
