import math
import random

class GameSetupSystem:
    @staticmethod
    def calculate_city_count(player_count: int) -> int:
        return player_count + round(abs(player_count * (2/3)))

    @staticmethod
    def _hex_to_pixel(q, r, size):
        """Converts axial coordinates to pixel coordinates for a flat-topped hex."""
        x = size * (3.0/2.0 * q)
        y = size * (math.sqrt(3.0)/2.0 * q  +  math.sqrt(3.0) * r)
        return x, y

    @staticmethod
    def _hex_distance(q1, r1, q2, r2):
        return (abs(q1 - q2) + abs(q1 + r1 - q2 - r2) + abs(r1 - r2)) // 2

    @staticmethod
    def generate_map(world, registry, player_count: int):
        """Generates a hexagonal game board."""
        city_count = GameSetupSystem.calculate_city_count(player_count)
        
        # Grid parameters
        map_radius = max(5, int(math.sqrt(city_count) * 3)) # Scale map size with cities
        hex_size = 30 # For rendering calculation

        # 1. Generate empty hex grid
        all_hexes = []
        for q in range(-map_radius, map_radius + 1):
            r1 = max(-map_radius, -q - map_radius)
            r2 = min(map_radius, -q + map_radius)
            for r in range(r1, r2 + 1):
                all_hexes.append((q, r))

        # 2. Distribute Cities
        city_hexes = set()
        while len(city_hexes) < city_count:
            # Pick a random hex that isn't already a city
            # Could add a minimum distance check between cities here later
            candidate = random.choice(all_hexes)
            city_hexes.add(candidate)

        city_hex_list = list(city_hexes)
        
        # 3. Get City Templates
        city_templates = registry.get_templates_by_component("CityComponent")
        base_templates = list(city_templates.values())
        available_city_templates = list(city_templates.values())
        random.shuffle(available_city_templates)

        city_ids = []
        hex_to_entity = {}
        
        # 4. Create City Entities
        for i, (q, r) in enumerate(city_hex_list):
            x, y = GameSetupSystem._hex_to_pixel(q, r, hex_size)
            
            if available_city_templates:
                city_template = available_city_templates.pop(0)
                import copy
                new_city = copy.deepcopy(city_template)
            elif base_templates:
                city_template = random.choice(base_templates)
                import copy
                new_city = copy.deepcopy(city_template)
                new_city["NameComponent"]["displayName"] = f"City {i+1}"
            else:
                new_city = {
                    "NameComponent": {"displayName": f"City {i+1}"},
                    "TileComponent": {"type": "CITY"},
                    "CityComponent": {"description": "A newly founded settlement.", "level": 1, "biome": "DIRT_PATH"}
                }
                
            new_city["HexPositionComponent"] = {"q": q, "r": r, "x": round(x), "y": round(y)}
            if i == 0:
                if "CityComponent" not in new_city:
                    new_city["CityComponent"] = {}
                new_city["CityComponent"]["isCapital"] = True
            city_id = world.create_entity(new_city)
                
            city_ids.append(city_id)
            hex_to_entity[(q, r)] = city_id

        # 5. Populate remaining hexes (Voronoi biomes)
        city_biomes = []
        for cid in city_ids:
            city_pos = world.entities[cid]["HexPositionComponent"]
            city_biome = world.entities[cid].get("CityComponent", {}).get("biome", "DIRT_PATH")
            city_biomes.append((city_pos["q"], city_pos["r"], city_biome))

        for (q, r) in all_hexes:
            if (q, r) in city_hex_list:
                continue
                
            x, y = GameSetupSystem._hex_to_pixel(q, r, hex_size)
            
            # Find closest city for biome
            closest_dist = float('inf')
            closest_biome = "DIRT_PATH"
            for (cq, cr, cb) in city_biomes:
                dist = GameSetupSystem._hex_distance(q, r, cq, cr)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_biome = cb
            
            # Create standard tile
            tile_id = world.create_entity({
                "NameComponent": {"displayName": f"Hex {q},{r}"},
                "TileComponent": {"type": closest_biome},
                "HexPositionComponent": {"q": q, "r": r, "x": round(x), "y": round(y)}
            })
            hex_to_entity[(q, r)] = tile_id
            
            # Chance for encounter
            if random.random() < 0.15:
                mob_types = ["WOLF", "BAT", "GOBLIN", "SOLDIER", "THIEF", "SKELETON"]
                mob_id = world.create_entity({
                    "NameComponent": {"displayName": f"Wild {random.choice(mob_types)}"},
                    "MobComponent": {"type": random.choice(mob_types)},
                    "StatsComponent": {"maxHp": 10, "currentHp": 10, "baseAttack": 3, "baseDefense": 1},
                    "LootDropComponent": {"lootTable": [{"itemType": "COPPER_RING", "dropChanceProbability": 0.5}]}
                })
                world.entities[tile_id]["EncounterComponent"] = {
                    "mobEntityId": mob_id,
                    "isDefeated": False
                }

        # Return a shuffled list of city IDs so clients can pop from it
        start_cities_pool = city_ids.copy()
        random.shuffle(start_cities_pool)
        
        return city_ids, start_cities_pool

    @staticmethod
    def assign_player_start(world, player_entity_id, start_cities_pool):
        if not start_cities_pool:
            return False
            
        start_city_id = start_cities_pool.pop()
        world.entities[player_entity_id]["PositionComponent"] = {
            "currentTileId": start_city_id
        }
        return True
