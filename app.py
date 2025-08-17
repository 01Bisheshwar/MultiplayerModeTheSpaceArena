#!/usr/bin/env python

import asyncio
import http
import signal
import websockets


async def echo(websocket):
    async for message in websocket:
        await websocket.send(message)


# Handle non-WebSocket HTTP requests (like Render health checks)
async def process_request(path, request_headers):
    if path in ["/", "/healthz"]:
        # If it's a HEAD request, don't return a body
        if request_headers.get("Method", "GET") == "HEAD":
            return http.HTTPStatus.OK, [("Content-Type", "text/plain")], b""
        return http.HTTPStatus.OK, [("Content-Type", "text/plain")], b"OK\n"

    # Anything else → 404
    return http.HTTPStatus.NOT_FOUND, [], b"Not Found\n"


async def main():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    async with websockets.serve(
        echo,
        host="0.0.0.0",
        port=8080,  # Render assigns this
        process_request=process_request,
    ):
        print("[SERVER] Running WebSocket + healthcheck on :8080")
        await stop


if __name__ == "__main__":
    asyncio.run(main())
