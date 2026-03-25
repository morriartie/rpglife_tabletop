import pytest
from game.systems import World, CombatSystem, PhaseSystem, MovementSystem
import random


class TestQuickResolveCombat:
    """Tests for CombatSystem.quick_resolve_combat()"""

    def _setup_combat(self):
        world = World()
        player = world.create_entity({
            "NameComponent": {"displayName": "Hero"},
            "PlayerComponent": {"clientId": "test"},
            "StatsComponent": {"maxHp": 100, "currentHp": 100, "baseAttack": 10, "baseDefense": 5},
            "PositionComponent": {"currentTileId": 99},
            "InventoryComponent": {"heldEntityIds": [], "maxWeightCapacity": 50, "currentWeight": 0},
        })

        tile = world.create_entity({
            "TileComponent": {"type": "FOREST"},
            "EncounterComponent": {"type": "BATTLE", "mobEntityId": None, "isDefeated": False},
        })
        # Override tile ID to match player position
        world.entities[player]["PositionComponent"]["currentTileId"] = tile

        mob = world.create_entity({
            "NameComponent": {"displayName": "Test Wolf"},
            "MobComponent": {"type": "WOLF"},
            "StatsComponent": {"maxHp": 30, "currentHp": 30, "baseAttack": 5, "baseDefense": 2},
            "PositionComponent": {"currentTileId": tile},
            "LootDropComponent": {"lootTable": [{"itemType": "LEATHER_BOOTS", "dropChanceProbability": 1.0}]},
        })
        world.entities[tile]["EncounterComponent"]["mobEntityId"] = mob

        return world, player, mob, tile

    def test_quick_resolve_win(self):
        """Player wins combat (forced via seed)."""
        world, player, mob, tile = self._setup_combat()
        random.seed(1)  # Ensure random() < 0.9

        result = CombatSystem.quick_resolve_combat(world, player, mob)

        assert result["outcome"] == "win"
        assert "Test Wolf" in result["message"]
        # Mob should be destroyed
        assert mob not in world.entities
        # Encounter should be marked defeated
        assert world.entities[tile]["EncounterComponent"]["isDefeated"] is True
        # Player should NOT have SkipNextTurn
        assert "SkipNextTurn" not in world.entities[player]

    def test_quick_resolve_loss(self):
        """Player loses combat (force loss by making random > 0.9)."""
        world, player, mob, tile = self._setup_combat()

        # Monkey-patch random to force a loss
        original_random = random.random
        random.random = lambda: 0.95
        try:
            result = CombatSystem.quick_resolve_combat(world, player, mob)
        finally:
            random.random = original_random

        assert result["outcome"] == "loss"
        assert "defeated by" in result["message"]
        # Mob should still exist
        assert mob in world.entities
        # Player should have SkipNextTurn
        assert world.entities[player].get("SkipNextTurn") is True


class TestPhaseSystem:
    """Tests for PhaseSystem.get_available_actions()"""

    def _setup_game(self):
        world = World()
        player = world.create_entity({
            "NameComponent": {"displayName": "Hero"},
            "PlayerComponent": {"clientId": "test"},
            "StatsComponent": {"maxHp": 100, "currentHp": 100, "baseAttack": 10, "baseDefense": 5},
            "PositionComponent": {"currentTileId": None},
            "InventoryComponent": {"heldEntityIds": [], "maxWeightCapacity": 50, "currentWeight": 0},
        })

        tile = world.create_entity({
            "TileComponent": {"type": "FOREST"},
            "HexPositionComponent": {"q": 0, "r": 0, "x": 0, "y": 0},
        })
        world.entities[player]["PositionComponent"]["currentTileId"] = tile

        # Set up GameState
        world.entities["GameState"]["turn_order"] = [player]
        world.entities["GameState"]["active_player_id"] = player
        world.entities["GameState"]["turn_phase"] = "Movement"

        return world, player, tile

    def test_movement_phase_shows_roll(self):
        world, player, tile = self._setup_game()

        result = PhaseSystem.get_available_actions(world, player)

        assert result["phase"] == "Movement"
        assert result["is_active"] is True
        actions = [a["action"] for a in result["actions"]]
        assert "roll_movement" in actions

    def test_movement_phase_after_roll_shows_dice_choices(self):
        world, player, tile = self._setup_game()
        world.entities[player]["PendingMovementComponent"] = {"rolls": [3, 5]}

        result = PhaseSystem.get_available_actions(world, player)

        actions = [a["action"] for a in result["actions"]]
        assert "choose_die_0" in actions
        assert "choose_die_1" in actions
        assert result["context"]["rolls"] == [3, 5]

    def test_skip_turn_when_penalized(self):
        world, player, tile = self._setup_game()
        world.entities[player]["SkipNextTurn"] = True

        result = PhaseSystem.get_available_actions(world, player)

        actions = [a["action"] for a in result["actions"]]
        assert "skip_turn" in actions
        assert "roll_movement" not in actions

    def test_tile_resolution_empty_tile_advances_to_end(self):
        world, player, tile = self._setup_game()
        world.entities["GameState"]["turn_phase"] = "Tile Resolution"

        result = PhaseSystem.get_available_actions(world, player)

        # Empty tile should auto-advance to End Turn
        assert result["phase"] == "End Turn"
        actions = [a["action"] for a in result["actions"]]
        assert "end_turn" in actions

    def test_tile_resolution_with_encounter_advances_to_combat(self):
        world, player, tile = self._setup_game()
        world.entities["GameState"]["turn_phase"] = "Tile Resolution"

        mob = world.create_entity({
            "NameComponent": {"displayName": "Big Wolf"},
            "MobComponent": {"type": "WOLF"},
            "StatsComponent": {"maxHp": 30, "currentHp": 30, "baseAttack": 5, "baseDefense": 2},
            "PositionComponent": {"currentTileId": tile},
        })
        world.entities[tile]["EncounterComponent"] = {
            "type": "BATTLE", "mobEntityId": mob, "isDefeated": False
        }

        result = PhaseSystem.get_available_actions(world, player)

        assert result["phase"] == "Combat"
        actions = [a["action"] for a in result["actions"]]
        assert "quick_resolve" in actions

    def test_not_active_player_gets_no_actions(self):
        world, player, tile = self._setup_game()
        other_player = world.create_entity({
            "PlayerComponent": {"clientId": "other"},
        })

        result = PhaseSystem.get_available_actions(world, other_player)

        assert result["is_active"] is False
        assert result["actions"] == []
