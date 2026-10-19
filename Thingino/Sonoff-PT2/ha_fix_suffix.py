"""Nach dem Update einer Kamera mit alter Discovery: Entitaeten mit Endung _2 auf den alten Namen zuruecksetzen.

Hintergrund: Die aktuelle Discovery nutzt teils neue unique_ids (z. B. light_white statt white_light). Die neuen
Entitaeten entstehen, bevor die alten Topics entfernt werden, daher haengt HA "_2" an - Dashboards und
Automationen zeigen aber auf den alten Namen. Umbenannt wird nur, wenn der alte Name frei ist.

Laeuft im HA-Container (install.ps1 macht das automatisch, wenn -HaHost erreichbar ist):
  docker exec -e T=$SUPERVISOR_TOKEN homeassistant python3 ha_fix_suffix.py <kamera-hostname> [apply]
"""
import asyncio, os, sys, aiohttp

HOST = sys.argv[1].replace("-", "_") if len(sys.argv) > 1 else "ing_sonoff_pt2"
APPLY = "apply" in sys.argv


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

            reg = (await call({"type": "config/entity_registry/list"}))["result"]
            ids = {e["entity_id"] for e in reg}
            found = 0
            for e in reg:
                i = e["entity_id"]
                if e.get("platform") != "mqtt" or HOST not in i or not i.endswith("_2"):
                    continue
                found += 1
                base = i[:-2]
                if base in ids:
                    print("  %s: %s ist noch belegt - nicht umbenannt" % (i, base))
                    continue
                if APPLY:
                    r = await call({"type": "config/entity_registry/update", "entity_id": i, "new_entity_id": base})
                    print("  %s -> %s: %s" % (i, base, "ok" if r.get("success") else r.get("error")))
                else:
                    print("  %s -> %s (Probelauf)" % (i, base))
            print("Entitaeten mit _2 fuer %s: %d" % (HOST, found))


asyncio.run(main())
