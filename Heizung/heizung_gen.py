"""Erzeugt Raum-Overlays (PNG) je Heizstufe aus den Grundriss-Bildern, das HA-Package und die Dashboard-Ansicht."""
import json, os
from collections import deque
from PIL import Image

OUT = "heizung_out"
os.makedirs(OUT + "/www", exist_ok=True)

PLANS = {
    "eg": {"file": "plan_eg.png", "title": "burlafingen2.png", "media": "c6418232873ff0dd1596abffac70aab7"},
    "og": {"file": "plan_og.png", "title": "burlafingen3OG.png", "media": "970f46084326b2c5e558adef1cf0cb81"},
}
# Raum -> (Plan, Saatpunkt in Pixeln im Raum, Klima-Entity, Anzeigename)
ROOMS = {
    "wz": ("eg", (108, 256), "climate.wz_son_thermostat", "Wohnzimmer"),
    "ez": ("eg", (188, 256), "climate.ez_son_thermostat", "Esszimmer"),
    "bd": ("eg", (185, 97), "climate.bd_son_heizung", "Bad"),
    "az": ("og", (140, 222), "climate.az_son_heizung", "Arbeitszimmer"),
    "sz": ("og", (190, 125), "climate.sz_son_thermostat", "Schlafzimmer"),
}
STATES = {  # Stufe -> RGBA der Raumflaeche
    "offline": (90, 90, 90, 130),
    "aus": (150, 150, 150, 80),
    "bereit": (60, 130, 235, 130),
    "leicht": (255, 190, 70, 120),
    "mittel": (255, 130, 30, 150),
    "stark": (230, 50, 20, 170),
}
VERSION = "1"


def is_floor(p):
    r, g, b, a = p
    return a > 200 and abs(r - 241) <= 6 and abs(g - 216) <= 6 and abs(b - 176) <= 8


geo = {}
images = {k: Image.open(v["file"]).convert("RGBA") for k, v in PLANS.items()}
for room, (plan, seed, climate, name) in ROOMS.items():
    im = images[plan]; W, H = im.size; px = im.load()
    assert is_floor(px[seed]), (room, px[seed])
    seen = {seed}; q = deque([seed])
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= n[0] < W and 0 <= n[1] < H and n not in seen and is_floor(px[n]):
                seen.add(n); q.append(n)
    xs = [p[0] for p in seen]; ys = [p[1] for p in seen]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    w, h = x1 - x0 + 1, y1 - y0 + 1
    for st, rgba in STATES.items():
        ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for (x, y) in seen:
            ov.putpixel((x - x0, y - y0), rgba)
        ov.save("%s/www/%s_%s.png" % (OUT, room, st))
    cx = sum(xs) / len(xs); cy = sum(ys) / len(ys)
    geo[room] = {
        "plan": plan, "climate": climate, "name": name, "pixels": len(seen),
        "left": round(100 * (x0 + w / 2) / W, 2), "top": round(100 * (y0 + h / 2) / H, 2),
        "width": round(100 * w / W, 2),
        "label_left": round(100 * cx / W, 2), "label_top": round(100 * cy / H, 2),
    }
    print(room, name, geo[room])

# ---------- HA-Package ----------
pkg = ["# Heizungs-Anzeige auf dem Grundriss (Testdashboard, Tab Heizung)",
       "# Je Raum: heizt gerade (hvac_action), Heizanteil der letzten Stunde, Stufe fuer die Raumfarbe.",
       "template:", "  - binary_sensor:"]
for r, g in geo.items():
    c = g["climate"]
    pkg += [
        "      - name: Heizung %s heizt" % r.upper(),
        "        unique_id: heizung_%s_heizt" % r,
        "        device_class: heat",
        "        state: \"{{ state_attr('%s', 'hvac_action') == 'heating' }}\"" % c,
        "        availability: \"{{ states('%s') not in ['unavailable', 'unknown'] }}\"" % c,
    ]
pkg += ["  - sensor:"]
for r, g in geo.items():
    c = g["climate"]
    pkg += [
        "      - name: Heizung %s Stufe" % r.upper(),
        "        unique_id: heizung_%s_stufe" % r,
        "        icon: mdi:radiator",
        "        state: >-",
        "          {%% set c = '%s' %%}" % c,
        "          {% set s = states(c) %}",
        "          {% if s in ['unavailable', 'unknown'] %}offline",
        "          {% elif s == 'off' %}aus",
        "          {% elif state_attr(c, 'hvac_action') != 'heating' %}bereit",
        "          {%% else %%}{%% set a = states('sensor.heizung_%s_heizanteil') | float(0) %%}" % r,
        "          {{ 'stark' if a >= 66 else ('mittel' if a >= 33 else 'leicht') }}{% endif %}",
        "        attributes:",
        "          anzeige: >-",
        "            {%% set c = '%s' %%}" % c,
        "            {% set ist = state_attr(c, 'current_temperature') %}",
        "            {% set soll = state_attr(c, 'temperature') %}",
        "            {% set f = '%.1f' %}",
        "            {% if states(c) in ['unavailable', 'unknown'] %}offline",
        "            {% elif ist is none %}–",
        "            {% elif states(c) == 'off' %}{{ (f | format(ist)) | replace('.', ',') }}° · aus",
        "            {% else %}{{ (f | format(ist)) | replace('.', ',') }}° → {{ (f | format(soll)) | replace('.', ',') }}°{% endif %}",
        "          heizanteil: \"{{ states('sensor.heizung_%s_heizanteil') | float(0) | round(0) }}\"" % r,
    ]
pkg += ["", "sensor:"]
for r, g in geo.items():
    pkg += [
        "  - platform: history_stats",
        "    name: Heizung %s Heizanteil" % r.upper(),
        "    unique_id: heizung_%s_heizanteil" % r,
        "    entity_id: binary_sensor.heizung_%s_heizt" % r,
        "    state: \"on\"",
        "    type: ratio",
        "    end: \"{{ now() }}\"",
        "    duration:",
        "      hours: 1",
    ]
open(OUT + "/heizung.yaml", "w", encoding="utf-8", newline="\n").write("\n".join(pkg) + "\n")


# ---------- Dashboard-Ansicht ----------
def plan_card(plan):
    p = PLANS[plan]
    els = []
    for r, g in geo.items():
        if g["plan"] != plan:
            continue
        stufe = "sensor.heizung_%s_stufe" % r
        more = {"action": "more-info", "entity": g["climate"]}
        els.append({
            "type": "image", "entity": stufe,
            "image": "/local/heizung/%s_aus.png?v=%s" % (r, VERSION),
            "state_image": {st: "/local/heizung/%s_%s.png?v=%s" % (r, st, VERSION) for st in STATES},
            "tap_action": more, "hold_action": more,
            "style": {"left": "%s%%" % g["left"], "top": "%s%%" % g["top"], "width": "%s%%" % g["width"]},
        })
        els.append({
            "type": "state-label", "entity": stufe, "attribute": "anzeige", "tap_action": more,
            "style": {"left": "%s%%" % g["label_left"], "top": "%s%%" % (g["label_top"] + 4),
                      "color": "#222", "font-weight": "600", "white-space": "nowrap",
                      "font-size": "clamp(9px, 1.3vw, 15px)", "background": "rgba(255,255,255,0.55)",
                      "border-radius": "6px", "padding": "1px 5px"},
        })
        els.append({
            "type": "conditional",
            "conditions": [{"condition": "state", "entity": "binary_sensor.heizung_%s_heizt" % r, "state": "on"}],
            "elements": [{
                "type": "icon", "icon": "mdi:fire", "tap_action": more,
                "style": {"left": "%s%%" % g["label_left"], "top": "%s%%" % (g["label_top"] - 3),
                          "color": "#ff5a1f", "--mdc-icon-size": "clamp(16px, 2.2vw, 28px)"},
            }],
        })
    return {
        "type": "picture-elements",
        "image": {"media_content_id": "media-source://image_upload/" + p["media"], "media_content_type": "image/png",
                  "metadata": {"title": p["title"], "thumbnail": "/api/image/serve/%s/256x256" % p["media"],
                               "media_class": "image"}},
        "elements": els,
    }


legend = ("**Raumfarbe** &nbsp; "
          "<font color='#e63214'>■</font> heizt stark (≥ 66 % der letzten Stunde) &nbsp; "
          "<font color='#ff821e'>■</font> mittel &nbsp; "
          "<font color='#ffbe46'>■</font> leicht &nbsp; "
          "<font color='#468ce6'>■</font> Ziel erreicht &nbsp; "
          "<font color='#969696'>■</font> aus / offline\n\n"
          "Raum antippen öffnet den Thermostat.")
VIEW = {
    "type": "sections", "title": "Heizung", "path": "heizung", "icon": "mdi:radiator", "max_columns": 2,
    "sections": [
        {"type": "grid", "cards": [{"type": "heading", "heading": "Erdgeschoss", "heading_style": "title"}, plan_card("eg")]},
        {"type": "grid", "cards": [{"type": "heading", "heading": "Obergeschoss", "heading_style": "title"}, plan_card("og")]},
        {"type": "grid", "column_span": 2, "cards": [
            {"type": "markdown", "content": legend, "grid_options": {"columns": "full"}},
            {"type": "heading", "heading": "Thermostate", "heading_style": "subtitle", "icon": "mdi:radiator",
             "entities": [
                 {"entity": "script.heizung_alle_aus", "state_content": "name", "color": "blue-grey",
                  "tap_action": {"action": "perform-action", "perform_action": "script.heizung_alle_aus",
                                 "confirmation": {"text": "Alle Thermostate ausschalten?"}}},
                 {"entity": "script.heizung_alle_16", "state_content": "name", "color": "deep-orange",
                  "tap_action": {"action": "perform-action", "perform_action": "script.heizung_alle_16",
                                 "confirmation": {"text": "Alle Thermostate auf Heizen mit 16 °C stellen?"}}},
             ]},
        ] + [
            {"type": "tile", "entity": g["climate"], "name": g["name"], "vertical": False,
             "features": [{"type": "target-temperature"}], "grid_options": {"columns": 6}}
            for g in geo.values()
        ]},
    ],
}
json.dump(VIEW, open(OUT + "/view.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok")
