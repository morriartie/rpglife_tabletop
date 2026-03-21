import re

with open("test_dash/app.py", "r") as f:
    content = f.read()

# Need to pass API_URL and GAME_ID, PLAYER_ID to JS
# Find where the JS vars are defined
js_vars_start = "                        const nodes = {json.dumps(nodes_data)};"

new_js_vars = f"""                        const API_URL = "{{API_URL}}";
                        const GAME_ID = "{{st.session_state.selected_game}}";
                        // Find a player that belongs to this session (just take the first one for testing)
                        const PLAYER_ID = players.length > 0 ? players[0].id : null;
                        
                        const nodes = {{json.dumps(nodes_data)}};"""

content = content.replace(js_vars_start, new_js_vars)


mouse_events_replacement = """                        // Selected path state
                        let currentPath = [];
                        let isPreviewing = false;
                        
                        async function previewPath(targetTileId) {
                            if (!PLAYER_ID) return;
                            
                            try {
                                const res = await fetch(`${API_URL}/game/${GAME_ID}/player/${PLAYER_ID}/preview_move`, {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        target_tile_id: targetTileId,
                                        chosen_index: 0 // testing with max distance
                                    })
                                });
                                
                                if (res.ok) {
                                    const data = await res.json();
                                    currentPath = data.path;
                                    isPreviewing = true;
                                    draw(); // redraw with path
                                }
                            } catch (e) {
                                console.error("Path preview err", e);
                            }
                        }
                        
                        async function executeMove() {
                            if (!PLAYER_ID || !isPreviewing || currentPath.length === 0) return;
                            
                            try {
                                const res = await fetch(`${API_URL}/game/${GAME_ID}/player/${PLAYER_ID}/move_choice`, {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        path: currentPath
                                    })
                                });
                                
                                if (res.ok) {
                                    currentPath = [];
                                    isPreviewing = false;
                                    // Let streamlit auto-refresh handle it later
                                }
                            } catch (e) {
                                console.error("Move error", e);
                            }
                        }

                        canvas.addEventListener('click', (e) => {
                            const rect = canvas.getBoundingClientRect();
                            const mx = e.clientX - rect.left;
                            const my = e.clientY - rect.top;
                            
                            let clicked = null;
                            for (const id in nodePositions) {
                                const pos = nodePositions[id];
                                const dist = Math.hypot(mx - pos.x, my - pos.y);
                                if (dist <= pos.radius) {
                                    clicked = pos;
                                    break;
                                }
                            }
                            
                            if (clicked) {
                                if (isPreviewing && currentPath.length > 0 && currentPath[currentPath.length - 1] === clicked.tile.id) {
                                    // Confirm move if clicked target again
                                    executeMove();
                                } else {
                                    previewPath(clicked.tile.id);
                                }
                            }
                        });

                        canvas.addEventListener('mousemove', (e) => {"""

old_mouse_start = "                        canvas.addEventListener('mousemove', (e) => {"

content = content.replace(old_mouse_start, mouse_events_replacement)

# Next, we need to inject the path drawing logic into the draw() function before the nodes are drawn
# we'll find "// Draw Hexes" and inject there

path_draw_logic = """                            // Draw Path Preview if active
                            if (isPreviewing && currentPath.length > 0) {
                                ctx.lineWidth = 10;
                                ctx.strokeStyle = 'rgba(0, 255, 255, 0.6)';
                                ctx.lineCap = 'round';
                                ctx.lineJoin = 'round';
                                ctx.beginPath();
                                
                                currentPath.forEach((nodeId, i) => {
                                    const p = nodePositions[nodeId];
                                    if (p) {
                                        if (i === 0) ctx.moveTo(p.x, p.y);
                                        else ctx.lineTo(p.x, p.y);
                                    }
                                });
                                ctx.stroke();
                            }
                            
                            // Draw Hexes"""

content = content.replace("                            // Draw Hexes", path_draw_logic)

with open("test_dash/app.py", "w") as f:
    f.write(content)
print("done")
