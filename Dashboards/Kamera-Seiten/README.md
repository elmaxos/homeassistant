# Kamera-Seiten (Testdashboard, Tab „Kamera“)

Der alte Tab `Kamera` (`/dashboard-testdashboard/kamera`) ist jetzt eine **Übersicht** mit vier Live-Vorschaubildern;
ein Tipp öffnet die Seite der Kamera. Tapo und LSC stehen unverändert darunter.

Pro Thingino-Kamera gibt es eine **Unterseite** (`subview`, erscheint nicht in der Tab-Leiste, Zurück-Pfeil führt zur
Übersicht): `kamera-wohnzimmer`, `kamera-schlafzimmer`, `kamera-unterstand`, `kamera-kamera4420`.
Oben eine Leiste mit allen vier Kameras zum direkten Wechseln (aktuelle mit ●). Bewusst keine Auswahl per Helfer –
die würde auf allen Geräten gleichzeitig umschalten.

Aufbau jeder Seite (wie der alte Tab, aber pro Kamera ausgewertet):

- Livebild (`picture-glance`, `camera_view: live`), darunter Pfeile ← ↑ ↓ → (`button.<host>_ptz_*_fast`;
  bei Schlafzimmer/Unterstand vertauscht verdrahtet, siehe `../Kameras/README.md`).
- **Position:** gespeicherte Presets + „Mitte“ (`position_reset`), in der Überschrift das erkannte Preset
  (`sensor.<host>_ptz_preset`, wo vorhanden).
- **Licht & Bild:** Weißlicht (nicht beim Schlafzimmer), IR-Licht, IR-Filter, Farbe/Schwarzweiß, Status-LED (nicht 4420),
  Privatsphäre.
- **Rauschen** (nur Schlafzimmer): Ein/Aus, Lautstärke-Regler, Farbe.
- **Ansage:** Textfeld `input_text.ansage_text_<kamera>` + „Senden“ → `script.tts_kamera_textansage`
  (ohne Gong, ohne Licht, nur diese Kamera; Schlafzimmer entfällt bei `baby_schlaeft` an, mit Hinweis).

Neu erzeugen/ändern: Liste `CAMS` in [kamera_seiten.py](kamera_seiten.py) anpassen, im HA-Container ausführen
(`docker exec -e T=$SUPERVISOR_TOKEN homeassistant python3 kamera_seiten.py`). Ansicht als YAML: [views.yaml](views.yaml).
