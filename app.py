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
    # Render will hit HEAD / and GET /healthz
    if path in ["/", "/healthz"]:
        return (
            http.HTTPStatus.OK,
            [("Content-Type", "text/plain")],
            b"OK\n",   # body is ignored on HEAD, safe on GET
        )
    # Fallback for everything else
    return http.HTTPStatus.NOT_FOUND, [], b"Not Found\n"


async def main():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    async with websockets.serve(
        echo,
        host="0.0.0.0",
        port=8080,  # Render sets $PORT, default 8080
        process_request=process_request,
    ):
        print("[SERVER] Running WebSocket + healthcheck on :8080")
        await stop


if __name__ == "__main__":
    asyncio.run(main())
