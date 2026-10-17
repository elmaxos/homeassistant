# Schlafzimmer

## `Sz_alp_an_aus` – ALPSTUGA-Display bei Bewegung ([automationen/sz_alp_an_aus.yaml](automationen/sz_alp_an_aus.yaml))

- Bewegung am Melder `binary_sensor.sz_myg_wand_belegung` → Display `switch.sz_alp_bett` an, **nur wenn
  `input_boolean.baby_schlaeft` aus ist** (seit 17.10.2026).
- Raum frei → Display aus (immer).

Weitere Schlafzimmer-Themen: Fernbedienung an der Tür `BILBUT_SZ_Tuer` in [../Blueprints/README.md](../Blueprints/README.md),
Rauschen auf der Kamera in [../Thingino/Sonoff-PT2/noise/README.md](../Thingino/Sonoff-PT2/noise/README.md).
Helfer `input_boolean.baby_schlaeft` wird über die Fernbedienung gesetzt (Licht aus + oben halten = wach, unten halten = schläft).
