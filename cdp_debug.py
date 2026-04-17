#!/usr/bin/env python3
"""
EntroFeed Chrome DevTools Protocol Debugger
Usage: python3 cdp_debug.py [command]

Commands:
  list          - List all targets/tabs
  console       - Stream console messages from the page
  network       - Stream network requests
  screenshot    - Take a screenshot
  eval <js>     - Execute JavaScript on the page
  navigate <url> - Navigate to a URL
"""
import asyncio
import json
import sys
import base64
from websockets.client import connect

WS_URL = "ws://localhost:9222/devtools/browser/465bac00-db4d-43c4-817b-9b207e55537a"

async def get_target_id(ws, url_contains=None):
    await ws.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
    while True:
        msg = json.loads(await ws.recv())
        if msg.get("id") == 1:
            targets = msg["result"]["targetInfos"]
            if url_contains:
                for t in targets:
                    if url_contains in t.get("url", ""):
                        return t["targetId"]
            # Return first page target
            for t in targets:
                if t["type"] == "page":
                    return t["targetId"]
            return targets[0]["targetId"] if targets else None

async def attach_to_target(ws, target_id):
    await ws.send(json.dumps({
        "id": 2, "method": "Target.attachToTarget",
        "params": {"targetId": target_id, "flatten": True}
    }))
    while True:
        msg = json.loads(await ws.recv())
        if msg.get("id") == 2:
            return msg["result"]["sessionId"]

async def send_cmd(ws, session_id, method, cmd_id, params=None):
    await ws.send(json.dumps({
        "id": cmd_id, "method": method,
        "sessionId": session_id,
        "params": params or {}
    }))

async def recv_msg(ws, session_id):
    while True:
        msg = json.loads(await ws.recv())
        if msg.get("sessionId") == session_id:
            return msg

async def list_targets():
    async with connect(WS_URL) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
        msg = json.loads(await ws.recv())
        print(json.dumps(msg["result"]["targetInfos"], indent=2))

async def console_stream(target_url=None):
    async with connect(WS_URL) as ws:
        target_id = await get_target_id(ws, target_url)
        if not target_id:
            print("No target found. Navigate to a page first.")
            return
        session_id = await attach_to_target(ws, target_id)
        await send_cmd(ws, session_id, "Runtime.enable", 3)
        await send_cmd(ws, session_id, "Log.enable", 4)
        print(f"Streaming console messages for target: {target_id} (session: {session_id})")
        print("-" * 60)
        try:
            while True:
                msg = await recv_msg(ws, session_id)
                if msg.get("method") == "Runtime.consoleAPICalled":
                    args = msg["params"].get("args", [])
                    values = [a.get("value", str(a)) for a in args]
                    print(f"[console.{msg['params']['type']}] {' '.join(values)}")
                elif msg.get("method") == "Log.entryAdded":
                    entry = msg["params"]["entry"]
                    print(f"[{entry['level']}] {entry.get('text', '')}")
        except KeyboardInterrupt:
            print("\nStopped.")

async def network_stream(target_url=None):
    async with connect(WS_URL) as ws:
        target_id = await get_target_id(ws, target_url)
        if not target_id:
            print("No target found.")
            return
        session_id = await attach_to_target(ws, target_id)
        await send_cmd(ws, session_id, "Network.enable", 3)
        await send_cmd(ws, session_id, "Page.enable", 4)
        print(f"Streaming network requests...")
        try:
            while True:
                msg = await recv_msg(ws, session_id)
                if msg.get("method") == "Network.requestWillBeSent":
                    req = msg["params"]["request"]
                    print(f"> {req['method']} {req['url'][:100]}")
                elif msg.get("method") == "Network.responseReceived":
                    resp = msg["params"]["response"]
                    print(f"< {resp['status']} {resp['url'][:100]}")
        except KeyboardInterrupt:
            print("\nStopped.")

async def screenshot(target_url=None):
    async with connect(WS_URL) as ws:
        target_id = await get_target_id(ws, target_url)
        if not target_id:
            print("No target found.")
            return
        session_id = await attach_to_target(ws, target_id)
        await send_cmd(ws, session_id, "Page.enable", 3)
        await send_cmd(ws, session_id, "Page.captureScreenshot", 4, {"format": "png"})
        msg = await recv_msg(ws, session_id)
        if "result" in msg and "data" in msg["result"]:
            with open("/tmp/cdp_screenshot.png", "wb") as f:
                f.write(base64.b64decode(msg["result"]["data"]))
            print("Screenshot saved to /tmp/cdp_screenshot.png")

async def eval_js(js, target_url=None):
    async with connect(WS_URL) as ws:
        target_id = await get_target_id(ws, target_url)
        if not target_id:
            print("No target found.")
            return
        session_id = await attach_to_target(ws, target_id)
        await send_cmd(ws, session_id, "Runtime.enable", 3)
        await send_cmd(ws, session_id, "Runtime.evaluate", 4, {"expression": js, "returnByValue": True})
        msg = await recv_msg(ws, session_id)
        result = msg.get("result", {})
        if "exceptionDetails" in result:
            print(f"Error: {result['exceptionDetails']}")
        else:
            print(json.dumps(result.get("result", {}), indent=2))

async def navigate(url):
    async with connect(WS_URL) as ws:
        target_id = await get_target_id(ws)
        if not target_id:
            print("No target found.")
            return
        session_id = await attach_to_target(ws, target_id)
        await send_cmd(ws, session_id, "Page.enable", 3)
        await send_cmd(ws, session_id, "Page.navigate", 4, {"url": url})
        print(f"Navigating to {url}...")
        # Wait for load event
        while True:
            msg = await recv_msg(ws, session_id)
            if msg.get("method") == "Page.loadEventFired":
                print("Page loaded.")
                break

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        asyncio.run(list_targets())
    elif cmd == "console":
        asyncio.run(console_stream())
    elif cmd == "network":
        asyncio.run(network_stream())
    elif cmd == "screenshot":
        asyncio.run(screenshot())
    elif cmd == "navigate":
        url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5173"
        asyncio.run(navigate(url))
    elif cmd == "eval":
        js = sys.argv[2] if len(sys.argv) > 2 else "document.title"
        asyncio.run(eval_js(js))
    else:
        print(__doc__)