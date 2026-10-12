import asyncio, json, os, time, aiohttp

DASH = "dashboard-testdashboard"
OLD_PATH = "schlafzimmer-kamera"
PATH = "kameras-ptz"

# Thingino-Kameras. invert=True: Bild nicht gedreht (flip aus) -> Pfeile vertauscht verdrahtet,
# wie im bestehenden Tab "Kamera" fuer 26a4/a574; bei 3684/4420 ist das Bild per flip um 180 Grad gedreht.
CAMS = [
    {"id": "unterstand", "host": "ing_sonoff_pt2_3684", "title": "Unterstand", "icon": "mdi:home-roof",
     "entity": "camera.sonoff_pt2_1_profile_0", "invert": False,
     "presets": [("Preset 1", 1), ("Preset 2", 2), ("Preset 0", 0)]},
    {"id": "schlafzimmer", "host": "ing_sonoff_pt2_a574", "title": "Schlafzimmer", "icon": "mdi:bed",
     "entity": "camera.sonoff_pt2_3_profile_0", "invert": True,
     "presets": [("Ansicht 1", 1), ("Privat", 0)]},
    {"id": "pt2_26a4", "host": "ing_sonoff_pt2_26a4", "title": "PT2 2 (26a4)", "icon": "mdi:cctv",
     "entity": "camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_0", "invert": True,
     "presets": [("Preset 1", 1), ("Preset 0", 0)]},
    {"id": "kamera4420", "host": "ing_sonoff_pt2_4420", "title": "Kamera 4420", "icon": "mdi:cctv",
     "entity": "camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_0_2", "invert": False,
     "presets": [("Preset 0", 0), ("Preset 1", 1)]},
]


def press(host, b):
    return {"action": "perform-action", "perform_action": "button.press",
            "target": {"entity_id": "button.%s_%s" % (host, b)}}


def dzoom(direction, phase):
    return {"action": "custom:advanced-camera-card-action", "advanced_camera_card_action": "ptz_digital",
            "ptz_action": direction, "ptz_phase": phase}


def camera(c):
    h = c["host"]
    lr = ("ptz_right_fast", "ptz_left_fast") if c["invert"] else ("ptz_left_fast", "ptz_right_fast")
    ud = ("ptz_down_fast", "ptz_up_fast") if c["invert"] else ("ptz_up_fast", "ptz_down_fast")
    return {
        "id": c["id"],
        "camera_entity": c["entity"],
        "title": c["title"],
        "icon": c["icon"],
        "ptz": {
            "r2c_delay_between_calls_seconds": 0.4,
            "actions_left": press(h, lr[0]),
            "actions_right": press(h, lr[1]),
            "actions_up": press(h, ud[0]),
            "actions_down": press(h, ud[1]),
            "presets": {name: press(h, "preset_%d_load" % n) for name, n in c["presets"]},
        },
    }


def state_icon(entity, icon, title):
    return {"type": "custom:advanced-camera-card-menu-state-icon", "entity": entity, "icon": icon,
            "title": title, "tap_action": {"action": "toggle"}}


ELEMENTS = [
    # Kamera hat keinen optischen Zoom -> eigene Menue-Tasten fuer digitalen Zoom (gedrueckt halten)
    {"type": "custom:advanced-camera-card-menu-icon", "icon": "mdi:magnify-plus-outline", "title": "Zoom +",
     "start_tap_action": dzoom("zoom_in", "start"), "end_tap_action": dzoom("zoom_in", "stop")},
    {"type": "custom:advanced-camera-card-menu-icon", "icon": "mdi:magnify-minus-outline", "title": "Zoom -",
     "start_tap_action": dzoom("zoom_out", "start"), "end_tap_action": dzoom("zoom_out", "stop")},
    {"type": "custom:advanced-camera-card-menu-icon", "icon": "mdi:magnify-close", "title": "Zoom zuruecksetzen",
     "tap_action": {"action": "custom:advanced-camera-card-action", "advanced_camera_card_action": "ptz_digital",
                    "absolute": {"zoom": 1, "pan": {"x": 50, "y": 50}}}},
]
# Licht/Privatsphaere nur fuer die gerade gewaehlte Kamera im Overlay-Menue
for c in CAMS:
    h = c["host"]
    ELEMENTS.append({
        "type": "custom:advanced-camera-card-conditional",
        "conditions": [{"condition": "camera", "cameras": [c["id"]]}],
        "elements": [
            state_icon("switch.%s_white_light" % h, "mdi:light-flood-down", "Weisslicht"),
            state_icon("switch.%s_ir_light_850nm" % h, "mdi:led-outline", "IR-Licht"),
            state_icon("switch.%s_privacy" % h, "mdi:eye-off", "Privatsphaere"),
        ],
    })

CARD = {
    "type": "custom:advanced-camera-card",
    "cameras": [camera(c) for c in CAMS],
    "view": {"default": "live"},
    "live": {
        "zoomable": True,
        "draggable": False,
        "preload": False,
        # nur die sichtbare Kamera streamt
        "lazy_unload": ["unselected", "hidden"],
        "display": {"mode": "single"},
        "controls": {"ptz": {"mode": "on", "position": "bottom-right", "orientation": "horizontal"}},
    },
    "menu": {"style": "overlay", "position": "top", "alignment": "right"},
    "elements": ELEMENTS,
    "dimensions": {"aspect_ratio": "16:9"},
    "grid_options": {"columns": "full"},
}

VIEW = {
    "type": "sections",
    "title": "Kameras",
    "path": PATH,
    "icon": "mdi:cctv",
    "max_columns": 4,
    "sections": [{"type": "grid", "column_span": 4, "cards": [CARD]}],
}


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
            idx = next((i for i, v in enumerate(views) if v.get("path") in (OLD_PATH, PATH)), None)
            if idx is None:
                idx = next((i + 1 for i, v in enumerate(views) if v.get("path") == "kamera"), len(views))
                views.insert(idx, VIEW)
            else:
                views[idx] = VIEW
            cfg["views"] = [v for i, v in enumerate(views) if i == idx or v.get("path") not in (OLD_PATH, PATH)]
            r = await call({"type": "lovelace/config/save", "url_path": DASH, "config": cfg})
            print("save:", r.get("success"), r.get("error"))
            chk = (await call({"type": "lovelace/config", "url_path": DASH}))["result"]
            print("views:", len(chk["views"]), [v.get("path") or v.get("title") for v in chk["views"]])
            json.dump(VIEW, open("/config/.cams_view.json", "w"), ensure_ascii=False, indent=2)


asyncio.run(main())
