# Schlafzimmer-Kamera – Tab im Testdashboard

Tab `Schlafzimmer` (`/dashboard-testdashboard/schlafzimmer-kamera`) für die Kamera SONOFF PT2 3
(`ing-sonoff-pt2-a574`). Konfiguration: [view.yaml](view.yaml).

## Voraussetzung

**Advanced Camera Card** über HACS (`dermotduffy/advanced-camera-card`). HACS trägt die Ressource
`/hacsfiles/advanced-camera-card/advanced-camera-card.js` selbst ein.

## Aufbau

- **Live-Bild** vom Hauptstream `camera.sonoff_pt2_3_profile_0` (1080p, damit digitaler Zoom scharf bleibt), 16:9.
- **PTZ-Steuerung** unten rechts im Bild:
  - Pfeile drücken die MQTT-Buttons `ptz_*_fast`. Gedrückt halten wiederholt den Schritt alle 0,4 s.
  - Die Richtungen sind wie im alten Tab `Kamera` vertauscht verdrahtet (links → `ptz_right_fast`, hoch → `ptz_down_fast`),
    weil die Kamera gedreht montiert ist.
  - **Zoom +/−** zoomt digital (die Kamera hat keinen optischen Zoom), solange die Taste gehalten wird.
  - Home/Presets: `Ansicht 1` (Preset 1, Home) und `Privat` (Preset 0).
- **Zoom per Geste:** Zwei-Finger-Pinch am Handy, am PC Strg + Mausrad. Danach mit einem Finger/der Maus verschieben.
- Darunter Kacheln für Position (Ansicht 1, Privat, Mitte, Privatsphäre) und Licht/Bild (Weißlicht, IR-Licht,
  Tag/Nacht, Status-LED).

## Einspielen

Dashboard bearbeiten → Ansicht hinzufügen → Raw-Konfigurationseditor, Inhalt von `view.yaml` einfügen.
