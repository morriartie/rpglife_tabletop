import json
import random

class TemplateRegistry:
    """Loads and stores entity templates from JSON to be instantiated into Worlds."""
    def __init__(self, entities_file):
        with open(entities_file, 'r') as f:
            raw_data = json.load(f)
            # Keys in JSON are strings, convert them to integers for template IDs
            self.templates = {int(k): v for k, v in raw_data.items()}
            
    def get_template(self, template_id: int):
        return self.templates.get(template_id)
        
    def get_templates_by_component(self, component_name: str) -> dict:
        """Returns a dict of {template_id: template_data} for all templates with the given component."""
        return {tid: data for tid, data in self.templates.items() if component_name in data}


class World:
    """A lightweight ECS Registry to manage entities and their components."""
    def __init__(self):
        self.entities = {}
        self.next_entity_id = 1
        
        # Ensure a singleton GameState entity exists
        self.entities["GameState"] = {
            "global_turn": 1,
            "phase": "EXPLORATION",
            "turn_limit": 20,
            "turn_order": [],
            "active_player_id": None,
            "turn_phase": "Movement"
        }

    def create_entity(self, components):
        entity_id = self.next_entity_id
        self.entities[entity_id] = components
        self.next_entity_id += 1
        return entity_id

    def destroy_entity(self, entity_id):
        if entity_id in self.entities:
            del self.entities[entity_id]

    def get_component(self, entity_id, component_name):
        return self.entities.get(entity_id, {}).get(component_name)

    def has_components(self, entity_id, *component_names):
        entity = self.entities.get(entity_id, {})
        return all(comp in entity for comp in component_names)


class MovementSystem:
    @staticmethod
    def roll_movement(world, player_entity_id):
        if not world.has_components(player_entity_id, "PositionComponent", "PlayerComponent"):
            return None
            
        if world.entities[player_entity_id].get("SkipNextTurn"):
            del world.entities[player_entity_id]["SkipNextTurn"]
            return {"skipped": True, "message": "You lose your turn due to a previous defeat."}
            
        roll1 = random.randint(1, 6)
        roll2 = random.randint(1, 6)
        
        world.entities[player_entity_id]["PendingMovementComponent"] = {
            "rolls": [roll1, roll2]
        }
        return [roll1, roll2]

    @staticmethod
    def _hex_distance(pos1, pos2):
        return (abs(pos1["q"] - pos2["q"]) + 
                abs(pos1["q"] + pos1["r"] - pos2["q"] - pos2["r"]) + 
                abs(pos1["r"] - pos2["r"])) // 2

    @staticmethod
    def preview_path(world, player_entity_id, chosen_index, target_tile_id):
        """Calculates an A* path and returns valid tiles up to the dice roll limit."""
        if not world.has_components(player_entity_id, "PositionComponent", "PendingMovementComponent"):
            return {"error": "Player cannot move right now."}
        
        if target_tile_id not in world.entities or not world.has_components(target_tile_id, "HexPositionComponent"):
            return {"error": "Invalid target tile."}

        pending = world.get_component(player_entity_id, "PendingMovementComponent")
        if chosen_index not in (0, 1):
            return {"error": "Invalid dice index."}
            
        dice_roll = pending["rolls"][chosen_index]
        pos = world.get_component(player_entity_id, "PositionComponent")
        start_tile_id = pos["currentTileId"]
        
        if start_tile_id == target_tile_id:
            return {"error": "Already at target tile."}

        # A* Pathfinding setup
        start_pos = world.get_component(start_tile_id, "HexPositionComponent")
        target_pos = world.get_component(target_tile_id, "HexPositionComponent")
        
        # Build hex lookup for neighbors
        hex_grid = {}
        for eid, comps in world.entities.items():
            if "HexPositionComponent" in comps and "TileComponent" in comps:
                p = comps["HexPositionComponent"]
                hex_grid[(p["q"], p["r"])] = eid

        open_set = {start_tile_id}
        came_from = {}
        g_score = {start_tile_id: 0}
        f_score = {start_tile_id: MovementSystem._hex_distance(start_pos, target_pos)}
        
        # Axial direction vectors
        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]

        while open_set:
            # Get node in open_set with lowest f_score
            current = min(open_set, key=lambda eid: f_score.get(eid, float('inf')))
            
            if current == target_tile_id:
                break
                
            open_set.remove(current)
            curr_pos = world.get_component(current, "HexPositionComponent")
            
            for dq, dr in directions:
                nq, nr = curr_pos["q"] + dq, curr_pos["r"] + dr
                neighbor_id = hex_grid.get((nq, nr))
                
                if neighbor_id is None:
                    continue # Not a valid tile
                    
                # Standard distance of 1 between adjacent hexes
                tentative_g_score = g_score[current] + 1
                
                if tentative_g_score < g_score.get(neighbor_id, float('inf')):
                    came_from[neighbor_id] = current
                    g_score[neighbor_id] = tentative_g_score
                    n_pos = world.get_component(neighbor_id, "HexPositionComponent")
                    f_score[neighbor_id] = tentative_g_score + MovementSystem._hex_distance(n_pos, target_pos)
                    if neighbor_id not in open_set:
                        open_set.add(neighbor_id)
                        
        if target_tile_id not in came_from:
            return {"error": "No path found to target."}
            
        # Reconstruct path
        path = []
        curr = target_tile_id
        while curr in came_from:
            path.append(curr)
            curr = came_from[curr]
        path.reverse()
        
        # Truncate by dice roll
        final_path = path[:dice_roll]
        return {"path": final_path, "dice_roll": dice_roll}

    @staticmethod
    def move_player(world, player_entity_id, path):
        """Applies an approved movement path, stopping at encounters."""
        if not world.has_components(player_entity_id, "PositionComponent", "PendingMovementComponent"):
            return False

        if not path:
             return False
             
        # Movement consumes the pending roll
        del world.entities[player_entity_id]["PendingMovementComponent"]

        pos = world.get_component(player_entity_id, "PositionComponent")
        
        final_tile = pos["currentTileId"]
        
        # Step through path
        for tile_id in path:
            final_tile = tile_id
            pos["currentTileId"] = final_tile
            
            # Stop early if there's an active encounter
            encounter = world.get_component(tile_id, "EncounterComponent")
            if encounter and "mobEntityId" in encounter and not encounter.get("isDefeated", False):
                break
                
        print(f"Player {player_entity_id} moved to Tile {final_tile}")
        
        # Trigger encounter on the final tile
        EncounterSystem.check_encounter(world, player_entity_id, final_tile)
        return True


class EncounterSystem:
    @staticmethod
    def check_encounter(world, player_entity_id, tile_entity_id):
        """Checks if landing on a tile triggers a battle."""
        encounter = world.get_component(tile_entity_id, "EncounterComponent")
        if not encounter:
            return
            
        if "mobEntityId" in encounter and not encounter.get("isDefeated", False):
            mob_id = encounter["mobEntityId"]
            print(f"Encounter triggered! Player {player_entity_id} vs Mob {mob_id}")
            CombatSystem.start_combat(world, player_entity_id, mob_id)
        else:
            # Chance for a random ambush when stopping on a tile
            ambush_chance = encounter.get("ambushChance", 0.0)
            if random.random() < ambush_chance:
                mob_types = ["WOLF", "BAT", "GOBLIN", "SOLDIER", "THIEF", "SKELETON"]
                mob_type = random.choice(mob_types)
                mob_id = world.create_entity({
                    "NameComponent": {"displayName": f"Ambushing {mob_type}"},
                    "MobComponent": {"type": mob_type},
                    "StatsComponent": {"maxHp": 10, "currentHp": 10, "baseAttack": 3, "baseDefense": 1},
                    "LootDropComponent": {"lootTable": [{"itemType": "COPPER_RING", "dropChanceProbability": 0.5}]}
                })
                # Update the encounter component
                encounter["mobEntityId"] = mob_id
                encounter["isDefeated"] = False
                print(f"Ambush triggered! Player {player_entity_id} vs Mob {mob_id}")
                CombatSystem.start_combat(world, player_entity_id, mob_id)


class PickupSystem:
    @staticmethod
    def pickup_item(world, player_entity_id, target_entity_id):
        """Attempts to move an entity from the world into a player's inventory."""
        if not world.has_components(player_entity_id, "InventoryComponent"):
            return False
            
        # The target MUST be Pickable. (This rejects the Giant Book tile, but accepts the Pocket Goblin)
        if not world.has_components(target_entity_id, "PickableComponent"):
            print("You cannot pick that up.")
            return False

        inventory = world.get_component(player_entity_id, "InventoryComponent")
        target_weight = world.get_component(target_entity_id, "PickableComponent")["weight"]

        if inventory["currentWeight"] + target_weight > inventory["maxWeightCapacity"]:
            print("Inventory is too heavy!")
            return False

        # Remove position (takes it off the board)
        if "PositionComponent" in world.entities[target_entity_id]:
            del world.entities[target_entity_id]["PositionComponent"]

        # Add to inventory
        inventory["heldEntityIds"].append(target_entity_id)
        inventory["currentWeight"] += target_weight
        
        target_name = world.get_component(target_entity_id, "NameComponent").get("displayName", "Item")
        print(f"Picked up {target_name}.")
        return True


class CombatSystem:
    @staticmethod
    def start_combat(world, entity1_id, entity2_id):
        world.entities[entity1_id]["CombatStateComponent"] = {"targetEntityId": entity2_id}
        world.entities[entity2_id]["CombatStateComponent"] = {"targetEntityId": entity1_id}
        world.entities[entity1_id]["DicePoolComponent"] = {"diceQueue": []}
        
        # Mobs auto-generate a generic pool for simplicity right now
        world.entities[entity2_id]["DicePoolComponent"] = {
            "diceQueue": [{"sides": 6, "keywords": []}, {"sides": 4, "keywords": []}]
        }

    @staticmethod
    def submit_dice(world, entity_id, dice_selection):
        if not world.has_components(entity_id, "DicePoolComponent"):
            return False
        world.entities[entity_id]["DicePoolComponent"]["diceQueue"] = dice_selection
        return True

    @staticmethod
    def resolve_combat_turn(world, combatant_id1, combatant_id2):
        if not world.has_components(combatant_id1, "DicePoolComponent") or not world.has_components(combatant_id2, "DicePoolComponent"):
            return "Missing components"
            
        pool1 = world.entities[combatant_id1]["DicePoolComponent"]["diceQueue"]
        pool2 = world.entities[combatant_id2]["DicePoolComponent"]["diceQueue"]
        
        # 1. Initiative Phase
        init1 = sum(1 for d in pool1 if "Initiative" in d.get("keywords", []))
        init2 = sum(1 for d in pool2 if "Initiative" in d.get("keywords", []))
        
        first, second = combatant_id1, combatant_id2
        if init1 < init2:
            first, second = combatant_id2, combatant_id1
        elif init1 == init2:
            if len(pool1) > len(pool2):
                first, second = combatant_id2, combatant_id1
            elif len(pool1) == len(pool2) and random.choice([True, False]):
                first, second = combatant_id2, combatant_id1

        # 2. Strike Phase
        res1 = CombatSystem._execute_strike(world, first, second)
        res2 = None
        
        if world.get_component(second, "StatsComponent")["currentHp"] > 0:
            res2 = CombatSystem._execute_strike(world, second, first)
            
        return {"first_striker": first, "second_striker": second, "log": [res1, res2]}

    @staticmethod
    def _execute_strike(world, attacker_id, defender_id):
        pool = world.entities[attacker_id]["DicePoolComponent"]["diceQueue"]
        if not pool:
            return f"Entity {attacker_id} has no dice to roll."
            
        # Get front die
        front_die = pool.pop(0)
        roll_val = random.randint(1, front_die.get("sides", 6))
        
        attacker_stats = world.get_component(attacker_id, "StatsComponent")
        defender_stats = world.get_component(defender_id, "StatsComponent")
        
        damage = max(1, (attacker_stats.get("baseAttack", 0) + roll_val) - defender_stats.get("baseDefense", 0))
        defender_stats["currentHp"] -= damage
        
        msg = f"Entity {attacker_id} rolled {roll_val} (D{front_die.get('sides',6)}). Dealt {damage} damage to Entity {defender_id}. Defender HP: {defender_stats['currentHp']}"
        print(msg)
        
        # Handle single-use and cycle
        if "SingleUse" not in front_die.get("keywords", []):
            pool.append(front_die)
            
        # Check death
        if defender_stats["currentHp"] <= 0:
            msg += f" | Entity {defender_id} defeated!"
            CombatSystem._handle_defeat(world, defender_id, attacker_id)
            
        return msg

    @staticmethod
    def _handle_defeat(world, defeated_id, winner_id):
        # Clean up tags
        if "CombatStateComponent" in world.entities[winner_id]:
            del world.entities[winner_id]["CombatStateComponent"]
        if "DicePoolComponent" in world.entities[winner_id]:
            del world.entities[winner_id]["DicePoolComponent"]
            
        # Player specific punishment
        if world.has_components(defeated_id, "PlayerComponent"):
            world.entities[defeated_id]["SkipNextTurn"] = True
            
        # Mob defeat rewards
        if world.has_components(defeated_id, "MobComponent"):
            pos = world.get_component(defeated_id, "PositionComponent")
            if pos:
                tile_encounter = world.get_component(pos["currentTileId"], "EncounterComponent")
                if tile_encounter:
                     tile_encounter["isDefeated"] = True
            LootSystem.generate_loot(world, defeated_id, winner_id)
            world.destroy_entity(defeated_id)


class LootSystem:
    @staticmethod
    def generate_loot(world, mob_id, killer_id):
        """Rolls for loot when a mob dies and drops it on the ground."""
        loot_drop = world.get_component(mob_id, "LootDropComponent")
        mob_pos = world.get_component(mob_id, "PositionComponent")
        
        if not loot_drop or not mob_pos:
            return

        for loot_entry in loot_drop["lootTable"]:
            if random.random() <= loot_entry["dropChanceProbability"]:
                # Create a new item entity on the same tile
                new_item = {
                    "SessionComponent": world.get_component(mob_id, "SessionComponent").copy() if "SessionComponent" in world.entities[mob_id] else {},
                    "NameComponent": {"displayName": f"Dropped {loot_entry['itemType']}"},
                    "ItemComponent": {"type": loot_entry["itemType"], "attackBonus": 0, "defenseBonus": 0},
                    "PickableComponent": {"weight": 2}, # Default weight
                    "PositionComponent": {"currentTileId": mob_pos["currentTileId"]}
                }
                new_item_id = world.create_entity(new_item)
                print(f"Loot dropped: {loot_entry['itemType']} (Entity ID: {new_item_id})")

class TurnSystem:
    @staticmethod
    def advance_turn(world):
        state = world.entities["GameState"]
        if state["phase"] == "GAME_OVER":
            return "Game is over."
            
        if "turn_order" in state and state["turn_order"] and "active_player_id" in state:
            idx = state["turn_order"].index(state["active_player_id"])
            idx = (idx + 1) % len(state["turn_order"])
            state["active_player_id"] = state["turn_order"][idx]
            state["turn_phase"] = "Movement"
            
            if idx == 0:
                state["global_turn"] += 1
                if state["phase"] == "EXPLORATION" and state["global_turn"] >= state["turn_limit"]:
                    TurnSystem._trigger_final_hour(world, state)
                    return "The Final Hour has begun!"
        else:
            state["global_turn"] += 1
            if state["phase"] == "EXPLORATION" and state["global_turn"] >= state["turn_limit"]:
                TurnSystem._trigger_final_hour(world, state)
                return "The Final Hour has begun!"
            
        return f"Advanced to Turn {state['global_turn']}"

    @staticmethod
    def _trigger_final_hour(world, state):
        state["phase"] = "FINAL_HOUR"
        print("THE FINAL HOUR HAS BEGUN!")
        
        # 1. Spawn Boss
        boss_id = world.create_entity({
            "NameComponent": {"displayName": "The Ancient Dragon"},
            "MobComponent": {"type": "BOSS"},
            "StatsComponent": {"maxHp": 200, "currentHp": 200, "baseAttack": 15, "baseDefense": 5},
            "DicePoolComponent": {"diceQueue": [{"sides": 12, "keywords": []}, {"sides": 12, "keywords": []}]}
        })
        
        # 2. Teleport players
        boss_tile = world.create_entity({
            "NameComponent": {"displayName": "The Final Arena"},
            "TileComponent": {"type": "ARENA"}
        })
        world.entities[boss_id]["PositionComponent"] = {"currentTileId": boss_tile}
        
        players = [eid for eid, comps in world.entities.items() if "PlayerComponent" in comps and comps.get("StatsComponent", {}).get("currentHp", 1) > 0]
        for pid in players:
            world.entities[pid]["PositionComponent"]["currentTileId"] = boss_tile
            world.entities[pid]["CombatStateComponent"] = {"targetEntityId": boss_id}
            
        world.entities[boss_id]["CombatStateComponent"] = {"targetEntityId": -1} # Co-op target

    @staticmethod
    def check_boss_defeat(world):
        state = world.entities.get("GameState")
        if state and state.get("phase") == "FINAL_HOUR":
            bosses = [eid for eid, comps in world.entities.items() if comps.get("MobComponent", {}).get("type") == "BOSS"]
            if not bosses:
                state["phase"] = "PVP_DUEL"
                print("THE BOSS IS DEAD. PVP DUEL BEGINS!")
                # Pair players up for PvP
                players = [eid for eid, comps in world.entities.items() if "PlayerComponent" in comps and comps.get("StatsComponent", {}).get("currentHp", 1) > 0]
                if len(players) > 1:
                    for i in range(0, len(players), 2):
                        if i+1 < len(players):
                            CombatSystem.start_combat(world, players[i], players[i+1])
                else:
                    state["phase"] = "GAME_OVER"
                    print("Only one player left. Game over!")

# Example usage (Uncomment to test if running locally):
# game_world = World('data/entities.json')
# MovementSystem.move_player(game_world, 50, 1) # Rolls a 1, moves from Tile 1 to Tile 2, triggers encounter
# CombatSystem.resolve_attack(game_world, 50) # Player attacks Wolf
