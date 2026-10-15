# Kameras – Tab im Testdashboard

Tab `Kameras` (`/dashboard-testdashboard/kameras-ptz`): alle Thingino-Kameras in einer Karte, immer eine Kamera
im Bild, umschalten mit den Pfeilen links/rechts im Bild oder über das Kamera-Symbol im Menü.
Konfiguration: [view.yaml](view.yaml), erzeugt von [cams_view.py](cams_view.py) (Kameraliste oben im Skript).

| Kamera | Host | IP | Live (Substream) / HD über Substream-Symbol | Pfeile |
|---|---|---|---|---|
| Wohnzimmer | `ing-sonoff-pt2-3684` | .71 | `camera.sonoff_pt2_1_profile_1` / `camera.sonoff_pt2_1_profile_0` | normal |
| Schlafzimmer | `ing-sonoff-pt2-a574` | .74 | `camera.sonoff_kamera_3_profile_1` / `camera.sonoff_pt2_3_profile_0` | vertauscht |
| Unterstand | `ing-sonoff-pt2-26a4` | .73 | `camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_1` (Substream!) | vertauscht |
| Kamera 4420 | `ing-sonoff-pt2-4420` | .72 | `camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_0_2` | normal |

„Vertauscht“: links → `ptz_right_fast`, hoch → `ptz_down_fast` (wie im alten Tab `Kamera`). Das betrifft die Kameras,
deren Bild nicht per Flip gedreht ist. Bei 3684 und 4420 sind horizontaler und vertikaler Flip an, dort passen die Pfeile direkt.
Für 4420 ist das aus der Flip-Einstellung abgeleitet und noch nicht ausprobiert.

Unterstand (26a4): Am Hauptstream ist das Video abgeschaltet (`switch.ing_sonoff_pt2_26a4_main_stream_video` aus),
deshalb nutzt die Karte dort den Substream `profile_1` (640×360). Mit `profile_0` bleibt das Bild schwarz.

Live läuft standardmäßig der Substream (weniger Last und WLAN). Den Hauptstream gibt es bei Wohnzimmer und
Schlafzimmer als zweite Kamera mit `capabilities.disable_except: [substream]`, als Abhängigkeit (`dependencies`) eingetragen.
Das Menü zeigt dann ein Substream-Symbol zum Umschalten.

## Voraussetzung

**Advanced Camera Card** über HACS (`dermotduffy/advanced-camera-card`, getestet mit 8.1.0). HACS trägt die Ressource
`/hacsfiles/advanced-camera-card/advanced-camera-card.js` selbst ein.

## Bedienung

- **PTZ-Steuerung** unten rechts im Bild: Pfeile drücken die MQTT-Buttons `ptz_*_fast`, gedrückt halten wiederholt
  alle 0,4 s. Home-Taste = erstes Preset, daneben die Preset-Liste (gespeicherte Presets je Kamera).
- **Menü oben rechts im Bild** (Overlay):
  - Lupe + / − zoomt digital, solange gedrückt; Lupe mit X setzt den Zoom zurück. Die Kameras haben keinen optischen
    Zoom. Die Karte erlaubt in `cameras[].ptz.actions_zoom_*` nur `perform-action`, deshalb liegen die Zoom-Tasten
    als `elements` im Menü.
  - Weißlicht, IR-Licht und Privatsphäre der **gerade gewählten** Kamera (`custom:advanced-camera-card-conditional`
    mit `condition: camera`).
- **Zoom per Geste:** Zwei-Finger-Pinch am Handy, am PC Strg + Mausrad, danach verschieben.
- Nur die sichtbare Kamera streamt (`live.lazy_unload: [unselected, hidden]`).

## Einspielen

Dashboard bearbeiten → Ansicht hinzufügen → Raw-Konfigurationseditor, Inhalt von `view.yaml` einfügen.
Oder `cams_view.py` im HA-Container ausführen
(`docker exec -e T=$SUPERVISOR_TOKEN homeassistant python3 cams_view.py`), es ersetzt den Tab per Websocket.
