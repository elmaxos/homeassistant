# Heizung auf dem Grundriss

Tab `Heizung` im Testdashboard (`/dashboard-testdashboard/heizung`). Er nutzt die beiden hochgeladenen Grundrisse
(`burlafingen2.png` = Erdgeschoss, `burlafingen3OG.png` = Obergeschoss). Jeder Raum mit Thermostat wird je nach
Heizzustand eingefärbt. Im Raum steht „Ist → Soll“, eine Flamme erscheint, solange das Thermostat heizt.
Ein Tipp auf den Raum öffnet den Thermostat. Über den Thermostat-Kacheln stehen in der Überschrift „Thermostate“ zwei
kleine Knöpfe: **Alle aus** (`script.heizung_alle_aus`) und **Alle 16 °C** (`script.heizung_alle_16`, Heizen mit 16 °C),
beide mit Rückfrage. Scripts: [scripts/heizung_alle.yaml](scripts/heizung_alle.yaml) (an `/config/scripts.yaml` anhängen).

| Farbe | Stufe (`sensor.heizung_<raum>_stufe`) | Bedeutung |
|---|---|---|
| rot | `stark` | heizt, Heizanteil der letzten Stunde ≥ 66 % |
| orange | `mittel` | heizt, 33–66 % |
| gelb | `leicht` | heizt, < 33 % |
| blau | `bereit` | an, Ziel erreicht (`hvac_action` ≠ heating) |
| grau | `aus` | Thermostat aus |
| dunkelgrau | `offline` | Thermostat nicht erreichbar |

Räume: Wohnzimmer (`climate.wz_son_thermostat`), Esszimmer (`climate.ez_son_thermostat`), Bad (`climate.bd_son_heizung`)
im EG; Arbeitszimmer (`climate.az_son_heizung`), Schlafzimmer (`climate.sz_son_thermostat`) im OG.
Die Zuordnung Raumfläche → Thermostat kommt von den Thermostat-Symbolen, die schon im Temperatur-Tab auf den Plänen lagen.

## Dateien

- `packages/heizung.yaml` → `/config/packages/heizung.yaml`. Je Raum:
  - `binary_sensor.heizung_<raum>_heizt` (Template: `hvac_action == heating`)
  - `sensor.heizung_<raum>_heizanteil` (`history_stats`, Anteil „heizt“ der letzten Stunde in %)
  - `sensor.heizung_<raum>_stufe` (Template, Attribut `anzeige` = „18,8° → 18,5°“)
- In `configuration.yaml` sind Pakete eingebunden:
  ```yaml
  homeassistant:
    packages: !include_dir_named packages
  ```
- `heizung_gen.py`: erzeugt aus den Grundriss-PNGs je Raum und Stufe ein Overlay-PNG (Raumfläche per Flood-Fill
  auf der Bodenfarbe 241/216/176, ausgehend von einem Saatpunkt je Raum), das Package und die Ansicht (`view.json`).
  Die Overlays gehören nach `/config/www/heizung/`. Grundrisse und Overlays liegen bewusst nicht im Repo.
- `heizung_view.py`: trägt `view.json` per Websocket ins Testdashboard ein (im HA-Container ausführen).
- `view.yaml`: die Ansicht zum Einfügen per Raw-Konfigurationseditor.

## Neu erzeugen

Grundrisse aus `/config/image/<id>/original` holen (`plan_eg.png`, `plan_og.png`), `python heizung_gen.py`, dann
`heizung_out/www/*` nach `/config/www/heizung/`, `heizung_out/heizung.yaml` nach `/config/packages/`, Konfiguration
prüfen, Templates neu laden. `history_stats` braucht beim ersten Mal einen Neustart von Home Assistant.
Nach geänderten Overlays `VERSION` im Skript erhöhen, damit der Browser-Cache die neuen Bilder lädt.

## Raumthermometer statt Thermostat-Fühler

Blueprint [`../Blueprints/meine_heizung/externer_temperaturfuehler.yaml`](../Blueprints/meine_heizung/externer_temperaturfuehler.yaml)
→ `/config/blueprints/automation/meine_heizung/`. Automationen daraus: [automationen/heizung_raumthermometer.yaml](automationen/heizung_raumthermometer.yaml).

| Thermostat | Raumthermometer |
|---|---|
| Wohnzimmer | `sensor.wz_son_thermo_temperature` |
| Arbeitszimmer | `sensor.az_son_thermo_temperature` |
| Bad | `sensor.bd_son_thermo_temperature` |
| Schlafzimmer | `sensor.sz_alp_bett_temperatur` (ALPSTUGA am Bett; `sz_son_thermo` hängt laut Bereich im Flur) |
| Esszimmer | `sensor.meter_plus_3986_temperatur` (liegt im Grundriss in diesem Raum) |

- Bei jeder Änderung des Thermometers und alle 15 min: Wert → `number.<thermostat>_external_temperature_input`,
  Fühlerauswahl → `remote_temperature`.
- **Fallback:** kein Zahlenwert oder letzte Meldung (`last_reported`) älter als 240 min (einstellbar) →
  Fühlerauswahl `local_temperature` (eingebauter Fühler) und eine Benachrichtigung in HA. Kommen wieder frische Werte,
  schaltet es zurück und die Benachrichtigung verschwindet.
- Die TRVZB (Firmware 1.4.4, Zigbee2MQTT) kennen als Fühlerauswahl `local_temperature`, `remote_temperature`,
  `remote_source_offline`. Die alte Automation `Heizung extern set temp` (id `1773573476032`, liegt zur Doku mit in
  der Datei) prüfte auf `internal` und wählte `external`. Diese Werte gibt es nicht (mehr), deshalb blieb das
  Arbeitszimmer im aufgezeichneten Zeitraum (ab 03.10.) immer auf dem eingebauten Fühler. Sie ist ausgeschaltet, nicht gelöscht.
