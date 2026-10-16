"""Legt per MQTT-Discovery (retain) Schalter, Lautstaerke und Farbe fuer das Rauschen an einer Kamera an."""
import json, os, sys, urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "ing-sonoff-pt2-a574"
OBJ = HOST.replace("-", "_")
H = {"Authorization": "Bearer " + os.environ["SUPERVISOR_TOKEN"], "Content-Type": "application/json"}
dev = {"identifiers": [HOST]}
cmd = HOST + "/cmd"
st = HOST + "/state/"

configs = {
    "switch/%s/noise/config" % HOST: {
        "name": "Rauschen", "unique_id": HOST + "_noise", "default_entity_id": "switch.%s_noise" % OBJ,
        "icon": "mdi:waveform", "command_topic": cmd, "payload_on": "noise start", "payload_off": "noise stop",
        "state_topic": st + "noise", "state_on": "ON", "state_off": "OFF", "device": dev,
    },
    "number/%s/noise_volume/config" % HOST: {
        "name": "Rauschen Lautstärke", "unique_id": HOST + "_noise_volume",
        "default_entity_id": "number.%s_noise_volume" % OBJ, "icon": "mdi:volume-medium",
        "command_topic": cmd, "command_template": "noise volume {{ value | int }}",
        "state_topic": st + "noise_volume", "min": 0, "max": 100, "step": 5, "mode": "slider", "device": dev,
    },
    "select/%s/noise_color/config" % HOST: {
        "name": "Rauschen Farbe", "unique_id": HOST + "_noise_color",
        "default_entity_id": "select.%s_noise_color" % OBJ, "icon": "mdi:palette",
        "command_topic": cmd, "command_template": "noise color {{ value }}",
        "state_topic": st + "noise_color", "options": ["weiss", "rosa", "braun"], "device": dev,
    },
}
for topic, payload in configs.items():
    body = json.dumps({"topic": "homeassistant/" + topic, "payload": json.dumps(payload, ensure_ascii=False), "retain": True})
    r = urllib.request.Request("http://supervisor/core/api/services/mqtt/publish", body.encode(), H)
    print(topic, urllib.request.urlopen(r).status)
