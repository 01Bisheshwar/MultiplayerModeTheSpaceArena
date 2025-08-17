#!/usr/bin/env python

import asyncio
import http
import signal
import websockets


async def echo(websocket):
    async for message in websocket:
        await websocket.send(message)


# Catch ALL non-WebSocket HTTP requests (Render health checks, curl, etc.)
async def process_request(path, request_headers):
    # Allow GET or HEAD on `/` or `/healthz`
    if path in ["/", "/healthz"]:
        return http.HTTPStatus.OK, [("Content-Type", "text/plain")], b"OK\n"
    # Anything else can be 404 instead of trying WebSocket handshake
    return http.HTTPStatus.NOT_FOUND, [], b"Not Found\n"


async def main():
    # Graceful shutdown on SIGTERM
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    async with websockets.serve(
        echo,
        host="0.0.0.0",
        port=8080,  # Render expects you to bind to PORT
        process_request=process_request,  # intercept health checks
    ):
        print("[SERVER] Running WebSocket+health on :8080")
        await stop


if __name__ == "__main__":
    asyncio.run(main())
