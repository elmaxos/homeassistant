# Rauschen auf der Kamera (Stand 16.10.2026, in Arbeit)

Weißes, rosa oder braunes Rauschen in Endlosschleife über den Kamera-Lautsprecher. Läuft komplett auf der Kamera,
HA startet/stoppt nur per MQTT (`<hostname>/cmd`, Payload wird per `eval` ausgeführt). Eingerichtet auf `ing-sonoff-pt2-a574` (Schlafzimmer).

- `noise` → `/usr/sbin/noise` (Befehle: `start [vol]`, `stop`, `volume 0-100`, `color weiss|rosa|braun`, `boot`, `status`),
  dazu `/etc/init.d/S99noise` (`start) (sleep 20; /usr/sbin/noise boot) &`) und `/etc/noise.conf` (VOL=35, COLOR=braun).
- `noise_gen.py` (auf HA ausführen) erzeugt `/config/www/noise/rosa_<k>.pcm`/`braun_<k>.pcm`; benutzt werden nur die Stufe-7-Dateien,
  umbenannt in `rosa.pcm`/`braun.pcm` (60 s, 16 kHz, s16le mono, nahtlos). Weiß erzeugt die Kamera selbst (halbe Amplitude).
- `noise_discovery.py <hostname>` (auf HA, braucht `SUPERVISOR_TOKEN`) legt per MQTT-Discovery (retain) an:
  `switch.<host>_noise`, `number.<host>_noise_volume`, `select.<host>_noise_color`.

Erkenntnisse (prudynt-Version 2026-03):
- Eine laufende Wiedergabe lässt sich weder per `STOP` (weder `audio_out` noch `audio_out_ctrl`) noch per Audio-Thread-Neustart
  abbrechen; `vol=` bei PLAY wird ignoriert. Stopp = Lautsprecher sofort stumm (`spk_vol 0`) + prudynt-Neustart
  (leert die Warteschlange, Bild ~10 s weg, lädt die Ansage-Lautstärke aus `/etc/prudynt.json`).
- Lautstärke = `audio.spk_vol` live per `prudyntctl` **ohne** `restart_thread` (mit Neustart des Audio-Threads gab es Aussetzer).
- 5-s-Stücke statt einer Datei mit `loop=` schwankten und hatten Aussetzer → eine 60-s-Datei mit `loop=32`.
- **Aussetzer im Raum kamen vom Mikrofon-Encoder** (AAC 48 kHz, >90 % Frames verworfen): Mikrofon an a574 ausgeschaltet
  (`switch.ing_sonoff_pt2_a574_mic`), seitdem sauber.

Offen: „Stop Sound“ (`thingino-cmd play_stop`) nutzt noch das wirkungslose `play stop`; Einbindung in `install.ps1`.
