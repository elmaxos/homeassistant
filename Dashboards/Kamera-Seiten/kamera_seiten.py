"""Testdashboard: Tab "Kamera" als Uebersicht + eine Unterseite (subview) pro Thingino-Kamera.
Laeuft im HA-Container: docker exec -e T=$SUPERVISOR_TOKEN homeassistant python3 kamera_seiten.py"""
import asyncio, json, os, time, aiohttp

DASH = "dashboard-testdashboard"
BASE = "/" + DASH + "/"

CAMS = [
    # key = Ziel in tts_cam_sound_text; invert: Pfeile vertauscht (Bild nicht per Flip gedreht)
    {"key": "wohnzimmer", "title": "Wohnzimmer", "icon": "mdi:sofa", "h": "ing_sonoff_pt2_3684",
     "cam": "camera.sonoff_pt2_1_profile_0", "invert": False, "presets": [(1, "mdi:numeric-1-box"), (2, "mdi:numeric-2-box"), (0, "mdi:numeric-0-box")],
     "preset_sensor": True},
    {"key": "schlafzimmer", "title": "Schlafzimmer", "icon": "mdi:bed", "h": "ing_sonoff_pt2_a574",
     "cam": "camera.sonoff_pt2_3_profile_0", "invert": True, "presets": [(1, "mdi:numeric-1-box"), (0, "mdi:incognito")],
     "preset_sensor": True, "no_white": True, "noise": True},
    {"key": "unterstand", "title": "Unterstand", "icon": "mdi:home-roof", "h": "ing_sonoff_pt2_26a4",
     "cam": "camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_1", "invert": True, "presets": [(1, "mdi:numeric-1-box"), (0, "mdi:numeric-0-box")]},
    {"key": "kamera4420", "title": "Kamera 4420", "icon": "mdi:cctv", "h": "ing_sonoff_pt2_4420",
     "cam": "camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_0_2", "invert": False, "presets": [(0, "mdi:numeric-0-box")],
     "ircut": "ir_cut_filter", "no_led": True},
]


def path(c):
    return "kamera-" + c["key"]


def press(ent):
    return {"action": "perform-action", "perform_action": "button.press", "target": {"entity_id": ent}}


def btn(icon, ent=None, name=None, tap=None, cols=3, rows=1):
    b = {"type": "button", "icon": icon, "show_name": bool(name), "show_icon": True, "grid_options": {"columns": cols, "rows": rows}}
    if name:
        b["name"] = name
    if ent:
        b["entity"] = ent
        b["show_state"] = False
    b["tap_action"] = tap or {"action": "toggle"}
    return b


def tile(ent, name, icon=None, features=None, cols=6, tap=None):
    t = {"type": "tile", "entity": ent, "name": name, "vertical": False, "grid_options": {"columns": cols},
         "tap_action": tap or {"action": "toggle"}, "icon_tap_action": tap or {"action": "toggle"}}
    if icon:
        t["icon"] = icon
    if features:
        t["features"] = features
        t["tap_action"] = {"action": "more-info"}
    return t


def nav_bar(current=None):
    cards = []
    for c in CAMS:
        on = c is current
        cards.append({"type": "button", "name": ("● " if on else "") + c["title"], "icon": c["icon"], "show_state": False,
                      "tap_action": {"action": "navigate", "navigation_path": BASE + path(c)},
                      "grid_options": {"columns": 3, "rows": 1}})
    return cards


def camera_view(c):
    h = c["h"]
    s = "switch." + h + "_"
    b = "button." + h + "_"
    lr = ("ptz_right_fast", "ptz_left_fast") if c["invert"] else ("ptz_left_fast", "ptz_right_fast")
    ud = ("ptz_down_fast", "ptz_up_fast") if c["invert"] else ("ptz_up_fast", "ptz_down_fast")
    bild = [
        {"type": "heading", "heading": c["title"], "icon": c["icon"], "heading_style": "title"},
        {"type": "picture-glance", "camera_image": c["cam"], "camera_view": "live", "fit_mode": "cover", "entities": [],
         "title": c["title"], "grid_options": {"columns": "full"}},
        # Schwenken (Richtung wie im alten Tab: bei 26a4/a574 vertauscht verdrahtet)
        btn("mdi:arrow-left-bold", tap=press(b + lr[0])),
        btn("mdi:arrow-up-bold", tap=press(b + ud[0])),
        btn("mdi:arrow-down-bold", tap=press(b + ud[1])),
        btn("mdi:arrow-right-bold", tap=press(b + lr[1])),
    ]
    pos = [{"type": "heading", "heading": "Position", "heading_style": "subtitle", "icon": "mdi:camera-marker-outline",
            "entities": ([{"entity": "sensor." + h + "_ptz_preset", "state_content": "state"}] if c.get("preset_sensor") else [])}]
    pos += [btn(icon, name="Preset %d" % n, tap=press(b + "preset_%d_load" % n)) for n, icon in c["presets"]]
    pos.append(btn("mdi:image-filter-center-focus", name="Mitte", tap=press(b + "position_reset")))
    licht = [{"type": "heading", "heading": "Licht & Bild", "heading_style": "subtitle", "icon": "mdi:lightbulb-on-outline"}]
    if not c.get("no_white"):
        licht.append(tile(s + "white_light", "Weißlicht", "mdi:light-flood-down"))
    licht += [tile(s + "ir_light_850nm", "IR-Licht", "mdi:led-outline"),
              tile(s + c.get("ircut", "ir_cut"), "IR-Filter", "mdi:camera-iris"),
              tile(s + "color_mode", "Farbe (aus = Schwarzweiß)", "mdi:invert-colors")]
    if not c.get("no_led"):
        licht.append(tile(s + "status_led", "Status-LED (blau)", "mdi:led-on"))
    licht.append(tile(s + "privacy", "Privatsphäre", "mdi:eye-off"))
    ansage = [{"type": "heading", "heading": "Ansage", "heading_style": "subtitle", "icon": "mdi:bullhorn"},
              {"type": "entities", "entities": [{"entity": "input_text.ansage_text_" + c["key"], "name": "Text"}],
               "grid_options": {"columns": 9}},
              {"type": "button", "name": "Senden", "icon": "mdi:send", "show_state": False,
               "tap_action": {"action": "perform-action", "perform_action": "script.tts_kamera_textansage",
                              "data": {"kamera": c["key"]}},
               "grid_options": {"columns": 3, "rows": 1}}]
    if c["key"] == "schlafzimmer":
        ansage.append(tile("input_boolean.baby_schlaeft", "Baby schläft (dann keine Ansage)", "mdi:baby-face-outline", cols=12))
    sections = [{"type": "grid", "cards": nav_bar(c)}, {"type": "grid", "cards": bild},
                {"type": "grid", "cards": pos + licht}, {"type": "grid", "cards": ansage}]
    if c.get("noise"):
        sections.insert(3, {"type": "grid", "cards": [
            {"type": "heading", "heading": "Rauschen", "heading_style": "subtitle", "icon": "mdi:waveform"},
            tile(s + "noise", "Rauschen", "mdi:waveform", cols=12),
            tile("number." + h + "_noise_volume", "Lautstärke", "mdi:volume-medium",
                 features=[{"type": "numeric-input", "style": "slider"}], cols=12),
            tile("select." + h + "_noise_color", "Farbe", "mdi:palette", features=[{"type": "select-options"}], cols=12),
        ]})
    return {"type": "sections", "title": c["title"], "path": path(c), "icon": c["icon"], "subview": True,
            "back_path": BASE + "kamera", "max_columns": 2, "sections": sections}


def overview(old_extra):
    tiles = [{"type": "picture-entity", "entity": c["cam"], "name": c["title"], "camera_view": "auto", "show_state": False,
              "tap_action": {"action": "navigate", "navigation_path": BASE + path(c)},
              "hold_action": {"action": "navigate", "navigation_path": BASE + path(c)},
              "grid_options": {"columns": 6}} for c in CAMS]
    secs = [{"type": "grid", "column_span": 2, "cards": [
        {"type": "heading", "heading": "Kameras", "icon": "mdi:cctv", "heading_style": "title"}] + tiles}]
    return secs + old_extra


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

            have = {x["id"] for x in (await call({"type": "input_text/list"}))["result"]}
            for c in CAMS:
                hid = "ansage_text_" + c["key"]
                if hid not in have:
                    r = await call({"type": "input_text/create", "name": hid, "max": 255, "icon": "mdi:bullhorn"})
                    print("helper", hid, r.get("success"), r.get("error"))

            cfg = (await call({"type": "lovelace/config", "url_path": DASH}))["result"]
            json.dump(cfg, open("/config/.testdashboard_backup_%d.json" % time.time(), "w"), ensure_ascii=False, indent=1)
            views = cfg["views"]
            kv = next(v for v in views if v.get("path") == "kamera")
            if "_alt_sections" not in kv:
                # beim ersten Umbau: Nicht-Thingino-Bereiche (Tapo, LSC) unveraendert behalten
                keep = [sec for sec in kv["sections"] if not any("ing_sonoff_pt2" in json.dumps(c) for c in sec.get("cards", []))]
            else:
                keep = kv["_alt_sections"]
            kv["sections"] = overview(keep)
            kv["max_columns"] = 2
            views[:] = [v for v in views if not str(v.get("path", "")).startswith("kamera-") or v.get("path") == "kameras-ptz"]
            idx = views.index(kv) + 1
            for c in reversed(CAMS):
                views.insert(idx, camera_view(c))
            r = await call({"type": "lovelace/config/save", "url_path": DASH, "config": cfg})
            print("save:", r.get("success"), r.get("error"), "| behalten:", len(keep), "alte Bereiche")
            json.dump({"overview": kv, "cams": [camera_view(c) for c in CAMS]}, open("/config/.kamera_seiten.json", "w"),
                      ensure_ascii=False, indent=1)


asyncio.run(main())
