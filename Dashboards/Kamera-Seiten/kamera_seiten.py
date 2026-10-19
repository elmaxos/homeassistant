"""Testdashboard: Tab "Kamera" als Uebersicht + eine Unterseite (subview) pro Thingino-Kamera.
Layout: breit = Bild ueber 2 Spalten, Steuerung rechts daneben, darunter 3 Spalten; Handy = alles untereinander.
Laeuft im HA-Container: docker exec -e T=$SUPERVISOR_TOKEN homeassistant python3 kamera_seiten.py"""
import asyncio, json, os, time, aiohttp

DASH = "dashboard-testdashboard"
BASE = "/" + DASH + "/"

CAMS = [
    # key = Ziel in tts_cam_sound_text; invert: Pfeile vertauscht (Bild nicht per Flip gedreht); sub = LD-Stream (HD/LD-Umschalter)
    {"key": "wohnzimmer", "title": "Wohnzimmer", "icon": "mdi:sofa", "h": "ing_sonoff_pt2_3684",
     "cam": "camera.sonoff_pt2_1_profile_0", "sub": "camera.sonoff_pt2_1_profile_1", "invert": False,
     "presets": [(1, "Preset 1", "mdi:numeric-1-box-outline"), (2, "Preset 2", "mdi:numeric-2-box-outline"),
                 (0, "Preset 0", "mdi:numeric-0-box-outline")], "preset_sensor": True},
    {"key": "schlafzimmer", "title": "Schlafzimmer", "icon": "mdi:bed", "h": "ing_sonoff_pt2_a574",
     "cam": "camera.sonoff_pt2_3_profile_0", "sub": "camera.sonoff_kamera_3_profile_1", "invert": True,
     "presets": [(1, "Ansicht", "mdi:eye-outline"), (0, "Privat", "mdi:incognito")], "preset_sensor": True,
     "no_white": True, "noise": True},
    {"key": "unterstand", "title": "Unterstand", "icon": "mdi:home-roof", "h": "ing_sonoff_pt2_26a4",
     "cam": "camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_1", "invert": True,   # HD-Video an der Kamera aus
     "presets": [(1, "Preset 1", "mdi:numeric-1-box-outline"), (0, "Preset 0", "mdi:numeric-0-box-outline")]},
    {"key": "kamera4420", "title": "Kamera 4420", "icon": "mdi:cctv", "h": "ing_sonoff_pt2_4420",
     "cam": "camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_0_2", "invert": False,
     "presets": [(0, "Preset 0", "mdi:numeric-0-box-outline")], "ircut": "ir_cut_filter", "no_led": True},
]


def path(c):
    return "kamera-" + c["key"]


def press(ent):
    return {"action": "perform-action", "perform_action": "button.press", "target": {"entity_id": ent}}


def arrow(icon, ent):
    return {"type": "button", "icon": icon, "show_name": False, "show_state": False, "tap_action": press(ent),
            "hold_action": press(ent), "grid_options": {"columns": 3, "rows": 1}}


def tile(ent, name, icon=None, cols=6, tap=None, features=None, hide_state=False):
    t = {"type": "tile", "entity": ent, "name": name, "vertical": False, "grid_options": {"columns": cols}}
    if icon:
        t["icon"] = icon
    if hide_state:
        t["hide_state"] = True
    if features:
        t["features"] = features
        t["features_position"] = "bottom"
        t["tap_action"] = {"action": "more-info"}
    else:
        t["tap_action"] = tap or {"action": "toggle"}
        t["icon_tap_action"] = tap or {"action": "toggle"}
    return t


def nav(current):
    # schlanke Leiste zum Wechseln; aktuelle Kamera markiert
    return [tile(c["cam"], ("● " if c is current else "") + c["title"], c["icon"], cols=3, hide_state=True,
                 tap={"action": "navigate", "navigation_path": BASE + path(c)}) for c in CAMS]


def camera_card(c):
    cams = [{"id": c["key"], "camera_entity": c["cam"], "title": c["title"], "icon": c["icon"]}]
    if c.get("sub"):
        cams[0]["dependencies"] = {"cameras": [c["key"] + "_ld"]}
        cams.append({"id": c["key"] + "_ld", "camera_entity": c["sub"], "title": c["title"] + " (LD)",
                     "capabilities": {"disable_except": ["substream"]}})
    off = {"enabled": False}
    return {
        "type": "custom:advanced-camera-card",
        "cameras": cams,
        "view": {"default": "live"},
        "live": {"zoomable": True, "draggable": False, "lazy_unload": ["hidden"],
                 "controls": {"ptz": {"mode": "off"}, "next_previous": {"style": "none"}, "thumbnails": {"mode": "none"}}},
        # Menue UEBER dem Bild (outside): verdeckt nichts, kein versehentliches Antippen beim Einblenden
        "menu": {"style": "outside", "position": "top", "alignment": "right",
                 "buttons": {"iris": off, "cameras": off, "live": off, "image": off, "timeline": off, "media_player": off,
                             "expand": off, "display_mode": off, "ptz_controls": off, "ptz_home": off, "microphone": off,
                             "substreams": {"enabled": True, "icon": "mdi:high-definition-box"},
                             "fullscreen": {"enabled": True}, "screenshot": {"enabled": True}}},
        "status_bar": {"style": "none"},   # keine Infozeile im Bild
        "dimensions": {"aspect_ratio": "16:9"},
        "grid_options": {"columns": "full"},
    }


def camera_view(c):
    h = c["h"]
    s = "switch." + h + "_"
    b = "button." + h + "_"
    lr = ("ptz_right_fast", "ptz_left_fast") if c["invert"] else ("ptz_left_fast", "ptz_right_fast")
    ud = ("ptz_down_fast", "ptz_up_fast") if c["invert"] else ("ptz_up_fast", "ptz_down_fast")

    slr = ("ptz_right", "ptz_left") if c["invert"] else ("ptz_left", "ptz_right")
    sud = ("ptz_down", "ptz_up") if c["invert"] else ("ptz_up", "ptz_down")

    bild = nav(c) + [camera_card(c)]       # Titel steht schon in der Kopfzeile der Unterseite

    # langsam/fein: kleine Symbole rechts in der Ueberschrift, grosse Pfeile = schnell
    fein = [{"entity": b + e, "icon": i, "show_state": False, "show_icon": True, "tap_action": press(b + e)}
            for e, i in ((slr[0], "mdi:menu-left"), (sud[0], "mdi:menu-up"), (sud[1], "mdi:menu-down"), (slr[1], "mdi:menu-right"))]
    steuerung = [{"type": "heading", "heading": "Schwenken", "heading_style": "subtitle", "icon": "mdi:pan", "entities": fein},
                 arrow("mdi:chevron-left", b + lr[0]), arrow("mdi:chevron-up", b + ud[0]),
                 arrow("mdi:chevron-down", b + ud[1]), arrow("mdi:chevron-right", b + lr[1]),
                 {"type": "heading", "heading": "Position", "heading_style": "subtitle", "icon": "mdi:camera-marker-outline",
                  "entities": ([{"entity": "sensor." + h + "_ptz_preset"}] if c.get("preset_sensor") else [])}]
    steuerung += [tile(b + "preset_%d_load" % n, name, icon, cols=6, hide_state=True, tap=press(b + "preset_%d_load" % n))
                  for n, name, icon in c["presets"]]
    steuerung.append(tile(b + "position_reset", "Mitte", "mdi:image-filter-center-focus", cols=6, hide_state=True,
                          tap=press(b + "position_reset")))

    licht = [{"type": "heading", "heading": "Licht & Bild", "heading_style": "subtitle", "icon": "mdi:lightbulb-outline"}]
    if not c.get("no_white"):
        licht.append(tile(s + "white_light", "Weißlicht", "mdi:light-flood-down"))
    licht += [tile(s + "ir_light_850nm", "IR-Licht", "mdi:led-outline"),
              tile(s + c.get("ircut", "ir_cut"), "IR-Filter", "mdi:camera-iris"),
              tile(s + "color_mode", "Farbbild", "mdi:invert-colors")]
    if not c.get("no_led"):
        licht.append(tile(s + "status_led", "Status-LED", "mdi:led-on"))
    licht.append(tile(s + "privacy", "Privat-Modus", "mdi:eye-off-outline"))

    ton = [{"type": "heading", "heading": "Ton", "heading_style": "subtitle", "icon": "mdi:volume-high"},
           tile("number." + h + "_speaker_volume", "Lautstärke (Ansagen)", "mdi:bullhorn-variant-outline", cols=12,
                features=[{"type": "numeric-input", "style": "slider"}])]
    if c.get("noise"):
        ton += [tile(s + "noise", "Rauschen", "mdi:waveform", cols=12),
                tile("number." + h + "_noise_volume", "Rauschen Lautstärke", "mdi:volume-medium", cols=12,
                     features=[{"type": "numeric-input", "style": "slider"}]),
                tile("select." + h + "_noise_color", "Rauschen Farbe", "mdi:palette-outline", cols=12,
                     features=[{"type": "select-options"}])]

    # Stream: Video/Ton je Profil (HD = profile_0/main, LD = profile_1/sub); Mikrofon = Aufnahme komplett
    def confirm(text):
        return {"action": "toggle", "confirmation": {"text": text}}
    stream = [{"type": "heading", "heading": "Stream", "heading_style": "subtitle", "icon": "mdi:video-wireless-outline"},
              tile(s + "main_stream_video", "HD Video", "mdi:video-high-definition",
                   tap=confirm("HD-Video umschalten? Der HD-Stream ist dann kurz weg bzw. bleibt schwarz.")),
              tile(s + "sub_stream_video", "LD Video", "mdi:video-outline",
                   tap=confirm("LD-Video umschalten? Der LD-Stream ist dann kurz weg bzw. bleibt schwarz.")),
              tile(s + "main_stream_audio", "HD Ton", "mdi:volume-source"),
              tile(s + "sub_stream_audio", "LD Ton", "mdi:volume-source"),
              tile(s + "mic", "Mikrofon", "mdi:microphone", cols=12,
                   # a574: laufender AAC-Encoder laesst Rauschen/Ansagen stocken -> dort bewusst aus
                   tap=confirm("Mikrofon umschalten? Bei eingeschaltetem Mikrofon kann das Rauschen stocken.")
                   if c.get("noise") else None)]

    ansage = [{"type": "heading", "heading": "Ansage", "heading_style": "subtitle", "icon": "mdi:message-text-outline"},
              {"type": "entities", "entities": [
                  {"entity": "input_text.ansage_text_" + c["key"], "name": "Text"},
                  {"type": "button", "name": "Nur an diese Kamera", "icon": "mdi:send", "action_name": "Senden",
                   "tap_action": {"action": "perform-action", "perform_action": "script.tts_kamera_textansage",
                                  "data": {"kamera": c["key"]}}}],
               "grid_options": {"columns": "full"}}]
    if c["key"] == "schlafzimmer":
        ansage.append(tile("input_boolean.baby_schlaeft", "Baby schläft (keine Ansagen)", "mdi:baby-face-outline", cols=12))

    return {"type": "sections", "title": c["title"], "path": path(c), "icon": c["icon"], "subview": True,
            "back_path": BASE + "kamera", "max_columns": 3, "dense_section_placement": True,
            "sections": [{"type": "grid", "column_span": 2, "cards": bild},
                         {"type": "grid", "cards": steuerung},
                         {"type": "grid", "cards": licht},
                         {"type": "grid", "cards": ton},
                         {"type": "grid", "cards": ansage},
                         {"type": "grid", "cards": stream}]}


def overview(old_extra):
    tiles = [{"type": "picture-entity", "entity": c["cam"], "name": c["title"], "camera_view": "auto", "show_state": False,
              "tap_action": {"action": "navigate", "navigation_path": BASE + path(c)},
              "hold_action": {"action": "navigate", "navigation_path": BASE + path(c)},
              "grid_options": {"columns": 6}} for c in CAMS]
    return [{"type": "grid", "column_span": 2, "cards": [
        {"type": "heading", "heading": "Kameras", "icon": "mdi:cctv", "heading_style": "title"}] + tiles}] + old_extra


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
            keep = [sec for sec in kv["sections"] if not any("ing_sonoff_pt2" in json.dumps(c) or "Kameras" == c.get("heading")
                                                             for c in sec.get("cards", []))]
            kv["sections"] = overview(keep)
            kv["max_columns"] = 2
            views[:] = [v for v in views if not (str(v.get("path", "")).startswith("kamera-"))]
            idx = views.index(kv) + 1
            for c in reversed(CAMS):
                views.insert(idx, camera_view(c))
            r = await call({"type": "lovelace/config/save", "url_path": DASH, "config": cfg})
            print("save:", r.get("success"), r.get("error"), "| behalten:", len(keep), "alte Bereiche")
            json.dump({"overview": kv, "cams": [camera_view(c) for c in CAMS]}, open("/config/.kamera_seiten.json", "w"),
                      ensure_ascii=False, indent=1)


asyncio.run(main())
