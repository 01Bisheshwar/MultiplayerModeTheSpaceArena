import os
import json
from aiohttp import web

players = {}      # player_id -> player data
connections = {}  # ws -> player_id

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    print(f"[SERVER] New connection: {request.remote}")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue

                event = data.get("event_type")
                player_id = data.get("player_id")

                # === CONNECT ===
                if event == "connect":
                    players[player_id] = {
                        "player_name": data.get("player_name"),
                        "position": data.get("position")
                    }
                    connections[ws] = player_id

                    # send existing players to this player
                    await ws.send_json({
                        "event_type": "all_players",
                        "all_players": [
                            {"player_id": pid, **pdata}
                            for pid, pdata in players.items() if pid != player_id
                        ]
                    })

                    # broadcast new player to others
                    new_player_msg = {
                        "event_type": "new_player",
                        "new_player": {
                            "player_id": player_id,
                            "player_name": data.get("player_name"),
                            "position": data.get("position")
                        }
                    }
                    await broadcast(new_player_msg, exclude=ws)

                # === POSITION UPDATE ===
                elif event == "update_position":
                    if player_id in players:
                        players[player_id]["position"] = data.get("position")
                        players[player_id]["gun_rotation"] = data.get("gun_rotation")
                        players[player_id]["gun_position"] = data.get("gun_position")

                    await broadcast({
                        "event_type": "update_position",
                        "player_id": player_id,
                        "position": data.get("position"),
                        "gun_rotation": data.get("gun_rotation"),
                        "gun_position": data.get("gun_position")
                    }, exclude=ws)

                # === ENEMY POSITION UPDATE ===
                elif event == "update_enemy_position":
                    await broadcast({
                        "event_type": "update_enemy_position",
                        "player_id": player_id,
                        "pushDirection": data.get("pushDirection"),
                        "pushForce": data.get("pushForce"),
                        "gun_rotation": data.get("gun_rotation"),
                        "gun_position": data.get("gun_position")
                    }, exclude=ws)

                # === DISCONNECT ===
                elif event == "disconnect":
                    if player_id in players:
                        players.pop(player_id, None)
                    await broadcast({"event_type": "player_left", "player_id": player_id}, exclude=ws)

                # === FIRE ===
                elif event == "fire":
                    await broadcast({
                        "event_type": "fire",
                        "player_id": player_id,
                        "player_fireType": data.get("player_fireType")
                    }, exclude=ws)

                # === DAMAGE ===
                elif event == "damage":
                    await broadcast({
                        "event_type": "damage",
                        "player_id": player_id,
                        "damage": data.get("player_damage")
                    }, exclude=ws)

                # === EXTERNAL MOVE ===
                elif event == "external_move":
                    target_id = data.get("target_id")
                    new_pos = data.get("position")
                    players[target_id] = new_pos
                    await broadcast({
                        "event_type": "external_move",
                        "target_id": target_id,
                        "position": new_pos
                    }, exclude=ws)

    finally:
        # cleanup on disconnect
        pid = connections.pop(ws, None)
        if pid and pid in players:
            del players[pid]
            await broadcast({"event_type": "player_left", "player_id": pid}, exclude=ws)

    return ws

async def broadcast(message, exclude=None):
    """Send JSON message to all connected players except `exclude`"""
    dead = []
    for ws in list(connections.keys()):
        if ws.closed:
            dead.append(ws)
            continue
        if ws != exclude:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"[BROADCAST ERROR] {e}")
                dead.append(ws)
    # cleanup closed connections
    for ws in dead:
        connections.pop(ws, None)

async def health(request):
    return web.Response(text="OK")

# --- MAIN APP ---
app = web.Application()
app.router.add_get("/", health)
app.router.add_get("/ws", websocket_handler)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Render gives you $PORT
    web.run_app(app, host="0.0.0.0", port=port)
