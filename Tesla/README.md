# Tesla (Integration `tesla_fleet`, Fahrzeug `fky`)

Die Integration fragt das Auto von sich aus nur alle 10 Minuten ab (`VEHICLE_INTERVAL_SECONDS = 600`).
Schnelleres Polling läuft über Automationen mit `homeassistant.update_entity` (ein Aufruf aktualisiert alle Fahrzeug-Entities).

| Datei | Zweck |
|---|---|
| `automationen/tesla_fenster_automatik.yaml` | Fenster nach Wetter/Zeit |
| `automationen/tesla_ankunfts_benachrichtigung.yaml` | Ansagen zur Navigation: **neues Ziel** (Ziel, Ankunftszeit, Strecke; Navi-Ziel setzt `input_text.tesla_letztes_ziel`), **angekommen** (Navigation endet und Ankunftszeit liegt höchstens 5 min in der Zukunft; Abbruch der Navigation sagt nichts). Ansage, sobald ein Navigationsziel (jedes Ziel) weniger als 10 Minuten entfernt ist: Ziel, Ankunftszeit, Minuten, Restkilometer. Zielname: HA-Zone aus `device_tracker.fky_route` (bei `home` „zuhause“), sonst Navi-Ziel `sensor.fky_ziel`, sonst „sein Ziel“. Außerdem Ansage bei Losfahrt Richtung Zuhause und ohne Navigation 1 km vor Zuhause. |
| `automationen/tesla_ankunfts_benachrichtigung_reset.yaml` | setzt `input_boolean.tesla_ankunft_benachrichtigt` zurück, wenn das Auto > 3 km von zuhause ist |
| `automationen/tesla_fast_polling_annaeherung.yaml` | Navi-Ziel 15–30 min entfernt: jede Minute; unter 15 min und 3 min nach Ankunft: alle 30 s (kein Wecken) |
| `automationen/tesla_fast_polling_schnellladen.yaml` | alle 15 s, solange `sensor.fky_ladegerat_leistung` > 15 kW |
| `scripts/tesla_alles_aktualisieren.yaml` | Auto wecken und alle Entities aktualisieren |
| `scripts/tts_tesla_statusansage.yaml` | Statusansage über `script.tts_cam_sound_text` (Datenalter über `last_reported`; Standort: HA-Zone oder Adresse) |
| `scripts/tesla_standort_adresse.yaml` | liefert `{zone, adresse}`: in einer HA-Zone den Zonennamen, sonst die Adresse über OpenStreetMap (`rest_command.nominatim_reverse`, siehe `TTS/configuration_rest_command.yaml`) |

Hinweise:
- Die 10-Minuten-Ansage braucht eine aktive Navigation (`sensor.fky_zeit_bis_zur_ankunft`). Sie kommt einmal pro Annäherung
  (Template-Trigger, scharf erst wieder, wenn die Bedingung einmal falsch war).
- Das Schnelllade-Polling startet erst, wenn die normale 10-Minuten-Abfrage die Ladeleistung über 15 kW gesehen hat.
- Jede Abfrage kostet Fleet-API-Kontingent.
- Helfer `input_text.tesla_letztes_ziel` (Text, max. 255) anlegen; er merkt das letzte Ziel für die Ankunftsansage.
- Adresse per OpenStreetMap: dabei gehen die Koordinaten des Autos an nominatim.openstreetmap.org, nur wenn das Auto in keiner Zone steht
  und die Statusansage läuft. Nominatim erlaubt höchstens eine Anfrage pro Sekunde.
- Das Navi hängt an Ziele oft ", Germany" an; das wird in den Ansagen entfernt.
- Neues Ziel wird erst bei der nächsten Abfrage des Autos erkannt (ohne Annäherung bis zu 10 Minuten später).
