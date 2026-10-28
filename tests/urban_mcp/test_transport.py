"""Exercise legacy HTTP session teardown through the public ASGI interface."""

import logging

import anyio
import httpx
import pytest
from fastmcp import FastMCP
from mcp.server.streamable_http import GET_STREAM_KEY, StreamableHTTPServerTransport
from starlette.requests import Request


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_session_termination_before_sse_read_checkpoint_is_not_an_error(caplog):
    """Characterize the SDK race: terminate after GET setup, before its first read."""
    caplog.set_level(logging.ERROR, logger="mcp.server.streamable_http")
    transport = StreamableHTTPServerTransport(mcp_session_id="shutdown-race")
    started = anyio.Event()
    finished = anyio.Event()
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "headers": [
            (b"accept", b"text/event-stream"),
            (b"mcp-session-id", b"shutdown-race"),
            (b"mcp-protocol-version", b"2025-03-26"),
        ],
    }

    async def receive():
        await anyio.sleep_forever()

    async def send(message):
        if message["type"] == "http.response.start":
            assert message["status"] == 200
            started.set()

    async def serve_get():
        await transport._handle_get_request(Request(scope, receive), send)
        finished.set()

    with anyio.fail_after(5):
        async with anyio.create_task_group() as tasks:
            async with transport.connect():
                tasks.start_soon(serve_get)
                await started.wait()
                while GET_STREAM_KEY not in transport._request_streams:
                    await anyio.lowlevel.checkpoint()
                await transport.terminate()
                await finished.wait()

    assert not caplog.records


@pytest.mark.anyio
@pytest.mark.parametrize("session_count", [1, 6])
async def test_terminating_sessions_finishes_standalone_sse_without_errors(caplog, session_count):
    caplog.set_level(logging.ERROR)
    app = FastMCP("shutdown regression").http_app(path="/")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            with anyio.fail_after(10):
                async with anyio.create_task_group() as tasks:
                    for index in range(session_count):
                        headers = {"Accept": "application/json, text/event-stream"}
                        initialized = await client.post(
                            "/",
                            headers=headers,
                            json={
                                "jsonrpc": "2.0",
                                "id": index,
                                "method": "initialize",
                                "params": {
                                    "protocolVersion": "2025-03-26",
                                    "capabilities": {},
                                    "clientInfo": {"name": "shutdown-test", "version": "1"},
                                },
                            },
                        )
                        assert initialized.status_code == 200
                        session_id = initialized.headers["mcp-session-id"]
                        headers.update({"mcp-session-id": session_id, "mcp-protocol-version": "2025-03-26"})
                        notified = await client.post(
                            "/",
                            headers=headers,
                            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                        )
                        assert notified.status_code == 202
                        started = anyio.Event()
                        finished = anyio.Event()
                        scope = {
                            "type": "http",
                            "asgi": {"version": "3.0"},
                            "http_version": "1.1",
                            "scheme": "http",
                            "method": "GET",
                            "path": "/",
                            "raw_path": b"/",
                            "query_string": b"",
                            "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
                            "server": ("testserver", 80),
                            "client": ("127.0.0.1", 1234),
                        }
                        request_received = False

                        async def receive():
                            nonlocal request_received
                            if not request_received:
                                request_received = True
                                return {"type": "http.request", "body": b"", "more_body": False}
                            await anyio.sleep_forever()

                        async def send(message):
                            if message["type"] == "http.response.start":
                                assert message["status"] == 200
                                started.set()

                        async def serve_get():
                            await app(scope, receive, send)
                            finished.set()

                        tasks.start_soon(serve_get)
                        await started.wait()
                        await anyio.lowlevel.checkpoint()
                        deleted = await client.delete("/", headers=headers)
                        assert deleted.status_code == 200
                        await finished.wait()
                        assert (await client.delete("/", headers=headers)).status_code == 404

    assert not caplog.records
