import asyncio
import json
import sys
import websockets

URL = sys.argv[1]  # ws://127.0.0.1:8000/ws/cases/YOUR_CASE?token=JWT

async def main():
    async with websockets.connect(URL) as ws:
        print(await ws.recv())
        await ws.send(json.dumps({"type": "ping"}))
        print(await ws.recv())
        await ws.send(json.dumps({"type": "chat", "message_text": "hi", "sender_role": "owner", "invite_sent": False, "run_ai": False}))

asyncio.run(main())