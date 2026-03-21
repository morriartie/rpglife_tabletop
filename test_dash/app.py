import streamlit as st
import requests
import json
import subprocess
import os

API_URL = os.getenv("API_URL", "http://localhost:8001")

st.set_page_config(page_title="Tabletop RPG Test Dashboard", page_icon="🎲", layout="wide")

st.title("Tabletop RPG Test Dashboard")

tab1, tab2, tab3 = st.tabs(["🎮 Games", "🗄️ Database", "🧪 Tests"])

# State for selected game to view details
if "selected_game" not in st.session_state:
    st.session_state.selected_game = None

with tab1:
    st.header("Running Games")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("Refresh Games"):
            pass # Button click re-runs script
            
        try:
            response = requests.get(f"{API_URL}/games")
            if response.status_code == 200:
                games = response.json().get("games", [])
                if games:
                    for game in games:
                        cols = st.columns([3, 1])
                        with cols[0]:
                            st.info(f"Game ID: `{game}`")
                        with cols[1]:
                            if st.button("View Details", key=f"view_{game}"):
                                st.session_state.selected_game = game
                else:
                    st.warning("No running games found.")
                    st.session_state.selected_game = None
            else:
                st.error("Failed to fetch games.")
        except requests.exceptions.ConnectionError:
            st.error(f"Cannot connect to API at {API_URL}. Is it running?")

    with col2:
        st.subheader("Create Game")
        player_count = st.number_input("Player Count", min_value=1, max_value=8, value=4)
        if st.button("Create New Game"):
            try:
                res = requests.post(f"{API_URL}/game", json={"player_count": player_count})
                if res.status_code == 200:
                    st.success(f"Created game: {res.json().get('game_id')}")
                    st.rerun() # Refresh games list
                else:
                    st.error("Failed to create game.")
            except requests.exceptions.ConnectionError:
                st.error("API unreachable.")

    if st.session_state.selected_game:
        st.divider()
        st.subheader(f"Game Details: `{st.session_state.selected_game}`")
        try:
            res = requests.get(f"{API_URL}/game/{st.session_state.selected_game}/state")
            if res.status_code == 200:
                world_state = res.json().get("entities", {})
                
                players = []
                cities = []
                all_tiles = []
                
                # Parse entities
                for eid_str, comps in world_state.items():
                    if eid_str == "GameState":
                        continue
                        
                    eid = int(eid_str)
                    
                    if "PlayerComponent" in comps:
                        players.append((eid, comps))
                        
                    if "TileComponent" in comps:
                        all_tiles.append((eid, comps))
                        if comps["TileComponent"].get("type") == "CITY":
                            cities.append((eid, comps))
                            
                import streamlit.components.v1 as components
                
                # Build players data for JS
                players_data = []
                for pid, p_comps in players:
                    players_data.append({
                        "id": pid,
                        "name": p_comps.get("NameComponent", {}).get("displayName", f"Player {pid}"),
                        "hp": p_comps.get("StatsComponent", {}).get("currentHp", "?"),
                        "max_hp": p_comps.get("StatsComponent", {}).get("maxHp", "?"),
                        "tile_id": p_comps.get("PositionComponent", {}).get("currentTileId")
                    })
                
                # Build nodes and edges sequence
                nodes_data = []
                edges_data = []
                tile_map = {t[0]: t[1] for t in all_tiles}
                
                for eid, comps in all_tiles:
                    if "HexPositionComponent" in comps:
                        pos = comps.get("HexPositionComponent")
                        nodes_data.append({
                            "id": eid,
                            "name": comps.get("NameComponent", {}).get("displayName", f"Tile {eid}"),
                            "type": comps.get("TileComponent", {}).get("type", "UNKNOWN"),
                            "q": pos.get("q", 0),
                            "r": pos.get("r", 0),
                            "x": pos.get("x", 0),
                            "y": pos.get("y", 0)
                        })

                # Generate HTML visualization
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ margin: 0; padding: 0; overflow: hidden; background-color: #1e1e2f; color: white; font-family: sans-serif; height: 100%; }}
                        canvas {{ display: block; width: 100%; height: 600px; }}
                        #tooltip {{
                            position: absolute;
                            background: rgba(0, 0, 0, 0.85);
                            color: white;
                            padding: 10px;
                            border-radius: 6px;
                            pointer-events: none;
                            display: none;
                            font-size: 14px;
                            border: 1px solid #555;
                            z-index: 10;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                        }}
                    </style>
                </head>
                <body>
                    <div id="tooltip"></div>
                    <canvas id="gameCanvas"></canvas>
                    <script>
                        const API_URL = "{API_URL}";
                        const GAME_ID = "{st.session_state.selected_game}";
                        // Find a player that belongs to this session (just take the first one for testing)
                        const PLAYER_ID = players.length > 0 ? players[0].id : null;
                        
                        const nodes = {json.dumps(nodes_data)};
                        const edges = {json.dumps(edges_data)};
                        const players = {json.dumps(players_data)};
                        
                        const canvas = document.getElementById('gameCanvas');
                        const ctx = canvas.getContext('2d');
                        const tooltip = document.getElementById('tooltip');
                        
                        let width = window.innerWidth;
                        let height = 600;
                        
                        function resize() {{
                            width = window.innerWidth;
                            canvas.width = width;
                            canvas.height = height;
                            draw();
                        }}
                        
                        window.addEventListener('resize', resize);
                        
                        const nodePositions = {{}};
                        
                        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
                        nodes.forEach(n => {{
                            if (n.x < minX) minX = n.x;
                            if (n.x > maxX) maxX = n.x;
                            if (n.y < minY) minY = n.y;
                            if (n.y > maxY) maxY = n.y;
                        }});
                        
                        if (maxX === minX) {{ maxX += 10; minX -= 10; }}
                        if (maxY === minY) {{ maxY += 10; minY -= 10; }}
                        
                        function draw() {{
                            ctx.clearRect(0, 0, width, height);
                            if (nodes.length === 0) return;
                            
                            const padding = 60;
                            const drawWidth = width - padding * 2;
                            const drawHeight = height - padding * 2;
                            
                            // Calculate node positions 
                            nodes.forEach((node) => {{
                                const nx = (node.x - minX) / (maxX - minX);
                                const ny = (node.y - minY) / (maxY - minY);
                                const x = padding + nx * drawWidth;
                                const y = padding + ny * drawHeight;
                                nodePositions[node.id] = {{ x, y, tile: node, radius: node.type === 'CITY' ? 24 : 14 }};
                            }});
                            
                            // Draw path connecting them
                            ctx.lineWidth = 6;
                            ctx.strokeStyle = '#444';
                            edges.forEach(edge => {{
                                const p1 = nodePositions[edge.from];
                                const p2 = nodePositions[edge.to];
                                
                                if (p1 && p2) {{
                                    ctx.beginPath();
                                    ctx.moveTo(p1.x, p1.y);
                                    ctx.lineTo(p2.x, p2.y);
                                    ctx.stroke();
                                }}
                            }});
                            
                            // Draw nodes
                            nodes.forEach(tile => {{
                                const pos = nodePositions[tile.id];
                                ctx.beginPath();
                                ctx.arc(pos.x, pos.y, pos.radius, 0, Math.PI * 2);
                                
                                let fillStyle = '#888';
                                switch(tile.type) {{
                                    case 'CITY': fillStyle = '#ffd700'; break;
                                    case 'GRASS_PATH': fillStyle = '#4caf50'; break;
                                    case 'DIRT_PATH': fillStyle = '#8d6e63'; break;
                                    case 'ROCK_PATH': fillStyle = '#9e9e9e'; break;
                                    case 'FOREST': fillStyle = '#2e7d32'; break;
                                    case 'LAKE': fillStyle = '#2196f3'; break;
                                }}
                                ctx.fillStyle = fillStyle;
                                ctx.fill();
                                
                                ctx.lineWidth = 3;
                                ctx.strokeStyle = tile.type === 'CITY' ? '#ff8f00' : '#222';
                                ctx.stroke();
                                
                                // Node label if city
                                if (tile.type === 'CITY') {{
                                    ctx.fillStyle = '#fff';
                                    ctx.font = 'bold 12px sans-serif';
                                    ctx.textAlign = 'center';
                                    ctx.fillText(tile.name, pos.x, pos.y + pos.radius + 15);
                                }}
                            }});
                            
                            // Draw players near their tiles
                            players.forEach((player, idx) => {{
                                const tilePos = nodePositions[player.tile_id];
                                if (tilePos) {{
                                    const offsetAngle = (idx / players.length) * Math.PI * 2;
                                    const ox = Math.cos(offsetAngle) * (tilePos.radius + 12);
                                    const oy = Math.sin(offsetAngle) * (tilePos.radius + 12);
                                    
                                    const px = tilePos.x + ox;
                                    const py = tilePos.y + oy;
                                    
                                    ctx.beginPath();
                                    ctx.arc(px, py, 8, 0, Math.PI * 2);
                                    ctx.fillStyle = '#ff1744';
                                    ctx.fill();
                                    ctx.lineWidth = 2;
                                    ctx.strokeStyle = '#fff';
                                    ctx.stroke();
                                    
                                    // Player label
                                    ctx.fillStyle = '#fff';
                                    ctx.font = '11px sans-serif';
                                    ctx.textAlign = 'center';
                                    ctx.fillText(player.name + ' (' + player.hp + '/' + player.max_hp + ')', px, py - 12);
                                }}
                            }});
                        }}
                        
                        // Selected path state
                        let currentPath = [];
                        let isPreviewing = false;
                        
                        async function previewPath(targetTileId) {{
                            if (!PLAYER_ID) return;
                            
                            try {{
                                const res = await fetch(`${{API_URL}}/game/${{GAME_ID}}/player/${{PLAYER_ID}}/preview_move`, {{
                                    method: 'POST',
                                    headers: {{ 'Content-Type': 'application/json' }},
                                    body: JSON.stringify({{
                                        target_tile_id: targetTileId,
                                        chosen_index: 0 // testing with max distance
                                    }})
                                }});
                                
                                if (res.ok) {{
                                    const data = await res.json();
                                    currentPath = data.path;
                                    isPreviewing = true;
                                    draw(); // redraw with path
                                }}
                            }} catch (e) {{
                                console.error("Path preview err", e);
                            }}
                        }}
                        
                        async function executeMove() {{
                            if (!PLAYER_ID || !isPreviewing || currentPath.length === 0) return;
                            
                            try {{
                                const res = await fetch(`${{API_URL}}/game/${{GAME_ID}}/player/${{PLAYER_ID}}/move_choice`, {{
                                    method: 'POST',
                                    headers: {{ 'Content-Type': 'application/json' }},
                                    body: JSON.stringify({{
                                        path: currentPath
                                    }})
                                }});
                                
                                if (res.ok) {{
                                    currentPath = [];
                                    isPreviewing = false;
                                    // Let streamlit auto-refresh handle it later
                                }}
                            }} catch (e) {{
                                console.error("Move error", e);
                            }}
                        }}

                        canvas.addEventListener('click', (e) => {{
                            const rect = canvas.getBoundingClientRect();
                            const mx = e.clientX - rect.left;
                            const my = e.clientY - rect.top;
                            
                            let clicked = null;
                            for (const id in nodePositions) {{
                                const pos = nodePositions[id];
                                const dist = Math.hypot(mx - pos.x, my - pos.y);
                                if (dist <= pos.radius) {{
                                    clicked = pos;
                                    break;
                                }}
                            }}
                            
                            if (clicked) {{
                                if (isPreviewing && currentPath.length > 0 && currentPath[currentPath.length - 1] === clicked.tile.id) {{
                                    // Confirm move if clicked target again
                                    executeMove();
                                }} else {{
                                    previewPath(clicked.tile.id);
                                }}
                            }}
                        }});

                        canvas.addEventListener('mousemove', (e) => {{
                            const rect = canvas.getBoundingClientRect();
                            const mx = e.clientX - rect.left;
                            const my = e.clientY - rect.top;
                            
                            let hovered = null;
                            for (const id in nodePositions) {{
                                const pos = nodePositions[id];
                                const dist = Math.hypot(mx - pos.x, my - pos.y);
                                if (dist <= pos.radius) {{
                                    hovered = pos;
                                    break;
                                }}
                            }}
                            
                            if (hovered) {{
                                tooltip.style.display = 'block';
                                tooltip.style.left = (e.clientX + 15) + 'px';
                                tooltip.style.top = (e.clientY + 15) + 'px';
                                tooltip.innerHTML = `<strong>${{hovered.tile.name}}</strong><br/><span style="color:#aaa">Type: ${{hovered.tile.type}}</span>`;
                                document.body.style.cursor = 'pointer';
                                
                                // Redraw to highlight
                                draw();
                                ctx.beginPath();
                                ctx.arc(hovered.x, hovered.y, hovered.radius + 4, 0, Math.PI * 2);
                                ctx.lineWidth = 2;
                                ctx.strokeStyle = '#00e5ff';
                                ctx.stroke();
                                
                            }} else {{
                                tooltip.style.display = 'none';
                                document.body.style.cursor = 'default';
                                draw();
                            }}
                        }});
                        
                        resize();
                        setTimeout(resize, 100);
                    </script>
                </body>
                </html>
                """
                
                # Render using Streamlit component
                st.markdown("### 🗺️ World Map")
                components.html(html_content, height=620)
                
                # Render Player Mats
                st.markdown("### 🪪 Player Mats")
                for pid, p_comps in players:
                    p_name = p_comps.get("NameComponent", {}).get("displayName", f"Player {pid}")
                    tile_id = p_comps.get("PositionComponent", {}).get("currentTileId")
                    location_name = "Unknown Location"
                    if tile_id is not None:
                        t_id = int(tile_id)
                        if t_id in tile_map:
                            location_name = tile_map[t_id].get("NameComponent", {}).get("displayName", f"Tile {t_id}")
                        else:
                            location_name = f"Tile {t_id}"

                    with st.expander(f"**{p_name}** - 📍 {location_name}", expanded=False):
                        st.markdown(f"**Current Location:** {location_name}")
                        mat_cols = st.columns(3)
                        
                        # Equipment
                        with mat_cols[0]:
                            st.markdown("#### Equipment")
                            equipment = p_comps.get("EquipmentComponent", {})
                            slots = ["headEntityId", "bodyEntityId", "feetEntityId", "weaponEntityId", "ringEntityId"]
                            slot_names = ["Head", "Body", "Feet", "Weapon", "Ring"]
                            for slot_key, slot_name in zip(slots, slot_names):
                                item_id = equipment.get(slot_key)
                                if item_id:
                                    item_comps = world_state.get(str(item_id), {})
                                    item_name = item_comps.get("NameComponent", {}).get("displayName", f"Item {item_id}")
                                    st.markdown(f"**{slot_name}:** {item_name}")
                                    item_data = item_comps.get("ItemComponent", {})
                                    dice = item_data.get("dice", [])
                                    if dice:
                                        for d in dice:
                                            st.caption(f"🎲 D{d.get('sides')} [{', '.join(d.get('keywords', []))}]")
                                else:
                                    st.markdown(f"**{slot_name}:** *(Empty)*")
                        
                        # Dice Pool
                        with mat_cols[1]:
                            st.markdown("#### Dice Pool")
                            dice_pool = p_comps.get("DicePoolComponent", {}).get("diceQueue", [])
                            if not dice_pool:
                                st.markdown("*(Empty Pool)*")
                            else:
                                for d in dice_pool:
                                    src_item = d.get('sourceItemEntityId')
                                    src_name = world_state.get(str(src_item), {}).get("NameComponent", {}).get("displayName", f"Item {src_item}") if src_item else "Unknown"
                                    st.markdown(f"🎲 **D{d.get('sides')}** [{', '.join(d.get('keywords', []))}]<br><small>from {src_name}</small>", unsafe_allow_html=True)
                                    
                        # Bag
                        with mat_cols[2]:
                            st.markdown("#### Bag")
                            inventory = p_comps.get("InventoryComponent", {})
                            st.markdown(f"**Weight:** {inventory.get('currentWeight', 0)} / {inventory.get('maxWeightCapacity', '?')}")
                            held_ids = inventory.get("heldEntityIds", [])
                            if not held_ids:
                                st.markdown("*(Empty Bag)*")
                            else:
                                for h_id in held_ids:
                                    h_comps = world_state.get(str(h_id), {})
                                    h_name = h_comps.get("NameComponent", {}).get("displayName", f"Item {h_id}")
                                    st.markdown(f"- {h_name}")
                            
            else:
                st.error("Failed to load game state.")
        except requests.exceptions.ConnectionError:
            st.error("API unreachable.")

with tab2:
    st.header("Entity Database (entities.json)")
    
    entities_path = "/game/entities.json"
    if not os.path.exists(entities_path):
        # Local fallback if not running in docker container
        entities_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "game", "entities.json")
    
    if os.path.exists(entities_path):
        with open(entities_path, "r") as f:
            entities = json.load(f)
            
        st.write(f"Loaded **{len(entities)}** entities in total.")
        
        # Collect all unique components
        all_components = set()
        for eid, comps in entities.items():
            for comp_name in comps.keys():
                all_components.add(comp_name)
        
        all_components = sorted(list(all_components))
        
        selected_components = st.multiselect("Search by Components", options=all_components)
        
        if selected_components:
            st.subheader("Entities with selected components")
            
            matching_entities = {eid: comps for eid, comps in entities.items() if all(c in comps for c in selected_components)}
            
            if not matching_entities:
                st.write("No entities found with these components.")
            else:
                for eid, comps in matching_entities.items():
                    name = comps.get("NameComponent", {}).get("displayName", f"Entity {eid}")
                    
                    # Entity card that expands when clicked to show all components
                    with st.expander(f"**{name}** (ID: `{eid}`)", expanded=False):
                        for comp_name, comp_data in comps.items():
                            with st.container(border=True):
                                if comp_name in selected_components:
                                    # Selected component is a different color
                                    st.markdown(f"**:blue[{comp_name}]**")
                                else:
                                    # Default color
                                    st.markdown(f"**{comp_name}**")
                                
                                if not comp_data:
                                    st.markdown("*(No attributes)*")
                                else:
                                    for k, v in comp_data.items():
                                        st.markdown(f"**:gray[{k}]:** {v}")
    else:
        st.error(f"Entities file not found at {entities_path}. Is the volume mounted correctly?")

with tab3:
    st.header("Run Tests")
    st.write("Execute pytest in the API volume.")
    
    if st.button("Run Tests"):
        with st.spinner("Running tests..."):
            try:
                cwd = None
                tests_path = "/api/src/tests/"
                if not os.path.exists(tests_path):
                    api_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api")
                    tests_path = os.path.join(api_dir, "src", "tests")
                    cwd = api_dir if os.path.exists(api_dir) else None
                    
                result = subprocess.run(
                    ["uv", "run", "pytest", tests_path, "-v"],
                    cwd=cwd,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    st.success("All tests passed!")
                else:
                    st.error("Some tests failed.")
                    
                st.code(result.stdout, language="bash")
                if result.stderr:
                    st.code(result.stderr, language="bash")
            except Exception as e:
                st.error(f"Error running tests: {e}")
