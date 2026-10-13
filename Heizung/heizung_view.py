import asyncio, json, os, time, aiohttp

DASH = "dashboard-testdashboard"
VIEW = json.load(open("/config/.heizung_view.json", encoding="utf-8"))
PATH = VIEW["path"]


async def main():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect("ws://supervisor/core/websocket", max_msg_size=0) as ws:
            await ws.receive_json()
            await ws.send_json({"type": "auth", "access_token": os.environ["T"]})
            await ws.receive_json()
            n = 0

            async def call(msg):
                nonlocal n
                n += 1
                msg["id"] = n
                await ws.send_json(msg)
                while True:
                    r = await ws.receive_json()
                    if r.get("id") == n:
                        return r

            cfg = (await call({"type": "lovelace/config", "url_path": DASH}))["result"]
            json.dump(cfg, open("/config/.testdashboard_backup_%d.json" % time.time(), "w"), ensure_ascii=False, indent=1)
            views = cfg["views"]
            idx = next((i for i, v in enumerate(views) if v.get("path") == PATH), None)
            if idx is None:
                # direkt hinter den Temperatur-Tab (Icon Thermometer)
                idx = next((i + 1 for i, v in enumerate(views) if v.get("icon") == "mdi:thermometer"), len(views))
                views.insert(idx, VIEW)
            else:
                views[idx] = VIEW
            r = await call({"type": "lovelace/config/save", "url_path": DASH, "config": cfg})
            print("save:", r.get("success"), r.get("error"))
            chk = (await call({"type": "lovelace/config", "url_path": DASH}))["result"]
            print("views:", len(chk["views"]), [v.get("path") or v.get("icon") for v in chk["views"]])


asyncio.run(main())
