"""Legt per MQTT-Discovery (retain) Schalter, Lautstaerke und Farbe fuer das Rauschen an einer Kamera an."""
import json, os, sys, urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "ing-sonoff-pt2-a574"
DEV_ID = sys.argv[2] if len(sys.argv) > 2 else HOST
OBJ = HOST.replace("-", "_")
H = {"Authorization": "Bearer " + os.environ["SUPERVISOR_TOKEN"], "Content-Type": "application/json"}
dev = {"identifiers": [DEV_ID]}
cmd = HOST + "/cmd"
st = HOST + "/state/"

configs = {
    "switch/%s_noise/config" % HOST: {
        "name": "Rauschen", "unique_id": HOST + "_noise", "default_entity_id": "switch.%s_noise" % OBJ,
        "icon": "mdi:waveform", "command_topic": cmd, "payload_on": "noise start", "payload_off": "noise stop",
        "state_topic": st + "noise", "state_on": "ON", "state_off": "OFF", "device": dev,
    },
    "number/%s_noise_volume/config" % HOST: {
        "name": "Rauschen Lautstärke", "unique_id": HOST + "_noise_volume",
        "default_entity_id": "number.%s_noise_volume" % OBJ, "icon": "mdi:volume-medium",
        "command_topic": cmd, "command_template": "noise volume {{ value | int }}",
        "state_topic": st + "noise_volume", "min": 0, "max": 100, "step": 5, "mode": "slider", "device": dev,
    },
    "select/%s_noise_color/config" % HOST: {
        "name": "Rauschen Farbe", "unique_id": HOST + "_noise_color",
        "default_entity_id": "select.%s_noise_color" % OBJ, "icon": "mdi:palette",
        "command_topic": cmd, "command_template": "noise color {{ value }}",
        "state_topic": st + "noise_color", "options": ["weiss", "rosa", "braun"], "device": dev,
    },
    "number/%s_noise_fade_in/config" % HOST: {
        "name": "Rauschen Einblenden", "unique_id": HOST + "_noise_fade_in",
        "default_entity_id": "number.%s_noise_fade_in" % OBJ, "icon": "mdi:volume-plus",
        "command_topic": cmd, "command_template": "noise fade_in {{ value | int }}",
        "state_topic": st + "noise_fade_in", "min": 0, "max": 30, "step": 1, "unit_of_measurement": "s",
        "mode": "slider", "device": dev,
    },
    "number/%s_noise_fade_out/config" % HOST: {
        "name": "Rauschen Ausblenden", "unique_id": HOST + "_noise_fade_out",
        "default_entity_id": "number.%s_noise_fade_out" % OBJ, "icon": "mdi:volume-minus",
        "command_topic": cmd, "command_template": "noise fade_out {{ value | int }}",
        "state_topic": st + "noise_fade_out", "min": 0, "max": 30, "step": 1, "unit_of_measurement": "s",
        "mode": "slider", "device": dev,
    },
}
# altes Topic-Format (<typ>/<host>/<name>) leeren, damit es keine doppelte unique_id gibt
old = ["switch/%s/noise/config" % HOST, "number/%s/noise_volume/config" % HOST, "select/%s/noise_color/config" % HOST]
for topic in old:
    body = json.dumps({"topic": "homeassistant/" + topic, "payload": "", "retain": True})
    urllib.request.urlopen(urllib.request.Request("http://supervisor/core/api/services/mqtt/publish", body.encode(), H))
for topic, payload in configs.items():
    body = json.dumps({"topic": "homeassistant/" + topic, "payload": json.dumps(payload, ensure_ascii=False), "retain": True})
    r = urllib.request.Request("http://supervisor/core/api/services/mqtt/publish", body.encode(), H)
    print(topic, urllib.request.urlopen(r).status)
