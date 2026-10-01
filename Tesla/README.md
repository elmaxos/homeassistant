# Tesla (Integration `tesla_fleet`, Fahrzeug `fky`)

Die Integration fragt das Auto von sich aus nur alle 10 Minuten ab (`VEHICLE_INTERVAL_SECONDS = 600`).
Schnelleres Polling läuft über Automationen mit `homeassistant.update_entity` (ein Aufruf aktualisiert alle Fahrzeug-Entities).

| Datei | Zweck |
|---|---|
| `automationen/tesla_fenster_automatik.yaml` | Fenster nach Wetter/Zeit |
| `automationen/tesla_ankunfts_benachrichtigung.yaml` | Ansage, sobald ein Navigationsziel (jedes Ziel) weniger als 10 Minuten entfernt ist: Ziel, Ankunftszeit, Minuten, Restkilometer. Außerdem Ansage bei Losfahrt Richtung Zuhause und ohne Navigation 1 km vor Zuhause. |
| `automationen/tesla_ankunfts_benachrichtigung_reset.yaml` | setzt `input_boolean.tesla_ankunft_benachrichtigt` zurück, wenn das Auto > 3 km von zuhause ist |
| `automationen/tesla_fast_polling_annaeherung.yaml` | Navi-Ziel 15–30 min entfernt: jede Minute; unter 15 min und 3 min nach Ankunft: alle 30 s; täglich 13:00 mit Wecken |
| `automationen/tesla_fast_polling_schnellladen.yaml` | alle 15 s, solange `sensor.fky_ladegerat_leistung` > 15 kW |
| `scripts/tesla_alles_aktualisieren.yaml` | Auto wecken und alle Entities aktualisieren |
| `scripts/tts_tesla_statusansage.yaml` | Statusansage über `script.tts_cam_sound_text` (Datenalter über `last_reported`) |

Hinweise:
- Die 10-Minuten-Ansage braucht eine aktive Navigation (`sensor.fky_zeit_bis_zur_ankunft`). Sie kommt einmal pro Annäherung
  (Template-Trigger, scharf erst wieder, wenn die Bedingung einmal falsch war).
- Das Schnelllade-Polling startet erst, wenn die normale 10-Minuten-Abfrage die Ladeleistung über 15 kW gesehen hat.
- Jede Abfrage kostet Fleet-API-Kontingent.
