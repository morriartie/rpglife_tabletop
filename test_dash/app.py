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
                
                game_state_entity = world_state.get("GameState", {})
                global_turn = game_state_entity.get("global_turn", 1)
                active_player_id = game_state_entity.get("active_player_id")
                turn_phase = game_state_entity.get("turn_phase", "Unknown")
                
                active_player_name = "Unknown"
                if active_player_id and str(active_player_id) in world_state:
                    active_player_name = world_state[str(active_player_id)].get("NameComponent", {}).get("displayName", f"Player {active_player_id}")
                
                st.markdown(f"### ⚔️ Round {global_turn} | Active Player: **{active_player_name}**")
                
                phases = ["Movement", "Tile Resolution", "Combat", "Reward", "Punishment"]
                if turn_phase not in phases:
                    phases.append(turn_phase)
                    
                cols = st.columns(len(phases))
                for i, p in enumerate(phases):
                    with cols[i]:
                        if p == turn_phase:
                            st.markdown(f"<div style='text-align: center; padding: 10px; margin-bottom: 20px; background-color: #4CAF50; color: white; border-radius: 5px; font-weight: bold;'>{p}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='text-align: center; padding: 10px; margin-bottom: 20px; background-color: #ffffff11; color: #888; border-radius: 5px;'>{p}</div>", unsafe_allow_html=True)
                
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
                
                # Group entities by their currentTileId
                tile_contents = {}
                for eid_str, comps in world_state.items():
                    if "PositionComponent" in comps:
                        tid = comps["PositionComponent"].get("currentTileId")
                        if tid is not None:
                            if tid not in tile_contents:
                                tile_contents[tid] = []
                            
                            name = comps.get("NameComponent", {}).get("displayName", f"Entity {eid_str}")
                            type_ = "Unknown"
                            if "PlayerComponent" in comps:
                                type_ = "Player"
                            elif "MobComponent" in comps:
                                type_ = "Mob"
                            elif "ItemComponent" in comps:
                                type_ = "Item"
                            
                            tile_contents[tid].append({
                                "id": eid_str,
                                "name": name,
                                "type": type_
                            })
                
                for eid, comps in all_tiles:
                    if "HexPositionComponent" in comps:
                        pos = comps.get("HexPositionComponent")
                        
                        desc = ""
                        if "CityComponent" in comps:
                            desc = comps["CityComponent"].get("description", "")
                        elif "DescriptionComponent" in comps:
                            desc = comps["DescriptionComponent"].get("description", "")
                            
                        encounters = []
                        if "EncounterComponent" in comps:
                            mob_id = comps["EncounterComponent"].get("mobEntityId")
                            is_def = comps["EncounterComponent"].get("isDefeated", False)
                            mob_name = "Unknown Mob"
                            if mob_id and str(mob_id) in world_state:
                                mob_name = world_state[str(mob_id)].get("NameComponent", {}).get("displayName", f"Mob {mob_id}")
                            if not is_def:
                                encounters.append({"id": mob_id, "name": mob_name})
                                
                        inventory = []
                        if "InventoryComponent" in comps:
                            held = comps["InventoryComponent"].get("heldEntityIds", [])
                            for h_id in held:
                                if str(h_id) in world_state:
                                    i_name = world_state[str(h_id)].get("NameComponent", {}).get("displayName", f"Item {h_id}")
                                    inventory.append({"id": h_id, "name": i_name})
                                    
                        entities_here = tile_contents.get(eid, [])
                        for ent in entities_here:
                            if ent["type"] == "Mob":
                                if not any(str(e["id"]) == str(ent["id"]) for e in encounters):
                                    encounters.append(ent)
                            elif ent["type"] == "Item":
                                if not any(str(i["id"]) == str(ent["id"]) for i in inventory):
                                    inventory.append(ent)
                        
                        players_on_tile = [ent for ent in entities_here if ent["type"] == "Player"]

                        nodes_data.append({
                            "id": eid,
                            "name": comps.get("NameComponent", {}).get("displayName", f"Tile {eid}"),
                            "type": comps.get("TileComponent", {}).get("type", "UNKNOWN"),
                            "description": desc,
                            "q": pos.get("q", 0),
                            "r": pos.get("r", 0),
                            "x": pos.get("x", 0),
                            "y": pos.get("y", 0),
                            "encounters": encounters,
                            "inventory": inventory,
                            "players": players_on_tile,
                            "raw_comps": comps
                        })

                # Generate HTML visualization
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ margin: 0; padding: 0; background-color: #1e1e2f; color: white; font-family: sans-serif; height: 100%; }}
                        canvas {{ display: block; width: 100%; height: 460px; }}
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
                        #bottomDrawer {{
                            position: relative;
                            width: 100%;
                            background: #2a2a3f;
                            border-top: 2px solid #555;
                            box-sizing: border-box;
                            overflow: hidden;
                            transition: max-height 0.3s ease;
                            max-height: 160px;
                        }}
                        #bottomDrawer.collapsed {{
                            max-height: 40px;
                        }}
                        #drawerHeader {{
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                            padding: 8px 16px;
                            background: #1e1e2f;
                            border-bottom: 1px solid #444;
                            cursor: pointer;
                            user-select: none;
                        }}
                        #drawerHeader span {{
                            font-size: 13px;
                            font-weight: bold;
                            color: #00e5ff;
                        }}
                        #drawerHeader .toggle {{
                            font-size: 16px;
                            color: #888;
                        }}
                        #drawerBody {{
                            padding: 12px 16px;
                            display: flex;
                            gap: 24px;
                            align-items: flex-start;
                        }}
                        #drawerActions {{
                            display: flex;
                            gap: 8px;
                            flex-wrap: wrap;
                            align-items: center;
                        }}
                        #drawerActions button {{
                            padding: 8px 16px;
                            border: none;
                            border-radius: 6px;
                            font-size: 13px;
                            font-weight: bold;
                            cursor: pointer;
                            transition: background 0.2s, transform 0.1s;
                            color: white;
                            background: #4CAF50;
                        }}
                        #drawerActions button:hover {{
                            filter: brightness(1.15);
                            transform: translateY(-1px);
                        }}
                        #drawerActions button.secondary {{
                            background: #555;
                        }}
                        #drawerActions button.danger {{
                            background: #e53935;
                        }}
                        #drawerActions button.combat {{
                            background: #ff6f00;
                        }}
                        #drawerFeedback {{
                            font-size: 13px;
                            color: #ccc;
                            flex: 1;
                            min-height: 20px;
                            line-height: 1.5;
                        }}
                        #drawerFeedback .result-win {{ color: #4CAF50; font-weight: bold; }}
                        #drawerFeedback .result-loss {{ color: #e53935; font-weight: bold; }}
                        #playerMat {{
                            background: #2a2a3f;
                            border-top: 1px solid #444;
                            padding: 12px 16px;
                            display: flex;
                            gap: 24px;
                            font-size: 13px;
                            color: #ccc;
                            overflow-x: auto;
                        }}
                        #playerMat .mat-section {{
                            min-width: 150px;
                        }}
                        #playerMat h4 {{
                            color: #00e5ff;
                            margin: 0 0 6px 0;
                            font-size: 13px;
                            text-transform: uppercase;
                        }}
                        #playerMat .slot {{
                            margin-bottom: 4px;
                        }}
                        #playerMat .slot-name {{
                            color: #888;
                        }}
                        #playerMat .slot-item {{
                            color: #fff;
                        }}
                        #playerMat .hp-bar {{
                            height: 8px;
                            background: #444;
                            border-radius: 4px;
                            overflow: hidden;
                            margin-top: 4px;
                        }}
                        #playerMat .hp-fill {{
                            height: 100%;
                            background: #4CAF50;
                            border-radius: 4px;
                            transition: width 0.3s;
                        }}
                        #playerMat .mat-player-name {{
                            color: #fff;
                            font-weight: bold;
                            font-size: 14px;
                            margin-bottom: 8px;
                        }}
                        #matTabs {{
                            display: flex;
                            gap: 0;
                            background: #1e1e2f;
                            border-top: 1px solid #444;
                        }}
                        #matTabs button {{
                            flex: 1;
                            padding: 8px 12px;
                            background: #1e1e2f;
                            color: #888;
                            border: none;
                            border-bottom: 2px solid transparent;
                            font-size: 12px;
                            font-weight: bold;
                            cursor: pointer;
                            transition: all 0.2s;
                        }}
                        #matTabs button:hover {{
                            color: #ccc;
                        }}
                        #matTabs button.active {{
                            color: #00e5ff;
                            border-bottom-color: #00e5ff;
                        }}
                    </style>
                </head>
                <body>
                    <div id="tooltip"></div>
                    <div id="sidePanel" style="position: absolute; right: 0; top: 0; width: 350px; height: 100%; background: #2a2a3f; border-left: 2px solid #555; padding: 20px; box-sizing: border-box; display: none; overflow-y: auto; z-index: 5; box-shadow: -4px 0 10px rgba(0,0,0,0.5);">
                        <div id="spBreadcrumbs" style="margin-bottom: 15px; font-size: 12px; color: #888; overflow-wrap: break-word;"></div>
                        <h2 id="spName" style="margin-top: 0; color: #fff; margin-bottom: 5px;">Entity Name</h2>
                        <span id="spType" style="color: #00e5ff; font-size: 13px; display: block; margin-bottom: 15px; font-weight: bold; text-transform: uppercase;">Type</span>
                        
                        <div id="spContent"></div>
                        
                        <button id="spClose" style="margin-top: 25px; width: 100%; padding: 10px; background: #555; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: bold;">Close Panel</button>
                    </div>
                    <canvas id="gameCanvas"></canvas>
                    <div id="bottomDrawer">
                        <div id="drawerHeader">
                            <span id="drawerPhaseLabel">Loading...</span>
                            <span class="toggle" id="drawerToggle">▼</span>
                        </div>
                        <div id="drawerBody">
                            <div id="drawerActions"></div>
                            <div id="drawerFeedback"></div>
                        </div>
                    </div>
                    <div id="matTabs"></div>
                    <div id="playerMat">Loading player mat...</div>
                    <script>
                        const PUBLIC_API_URL = `http://${{window.location.hostname || 'localhost'}}:8001`;
                        const GAME_ID = "{st.session_state.selected_game}";
                        const nodes = {json.dumps(nodes_data)};
                        const edges = {json.dumps(edges_data)};
                        const players = {json.dumps(players_data)};
                        const allEntities = {json.dumps(world_state)};
                        
                        // Find a player that belongs to this session (just take the first one for testing)
                        let PLAYER_ID = players.length > 0 ? players[0].id : null;
                        
                        const canvas = document.getElementById('gameCanvas');
                        const ctx = canvas.getContext('2d');
                        const tooltip = document.getElementById('tooltip');
                        
                        const sidePanel = document.getElementById('sidePanel');
                        const spBreadcrumbs = document.getElementById('spBreadcrumbs');
                        const spName = document.getElementById('spName');
                        const spType = document.getElementById('spType');
                        const spContent = document.getElementById('spContent');
                        const spClose = document.getElementById('spClose');
                        
                        let selectedTileId = null;
                        let inspectionStack = [];
                        
                        spClose.addEventListener('click', () => {{
                            sidePanel.style.display = 'none';
                            selectedTileId = null;
                            inspectionStack = [];
                            draw();
                        }});
                        
                        function getEntityName(eid) {{
                            const ent = allEntities[eid];
                            if (!ent) return `Unknown Entity ${{eid}}`;
                            return ent.NameComponent?.displayName || `Entity ${{eid}}`;
                        }}
                        
                        window.pushInspect = function(eid) {{
                            inspectionStack.push(eid.toString());
                            renderInspector();
                        }};
                        
                        window.inspectType = async function(typeVal) {{
                            const pseudoId = 'TPL_' + typeVal;
                            
                            if (allEntities[pseudoId]) {{
                                pushInspect(pseudoId);
                                return;
                            }}
                            
                            try {{
                                const res = await fetch(PUBLIC_API_URL + '/template/' + typeVal);
                                if (res.ok) {{
                                    const data = await res.json();
                                    allEntities[pseudoId] = data.template;
                                    
                                    if (!allEntities[pseudoId].NameComponent) {{
                                        allEntities[pseudoId].NameComponent = {{ displayName: typeVal + ' (Template)' }};
                                    }}
                                    
                                    pushInspect(pseudoId);
                                }} else {{
                                    alert('No detailed template data available for type: ' + typeVal);
                                }}
                            }} catch (e) {{
                                console.error(e);
                                alert('Failed to fetch template data for type: ' + typeVal);
                            }}
                        }};
                        
                        window.popToInspect = function(idx) {{
                            inspectionStack = inspectionStack.slice(0, idx + 1);
                            renderInspector();
                        }};
                        
                        function renderInspector() {{
                            if (inspectionStack.length === 0) {{
                                sidePanel.style.display = 'none';
                                return;
                            }}
                            sidePanel.style.display = 'block';
                            
                            const currentId = inspectionStack[inspectionStack.length - 1];
                            const entity = allEntities[currentId];
                            
                            // Render Breadcrumbs
                            let breadcrumbsHtml = '';
                            for (let i = 0; i < inspectionStack.length; i++) {{
                                const id = inspectionStack[i];
                                const maxLen = 15;
                                let name = getEntityName(id);
                                if (name.length > maxLen) name = name.substring(0, maxLen) + '...';
                                
                                if (i === inspectionStack.length - 1) {{
                                    breadcrumbsHtml += `<span style="color: #fff;">${{name}}</span>`;
                                }} else {{
                                    breadcrumbsHtml += `<a href="#" onclick="event.preventDefault(); popToInspect(${{i}})" style="color: #00e5ff; text-decoration: none;">${{name}}</a> &gt; `;
                                }}
                            }}
                            spBreadcrumbs.innerHTML = breadcrumbsHtml;
                            
                            if (!entity) {{
                                spName.innerText = "Entity Not Found";
                                spType.innerText = "ERROR";
                                spContent.innerHTML = `<p style="color: red;">Entity ID ${{currentId}} does not exist in world state.</p>`;
                                return;
                            }}
                            
                            spName.innerText = getEntityName(currentId);
                            // Determine a loose "Type" by finding the main component
                            let typeStr = Object.keys(entity).find(k => k.endsWith('Component') && k !== 'NameComponent' && k !== 'PositionComponent') || 'Entity';
                            spType.innerText = typeStr.replace('Component', '');
                            
                            let contentHtml = '';
                            
                            // 1. Entities physically "here" (on this tile or in this container)
                            const entitiesHere = [];
                            for (const [eid, comps] of Object.entries(allEntities)) {{
                                if (eid === currentId) continue;
                                if (comps.PositionComponent?.currentTileId == currentId) {{
                                    entitiesHere.push(eid);
                                }}
                            }}
                            
                            if (entitiesHere.length > 0) {{
                                contentHtml += `<div style="margin-bottom: 15px; border-bottom: 1px solid #444; padding-bottom: 10px;">`;
                                contentHtml += `<h3 style="font-size: 14px; color: #a1b56c; margin-top: 0;">Entities Here</h3>`;
                                contentHtml += `<ul style="list-style: none; padding: 0; margin: 0; font-size: 13px;">`;
                                for (const eid of entitiesHere) {{
                                    const typeIcon = allEntities[eid]?.PlayerComponent ? '👤' : (allEntities[eid]?.MobComponent ? '🐺' : '📦');
                                    contentHtml += `<li style="margin-bottom: 4px;">${{typeIcon}} <a href="#" onclick="event.preventDefault(); pushInspect('${{eid}}')" style="color: #ffd700; text-decoration: none;">${{getEntityName(eid)}}</a></li>`;
                                }}
                                contentHtml += `</ul></div>`;
                            }}
                            
                            // 2. Generic Component Rendering
                            for (const [compName, compData] of Object.entries(entity)) {{
                                contentHtml += `<div style="margin-bottom: 15px; background: #1e1e2f; padding: 10px; border-radius: 4px;">`;
                                contentHtml += `<h4 style="margin: 0 0 8px 0; font-size: 13px; color: #e1b2ff;">${{compName}}</h4>`;
                                
                                if (Object.keys(compData).length === 0) {{
                                    contentHtml += `<span style="font-size: 12px; color: #888;">(No properties)</span>`;
                                }} else {{
                                    contentHtml += `<table style="width: 100%; font-size: 12px; border-collapse: collapse;">`;
                                    for (const [key, val] of Object.entries(compData)) {{
                                        contentHtml += `<tr><td style="color: #999; padding: 2px 5px 2px 0; max-width: 120px; overflow: hidden; text-overflow: ellipsis;">${{key}}</td><td style="color: #fff; padding: 2px 0; word-break: break-all;">`;
                                        
                                        const isEntityId = key.endsWith('EntityId');
                                        const isEntityIds = key.endsWith('EntityIds');
                                        const isTypeString = key === 'type' || key === 'itemType' || key === 'mobType' || key === 'biome';
                                        
                                        if (isEntityId && val) {{
                                            contentHtml += `<a href="#" onclick="event.preventDefault(); pushInspect('${{val}}')" style="color: #ffd700; text-decoration: none; font-weight: bold;">[🔗 ${{getEntityName(val)}}]</a>`;
                                        }} else if (isEntityIds && Array.isArray(val)) {{
                                            if (val.length === 0) {{
                                                contentHtml += `[]`;
                                            }} else {{
                                                contentHtml += val.map(v => `<a href="#" onclick="event.preventDefault(); pushInspect('${{v}}')" style="color: #ffd700; text-decoration: none; font-weight: bold;">[🔗 ${{getEntityName(v)}}]</a>`).join(', ');
                                            }}
                                        }} else if (isTypeString && typeof val === 'string') {{
                                            contentHtml += `<a href="#" onclick="event.preventDefault(); inspectType('${{val}}')" style="color: #ff9800; text-decoration: none; font-weight: bold;">[📜 ${{val}}]</a>`;
                                        }} else if (typeof val === 'object' && val !== null) {{
                                            contentHtml += `<pre style="margin: 0; font-size: 11px; color: #aaa;">${{JSON.stringify(val, null, 2)}}</pre>`;
                                        }} else {{
                                            contentHtml += val;
                                        }}
                                        contentHtml += `</td></tr>`;
                                    }}
                                    contentHtml += `</table>`;
                                }}
                                contentHtml += `</div>`;
                            }}
                            
                            spContent.innerHTML = contentHtml;
                        }}
                        
                        function showSidePanel(tile) {{
                            inspectionStack = [tile.id.toString()];
                            renderInspector();
                        }}

                        
                        let width = window.innerWidth;
                        let height = 460;
                        
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
                        
                        function drawHexShape(ctx, cx, cy, sz) {{
                            ctx.beginPath();
                            for (let i = 0; i < 6; i++) {{
                                const angle_rad = Math.PI / 180 * (60 * i);
                                const px = cx + sz * Math.cos(angle_rad);
                                const py = cy + sz * Math.sin(angle_rad);
                                if (i === 0) ctx.moveTo(px, py);
                                else ctx.lineTo(px, py);
                            }}
                            ctx.closePath();
                        }}

                        function draw() {{
                            ctx.clearRect(0, 0, width, height);
                            if (nodes.length === 0) return;
                            
                            const padding = 60;
                            const drawWidth = width - padding * 2;
                            const drawHeight = height - padding * 2;
                            
                            // Calculate node positions 
                            const dataWidth = maxX === minX ? 1 : (maxX - minX);
                            const dataHeight = maxY === minY ? 1 : (maxY - minY);
                            const scale = Math.min(drawWidth / dataWidth, drawHeight / dataHeight) * 0.95;
                            const xOffset = padding + (drawWidth - dataWidth * scale) / 2;
                            const yOffset = padding + (drawHeight - dataHeight * scale) / 2;
                            const hexSize = 30 * scale;

                            nodes.forEach((node) => {{
                                const x = xOffset + (node.x - minX) * scale;
                                const y = yOffset + (node.y - minY) * scale;
                                nodePositions[node.id] = {{ x, y, tile: node, radius: hexSize, hexSize: hexSize }};
                            }});
                            
                            // Draw base edges (if any)
                            ctx.lineWidth = 4;
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

                            // Draw preview path
                            if (typeof currentPath !== 'undefined' && currentPath && currentPath.length > 0) {{
                                // Draw path line
                                const fullPath = [getPlayerTileId(), ...currentPath];
                                ctx.lineWidth = 4;
                                ctx.strokeStyle = '#00e5ff';
                                ctx.setLineDash([8, 4]);
                                ctx.beginPath();
                                for (let i = 0; i < fullPath.length; i++) {{
                                    const p = nodePositions[fullPath[i]];
                                    if (p) {{
                                        if (i === 0) ctx.moveTo(p.x, p.y);
                                        else ctx.lineTo(p.x, p.y);
                                    }}
                                }}
                                ctx.stroke();
                                ctx.setLineDash([]);
                                
                                // Highlight destination tile
                                const dest = nodePositions[currentPath[currentPath.length - 1]];
                                if (dest) {{
                                    drawHexShape(ctx, dest.x, dest.y, dest.hexSize + 3);
                                    ctx.lineWidth = 3;
                                    ctx.strokeStyle = '#00e5ff';
                                    ctx.stroke();
                                }}
                            }}
                            
                            // Draw nodes
                            nodes.forEach(tile => {{
                                const pos = nodePositions[tile.id];
                                drawHexShape(ctx, pos.x, pos.y, pos.hexSize - 0.5);
                                
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
                                
                                ctx.lineWidth = 1.5;
                                ctx.strokeStyle = tile.type === 'CITY' ? '#ff8f00' : '#222';
                                ctx.stroke();
                                
                                if (selectedTileId === tile.id) {{
                                    ctx.lineWidth = 3;
                                    ctx.strokeStyle = '#fff';
                                    ctx.stroke();
                                }}
                                
                                // Node label if city
                                if (tile.type === 'CITY') {{
                                    ctx.fillStyle = '#000';
                                    ctx.font = 'bold 12px sans-serif';
                                    ctx.textAlign = 'center';
                                    ctx.fillText(tile.name, pos.x, pos.y + 4);
                                }}
                            }});
                            
                            // Draw reachable tile highlights
                            if (reachableTiles.size > 0) {{
                                const pulse = 0.5 + 0.5 * Math.sin(Date.now() / 300);
                                reachableTiles.forEach(tileId => {{
                                    const pos = nodePositions[tileId];
                                    if (pos) {{
                                        drawHexShape(ctx, pos.x, pos.y, pos.hexSize + 3);
                                        ctx.lineWidth = 2.5;
                                        ctx.strokeStyle = `rgba(0, 229, 255, ${{0.4 + pulse * 0.6}})`;
                                        ctx.stroke();
                                    }}
                                }});
                                // Request animation frame to keep pulsing
                                requestAnimationFrame(() => draw());
                            }}
                            
                            // Draw players on their tiles
                            // Group players by tile so we can offset multiples
                            const playersByTile = {{}};
                            players.forEach((player, idx) => {{
                                const tid = player.tile_id;
                                if (!playersByTile[tid]) playersByTile[tid] = [];
                                playersByTile[tid].push(player);
                            }});
                            
                            for (const [tid, tilePlayers] of Object.entries(playersByTile)) {{
                                const tilePos = nodePositions[tid];
                                if (!tilePos) continue;
                                
                                tilePlayers.forEach((player, idx) => {{
                                    let px, py;
                                    if (tilePlayers.length === 1) {{
                                        // Single player: center on hex
                                        px = tilePos.x;
                                        py = tilePos.y;
                                    }} else {{
                                        // Multiple players: spread in small cluster inside hex
                                        const offsetAngle = (idx / tilePlayers.length) * Math.PI * 2 - Math.PI / 2;
                                        const offsetDist = Math.min(tilePos.radius * 0.35, 14);
                                        px = tilePos.x + Math.cos(offsetAngle) * offsetDist;
                                        py = tilePos.y + Math.sin(offsetAngle) * offsetDist;
                                    }}
                                    
                                    ctx.beginPath();
                                    ctx.arc(px, py, 7, 0, Math.PI * 2);
                                    ctx.fillStyle = '#ff1744';
                                    ctx.fill();
                                    ctx.lineWidth = 2;
                                    ctx.strokeStyle = '#fff';
                                    ctx.stroke();
                                    
                                    // Player label above dot
                                    ctx.fillStyle = '#fff';
                                    ctx.font = '11px sans-serif';
                                    ctx.textAlign = 'center';
                                    ctx.fillText(player.name + ' (' + player.hp + '/' + player.max_hp + ')', px, py - 11);
                                }});
                            }}
                        }}
                        
                        // ========== BOTTOM DRAWER STATE ==========
                        const drawer = document.getElementById('bottomDrawer');
                        const drawerHeader = document.getElementById('drawerHeader');
                        const drawerPhaseLabel = document.getElementById('drawerPhaseLabel');
                        const drawerToggle = document.getElementById('drawerToggle');
                        const drawerActions = document.getElementById('drawerActions');
                        const drawerFeedback = document.getElementById('drawerFeedback');
                        
                        let drawerCollapsed = false;
                        drawerHeader.addEventListener('click', () => {{
                            drawerCollapsed = !drawerCollapsed;
                            drawer.classList.toggle('collapsed', drawerCollapsed);
                            drawerToggle.textContent = drawerCollapsed ? '▲' : '▼';
                        }});
                        
                        // Movement flow state
                        let currentPath = [];
                        let isPreviewing = false;
                        let chosenDieIndex = null;
                        let waitingForTileClick = false;
                        let reachableTiles = new Set();
                        
                        function getPlayerTileId() {{
                            const p = players.find(p => p.id == PLAYER_ID);
                            return p ? p.tile_id : null;
                        }}
                        
                        function computeReachable(maxSteps) {{
                            reachableTiles = new Set();
                            const startTileId = getPlayerTileId();
                            if (!startTileId) return;
                            
                            // Build (q,r) -> tileId lookup
                            const hexLookup = {{}};
                            nodes.forEach(n => {{
                                hexLookup[n.q + ',' + n.r] = n.id;
                            }});
                            
                            // Also build id -> node lookup for q,r access
                            const nodeById = {{}};
                            nodes.forEach(n => {{ nodeById[n.id] = n; }});
                            
                            // BFS from startTileId up to maxSteps
                            const directions = [[1,0],[1,-1],[0,-1],[-1,0],[-1,1],[0,1]];
                            let frontier = [startTileId];
                            const visited = new Set([startTileId]);
                            
                            for (let step = 0; step < maxSteps; step++) {{
                                const nextFrontier = [];
                                for (const tileId of frontier) {{
                                    const node = nodeById[tileId];
                                    if (!node) continue;
                                    for (const [dq, dr] of directions) {{
                                        const nq = node.q + dq;
                                        const nr = node.r + dr;
                                        const neighborId = hexLookup[nq + ',' + nr];
                                        if (neighborId !== undefined && !visited.has(neighborId)) {{
                                            visited.add(neighborId);
                                            nextFrontier.push(neighborId);
                                            reachableTiles.add(neighborId);
                                        }}
                                    }}
                                }}
                                frontier = nextFrontier;
                            }}
                            draw();
                        }}
                        
                        // ========== DRAWER API ==========
                        async function fetchActions() {{
                            if (!PLAYER_ID) {{
                                drawerPhaseLabel.textContent = '⚠️ No player found';
                                return;
                            }}
                            const url = `${{PUBLIC_API_URL}}/game/${{GAME_ID}}/player/${{PLAYER_ID}}/available_actions`;
                            try {{
                                const res = await fetch(url);
                                if (res.ok) {{
                                    const data = await res.json();
                                    renderDrawer(data);
                                }} else {{
                                    drawerPhaseLabel.textContent = `⚠️ API error ${{res.status}}`;
                                }}
                            }} catch (e) {{
                                console.error('fetchActions error', e, 'URL:', url);
                                drawerPhaseLabel.textContent = '⚠️ API unreachable';
                                drawerFeedback.innerHTML = `<span style="color:#888;font-size:11px">Tried: ${{url}}</span>`;
                            }}
                        }}
                        
                        function renderDrawer(data) {{
                            const phase = data.phase || 'Unknown';
                            const isActive = data.is_active;
                            const actions = data.actions || [];
                            const ctx2 = data.context || {{}};
                            
                            drawerPhaseLabel.textContent = isActive 
                                ? `⬆ ${{phase}}` 
                                : `⏳ Waiting — ${{phase}}`;
                            
                            drawerActions.innerHTML = '';
                            
                            if (!isActive) {{
                                drawerFeedback.innerHTML = '<span style="color:#888">Waiting for your turn...</span>';
                                return;
                            }}
                            
                            // Show context info in feedback
                            if (ctx2.skip_reason) {{
                                drawerFeedback.innerHTML = `<span style="color:#ff9800">${{ctx2.skip_reason}}</span>`;
                            }} else if (ctx2.instruction) {{
                                drawerFeedback.innerHTML = `<span style="color:#aaa">${{ctx2.instruction}}</span>`;
                            }} else if (ctx2.encounter) {{
                                drawerFeedback.innerHTML = `<span style="color:#ff6f00">⚔️ ${{ctx2.encounter.mob_name}} blocks your path!</span>`;
                            }} else if (waitingForTileClick) {{
                                // Keep current feedback
                            }} else if (!drawerFeedback.innerHTML.includes('result-')) {{
                                drawerFeedback.innerHTML = '';
                            }}
                            
                            // Render action buttons
                            for (const act of actions) {{
                                const btn = document.createElement('button');
                                btn.textContent = act.label;
                                
                                // Style based on action type
                                if (act.action === 'end_turn' || act.action === 'skip_pickup' || act.action.startsWith('choose_die')) {{
                                    btn.className = 'secondary';
                                }} else if (act.action === 'quick_resolve') {{
                                    btn.className = 'combat';
                                }} else if (act.action === 'skip_turn') {{
                                    btn.className = 'danger';
                                }}
                                
                                btn.addEventListener('click', () => handleAction(act.action, ctx2));
                                drawerActions.appendChild(btn);
                            }}
                        }}
                        
                        async function handleAction(action, ctx2) {{
                            if (action === 'roll_movement') {{
                                drawerFeedback.innerHTML = '<span style="color:#aaa">Rolling...</span>';
                                try {{
                                    const res = await fetch(`${{PUBLIC_API_URL}}/game/${{GAME_ID}}/player/${{PLAYER_ID}}/roll_movement`, {{ method: 'POST' }});
                                    if (res.ok) {{
                                        const data = await res.json();
                                        const rolls = data.rolls;
                                        if (rolls.skipped) {{
                                            drawerFeedback.innerHTML = `<span style="color:#ff9800">${{rolls.message}}</span>`;
                                            setTimeout(fetchActions, 1000);
                                        }} else {{
                                            drawerFeedback.innerHTML = `🎲 Rolled: <strong>${{rolls[0]}}</strong> and <strong>${{rolls[1]}}</strong> — choose one!`;
                                            renderDrawer(data.available_actions);
                                        }}
                                    }}
                                }} catch (e) {{ console.error(e); }}
                                
                            }} else if (action === 'choose_die_0' || action === 'choose_die_1') {{
                                chosenDieIndex = action === 'choose_die_0' ? 0 : 1;
                                const dieVal = ctx2.rolls ? ctx2.rolls[chosenDieIndex] : '?';
                                waitingForTileClick = true;
                                drawerActions.innerHTML = '';
                                
                                // Compute and highlight reachable tiles
                                if (typeof dieVal === 'number') {{
                                    computeReachable(dieVal);
                                }}
                                
                                // Add cancel button
                                const cancelBtn = document.createElement('button');
                                cancelBtn.textContent = '↩ Cancel';
                                cancelBtn.className = 'secondary';
                                cancelBtn.addEventListener('click', () => {{
                                    waitingForTileClick = false;
                                    chosenDieIndex = null;
                                    currentPath = [];
                                    isPreviewing = false;
                                    reachableTiles = new Set();
                                    draw();
                                    fetchActions();
                                }});
                                drawerActions.appendChild(cancelBtn);
                                
                                drawerFeedback.innerHTML = `Using die <strong>${{dieVal}}</strong> — click a highlighted tile on the map to preview your path.`;
                                
                            }} else if (action === 'confirm_move') {{
                                drawerFeedback.innerHTML = '<span style="color:#aaa">Moving...</span>';
                                try {{
                                    const res = await fetch(`${{PUBLIC_API_URL}}/game/${{GAME_ID}}/player/${{PLAYER_ID}}/move_choice`, {{
                                        method: 'POST',
                                        headers: {{ 'Content-Type': 'application/json' }},
                                        body: JSON.stringify({{ path: currentPath }})
                                    }});
                                    if (res.ok) {{
                                        const data = await res.json();
                                        // Update player position in JS
                                        const newState = data.entity_state;
                                        if (newState && newState.PositionComponent) {{
                                            const p = players.find(p => p.id == PLAYER_ID);
                                            if (p) p.tile_id = newState.PositionComponent.currentTileId;
                                        }}
                                        currentPath = [];
                                        isPreviewing = false;
                                        waitingForTileClick = false;
                                        chosenDieIndex = null;
                                        reachableTiles = new Set();
                                        drawerFeedback.innerHTML = '<span style="color:#4CAF50">✓ Moved!</span>';
                                        draw();
                                        refreshPlayerMat();
                                        // Brief pause then show next actions
                                        setTimeout(() => renderDrawer(data.available_actions), 600);
                                    }}
                                }} catch (e) {{ console.error(e); }}
                                
                            }} else if (action === 'quick_resolve') {{
                                drawerFeedback.innerHTML = '<span style="color:#ff6f00">⚔️ Fighting...</span>';
                                drawerActions.innerHTML = '';
                                try {{
                                    const res = await fetch(`${{PUBLIC_API_URL}}/game/${{GAME_ID}}/player/${{PLAYER_ID}}/combat/quick_resolve`, {{ method: 'POST' }});
                                    if (res.ok) {{
                                        const data = await res.json();
                                        const cssClass = data.outcome === 'win' ? 'result-win' : 'result-loss';
                                        drawerFeedback.innerHTML = `<span class="${{cssClass}}">${{data.message}}</span>`;
                                        refreshPlayerMat();
                                        setTimeout(() => renderDrawer(data.available_actions), 1200);
                                    }}
                                }} catch (e) {{ console.error(e); }}
                                
                            }} else if (action.startsWith('pickup_')) {{
                                const itemId = parseInt(action.replace('pickup_', ''));
                                try {{
                                    const res = await fetch(`${{PUBLIC_API_URL}}/game/${{GAME_ID}}/player/${{PLAYER_ID}}/pickup`, {{
                                        method: 'POST',
                                        headers: {{ 'Content-Type': 'application/json' }},
                                        body: JSON.stringify({{ target_entity_id: itemId }})
                                    }});
                                    if (res.ok) {{
                                        const data = await res.json();
                                        drawerFeedback.innerHTML = `<span style="color:#4CAF50">📦 ${{data.message}}</span>`;
                                        refreshPlayerMat();
                                        setTimeout(() => renderDrawer(data.available_actions), 600);
                                    }} else {{
                                        const err = await res.json();
                                        drawerFeedback.innerHTML = `<span style="color:#e53935">${{err.detail || 'Failed to pick up'}}</span>`;
                                    }}
                                }} catch (e) {{ console.error(e); }}
                                
                            }} else if (action === 'skip_pickup') {{
                                try {{
                                    const res = await fetch(`${{PUBLIC_API_URL}}/game/${{GAME_ID}}/player/${{PLAYER_ID}}/skip_pickup`, {{ method: 'POST' }});
                                    if (res.ok) {{
                                        const data = await res.json();
                                        renderDrawer(data.available_actions);
                                    }}
                                }} catch (e) {{ console.error(e); }}
                                
                            }} else if (action === 'skip_turn') {{
                                try {{
                                    const res = await fetch(`${{PUBLIC_API_URL}}/game/${{GAME_ID}}/player/${{PLAYER_ID}}/skip_turn`, {{ method: 'POST' }});
                                    if (res.ok) {{
                                        const data = await res.json();
                                        drawerFeedback.innerHTML = '<span style="color:#ff9800">Turn skipped.</span>';
                                        setTimeout(() => renderDrawer(data.available_actions), 600);
                                    }}
                                }} catch (e) {{ console.error(e); }}
                                
                            }} else if (action === 'end_turn') {{
                                drawerFeedback.innerHTML = '<span style="color:#aaa">Ending turn...</span>';
                                drawerActions.innerHTML = '';
                                try {{
                                    const res = await fetch(`${{PUBLIC_API_URL}}/game/${{GAME_ID}}/end_turn`, {{ method: 'POST' }});
                                    if (res.ok) {{
                                        const data = await res.json();
                                        // Switch to the new active player
                                        const newActiveId = data.game_state && data.game_state.active_player_id;
                                        if (newActiveId !== null && newActiveId !== undefined) {{
                                            PLAYER_ID = newActiveId;
                                        }}
                                        drawerFeedback.innerHTML = '<span style="color:#4CAF50">✓ Turn ended!</span>';
                                        draw();
                                        matPlayerId = PLAYER_ID;
                                        buildMatTabs();
                                        refreshPlayerMat();
                                        setTimeout(fetchActions, 600);
                                    }}
                                }} catch (e) {{ console.error(e); }}
                            }}
                        }}
                        
                        // ========== PATH PREVIEW (integrated with drawer) ==========
                        async function previewPath(targetTileId) {{
                            if (!PLAYER_ID || chosenDieIndex === null) {{
                                console.warn('previewPath skipped: PLAYER_ID=', PLAYER_ID, 'chosenDieIndex=', chosenDieIndex);
                                return;
                            }}
                            
                            const url = `${{PUBLIC_API_URL}}/game/${{GAME_ID}}/player/${{PLAYER_ID}}/preview_move`;
                            const body = {{ target_tile_id: targetTileId, chosen_index: chosenDieIndex }};
                            console.log('previewPath request:', url, body);
                            
                            try {{
                                const res = await fetch(url, {{
                                    method: 'POST',
                                    headers: {{ 'Content-Type': 'application/json' }},
                                    body: JSON.stringify(body)
                                }});
                                
                                if (res.ok) {{
                                    const data = await res.json();
                                    console.log('previewPath response:', data);
                                    currentPath = data.preview.path;
                                    isPreviewing = true;
                                    draw();
                                    
                                    // Show confirm/cancel in drawer
                                    drawerActions.innerHTML = '';
                                    const confirmBtn = document.createElement('button');
                                    confirmBtn.textContent = '✅ Confirm Move';
                                    confirmBtn.addEventListener('click', () => handleAction('confirm_move', {{}}));
                                    drawerActions.appendChild(confirmBtn);
                                    
                                    const cancelBtn = document.createElement('button');
                                    cancelBtn.textContent = '↩ Cancel';
                                    cancelBtn.className = 'secondary';
                                    cancelBtn.addEventListener('click', () => {{
                                        currentPath = [];
                                        isPreviewing = false;
                                        waitingForTileClick = false;
                                        chosenDieIndex = null;
                                        reachableTiles = new Set();
                                        draw();
                                        fetchActions();
                                    }});
                                    drawerActions.appendChild(cancelBtn);
                                    
                                    drawerFeedback.innerHTML = `Path: ${{currentPath.length}} tile(s). Click ✅ to move.`;
                                }} else {{
                                    const err = await res.json();
                                    drawerFeedback.innerHTML = `<span style="color:#e53935">${{err.detail || 'Invalid path'}}</span>`;
                                }}
                            }} catch (e) {{
                                console.error('Path preview err', e);
                            }}
                        }}

                        // ========== CANVAS EVENT HANDLERS ==========
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
                                selectedTileId = clicked.tile.id;
                                showSidePanel(clicked.tile);
                                draw();
                                
                                // If drawer is waiting for a tile click (movement), preview the path
                                if (waitingForTileClick && chosenDieIndex !== null) {{
                                    previewPath(clicked.tile.id);
                                }}
                            }} else {{
                                selectedTileId = null;
                                sidePanel.style.display = 'none';
                                draw();
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
                                
                                draw();
                                drawHexShape(ctx, hovered.x, hovered.y, hovered.hexSize + 2);
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
                        
                        // ========== PLAYER MAT ==========
                        let matPlayerId = PLAYER_ID;
                        
                        function buildMatTabs() {{
                            const container = document.getElementById('matTabs');
                            container.innerHTML = '';
                            for (const p of players) {{
                                const btn = document.createElement('button');
                                btn.textContent = p.name || `Player ${{p.id}}`;
                                if (p.id == matPlayerId) btn.className = 'active';
                                btn.addEventListener('click', () => {{
                                    matPlayerId = p.id;
                                    buildMatTabs();
                                    refreshPlayerMat();
                                }});
                                container.appendChild(btn);
                            }}
                        }}
                        
                        async function refreshPlayerMat() {{
                            if (!matPlayerId) return;
                            try {{
                                const res = await fetch(`${{PUBLIC_API_URL}}/game/${{GAME_ID}}/entity/${{matPlayerId}}`);
                                if (!res.ok) return;
                                const data = await res.json();
                                const c = data.components || {{}};
                                const name = (c.NameComponent || {{}}).displayName || `Player ${{matPlayerId}}`;
                                const stats = c.StatsComponent || {{}};
                                const hp = stats.currentHp || 0;
                                const maxHp = stats.maxHp || 1;
                                const hpPct = Math.round((hp / maxHp) * 100);
                                const hpColor = hpPct > 50 ? '#4CAF50' : hpPct > 25 ? '#ff9800' : '#e53935';
                                
                                // Equipment
                                const equip = c.EquipmentComponent || {{}};
                                const slots = [
                                    ['headEntityId', '🎩 Head'],
                                    ['bodyEntityId', '👕 Body'],
                                    ['feetEntityId', '👢 Feet'],
                                    ['weaponEntityId', '⚔️ Weapon'],
                                    ['ringEntityId', '💍 Ring']
                                ];
                                let equipHtml = '';
                                for (const [key, label] of slots) {{
                                    const itemId = equip[key];
                                    if (itemId && allEntities[String(itemId)]) {{
                                        const itemName = (allEntities[String(itemId)].NameComponent || {{}}).displayName || `Item ${{itemId}}`;
                                        equipHtml += `<div class="slot"><span class="slot-name">${{label}}:</span> <span class="slot-item">${{itemName}}</span></div>`;
                                    }} else {{
                                        equipHtml += `<div class="slot"><span class="slot-name">${{label}}:</span> <span style="color:#555">Empty</span></div>`;
                                    }}
                                }}
                                
                                // Bag
                                const inv = c.InventoryComponent || {{}};
                                const weight = inv.currentWeight || 0;
                                const maxWeight = inv.maxWeightCapacity || '?';
                                const heldIds = inv.heldEntityIds || [];
                                let bagHtml = `<div style="margin-bottom:4px">Weight: ${{weight}} / ${{maxWeight}}</div>`;
                                if (heldIds.length === 0) {{
                                    bagHtml += '<div style="color:#555">(Empty)</div>';
                                }} else {{
                                    for (const hId of heldIds) {{
                                        // Try local cache first, then fetch from API
                                        let hName = (allEntities[String(hId)] || {{}}).NameComponent;
                                        if (hName) {{
                                            bagHtml += `<div>• ${{hName.displayName}}</div>`;
                                        }} else {{
                                            // Fetch name from API for runtime-created items
                                            try {{
                                                const itemRes = await fetch(`${{PUBLIC_API_URL}}/game/${{GAME_ID}}/entity/${{hId}}`);
                                                if (itemRes.ok) {{
                                                    const itemData = await itemRes.json();
                                                    const itemName = (itemData.components.NameComponent || {{}}).displayName || `Item ${{hId}}`;
                                                    bagHtml += `<div>• ${{itemName}}</div>`;
                                                    // Cache it
                                                    allEntities[String(hId)] = itemData.components;
                                                }} else {{
                                                    bagHtml += `<div>• Item ${{hId}}</div>`;
                                                }}
                                            }} catch (e) {{
                                                bagHtml += `<div>• Item ${{hId}}</div>`;
                                            }}
                                        }}
                                    }}
                                }}
                                
                                // Dice Pool
                                const dicePool = (c.DicePoolComponent || {{}}).diceQueue || [];
                                let diceHtml = '';
                                if (dicePool.length === 0) {{
                                    diceHtml = '<div style="color:#555">(Empty)</div>';
                                }} else {{
                                    for (const d of dicePool) {{
                                        const kw = (d.keywords || []).join(', ');
                                        diceHtml += `<div>🎲 D${{d.sides}} ${{kw ? '[' + kw + ']' : ''}}</div>`;
                                    }}
                                }}
                                
                                document.getElementById('playerMat').innerHTML = `
                                    <div class="mat-section">
                                        <div class="mat-player-name">${{name}}</div>
                                        <div>❤️ ${{hp}} / ${{maxHp}}</div>
                                        <div class="hp-bar"><div class="hp-fill" style="width:${{hpPct}}%;background:${{hpColor}}"></div></div>
                                    </div>
                                    <div class="mat-section">
                                        <h4>Equipment</h4>
                                        ${{equipHtml}}
                                    </div>
                                    <div class="mat-section">
                                        <h4>Dice Pool</h4>
                                        ${{diceHtml}}
                                    </div>
                                    <div class="mat-section">
                                        <h4>Bag</h4>
                                        ${{bagHtml}}
                                    </div>
                                `;
                            }} catch (e) {{
                                console.error('refreshPlayerMat error', e);
                            }}
                        }}
                        
                        // Initialize drawer + mat on load
                        fetchActions();
                        buildMatTabs();
                        refreshPlayerMat();
                    </script>
                </body>
                </html>
                """
                
                # Render using Streamlit component
                st.markdown("### 🗺️ World Map")
                components.html(html_content, height=780)
                
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
