# Kamera-Seiten (Testdashboard, Tab „Kamera“)

Der alte Tab `Kamera` (`/dashboard-testdashboard/kamera`) ist jetzt eine **Übersicht** mit vier Live-Vorschaubildern;
ein Tipp öffnet die Seite der Kamera. Tapo und LSC stehen unverändert darunter.

Pro Thingino-Kamera gibt es eine **Unterseite** (`subview`, erscheint nicht in der Tab-Leiste, Zurück-Pfeil führt zur
Übersicht): `kamera-wohnzimmer`, `kamera-schlafzimmer`, `kamera-unterstand`, `kamera-kamera4420`.
Oben eine Leiste mit allen vier Kameras zum direkten Wechseln (aktuelle mit ●). Bewusst keine Auswahl per Helfer –
die würde auf allen Geräten gleichzeitig umschalten.

Aufbau jeder Seite (Abschnitte, `max_columns: 3`, `dense_section_placement`): breit liegt das Bild über zwei Spalten,
die Schwenk-Steuerung rechts daneben, darunter drei Spalten. Am Handy steht alles untereinander.

- **Bild:** Advanced Camera Card, Menü als Leiste **über** dem Bild (`menu.style: outside`), damit nichts das Bild verdeckt
  oder beim Einblenden versehentlich gedrückt wird. Knöpfe: HD/LD (Substream, wo es einen LD-Stream gibt), Vollbild,
  Screenshot. Keine Statuszeile im Bild. Zoom per Pinch bzw. Strg + Mausrad.
- **Schwenken:** große Pfeile = schnell (`button.<host>_ptz_*_fast`), kleine Dreiecke rechts in der Überschrift =
  langsam/fein (`button.<host>_ptz_*`). Bei Schlafzimmer/Unterstand vertauscht verdrahtet, siehe `../Kameras/README.md`.
- **Position:** gespeicherte Presets + „Mitte“ (`position_reset`), in der Überschrift das erkannte Preset
  (`sensor.<host>_ptz_preset`, wo vorhanden).
- **Licht & Bild:** Weißlicht (Schlafzimmer mit Rückfrage), IR-Licht, IR-Filter, Farbbild/Schwarzweiß, Status-LED (nicht 4420),
  Privat-Modus.
- **Ton:** Lautstärke-Regler `number.<host>_speaker_volume` (gespeicherte Lautstärke für Ansagen/TTS).
  Nur Schlafzimmer: Rauschen hat einen eigenen Regler; solange es läuft, setzt es `spk_vol` selbst, nach dem Stopp gilt
  wieder der gespeicherte Wert. Dazu
  Rauschen Ein/Aus, Lautstärke (10–80), Farbe.
- **Ansage:** Textfeld `input_text.ansage_text_<kamera>` + „Senden“ → `script.tts_kamera_textansage`
  (ohne Gong, ohne Licht, nur diese Kamera; Schlafzimmer entfällt bei `baby_schlaeft` an, mit Hinweis).
- **Stream:** HD/LD Video (`switch.<host>_main|sub_stream_video`, mit Rückfrage), HD/LD Ton
  (`switch.<host>_main|sub_stream_audio`) und Mikrofon (`switch.<host>_mic`).
  - *Ton* nimmt nur die Audiospur aus diesem RTSP-Stream (Stream startet dafür kurz neu, `restart_thread 3`).
  - *Mikrofon* schaltet die Aufnahme komplett ab, auch den AAC-Encoder (`restart_thread 4`), damit hat kein Stream mehr Ton.
  - Schlafzimmer: Mikrofon bewusst aus (Rückfrage beim Einschalten); der laufende Encoder ließ Rauschen und Ansagen stocken.
  - *Video aus* am angezeigten Stream = schwarzes Bild (Unterstand: HD-Video ist absichtlich aus).

Neu erzeugen/ändern: Liste `CAMS` in [kamera_seiten.py](kamera_seiten.py) anpassen, im HA-Container ausführen
(`docker exec -e T=$SUPERVISOR_TOKEN homeassistant python3 kamera_seiten.py`). Ansicht als YAML: [views.yaml](views.yaml).
