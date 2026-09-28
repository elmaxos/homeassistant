# Tesla (Integration `tesla_fleet`, Fahrzeug `fky`)

| Datei | Zweck |
|---|---|
| `automationen/tesla_fenster_automatik.yaml` | Fenster nach Wetter/Zeit |
| `scripts/tesla_alles_aktualisieren.yaml` | Auto wecken und alle Entities aktualisieren |
| `scripts/tesla_statusansage.yaml` | Statusansage über `script.tts_cam_sound_text` (Kameras wählbar, inkl. 4420) |

Hinweis zum Fast-Polling (in `automations.yaml`, „Tesla Fast-Polling bei Annäherung“): pollt alle 15 s bei
ETA ≤ 5 min und jede Minute bei ETA 5–15 min, plus täglich 13:00 mit Wecken. Greift nur, wenn im Auto eine
Navigation nach Hause aktiv ist (`sensor.fky_zeit_bis_zur_ankunft`).
