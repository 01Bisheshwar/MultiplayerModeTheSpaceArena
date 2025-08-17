import asyncio
import websockets
import json
from aiohttp import web   # lightweight HTTP server for health check

players = {}  # player_id: position
connections = {}  # websocket: player_id

async def handler(websocket):
    print(f"[SERVER] New connection: {websocket.remote_address}")

    try:
        async for message in websocket:
            print(f"[SERVER] Received: {message}")
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            event = data.get("event_type")
            player_name = data.get("player_name")
            player_id = data.get("player_id")
            player_fireType = data.get("player_fireType")
            player_damage = data.get("player_damage")
            position = data.get("position")
            gun_rotation = data.get('gun_rotation')
            gun_position = data.get('gun_position')
            pushDirection = data.get('pushDirection')
            pushForce = data.get('pushForce')

            if event == "connect":
                players[player_id] = {
                    "player_name": player_name,
                    "position": position
                }
                connections[websocket] = player_id
                print(connections)
                print(players)

                # Send existing players to new player
                print(websocket)
                await websocket.send(json.dumps({
                    "event_type": "all_players",
                    "all_players": [
                        {
                            "player_id": pid,
                            "player_name": pdata["player_name"],
                            "position": pdata["position"]
                        }
                        for pid, pdata in players.items() if pid != player_id
                    ]
                }))

                # Inform others of new player
                new_player_msg = json.dumps({
                    "event_type": "new_player",
                    "new_player": {
                        "player_id": player_id,
                        "player_name": player_name,
                        "position": position
                    }
                })

                for ws in connections:
                    print("Checking:", ws, "Closed:", ws.state)
                    if ws != websocket and ws.state==1:
                        try:
                            await ws.send(new_player_msg)
                            print(f"Successfully sent to {connections[ws]}")
                        except Exception as e:
                            print(f"Failed to send to {connections[ws]}: {str(e)}")



                # await asyncio.gather(*[
                #     ws.send(new_player_msg)
                #     for ws in connections if ws != websocket and not ws.close
                # ])

            elif event == "update_position":
                if player_id in players:
                    players[player_id]["position"] = position  # update only the position
                    players[player_id]['gun_rotation'] = gun_rotation
                    players[player_id]['gun_position'] = gun_position

                msg = json.dumps({
                    "event_type": "update_position",
                    "player_id": player_id,
                    "position": position,
                    "gun_rotation": gun_rotation,
                    "gun_position": gun_position
                })

                for ws in connections:
                    if ws != websocket and ws.state==1:
                        try:
                            await ws.send(msg)
                            print(f"Successfully sent to {connections[ws]}")
                        except Exception as e:
                            print(f"Failed to send to {connections[ws]}: {str(e)}")

                # await asyncio.gather(*[
                #     ws.send(msg)
                #     for ws in connections if ws.state==1
                # ])

            elif event == "update_enemy_position":
                if player_id in players:
                    players[player_id]["position"] = position
                    players[player_id]['gun_rotation'] = gun_rotation
                    players[player_id]['gun_position'] = gun_position

                msg = json.dumps({
                    "event_type": "update_enemy_position",
                    "player_id": player_id,
                    "pushDirection": pushDirection,
                    "pushForce": pushForce,
                    "gun_rotation": gun_rotation,
                    "gun_position": gun_position
                })

                for ws in connections:
                    if ws != websocket and ws.state==1:
                        try:
                            await ws.send(msg)
                            print(f"Successfully sent to {connections[ws]}")
                        except Exception as e:
                            print(f"Failed to send to {connections[ws]}: {str(e)}")

                # await asyncio.gather(*[
                #     ws.send(msg)
                #     for ws in connections if ws.state==1
                # ])

            elif event == "disconnect":
                if player_id in players:
                    del players[player_id]

                
                disconnect_msg = json.dumps({
                    "disconnected_player": player_id
                })

                await asyncio.gather(*[
                    ws.send(disconnect_msg)
                    for ws in connections if ws != websocket and ws.state==1
                ])

            # Fire Event
            elif event == "fire":
                if player_id in players:
                    players[player_id]["fire"] = player_fireType

                msg = json.dumps({
                    "event_type": "fire",
                    "player_id": player_id,
                    "player_fireType": player_fireType
                })

                for ws in connections:
                    if ws != websocket and ws.state==1:
                        try:
                            await ws.send(msg)
                            print(f"Successfully sent to {connections[ws]}")
                        except Exception as e:
                            print(f"Failed to send to {connections[ws]}: {str(e)}")

            # Damage
            elif event == "damage":
                msg = json.dumps({
                    "event_type": "damage",
                    "player_id": player_id,
                    "damage": player_damage
                })

                for ws in connections:
                    if ws != websocket and ws.state==1:
                        try:
                            await ws.send(msg)
                            print(f"Successfully sent to {connections[ws]}")
                        except Exception as e:
                            print(f"Failed to send to {connections[ws]}: {str(e)}")
            
            elif data["event_type"] == "external_move":
                target_id = data["target_id"]
                new_pos = data["position"]

                # Update the server's record of target player position
                players[target_id] = new_pos

                # Broadcast the new position to everyone
                response = {
                    "event_type": "external_move",
                    "target_id": target_id,
                    "position": new_pos
                }
                for ws in connections:
                    if ws.state == 1 and ws != websocket:
                        try:
                            await ws.send(json.dumps(response))
                            print(f"[EXTERNAL_MOVE] Sent to {connections[ws]}")
                        except Exception as e:
                            print(f"[EXTERNAL_MOVE ERROR] Failed to send to {connections[ws]}: {str(e)}")



    except websockets.exceptions.ConnectionClosed:
        print(f"[SERVER] Connection closed: {websocket.remote_address}")
    finally:
        pid = connections.pop(websocket, None)
        if pid and pid in players:
            del players[pid]

            # Notify others
            msg = json.dumps({
                "event_type": "player_left",
                "player_id": pid
            })

            await asyncio.gather(*[
                ws.send(msg)
                for ws in connections if ws.state==1
            ])

async def main():
    # Start WebSocket server
    ws_server = await websockets.serve(handler, "0.0.0.0", 8765)
    print("[SERVER] WebSocket running on ws://0.0.0.0:8765")

    # HTTP health check
    async def health(request):
        return web.Response(text="OK")

    app = web.Application()
    app.add_routes([web.get("/", health), web.head("/", health)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)  # HTTP health check port
    await site.start()
    print("[SERVER] Health check HTTP running on :10000")

    # Keep running forever
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())


