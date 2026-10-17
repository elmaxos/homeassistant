# Schlafzimmer

## `Sz_alp_an_aus` – ALPSTUGA-Display bei Bewegung ([automationen/sz_alp_an_aus.yaml](automationen/sz_alp_an_aus.yaml))

- Bewegung am Melder `binary_sensor.sz_myg_wand_belegung` → Display `switch.sz_alp_bett` an, **nur wenn
  `input_boolean.baby_schlaeft` aus ist** (seit 17.10.2026).
- Raum frei → Display aus (immer).

Weitere Schlafzimmer-Themen: Fernbedienung an der Tür `BILBUT_SZ_Tuer` in [../Blueprints/README.md](../Blueprints/README.md),
Rauschen auf der Kamera in [../Thingino/Sonoff-PT2/noise/README.md](../Thingino/Sonoff-PT2/noise/README.md).
Helfer `input_boolean.baby_schlaeft` wird über die Fernbedienung gesetzt (Licht aus + oben halten = wach, unten halten = schläft).

## Helfer `input_boolean.baby_schlaeft`

- **Zeitplan** ([automationen/baby_schlaeft_zeitplan.yaml](automationen/baby_schlaeft_zeitplan.yaml)): jeden Tag 22:00 an, 09:00 aus.
- **Fernbedienung** `BILBUT_SZ_Tuer`: Licht aus + oben halten = wach, unten halten = schläft.
- Wirkt auf:
  - `Sz_alp_an_aus`: Display bei Bewegung nur an, wenn das Baby **nicht** schläft.
  - `Tuer_auf_sz_az_licht_aus` ([automationen/tuer_auf_sz_az_licht_aus.yaml](automationen/tuer_auf_sz_az_licht_aus.yaml)):
    dimmt das Arbeitszimmerlicht beim Öffnen der Schlafzimmertür **nur**, wenn das Baby schläft.
  - TTS (`tts_cam_sound_text` / `tts_cam_ausgabe`): Ziel `schlafzimmer` wird übersprungen, solange das Baby schläft.
