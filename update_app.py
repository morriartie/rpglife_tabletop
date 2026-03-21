import re

with open("test_dash/app.py", "r") as f:
    content = f.read()

new_draw_func = """
                        function drawHexagon(x, y, size, fill, stroke, lineWidth) {
                            ctx.beginPath();
                            for (let i = 0; i < 6; i++) {
                                // flat-topped hex math matches the python backend
                                const angle_deg = 60 * i;
                                const angle_rad = Math.PI / 180 * angle_deg;
                                const hx = x + size * Math.cos(angle_rad);
                                const hy = y + size * Math.sin(angle_rad);
                                if (i === 0) {
                                    ctx.moveTo(hx, hy);
                                } else {
                                    ctx.lineTo(hx, hy);
                                }
                            }
                            ctx.closePath();
                            ctx.fillStyle = fill;
                            ctx.fill();
                            ctx.lineWidth = lineWidth || 1;
                            ctx.strokeStyle = stroke;
                            ctx.stroke();
                        }
                        
                        function draw() {
                            ctx.clearRect(0, 0, width, height);
                            if (nodes.length === 0) return;
                            
                            const padding = 60;
                            const drawWidth = width - padding * 2;
                            const drawHeight = height - padding * 2;
                            
                            // hex visual size
                            const hexBaseSize = 14; 
                            const scaleX = drawWidth / (maxX - minX || 1);
                            const scaleY = drawHeight / (maxY - minY || 1);
                            // Keep aspect ratio 1:1 for hexes
                            const uniformScale = Math.min(scaleX, scaleY);
                            
                            const hexRadius = hexBaseSize * uniformScale;
                            
                            // Calculate node positions 
                            nodes.forEach((node) => {
                                const nx = (node.x - minX) / (maxX - minX);
                                const ny = (node.y - minY) / (maxY - minY);
                                const x = padding + (node.x - minX) * uniformScale + (drawWidth - (maxX - minX) * uniformScale)/2;
                                const y = padding + (node.y - minY) * uniformScale + (drawHeight - (maxY - minY) * uniformScale)/2;
                                nodePositions[node.id] = { x, y, tile: node, radius: hexRadius };
                            });
                            
                            // Draw Hexes
                            nodes.forEach(tile => {
                                const pos = nodePositions[tile.id];
                                
                                let fillStyle = '#888';
                                switch(tile.type) {
                                    case 'CITY': fillStyle = '#ffd700'; break;
                                    case 'GRASS_PATH': fillStyle = '#4caf50'; break;
                                    case 'DIRT_PATH': fillStyle = '#8d6e63'; break;
                                    case 'ROCK_PATH': fillStyle = '#9e9e9e'; break;
                                    case 'FOREST': fillStyle = '#2e7d32'; break;
                                    case 'LAKE': fillStyle = '#2196f3'; break;
                                }
                                
                                const strokeColor = tile.type === 'CITY' ? '#ff8f00' : '#222';
                                const strokeWidth = tile.type === 'CITY' ? 3 : 1;
                                
                                drawHexagon(pos.x, pos.y, pos.radius, fillStyle, strokeColor, strokeWidth);
                                
                                // Node label if city
                                if (tile.type === 'CITY') {
                                    ctx.fillStyle = '#fff';
                                    ctx.font = 'bold 12px sans-serif';
                                    ctx.textAlign = 'center';
                                    ctx.fillText(tile.name, pos.x, pos.y + pos.radius + 15);
                                }
                            });
                            
                            // Draw players near their tiles
                            players.forEach((player, idx) => {
                                const tilePos = nodePositions[player.tile_id];
                                if (tilePos) {
                                    const offsetAngle = (idx / players.length) * Math.PI * 2;
                                    const ox = Math.cos(offsetAngle) * (tilePos.radius / 2);
                                    const oy = Math.sin(offsetAngle) * (tilePos.radius / 2);
                                    
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
                                }
                            });
                        }
"""

start_str = "                        function draw() {\n"
end_str = "                        }\n                        \n                        canvas.addEventListener('mousemove', (e) => {\n"

start_idx = content.find(start_str)
end_idx = content.find(end_str)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + new_draw_func + content[end_idx:]
    with open("test_dash/app.py", "w") as f:
        f.write(new_content)
    print("Successfully replaced draw function")
else:
    print("Could not find start or end strings")

