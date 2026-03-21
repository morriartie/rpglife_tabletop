import pytest
from game.systems import World, CombatSystem

def test_combat_fifo_and_initiative(tmp_path):
    d = tmp_path / "entities.json"
    d.write_text("{}")
    
    world = World(str(d))
    
    p1 = world.create_entity({
        "StatsComponent": {"maxHp": 20, "currentHp": 20, "baseAttack": 5, "baseDefense": 2}
    })
    
    p2 = world.create_entity({
        "StatsComponent": {"maxHp": 20, "currentHp": 20, "baseAttack": 5, "baseDefense": 2}
    })
    
    CombatSystem.start_combat(world, p1, p2)
    
    # Give p1 an Initiative die
    pool1 = [
        {"sides": 6, "keywords": ["Initiative"]}
    ]
    pool2 = [
        {"sides": 8, "keywords": []}
    ]
    
    CombatSystem.submit_dice(world, p1, pool1)
    CombatSystem.submit_dice(world, p2, pool2)
    
    res = CombatSystem.resolve_combat_turn(world, p1, p2)
    
    # p1 should strike first because of Initiative keyword
    assert res["first_striker"] == p1
    
    # Die should return to queue since it is not SingleUse
    assert len(world.entities[p1]["DicePoolComponent"]["diceQueue"]) == 1
    assert "Initiative" in world.entities[p1]["DicePoolComponent"]["diceQueue"][0]["keywords"]

def test_combat_single_use(tmp_path):
    d = tmp_path / "entities.json"
    d.write_text("{}")
    
    world = World(str(d))
    
    p1 = world.create_entity({
        "StatsComponent": {"maxHp": 20, "currentHp": 20, "baseAttack": 5, "baseDefense": 2}
    })
    
    p2 = world.create_entity({
        "StatsComponent": {"maxHp": 20, "currentHp": 20, "baseAttack": 5, "baseDefense": 2}
    })
    
    CombatSystem.start_combat(world, p1, p2)
    
    pool1 = [
        {"sides": 6, "keywords": ["SingleUse"]},
        {"sides": 4, "keywords": []}
    ]
    
    CombatSystem.submit_dice(world, p1, pool1)
    
    CombatSystem.resolve_combat_turn(world, p1, p2)
    
    # The SingleUse die should be discarded, the 4-sided die remains
    p1_pool = world.entities[p1]["DicePoolComponent"]["diceQueue"]
    assert len(p1_pool) == 1
    assert p1_pool[0]["sides"] == 4
