# Kameras – Tab im Testdashboard

Tab `Kameras` (`/dashboard-testdashboard/kameras-ptz`): alle Thingino-Kameras in einer Karte, immer eine Kamera
im Bild, umschalten mit den Pfeilen links/rechts im Bild oder über das Kamera-Symbol im Menü.
Konfiguration: [view.yaml](view.yaml), erzeugt von [cams_view.py](cams_view.py) (Kameraliste oben im Skript).

| Kamera | Host | IP | Live (1080p) / klein über Substream-Symbol | Pfeile |
|---|---|---|---|---|
| Wohnzimmer | `ing-sonoff-pt2-3684` | .71 | `camera.sonoff_pt2_1_profile_0` / `camera.sonoff_pt2_1_profile_1` | normal |
| Schlafzimmer | `ing-sonoff-pt2-a574` | .74 | `camera.sonoff_pt2_3_profile_0` / `camera.sonoff_kamera_3_profile_1` | vertauscht |
| Unterstand | `ing-sonoff-pt2-26a4` | .73 | `camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_1` (Substream!) | vertauscht |
| Kamera 4420 | `ing-sonoff-pt2-4420` | .72 | `camera.sonoff_pt2_t23n_sc2336p_atbm6012bx_profile_0_2` | normal |

„Vertauscht“: links → `ptz_right_fast`, hoch → `ptz_down_fast` (wie im alten Tab `Kamera`). Das betrifft die Kameras,
deren Bild nicht per Flip gedreht ist. Bei 3684 und 4420 sind horizontaler und vertikaler Flip an, dort passen die Pfeile direkt.
Für 4420 ist das aus der Flip-Einstellung abgeleitet und noch nicht ausprobiert.

Unterstand (26a4): Am Hauptstream ist das Video abgeschaltet (`switch.ing_sonoff_pt2_26a4_main_stream_video` aus),
deshalb nutzt die Karte dort den Substream `profile_1` (640×360). Mit `profile_0` bleibt das Bild schwarz.

Live läuft standardmäßig der Hauptstream (1080p). Den kleinen Substream gibt es bei Wohnzimmer und
Schlafzimmer als zweite Kamera mit `capabilities.disable_except: [substream]`, als Abhängigkeit (`dependencies`) eingetragen.
Das Menü zeigt dann ein Substream-Symbol zum Umschalten.

## Voraussetzung

**Advanced Camera Card** über HACS (`dermotduffy/advanced-camera-card`, getestet mit 8.1.0). HACS trägt die Ressource
`/hacsfiles/advanced-camera-card/advanced-camera-card.js` selbst ein.

## Bedienung

- **Kamera wechseln** mit den Pfeilen links/rechts im Bild (`next_previous: chevrons`) oder über das Kamera-Symbol im Menü.
- Das **Menü oben rechts** erscheint, sobald die Maus über dem Bild ist (am Handy nach Antippen, `menu.style: hover`). Darin:
  - **Schwenk-Steuerung ein/aus** (`menu.buttons.ptz_controls`, standardmäßig aus: `live.controls.ptz.mode: off`).
    Eingeblendet unten rechts: Pfeile drücken die MQTT-Buttons `ptz_*_fast`, gedrückt halten wiederholt alle 0,4 s;
    Home-Taste = erstes Preset, daneben die Preset-Liste.
  - **Substream** (kleiner Stream) bei Wohnzimmer und Schlafzimmer.
  - **Zoom** + / − (digital, gedrückt halten) und Zoom zurücksetzen. Die Karte erlaubt in `cameras[].ptz.actions_zoom_*`
    nur `perform-action`, deshalb liegen die Zoom-Tasten als `elements` im Menü.
  - Für die **gerade gewählte** Kamera (`custom:advanced-camera-card-conditional` mit `condition: camera`):
    Weißlicht (nicht beim Schlafzimmer, damit es nicht versehentlich angeht), IR-Licht, Privatsphäre, IR-Filter (`switch.<host>_ir_cut`, bei 4420 `_ir_cut_filter`),
    Farbe/Schwarzweiß (`switch.<host>_color_mode`) und Status-LED (blau, `switch.<host>_status_led`; 4420 meldet keine).
  - Nur Schlafzimmer: **Rauschen** ein/aus (`switch.ing_sonoff_pt2_a574_noise`), Untermenü **Farbe**
    (`menu-submenu-select` auf `select.ing_sonoff_pt2_a574_noise_color`) und Untermenü **Lautstärke** (20, 40, 60, 80, 100,
    `number.set_value` auf `number.ing_sonoff_pt2_a574_noise_volume`). Siehe `Thingino/Sonoff-PT2/noise/`.
- **Zoom per Geste:** Zwei-Finger-Pinch am Handy, am PC Strg + Mausrad, danach verschieben.
- Nur die sichtbare Kamera streamt (`live.lazy_unload: [unselected, hidden]`).

## Einspielen

Dashboard bearbeiten → Ansicht hinzufügen → Raw-Konfigurationseditor, Inhalt von `view.yaml` einfügen.
Oder `cams_view.py` im HA-Container ausführen
(`docker exec -e T=$SUPERVISOR_TOKEN homeassistant python3 cams_view.py`), es ersetzt den Tab per Websocket.

## Offener Punkt: Ruckeln am PC (Stand 15.10.2026, nicht abschließend geklärt)

Schlafzimmer (a574) ruckelt im Chrome am PC: Uhr hängt, nur alle paar Sekunden ein Bild, „stalled“, Wechsel zwischen
HLS und WebRTC, grüne/verpixelte Artefakte. Stream bleibt vorerst unverändert (1080p, 3000 kbit/s).

- Kamera → HA ist sauber: über den lokalen go2rtc-RTSP dekodiert 14,6 fps, 1 Decodierfehler in 30 s; Pi 5 kaum ausgelastet.
- PC → HA: 1 Gbit/s Link ohne Fehler, aber nur ~50 Mbit/s Durchsatz (SSH und HTTP gleich), Ping unter Last 25 ms (max. 72).
- Ein Handy über den OG-Repeater (gleicher Switch wie der PC) schafft 300 Mbit/s → Engpass vermutlich am PC
  (USB-C-Dock / USB-Ethernet-Adapter / Sicherheitssoftware), nicht an der Hausverkabelung.
- Nächste Schritte, falls nötig: auf anderem Gerät gegentesten; dann Bitrate a574 auf 2000 kbit/s und GOP 15 probieren.
