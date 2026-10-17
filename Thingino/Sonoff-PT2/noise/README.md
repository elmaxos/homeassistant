# Rauschen auf der Kamera (weiß / rosa / braun)

Endlos-Rauschen über den Kamera-Lautsprecher, z. B. zum Einschlafen. Läuft komplett auf der Kamera – HA startet/stoppt nur
per MQTT (`<hostname>/cmd`, Payload wird per `eval` ausgeführt). Hängt HA oder startet neu, läuft das Rauschen weiter.
Im Einsatz auf `ing-sonoff-pt2-a574` (Schlafzimmer). Der Installer (`../install.ps1`) spielt es auf jede neue Kamera.

## Dateien

| Datei | Ziel | Zweck |
|---|---|---|
| `noise` | `/usr/sbin/noise` | `start [vol]`, `stop`, `volume 0-80`, `color weiss\|rosa\|braun`, `fade_in 0-30`, `fade_out 0-30`, `boot`, `status` |
| – | `/etc/init.d/S99noise` | meldet 20 s nach dem Booten „aus“ + Lautstärke/Farbe an HA (legt der Installer an) |
| – | `/etc/noise.conf` | `VOL=35`, `COLOR=braun`, `FADE_IN=5`, `FADE_OUT=5` (zuletzt gewählt) |
| `noise_gen.py` | einmal auf HA ausführen | erzeugt `/config/www/noise/rosa.pcm` und `braun.pcm` (60 s, 16 kHz, s16le mono, nahtlos) |
| `noise_discovery.py` | nur für Kameras mit altem Discovery-Skript | legt die drei HA-Entitäten per Discovery an (`<host> <device-identifier>`) |

HA-Entitäten (vom Discovery-Skript `../thingino-ha-discovery.sh`, wenn `/usr/sbin/noise` existiert):
`switch.<host>_noise` (Rauschen), `number.<host>_noise_volume` (0–80, 10er-Schritte), `select.<host>_noise_color`,
`number.<host>_noise_fade_in` / `_noise_fade_out` (0–30 s).
„Stop Sound“ (`thingino-cmd play_stop`) beendet ein laufendes Rauschen ebenfalls.

## Wie es funktioniert (und warum so)

- **Abspielen:** 60 s Material in 2-s-Stücken, das Skript hängt immer ein Stück an (1 Stück Vorrat). Kein `loop=` von prudynt.
  rosa/braun lädt die Kamera einmal von HA (`http://<broker>:8123/local/noise/<farbe>.pcm`) nach `/tmp`, weiß erzeugt sie
  selbst aus `/dev/urandom` (halbe Amplitude, etwa so laut wie rosa/braun). Fallback ohne HA: weiß. Flash ist zu klein (~80 KB frei).
- **Lautstärke:** = Lautsprecher-Lautstärke `audio.spk_vol` (10er-Schritte, max. 80), jede Änderung wird über 1,5 s
  übergeblendet; live per `prudyntctl`, **ohne** `restart_thread`
  (mit Audio-Thread-Neustart gab es Aussetzer). Nicht gespeichert – die Ansage-Lautstärke in `/etc/prudynt.json` bleibt.
- **Ein-/Ausblenden:** Start beginnt bei 0 und blendet in 0,25-s-Schritten auf die Lautstärke (eine Änderung während
  des Einblendens wird übernommen). Stopp/Farbwechsel blenden erst aus, solange noch Stücke nachgeschoben werden.
- **Stopp / Farbwechsel:** nach dem Ausblenden stumm (`spk_vol 0`), dann **prudynt-Neustart** (Bild ~5–10 s weg). Der Neustart leert
  die Audio-Warteschlange und lädt die gespeicherte Ansage-Lautstärke.
- **Überblendung** am Dateiende mit konstanter Leistung (sin/cos). Linear gab alle 60 s eine hörbare Delle (~3 dB).

- **„start“ bei laufendem Rauschen** passt nur die Lautstärke an (kein Neustart). Keine eigene Sperre: der MQTT-Dispatcher
  arbeitet Befehle nacheinander ab; eine `mkdir`-Sperre mit EXIT-`trap` wurde unter dem Dispatcher nicht freigegeben
  (jeder Befehl wartete 40 s – das war die Verzögerung/das „erst leise, dann aus, dann einblenden“).

## Erkenntnisse zu prudynt (Version 2026-03), alle per Hörtest im Raum geprüft

- `STOP` (an `audio_out` wie `play stop`, oder an `audio_out_ctrl`), ein PLAY ohne `append` („Ersetzen“) und
  `restart_thread 4` beenden eine **laufende lange** Wiedergabe nicht zuverlässig. prudynt schiebt Dateien blockierend
  (`AudioOutputWorker::enqueuePcmBlocking`) in einen kleinen Puffer; `STOP` leert nur den Puffer (`clearQueue`).
  Bei `loop=` kommt nach `STOP` die nächste Wiederholung, bei Stücken/Farbwechseln blieben Reste hängen. Kurze
  Einzel-Sounds (Opus, TTS) lassen sich dagegen stoppen. Sicher stoppt nur ein prudynt-Neustart.
- `vol=` im PLAY-Befehl wird ignoriert.
- **Mikrofon aus!** Der AAC-Mikrofon-Encoder (48 kHz) verwirft >90 % seiner Frames („sink clogged“) und verursacht
  Aussetzer in der Wiedergabe. Mit ausgeschaltetem Mikrofon (HA-Schalter „Mic“) läuft das Rauschen sauber.
