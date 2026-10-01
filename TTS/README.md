# TTS-Ansagen auf Thingino-Kameras

Es gibt nur noch ein Ansage-Skript: `tts_cam_sound_text`. Ziele sind die Kameras und das Handy (Option `handy`, Android-TTS, nur Text).
Die Automationen rufen es mit `kameras: [wohnzimmer, handy]` auf. Der frühere Verteiler `tts_an_alle_geraete` wurde entfernt.
Alte Varianten (`tts_kamera_3684`, `tts_kamera`, `tts_cam_sound`, `gong`, `thingino_tts_ansage` und die Test-Skripte) wurden am 29.09.2026 entfernt.

Sprachausgabe: Piper (HA-Add-on, Engine `tts.piper`) erzeugt eine MP3 -> `rest_command.thingino_tts`
holt die URL -> per MQTT bekommt die Kamera den Befehl `play '<url>'` (siehe Ordner `Thingino/`).

## Voraussetzungen (bei Neuaufbau)

1. Piper-Add-on installiert, TTS-Entity `tts.piper` vorhanden (Stimmen z. B. `de_DE-thorsten-low`).
2. Long-lived Access Token anlegen (Profil -> Sicherheit) und in `secrets.yaml` eintragen:
   `thingino_74_tts: "Bearer <token>"`
3. Block aus `configuration_rest_command.yaml` in `configuration.yaml` übernehmen (`rest_command:`).
4. Sound-Dateien nach `/config/www/sounds/` kopieren: `alarm_1.mp3`, `bell_1.mp3`, `notification_1.mp3`,
   `music_trap.mp3`, `21st_century_fox.mp3`, `12uhr.wav`, `14uhr.wav` (WAV: 16 Bit mono, sonst spielt prudynt nicht).
5. Kameras per `Thingino/Sonoff-PT2/install.ps1` einrichten (MQTT-Topic `<hostname>/cmd`).
6. Skripte aus `scripts/` in `scripts.yaml` einfügen, dann *Entwicklerwerkzeuge -> YAML -> Skripte neu laden*.

## Skripte

| Datei | Zweck |
|---|---|
| `tts_cam_sound_text.yaml` | Hauptskript: Sound und/oder Text auf einer oder mehreren Kameras. Felder: Nachricht, Kameras, Sound, Stimme, Pause nach Sound, Zweimal, Auf Anwesenheit warten, Licht einschalten. |
| `tts_test_4420.yaml` | Testaufruf für die Kamera 4420. |
| `tts_zeitansage.yaml` | Stündliche Zeitansage (nutzt das Hauptskript). |

Ziele im Hauptskript: `wohnzimmer` = `ing-sonoff-pt2-3684`, `kamera4420` = `ing-sonoff-pt2-4420`, `handy` = Android-TTS auf
`notify.mobile_app_sm_g781b` (nur der Text, kein Sound, kein Licht; Piper wird dafür nicht aufgerufen).
Neue Kamera: Eintrag mit `topic`, `licht` (Weißlicht-Switch) und optional `bewegung` ergänzen und die Option
in allen `kameras`-Selektoren nachziehen.

## Pausen

Nach dem Sound wartet das Skript `dauer` Sekunden, dann startet die Sprache. Weil `play` auf der Kamera
die Warteschlange leert, schneidet die Sprache den Sound ab, wenn `dauer` kürzer ist als der Sound.
Gemessene Längen: bell 7,4 s, alarm 9,8 s, notification 1,1 s, music_trap 41 s, 21st_century_fox 20,6 s, 12uhr 2,6 s.
Eingestellt (bewusst kurz): Gong 2, Klingel/Alarm/Hinweis 1,5, Music Trap 8, Fox 15, 12 Uhr 3.
Sprachdauer wird geschätzt: Zeichen / 13 + 2 s (die Kamera meldet kein Ende der Wiedergabe).
Alternative ohne Schätzung: `play -A '<url>'` hängt an die Warteschlange an, statt sie zu leeren.

## Handy: keine verspätete Ansage-Flut

Die Handy-Ansage wird mit `ttl: 0` und `priority: high` gesendet: Google (FCM) stellt sie sofort zu oder verwirft sie.
Ohne das speichert FCM Nachrichten, wenn das Handy im Schlafmodus oder offline ist, und liefert später alle auf einmal aus.
Stoppen einer laufenden Handy-Ansage: `message: command_stop_tts` an `notify.mobile_app_sm_g781b`.

## Bedienhinweis

„Licht einschalten“ hat Standard *an*; HA zeigt bei Ja/Nein-Feldern mit Standard *an* kein Häkchen.
Solange der Schalter nicht angefasst wird, gilt der Standard.
