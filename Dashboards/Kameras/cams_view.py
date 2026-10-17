import asyncio, json, os, time, aiohttp

DASH = "dashboard-testdashboard"
OLD_PATH = "schlafzimmer-kamera"
PATH = "kameras-ptz"

# Thingino-Kameras. invert=True: Bild nicht gedreht (flip aus) -> Pfeile vertauscht verdrahtet,
# wie im bestehenden Tab "Kamera" fuer 26a4/a574; bei 3684/4420 ist das Bild per flip um 180 Grad gedreht.
CAMS = [
    {"id": "wohnzimmer", "host": "ing_sonoff_pt2_3684", "title": "Wohnzimmer", "icon": "mdi:sofa",
     # Live standardmaessig Hauptstream (1080p), kleiner Substream ueber das Substream-Symbol im Menue
     "entity": "camera.sonoff_pt2_1_profile_0", "sub": "camera.sonoff_pt2_1_profile_1", "invert": False,
     "presets": [("Preset 1", 1), ("Preset 2", 2), ("Preset 0", 0)]},
    {"id": "schlafzimmer", "host": "ing_sonoff_pt2_a574", "title": "Schlafzimmer", "icon": "mdi:bed",
     "entity": "camera.sonoff_pt2_3_profile_0", "sub": "camera.sonoff_kamera_3_profile_1", "invert": True,
     "noise": True, "no_white_light": True,   # Flutlicht im Schlafzimmer nicht versehentlich einschalten
     "presets": [("Ansicht 1", 1), ("Privat", 0)]},
    {"id": "unterstand", "host": "ing_sonoff_pt2_26a4", "title": "Unterstand", "icon": "mdi:home-roof",
     # Hauptstream-Video ist an dieser Kamera aus -> Substream (profile_1)
     "entity": "camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_1", "invert": True,
     "presets": [("Preset 1", 1), ("Preset 0", 0)]},
    {"id": "kamera4420", "host": "ing_sonoff_pt2_4420", "title": "Kamera 4420", "icon": "mdi:cctv",
     "entity": "camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_0_2", "invert": False,
     "ircut": "switch.ing_sonoff_pt2_4420_ir_cut_filter", "no_status_led": True,
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
        **({"dependencies": {"cameras": [c["id"] + "_sub"]}} if c.get("sub") else {}),
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


def sub_camera(c):
    # nur als Substream sichtbar, nicht in der Kameraliste
    return {"id": c["id"] + "_sub", "camera_entity": c["sub"], "title": c["title"] + " (klein)",
            "capabilities": {"disable_except": ["substream"]}}


def noise_menu(h):
    # Rauschen: Ein/Aus, Farbe (aus select-Entity), Lautstaerke in Stufen
    vol = "number.%s_noise_volume" % h
    return [
        state_icon("switch.%s_noise" % h, "mdi:waveform", "Rauschen"),
        {"type": "custom:advanced-camera-card-menu-submenu-select", "entity": "select.%s_noise_color" % h,
         "icon": "mdi:palette", "title": "Rauschen Farbe"},
        {"type": "custom:advanced-camera-card-menu-submenu", "icon": "mdi:volume-medium", "title": "Rauschen Lautstaerke",
         "items": [{"title": "Lautstaerke %d" % v, "icon": "mdi:volume-low" if v <= 30 else ("mdi:volume-medium" if v <= 60 else "mdi:volume-high"),
                    "tap_action": {"action": "perform-action", "perform_action": "number.set_value",
                                   "target": {"entity_id": vol}, "data": {"value": v}}}
                   for v in (10, 20, 30, 40, 50, 60, 70, 80)]},
    ]


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
        "elements": ([] if c.get("no_white_light") else [
            state_icon("switch.%s_white_light" % h, "mdi:light-flood-down", "Weisslicht"),
        ]) + [
            state_icon("switch.%s_ir_light_850nm" % h, "mdi:led-outline", "IR-Licht"),
            state_icon("switch.%s_privacy" % h, "mdi:eye-off", "Privatsphaere"),
            state_icon(c.get("ircut", "switch.%s_ir_cut" % h), "mdi:camera-iris", "IR-Filter"),
            state_icon("switch.%s_color_mode" % h, "mdi:invert-colors", "Farbe / Schwarzweiss"),
        ] + (noise_menu(h) if c.get("noise") else []) + [
        ] + ([] if c.get("no_status_led") else [
            state_icon("switch.%s_status_led" % h, "mdi:led-on", "Status-LED (blau)"),
        ]) + [
        ],
    })

CARD = {
    "type": "custom:advanced-camera-card",
    "cameras": [camera(c) for c in CAMS] + [sub_camera(c) for c in CAMS if c.get("sub")],
    "view": {"default": "live"},
    "live": {
        "zoomable": True,
        "draggable": False,
        "preload": False,
        # nur die sichtbare Kamera streamt
        "lazy_unload": ["unselected", "hidden"],
        "display": {"mode": "single"},
        # Bedienelemente aufgeraeumt: PTZ standardmaessig aus (Knopf im Menue); Wechsel-Pfeile links/rechts im Bild
        "controls": {"ptz": {"mode": "off", "position": "bottom-right", "orientation": "horizontal"},
                     "next_previous": {"style": "chevrons"}},
    },
    # Menue nur bei Maus ueber dem Bild bzw. nach Antippen
    "menu": {"style": "hover", "position": "top", "alignment": "right",
             "buttons": {"ptz_controls": {"enabled": True}}},
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
