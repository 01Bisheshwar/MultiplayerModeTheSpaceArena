import os
from aiohttp import web

PORT = int(os.environ.get("PORT", 5000))

async def handle_root(request):
    return web.Response(text="aiohttp WebSocket server is running!")

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            print(f"Received: {msg.data}")
            await ws.send_str(f"Echo: {msg.data}")
        elif msg.type == web.WSMsgType.ERROR:
            print(f"WebSocket closed with exception {ws.exception()}")

    print("WebSocket connection closed")
    return ws

app = web.Application()
app.router.add_get("/", handle_root)
app.router.add_get("/ws", websocket_handler)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
