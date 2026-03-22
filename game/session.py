import uuid
import os
from .systems import World, TemplateRegistry
from .map_builder import GameSetupSystem
import copy

class SessionManager:
    def __init__(self, entities_file_path: str):
        self.entities_file_path = entities_file_path
        self.registry = TemplateRegistry(entities_file_path)
        self.sessions = {}

    def create_session(self, player_count: int = 4) -> str:
        game_id = str(uuid.uuid4())
        world = World()
        
        # Generate new procedural board
        city_ids, start_cities_pool = GameSetupSystem.generate_map(world, self.registry, player_count)
        world.start_cities_pool = start_cities_pool
        
        # Instantiate players
        player_templates = self.registry.get_templates_by_component("PlayerComponent")
        if not player_templates:
            raise ValueError("No player templates found in entities.json!")
            
        base_player_template = list(player_templates.values())[0]
        
        player_ids = []
        for i in range(player_count):
            new_player = copy.deepcopy(base_player_template)
            new_player["NameComponent"]["displayName"] = f"Hero {i+1}"
            pid = world.create_entity(new_player)
            GameSetupSystem.assign_player_start(world, pid, world.start_cities_pool)
            player_ids.append(pid)
            
        world.entities["GameState"]["turn_order"] = player_ids
        world.entities["GameState"]["active_player_id"] = player_ids[0]
            
        self.sessions[game_id] = world
        return game_id

    def get_session(self, game_id: str) -> World:
        return self.sessions.get(game_id)
        
    def delete_session(self, game_id: str):
        if game_id in self.sessions:
            del self.sessions[game_id]
