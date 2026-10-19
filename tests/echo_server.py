"""Synthetic technical HTTP/WebSocket echo; never deployed as product behavior."""

from __future__ import annotations

import asyncio
import os

from aiohttp import WSMsgType, web

name = os.environ["FIXTURE_NAME"]
failed_posts = 0
slow_requests = 0


async def handle(request: web.Request) -> web.StreamResponse:
    global failed_posts, slow_requests
    if request.path == "/ws":
        socket = web.WebSocketResponse(heartbeat=2)
        await socket.prepare(request)
        async for message in socket:
            if message.type == WSMsgType.TEXT:
                await socket.send_json({"fixture": name, "echo": message.data})
            elif message.type == WSMsgType.BINARY:
                await socket.send_bytes(message.data)
        return socket
    if request.path == "/slow":
        slow_requests += 1
        await asyncio.sleep(1.0)
    if request.path == "/count":
        return web.json_response(
            {
                "fixture": name,
                "failed_posts": failed_posts,
                "slow_requests": slow_requests,
            }
        )
    if request.method == "POST" and request.path == "/fail":
        failed_posts += 1
        return web.json_response({"fixture": name}, status=503)
    body = await request.read()
    return web.json_response(
        {
            "fixture": name,
            "method": request.method,
            "path": request.path,
            "host": request.host,
            "body_size": len(body),
            "authorization": request.headers.get("Authorization"),
            "client_id": request.headers.get("X-Request-Id"),
            "forwarded_host": request.headers.get("X-Forwarded-Host"),
            "forwarded_proto": request.headers.get("X-Forwarded-Proto"),
            "forwarded_for": request.headers.get("X-Forwarded-For"),
        }
    )


application = web.Application(client_max_size=2 * 1024 * 1024)
application.router.add_route("*", "/{path:.*}", handle)
web.run_app(application, host="0.0.0.0", port=8080, access_log=None, print=None)
