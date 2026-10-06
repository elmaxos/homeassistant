# Keller – Warnung bei offener Kellertür

Automation `Keller auf Benachrichtigung und Alarm` (id `1775818895975`), Datei
[automationen/keller_tuer_warnung.yaml](automationen/keller_tuer_warnung.yaml).

## Verhalten

- Steht `binary_sensor.par_keller_contact` 5 s auf `on`, sagt `script.tts_cam_sound_text`
  „Die Kellertür ist offen“ auf der Wohnzimmer-Kamera und dem Handy an. Dazu
  schaltet `switch.relay_switch_1pm` 2 s um.
- Das wiederholt sich etwa alle 15 s, solange die Tür offen ist.
- **Nur zwischen 08:00 und 21:00 Uhr:**
  - Öffnet die Tür außerhalb dieser Zeit, passiert nichts.
  - Steht die Tür um 08:00 schon offen, beginnt die Warnung dann (Zeit-Trigger 08:00).
  - Um 21:00 hört eine laufende Warnung auf (Zeitbedingung in der `while`-Schleife).

## Einspielen

Den Block in `/config/automations.yaml` einfügen (oder die gleiche id ersetzen),
dann `ha core check` und **Automationen neu laden**.
