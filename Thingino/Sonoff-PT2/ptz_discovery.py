"""MQTT-Discovery (retain) fuer die PTZ-Sensoren einer Kamera: python3 ptz_discovery.py <hostname> <device-identifier>"""
import json, os, sys, urllib.request

HOST = sys.argv[1]
DEV_ID = sys.argv[2] if len(sys.argv) > 2 else HOST
OBJ = HOST.replace("-", "_")
H = {"Authorization": "Bearer " + os.environ["SUPERVISOR_TOKEN"], "Content-Type": "application/json"}
dev = {"identifiers": [DEV_ID]}
configs = {
    "sensor/%s_ptz_position/config" % HOST: {
        "name": "PTZ Position", "unique_id": HOST + "_ptz_position", "default_entity_id": "sensor.%s_ptz_position" % OBJ,
        "icon": "mdi:crosshairs-gps", "state_topic": HOST + "/state/ptz_position", "device": dev},
    "sensor/%s_ptz_preset/config" % HOST: {
        "name": "PTZ Preset", "unique_id": HOST + "_ptz_preset", "default_entity_id": "sensor.%s_ptz_preset" % OBJ,
        "icon": "mdi:camera-marker-outline", "state_topic": HOST + "/state/ptz_preset", "device": dev},
}
# altes Topic-Format (<typ>/<host>/<name>) leeren, damit es keine doppelte unique_id gibt
old = ["sensor/%s/ptz_position/config" % HOST, "sensor/%s/ptz_preset/config" % HOST]
for topic in old:
    body = json.dumps({"topic": "homeassistant/" + topic, "payload": "", "retain": True})
    urllib.request.urlopen(urllib.request.Request("http://supervisor/core/api/services/mqtt/publish", body.encode(), H))
for topic, payload in configs.items():
    body = json.dumps({"topic": "homeassistant/" + topic, "payload": json.dumps(payload, ensure_ascii=False), "retain": True})
    r = urllib.request.Request("http://supervisor/core/api/services/mqtt/publish", body.encode(), H)
    print(topic, urllib.request.urlopen(r).status)
